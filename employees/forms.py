import re
from django import forms
from django.db.models import Q
from .models import Employee, validate_cpf

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'company', 'unit', 'matricula', 'nome_completo', 'cpf',
            'funcao', 'setor', 'centro_custo', 'turno', 'data_admissao',
            'situacao', 'data_desligamento', 'telefone', 'email',
            'tamanho_camisa', 'tamanho_calca', 'num_calcado',
            'tamanho_luva', 'modelo_farda', 'observacoes'
        ]

    def clean_cpf(self):
        cpf_raw = self.cleaned_data.get('cpf', '')
        if not cpf_raw:
            return cpf_raw
        
        # Remove todos os caracteres não numéricos
        cpf_digits = "".join(re.findall(r"\d", str(cpf_raw)))
        
        # Executa validação de formato/dígitos
        validate_cpf(cpf_digits)
        
        # Formata canonicamente como 000.000.000-00
        cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
        
        # Verifica duplicidade em ambas as formas (com e sem máscara)
        query = Employee.objects.filter(Q(cpf=cpf_digits) | Q(cpf=cpf_formatted))
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
            
        if query.exists():
            raise forms.ValidationError("Já existe um colaborador cadastrado com este CPF.")
            
        return cpf_formatted
