from django.contrib import admin
from .models import Company, Unit, Sector, CostCenter, Function, InventoryLocation

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['nome_fantasia', 'razao_social', 'cnpj', 'ativo']
    search_fields = ['nome_fantasia', 'razao_social', 'cnpj']
    list_filter = ['ativo']
    ordering = ['nome_fantasia']

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'company', 'cidade', 'estado', 'ativo']
    search_fields = ['codigo', 'nome', 'cidade']
    list_filter = ['company', 'ativo', 'estado']
    ordering = ['codigo']

@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'unit', 'ativo']
    search_fields = ['nome', 'codigo']
    list_filter = ['unit', 'ativo']
    ordering = ['unit', 'nome']

@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'company', 'ativo']
    search_fields = ['codigo', 'nome']
    list_filter = ['company', 'ativo']
    ordering = ['company', 'codigo']

@admin.register(Function)
class FunctionAdmin(admin.ModelAdmin):
    list_display = ['nome', 'company', 'ativo']
    search_fields = ['nome', 'descricao']
    list_filter = ['company', 'ativo']
    ordering = ['company', 'nome']

@admin.register(InventoryLocation)
class InventoryLocationAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'unit', 'tipo', 'ativo']
    search_fields = ['codigo', 'nome']
    list_filter = ['unit', 'tipo', 'ativo']
    ordering = ['unit', 'codigo']
