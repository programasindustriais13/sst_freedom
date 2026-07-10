from django.contrib import admin
from .models import Employee, EmployeeHistory

class EmployeeHistoryInline(admin.TabularInline):
    model = EmployeeHistory
    extra = 0
    readonly_fields = ['funcao', 'setor', 'unit', 'centro_custo', 'data_inicio', 'data_fim', 'alterado_por', 'observacao']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['matricula', 'nome_completo', 'cpf', 'company', 'unit', 'funcao', 'situacao']
    search_fields = ['matricula', 'nome_completo', 'cpf']
    list_filter = ['company', 'unit', 'funcao', 'situacao']
    ordering = ['nome_completo']
    inlines = [EmployeeHistoryInline]
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(EmployeeHistory)
class EmployeeHistoryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'funcao', 'setor', 'unit', 'centro_custo', 'data_inicio', 'data_fim', 'alterado_por']
    search_fields = ['employee__nome_completo', 'employee__matricula']
    list_filter = ['unit', 'funcao', 'data_inicio']
    ordering = ['-data_inicio']
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
