from django import forms
from .models import Product, PPEMatrix, ProductVariant, PPEDelivery
from organizations.models import Function

class ProductForm(forms.ModelForm):
    tamanhos_str = forms.CharField(
        required=False,
        label="Tamanhos / Variantes Disponíveis (separados por vírgula)",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-premium',
            'placeholder': 'Ex: P, M, G, GG ou 38, 39, 40 ou Único (deixe em branco para Único \'U\')'
        })
    )

    class Meta:
        model = Product
        fields = [
            'nome', 'tipo_produto', 'categoria', 'ca_numero', 
            'descricao', 'unidade_medida', 'fabricante', 
            'exige_ca', 'controlado_individualmente', 'ativo'
        ]

    def clean(self):
        import logging
        logger = logging.getLogger('ppe.forms')
        
        cleaned_data = super().clean()
        tipo_produto = cleaned_data.get('tipo_produto')
        ca_numero = cleaned_data.get('ca_numero')

        if tipo_produto == 'EPI':
            if ca_numero:
                # Normaliza o número do CA (apenas dígitos)
                num_norm = "".join([c for c in str(ca_numero) if c.isdigit()])
                cleaned_data['ca_numero'] = num_norm
                
                # Validação de duplicidade de CA no nível de aplicação (SPEC 1 - Objetivo 5)
                if num_norm:
                    dup_qs = Product.objects.filter(tipo_produto='EPI', ca_numero=num_norm)
                    if self.instance and self.instance.pk:
                        dup_qs = dup_qs.exclude(pk=self.instance.pk)
                    
                    existing_epi = dup_qs.first()
                    if existing_epi:
                        self.add_error(
                            'ca_numero',
                            f"Já existe um EPI cadastrado com o CA {num_norm}. Abra o cadastro existente para adicionar ou editar os tamanhos disponíveis."
                        )
                
                # Tenta obter ou consultar do ConsultaCA no backend para persistir snapshot
                try:
                    from .ca_services import ConsultaCAService
                    result = ConsultaCAService.get_or_query(num_norm)
                    
                    if result.get('success'):
                        if result.get('found'):
                            # Auto-preenche fabricante se estiver em branco, usando o nome oficial/fantasia
                            if not cleaned_data.get('fabricante'):
                                cleaned_data['fabricante'] = result.get('nome_fantasia') or result.get('fabricante')
                        else:
                            # Se não foi encontrado, mas o fluxo manual é permitido, o salvamento prossegue.
                            # O registro correspondente em CertificadoAprovacao já terá status_verificacao='NAO_ENCONTRADO'.
                            logger.info(f"CA {num_norm} não encontrado. Cadastro mantido como não confirmado pela consulta.")
                    elif result.get('indisponivel'):
                        # Se indisponível, permite salvar normalmente para não bloquear a operação
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

        # Valida restrição de unicidade (funcao + product) para evitar IntegrityError
        if self.funcao and product:
            exists_query = PPEMatrix.objects.filter(funcao=self.funcao, product=product)
            if self.instance and self.instance.pk:
                exists_query = exists_query.exclude(pk=self.instance.pk)
            if exists_query.exists():
                self.add_error('product', "Este EPI já está cadastrado na matriz de recomendação para esta função.")

        return cleaned_data


class PPEMatrixItemForm(forms.ModelForm):
    class Meta:
        model = PPEMatrix
        fields = ['product', 'vida_util_dias', 'obrigatorio', 'principal']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select form-control-premium ppe-product-select'}),
            'vida_util_dias': forms.NumberInput(attrs={'class': 'form-control form-control-premium', 'min': '1', 'placeholder': 'Dias'}),
            'obrigatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'principal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'product': 'EPI',
            'vida_util_dias': 'Vida útil estimada (dias)',
            'obrigatorio': 'Obrigatório',
            'principal': 'EPI principal da função',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(tipo_produto='EPI', ativo=True).order_by('nome')
        if not self.instance or not self.instance.pk:
            self.fields['vida_util_dias'].initial = 365
            self.fields['obrigatorio'].initial = True
            self.fields['principal'].initial = True

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
    extra=1,
    can_delete=True
)


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
            'employee': forms.Select(attrs={'class': 'form-select form-control-premium'}),
            'lot': forms.Select(attrs={'class': 'form-select form-control-premium'}),
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



