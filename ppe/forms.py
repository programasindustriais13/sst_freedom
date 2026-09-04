from django import forms
from .models import Product, PPEMatrix, ProductVariant, PPEDelivery, SectorPPEMatrix
from organizations.models import Function, Sector
from .constants import (
    UNIDADE_MEDIDA_CHOICES, UNIDADE_MEDIDA_PADRAO, normalize_unit_of_measure,
    CANONICAL_SIZES_BY_GROUP, ALL_CANONICAL_SIZES, TAMANHO_UNICO
)
from .services import canonical_size_key, normalize_size_string

class ProductForm(forms.ModelForm):
    unidade_medida = forms.ChoiceField(
        choices=Product.UNIDADE_MEDIDA_CHOICES,
        label="Como este EPI será contado no estoque?",
        initial=UNIDADE_MEDIDA_PADRAO,
        widget=forms.Select(attrs={'class': 'form-select form-control-premium'})
    )
    tem_variacao_tamanho = forms.ChoiceField(
        choices=[('nao', 'Não — Tamanho único'), ('sim', 'Sim — Possui tamanhos')],
        required=False,
        initial='nao'
    )
    tamanhos_str = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Product
        fields = [
            'nome', 'tipo_produto', 'categoria', 'ca_numero', 
            'descricao', 'unidade_medida', 'fabricante', 
            'exige_ca', 'controlado_individualmente', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Ex: Respirador PFF2'}),
            'categoria': forms.Select(attrs={'class': 'form-select form-control-premium'}),
            'fabricante': forms.TextInput(attrs={'class': 'form-control form-control-premium', 'placeholder': 'Ex: 3M'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control form-control-premium', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            active_vars = self.instance.variants.filter(ativo=True)
            non_unique = [v.tamanho for v in active_vars if v.tamanho != 'U']
            if non_unique:
                self.initial['tem_variacao_tamanho'] = 'sim'
                self.initial['tamanhos_str'] = ", ".join(non_unique)
            else:
                self.initial['tem_variacao_tamanho'] = 'nao'
                self.initial['tamanhos_str'] = 'U'
        else:
            self.initial.setdefault('tem_variacao_tamanho', 'nao')
            self.initial.setdefault('unidade_medida', UNIDADE_MEDIDA_PADRAO)

    def clean(self):
        import logging
        logger = logging.getLogger('ppe.forms')
        
        cleaned_data = super().clean()
        tipo_produto = cleaned_data.get('tipo_produto')
        ca_numero = cleaned_data.get('ca_numero')

        # 1. Validação da Unidade de Medida
        raw_um = cleaned_data.get('unidade_medida') or self.data.get('unidade_medida')
        um_norm = normalize_unit_of_measure(raw_um)
        valid_ums = [c[0] for c in Product.UNIDADE_MEDIDA_CHOICES]
        if um_norm not in valid_ums:
            self.add_error('unidade_medida', "Unidade de medida inválida.")
        else:
            cleaned_data['unidade_medida'] = um_norm

        # Extrai tamanhos enviados via checkboxes ('tamanhos') ou 'tamanhos_str'
        if hasattr(self.data, 'getlist'):
            raw_tamanhos = self.data.getlist('tamanhos')
        else:
            val = self.data.get('tamanhos')
            raw_tamanhos = val if isinstance(val, list) else ([val] if val else [])
            
        if not raw_tamanhos:
            ts_val = self.data.get('tamanhos_str') or cleaned_data.get('tamanhos_str') or ''
            if ts_val:
                raw_tamanhos = [t.strip() for t in ts_val.split(',') if t.strip()]

        # 2. Validação da Variação de Tamanho
        tem_var = self.data.get('tem_variacao_tamanho') or cleaned_data.get('tem_variacao_tamanho')
        if not tem_var:
            if raw_tamanhos and any(t.upper() not in ('U', 'UNICO', 'ÚNICO') for t in raw_tamanhos):
                tem_var = 'sim'
            else:
                tem_var = 'nao'
        cleaned_data['tem_variacao_tamanho'] = tem_var

        if tem_var == 'nao':
            # Tamanho único
            outros_tamanhos = [t for t in raw_tamanhos if t.upper() not in ('U', 'UNICO', 'ÚNICO')]
            if outros_tamanhos:
                self.add_error('tem_variacao_tamanho', "A opção 'Único' não pode ser utilizada junto com outros tamanhos.")
                self.add_error('tamanhos_str', "A opção 'Único' não pode ser utilizada junto com outros tamanhos.")
            cleaned_data['tamanhos_list'] = ['U']
            cleaned_data['tamanhos_str'] = 'U'
        else:
            # Possui tamanhos
            tamanhos_sem_u = [t for t in raw_tamanhos if t.upper() not in ('U', 'UNICO', 'ÚNICO')]
            tem_u = any(t.upper() in ('U', 'UNICO', 'ÚNICO') for t in raw_tamanhos)
            if tem_u:
                self.add_error('tem_variacao_tamanho', "A opção 'Único' não pode ser utilizada junto com outros tamanhos.")
                self.add_error('tamanhos_str', "A opção 'Único' não pode ser utilizada junto com outros tamanhos.")
            if not tamanhos_sem_u:
                self.add_error('tem_variacao_tamanho', "Selecione pelo menos um tamanho para este EPI.")
                self.add_error('tamanhos_str', "Selecione pelo menos um tamanho para este EPI.")

            # Validação contra o catálogo canônico
            invalid_sizes = []
            for s in tamanhos_sem_u:
                s_key = canonical_size_key(s)
                if s_key not in ALL_CANONICAL_SIZES:
                    invalid_sizes.append(s)
            if invalid_sizes:
                err_msg = f"O tamanho '{invalid_sizes[0]}' não pertence ao catálogo permitido."
                self.add_error('tem_variacao_tamanho', err_msg)
                self.add_error('tamanhos_str', err_msg)

            normalized_list = normalize_size_string(tamanhos_sem_u)
            cleaned_data['tamanhos_list'] = normalized_list
            cleaned_data['tamanhos_str'] = ", ".join(normalized_list)

        # 3. Validação do C.A.
        if tipo_produto == 'EPI':
            if ca_numero:
                # Normaliza o número do CA (apenas dígitos)
                num_norm = "".join([c for c in str(ca_numero) if c.isdigit()])
                cleaned_data['ca_numero'] = num_norm if num_norm else None
                
                # Validação de duplicidade de CA no nível de aplicação
                if num_norm:
                    dup_qs = Product.objects.filter(ca_numero=num_norm)
                    if self.instance and self.instance.pk:
                        dup_qs = dup_qs.exclude(pk=self.instance.pk)
                    
                    existing_epi = dup_qs.first()
                    if existing_epi:
                        tamanhos_existentes = ", ".join([v.tamanho for v in existing_epi.variants.filter(ativo=True)]) or "Nenhum"
                        self.add_error(
                            'ca_numero',
                            f"Este C.A. já está cadastrado no sistema. Já existe um EPI cadastrado com o CA {num_norm}.\n"
                            f"EPI: {existing_epi.nome}\n"
                            f"Tamanhos atuais: {tamanhos_existentes}\n"
                            f"Para incluir outro tamanho, edite o cadastro existente. Não crie um novo EPI para cada tamanho."
                        )
                
                # Tenta obter ou consultar do ConsultaCA no backend para persistir snapshot
                try:
                    from .ca_services import ConsultaCAService
                    result = ConsultaCAService.get_or_query(num_norm)
                    
                    if result.get('success'):
                        if result.get('found'):
                            # Auto-preenche fabricante se estiver em branco
                            if not cleaned_data.get('fabricante'):
                                cleaned_data['fabricante'] = result.get('nome_fantasia') or result.get('fabricante')
                        else:
                            logger.info(f"CA {num_norm} não encontrado. Cadastro mantido como não confirmado pela consulta.")
                    elif result.get('indisponivel'):
                        logger.warning(f"ConsultaCA indisponível durante salvamento de EPI com CA {num_norm}. Salvamento permitido.")
                except Exception as e:
                    logger.warning(f"Erro ao consultar/atualizar cache do CA no salvamento do formulário: {str(e)}")
            else:
                self.add_error('ca_numero', "Número do C.A. é obrigatório para produtos do tipo EPI.")
        else:
            # Se não for EPI, limpa o C.A. e categoria de proteção
            cleaned_data['ca_numero'] = None
            cleaned_data['categoria'] = 'OUTRO'
            cleaned_data['exige_ca'] = False
        
        return cleaned_data



class PPEMatrixForm(forms.ModelForm):
    class Meta:
        model = PPEMatrix
        fields = [
            'product', 'variant', 'obrigatorio', 'principal', 
            'quantidade_padrao', 'vida_util_dias', 'prazo_troca_preventiva', 
            'orientacoes', 'ativo'
        ]

    def __init__(self, *args, **kwargs):
        self.funcao = kwargs.pop('funcao', None)
        self.setor = kwargs.pop('setor', None)
        super().__init__(*args, **kwargs)
        # Filtra apenas produtos do tipo EPI e que estão ativos
        self.fields['product'].queryset = Product.objects.filter(tipo_produto='EPI', ativo=True).order_by('nome')
        # Filtra variantes ativas
        self.fields['variant'].queryset = ProductVariant.objects.filter(ativo=True).select_related('product').order_by('product__nome', 'tamanho')
        self.fields['variant'].required = False

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        variant = cleaned_data.get('variant')

        # Valida se a variante pertence ao produto selecionado
        if variant and product and variant.product != product:
            self.add_error('variant', "A variante/tamanho selecionada não pertence ao EPI escolhido.")

        # Valida restrição de unicidade para setor
        if self.setor and product:
            exists_query = PPEMatrix.objects.filter(setor=self.setor, product=product, ativo=True)
            if self.instance and self.instance.pk:
                exists_query = exists_query.exclude(pk=self.instance.pk)
            if exists_query.exists():
                self.add_error('product', f"Este EPI já está cadastrado na matriz de recomendação do setor {self.setor.nome}.")

        # Valida restrição de unicidade para funcao
        if self.funcao and product:
            exists_query = PPEMatrix.objects.filter(funcao=self.funcao, product=product, ativo=True)
            if self.instance and self.instance.pk:
                exists_query = exists_query.exclude(pk=self.instance.pk)
            if exists_query.exists():
                self.add_error('product', "Este EPI já está cadastrado na matriz de recomendação para esta função.")

        return cleaned_data


class PPEMatrixItemForm(forms.ModelForm):
    class Meta:
        model = PPEMatrix
        fields = ['product', 'quantidade_padrao', 'vida_util_dias', 'obrigatorio', 'principal']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-select form-control-premium ppe-product-select searchable-select',
                'data-search-url': '/ppe/api/search/',
                'data-placeholder': 'Selecione ou pesquise o EPI...'
            }),
            'quantidade_padrao': forms.NumberInput(attrs={'class': 'form-control form-control-premium', 'min': '1', 'placeholder': 'Qtd'}),
            'vida_util_dias': forms.NumberInput(attrs={'class': 'form-control form-control-premium', 'min': '1', 'placeholder': 'Dias'}),
            'obrigatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'principal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'product': 'EPI',
            'quantidade_padrao': 'Quantidade Padrão',
            'vida_util_dias': 'Vida útil estimada (dias)',
            'obrigatorio': 'Obrigatório',
            'principal': 'EPI Principal',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(tipo_produto='EPI', ativo=True).order_by('nome')
        if not self.instance or not self.instance.pk:
            self.fields['quantidade_padrao'].initial = 1
            self.fields['vida_util_dias'].initial = 365
            self.fields['obrigatorio'].initial = True
            self.fields['principal'].initial = True

    def clean_quantidade_padrao(self):
        qtd = self.cleaned_data.get('quantidade_padrao')
        if qtd is None or qtd <= 0:
            raise forms.ValidationError("A quantidade padrão deve ser um número inteiro positivo maior que zero.")
        return qtd

    def clean_vida_util_dias(self):
        vud = self.cleaned_data.get('vida_util_dias')
        if vud is None or vud <= 0:
            raise forms.ValidationError("A vida útil deve ser um número inteiro positivo maior que zero.")
        return vud


class BasePPEMatrixFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        
        products_seen = set()
        active_count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                product = form.cleaned_data.get('product')
                if product:
                    active_count += 1
                    if product.id in products_seen:
                        form.add_error('product', f"O EPI '{product.nome}' foi incluído mais de uma vez nesta função.")
                    else:
                        products_seen.add(product.id)
        if active_count == 0:
            raise forms.ValidationError("Adicione pelo menos um EPI recomendado para a matriz da função.")


PPEMatrixFormSet = forms.inlineformset_factory(
    Function,
    PPEMatrix,
    form=PPEMatrixItemForm,
    formset=BasePPEMatrixFormSet,
    fk_name='funcao',
    extra=1,
    can_delete=True
)


class BasePPEMatrixSectorFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        
        products_seen = set()
        active_count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                product = form.cleaned_data.get('product')
                if product:
                    active_count += 1
                    if product.id in products_seen:
                        form.add_error('product', f"O EPI '{product.nome}' foi incluído mais de uma vez neste setor.")
                    else:
                        products_seen.add(product.id)
        if active_count == 0:
            raise forms.ValidationError("Adicione pelo menos um EPI recomendado para a matriz do setor.")


PPEMatrixSectorFormSet = forms.inlineformset_factory(
    Sector,
    PPEMatrix,
    form=PPEMatrixItemForm,
    formset=BasePPEMatrixSectorFormSet,
    fk_name='setor',
    extra=1,
    can_delete=True
)


class PPEMatrixSectorChoiceForm(forms.Form):
    setor = forms.ModelChoiceField(
        queryset=None,
        label="Setor",
        widget=forms.Select(attrs={'class': 'form-select form-control-premium'})
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Sector.objects.filter(ativo=True).select_related('unit', 'unit__company').order_by('unit__company__nome_fantasia', 'unit__codigo', 'nome')
        if user and not user.is_superuser:
            qs = qs.filter(unit__in=user.units.all())
        self.fields['setor'].queryset = qs


class PPEMatrixFunctionForm(forms.Form):
    funcao = forms.ModelChoiceField(
        queryset=None,
        label="Função/Cargo",
        widget=forms.Select(attrs={'class': 'form-select form-control-premium'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from organizations.models import Function
        self.fields['funcao'].queryset = Function.objects.filter(ativo=True).order_by('nome')



class PPEMatrixBulkForm(forms.Form):
    funcao = forms.ModelChoiceField(
        queryset=None,
        label="Função/Cargo",
        widget=forms.Select(attrs={'class': 'form-select form-control-premium'})
    )
    products = forms.ModelMultipleChoiceField(
        queryset=None,
        label="EPIs Recomendados",
        widget=forms.CheckboxSelectMultiple(),
        required=True
    )
    quantidade_padrao = forms.IntegerField(
        initial=1,
        min_value=1,
        label="Quantidade Padrão",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-premium'})
    )
    vida_util_dias = forms.IntegerField(
        initial=365,
        min_value=1,
        label="Vida Útil Padrão (Dias)",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-premium'})
    )
    obrigatorio = forms.BooleanField(
        initial=True,
        required=False,
        label="Obrigatório",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    principal = forms.BooleanField(
        initial=True,
        required=False,
        label="EPI Principal da Função",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    orientacoes = forms.CharField(
        required=False,
        label="Orientações e Instruções de Uso",
        widget=forms.Textarea(attrs={'class': 'form-control form-control-premium', 'rows': 4})
    )

    def __init__(self, *args, **kwargs):
        self.is_update = kwargs.pop('is_update', False)
        super().__init__(*args, **kwargs)
        from organizations.models import Function
        self.fields['funcao'].queryset = Function.objects.filter(ativo=True).order_by('nome')
        self.fields['products'].queryset = Product.objects.filter(tipo_produto='EPI', ativo=True).order_by('nome')
        
        if self.is_update:
            self.fields['funcao'].disabled = True
            self.fields['funcao'].required = False


class PPEDeliveryForm(forms.ModelForm):
    class Meta:
        model = PPEDelivery
        fields = ['employee', 'lot', 'quantidade', 'data_entrega', 'natureza_entrega', 'motivo_substituicao', 'product_variant']
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'form-select form-control-premium searchable-select',
                'data-search-url': '/employees/api/search/',
                'data-placeholder': 'Selecione o trabalhador...'
            }),
            'lot': forms.Select(attrs={
                'class': 'form-select form-control-premium searchable-select',
                'data-placeholder': 'Selecione o EPI disponível no estoque SST...'
            }),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control form-control-premium', 'min': '1'}),
            'data_entrega': forms.DateInput(attrs={'class': 'form-control form-control-premium', 'type': 'date'}),
            'natureza_entrega': forms.Select(attrs={'class': 'form-select form-control-premium'}),
            'motivo_substituicao': forms.Textarea(attrs={'class': 'form-control form-control-premium', 'rows': 3}),
            'product_variant': forms.HiddenInput(),
        }
        labels = {
            'employee': 'Colaborador / Beneficiário',
            'lot': 'EPI disponível no estoque SST',
            'quantidade': 'Quantidade Entregue',
            'data_entrega': 'Data da Entrega',
            'natureza_entrega': 'Natureza da Entrega',
            'motivo_substituicao': 'Justificativa / Motivo de Substituição / Observações',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product_variant'].required = False

    def clean(self):
        cleaned_data = super().clean()
        lot = cleaned_data.get('lot')
        pv_provided = cleaned_data.get('product_variant')
        quantidade = cleaned_data.get('quantidade')

        if not lot:
            self.add_error('lot', "Selecione um EPI disponível no estoque SST.")
            return cleaned_data

        # Determina/vincula a variante automaticamente a partir do lote
        expected_variant = lot.product_variant
        if pv_provided and pv_provided != expected_variant:
            self.add_error('lot', "O lote selecionado não pertence ao EPI ou tamanho informado.")
            return cleaned_data

        cleaned_data['product_variant'] = expected_variant

        # Validação de saldo no backend
        from inventory.services import get_stock_balance
        from organizations.models import InventoryLocation
        
        employee = cleaned_data.get('employee')
        if employee and quantidade:
            loc_sst = InventoryLocation.objects.filter(unit=employee.unit, tipo='SST', ativo=True).first()
            if loc_sst:
                bal = get_stock_balance(loc_sst, expected_variant, lot)
                if bal <= 0:
                    self.add_error('lot', "O lote selecionado não possui saldo disponível no estoque SST.")
                elif quantidade > bal:
                    self.add_error('quantidade', f"A quantidade informada ({quantidade}) é maior que o saldo disponível neste lote ({bal}).")

        return cleaned_data



