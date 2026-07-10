from django import forms
from .models import Product

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
