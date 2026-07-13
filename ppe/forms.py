from django import forms
from .models import Product, PPEMatrix, ProductVariant

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'nome', 'tipo_produto', 'categoria', 'ca_numero', 
            'descricao', 'unidade_medida', 'fabricante', 
            'exige_ca', 'controlado_individualmente', 'ativo'
        ]

    def clean(self):
        cleaned_data = super().clean()
        tipo_produto = cleaned_data.get('tipo_produto')
        ca_numero = cleaned_data.get('ca_numero')

        if tipo_produto == 'EPI':
            # Validação opcional de C.A., mas mostraremos aviso no template se estiver vazio
            pass
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


