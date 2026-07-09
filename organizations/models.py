from django.db import models

class Company(models.Model):
    razao_social = models.CharField(max_length=255, verbose_name="Razão Social")
    nome_fantasia = models.CharField(max_length=255, verbose_name="Nome Fantasia")
    cnpj = models.CharField(max_length=18, unique=True, verbose_name="CNPJ")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.nome_fantasia


class Unit(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='units', verbose_name="Empresa")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código da Unidade")
    nome = models.CharField(max_length=255, verbose_name="Nome da Unidade")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="UF")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Sector(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='sectors', verbose_name="Unidade")
    nome = models.CharField(max_length=255, verbose_name="Nome do Setor")
    codigo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código do Setor")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        unique_together = ('unit', 'nome')

    def __str__(self):
        return f"{self.nome} ({self.unit.codigo})"


class CostCenter(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='cost_centers', verbose_name="Empresa")
    codigo = models.CharField(max_length=50, verbose_name="Código do Centro de Custo")
    nome = models.CharField(max_length=255, verbose_name="Nome")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Centro de Custo"
        verbose_name_plural = "Centros de Custo"
        unique_together = ('company', 'codigo')

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Function(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='functions', verbose_name="Empresa")
    nome = models.CharField(max_length=255, verbose_name="Nome da Função/Cargo")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Função/Cargo"
        verbose_name_plural = "Funções/Cargos"
        unique_together = ('company', 'nome')

    def __str__(self):
        return self.nome


class InventoryLocation(models.Model):
    ALMOXARIFADO = 'ALMOXARIFADO'
    SST = 'SST'
    OUTRO = 'OUTRO'

    TIPO_CHOICES = (
        (ALMOXARIFADO, 'Almoxarifado'),
        (SST, 'Estoque SST'),
        (OUTRO, 'Outro'),
    )

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='inventory_locations', verbose_name="Unidade")
    codigo = models.CharField(max_length=50, verbose_name="Código do Local")
    nome = models.CharField(max_length=255, verbose_name="Nome do Local")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=ALMOXARIFADO, verbose_name="Tipo de Local")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Local de Estoque"
        verbose_name_plural = "Locais de Estoque"
        unique_together = ('unit', 'codigo')

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()}) - {self.unit.codigo}"
