import re
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from organizations.models import Company, Unit, Sector, CostCenter, Function

def validate_cpf(value):
    # normaliza apenas digitos
    cpf = "".join(re.findall(r"\d", str(value)))
    if len(cpf) != 11:
        raise ValidationError("O CPF deve conter exatamente 11 dígitos.")
    
    # validação de dígitos repetidos
    if cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido. Sequência de dígitos repetidos não é permitida.")
        
    # validação de dígitos verificadores (módulo 11)
    for i in range(9, 11):
        value_sum = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        digit = ((value_sum * 10) % 11) % 10
        if digit != int(cpf[i]):
            raise ValidationError("CPF inválido. Os dígitos verificadores informados não conferem.")

class Employee(models.Model):
    SITUACAO_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('AFASTADO', 'Afastado'),
        ('DESLIGADO', 'Desligado'),
    )

    TURNO_CHOICES = (
        ('TURNO_1', '1º Turno'),
        ('TURNO_2', '2º Turno'),
        ('TURNO_3', '3º Turno'),
        ('ADM', 'Administrativo'),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='employees', verbose_name="Empresa")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='employees', verbose_name="Unidade")
    matricula = models.CharField(max_length=50, verbose_name="Matrícula")
    nome_completo = models.CharField(max_length=255, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, unique=True, validators=[validate_cpf], verbose_name="CPF")
    
    funcao = models.ForeignKey(Function, on_delete=models.PROTECT, related_name='employees', verbose_name="Função/Cargo")
    setor = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name='employees', verbose_name="Setor")
    centro_custo = models.ForeignKey(CostCenter, on_delete=models.PROTECT, related_name='employees', verbose_name="Centro de Custo")
    
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES, default='ADM', verbose_name="Turno")
    data_admissao = models.DateField(verbose_name="Data de Admissão")
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default='ATIVO', verbose_name="Situação Cadastral")
    data_desligamento = models.DateField(blank=True, null=True, verbose_name="Data de Desligamento")
    
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")
    
    # Tamanhos corporativos
    tamanho_camisa = models.CharField(max_length=10, blank=True, null=True, verbose_name="Tamanho da Camisa")
    tamanho_calca = models.CharField(max_length=10, blank=True, null=True, verbose_name="Tamanho da Calça")
    num_calcado = models.IntegerField(blank=True, null=True, verbose_name="Numeração do Calçado")
    tamanho_luva = models.CharField(max_length=10, blank=True, null=True, verbose_name="Tamanho da Luva")
    modelo_farda = models.CharField(max_length=100, blank=True, null=True, verbose_name="Modelo de Farda")
    
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações Operacionais")
    
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_employees', verbose_name="Criado por")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
        unique_together = ('company', 'matricula')

    def __str__(self):
        return f"{self.matricula} - {self.nome_completo}"

    def clean(self):
        # Normalização do CPF
        if self.cpf:
            self.cpf = "".join(re.findall(r"\d", str(self.cpf)))
            # Formata como 000.000.000-00 para exibição
            if len(self.cpf) == 11:
                self.cpf = f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"

        if self.situacao == 'DESLIGADO' and not self.data_desligamento:
            raise ValidationError({"data_desligamento": "A data de desligamento é obrigatória para colaboradores desligados."})


class EmployeeHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='history', verbose_name="Colaborador")
    funcao = models.ForeignKey(Function, on_delete=models.PROTECT, verbose_name="Função/Cargo")
    setor = models.ForeignKey(Sector, on_delete=models.PROTECT, verbose_name="Setor")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Unidade")
    centro_custo = models.ForeignKey(CostCenter, on_delete=models.PROTECT, verbose_name="Centro de Custo")
    
    data_inicio = models.DateTimeField(auto_now_add=True, verbose_name="Data de Início")
    data_fim = models.DateTimeField(blank=True, null=True, verbose_name="Data de Fim")
    
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Alterado por")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Histórico de Colaborador"
        verbose_name_plural = "Históricos de Colaboradores"
        ordering = ['-data_inicio']

    def __str__(self):
        return f"{self.employee.nome_completo} - {self.funcao.nome} em {self.data_inicio.strftime('%d/%m/%Y')}"
