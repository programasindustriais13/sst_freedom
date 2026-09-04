import re
from django import forms
from django.conf import settings
from django.db.models import Q
from .models import Employee, validate_cpf
from organizations.models import Sector, Unit

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'company', 'nome_completo', 'cpf',
            'setor', 'centro_custo', 'turno',
            'situacao', 'data_desligamento',
            'tamanho_camisa', 'tamanho_calca', 'num_calcado',
            'tamanho_luva', 'modelo_farda', 'observacoes'
        ]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Filtra setores disponíveis se usuário restrito for fornecido
        if self.user and not self.user.is_superuser:
            user_units = self.user.units.all()
            self.fields['setor'].queryset = Sector.objects.filter(unit__in=user_units).select_related('unit', 'unit__company')
            from organizations.models import Company
            self.fields['company'].queryset = Company.objects.filter(ativo=True, units__in=user_units).distinct()
        else:
            self.fields['setor'].queryset = Sector.objects.all().select_related('unit', 'unit__company')

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

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get('company')
        setor = cleaned_data.get('setor')

        if setor:
            # 1. Valida que o Setor pertence à Empresa selecionada
            if company and setor.unit.company != company:
                self.add_error('setor', f"O Setor '{setor.nome}' pertence à empresa '{setor.unit.company.nome_fantasia}', que difere da empresa selecionada.")
            
            # 2. Valida se o usuário tem permissão na Unidade do Setor
            if self.user and not self.user.is_superuser:
                if not self.user.units.filter(id=setor.unit_id).exists():
                    self.add_error('setor', f"Você não possui permissão de acesso à Unidade '{setor.unit.nome}' vinculada a este setor.")

            # 3. Derivação automática da Unidade exclusivamente pelo setor
            cleaned_data['unit'] = setor.unit

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Unidade derivada exclusivamente do setor
        if 'setor' in self.cleaned_data and self.cleaned_data['setor']:
            instance.unit = self.cleaned_data['setor'].unit

        # Preserva campos legados caso esteja editando colaborador existente
        if self.instance and self.instance.pk:
            try:
                old_instance = Employee.objects.get(pk=self.instance.pk)
                instance.funcao = old_instance.funcao
                instance.matricula = old_instance.matricula
                instance.data_admissao = old_instance.data_admissao
                instance.telefone = old_instance.telefone
                instance.email = old_instance.email
            except Employee.DoesNotExist:
                pass
        else:
            # Novo colaborador: campos legados nulos sem valores artificiais
            instance.funcao = None
            instance.matricula = None
            instance.data_admissao = None
            instance.telefone = None
            instance.email = None

        if commit:
            instance.save()
        return instance

