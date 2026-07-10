from django.contrib import admin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Employee, EmployeeHistory


class SuperUserDeleteMixin:
    """
    Mixin que libera exclusão apenas para superusuários e trata ProtectedError
    exibindo mensagem amigável em português ao invés de erro 500.
    """

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def delete_view(self, request, object_id, extra_context=None):
        try:
            return super().delete_view(request, object_id, extra_context)
        except ProtectedError:
            self.message_user(
                request,
                "Este registro não pode ser excluído porque está vinculado a outros "
                "dados protegidos. Verifique os registros relacionados antes de "
                "tentar novamente.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(".")


class EmployeeHistoryInline(admin.TabularInline):
    model = EmployeeHistory
    extra = 0
    readonly_fields = [
        "funcao",
        "setor",
        "unit",
        "centro_custo",
        "data_inicio",
        "data_fim",
        "alterado_por",
        "observacao",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Employee)
class EmployeeAdmin(SuperUserDeleteMixin, admin.ModelAdmin):
    list_display = [
        "matricula",
        "nome_completo",
        "cpf",
        "company",
        "unit",
        "funcao",
        "situacao",
    ]
    search_fields = ["matricula", "nome_completo", "cpf"]
    list_filter = ["company", "unit", "funcao", "situacao"]
    ordering = ["nome_completo"]
    inlines = [EmployeeHistoryInline]
    date_hierarchy = "data_admissao"
    list_per_page = 50


@admin.register(EmployeeHistory)
class EmployeeHistoryAdmin(SuperUserDeleteMixin, admin.ModelAdmin):
    list_display = [
        "employee",
        "funcao",
        "setor",
        "unit",
        "centro_custo",
        "data_inicio",
        "data_fim",
        "alterado_por",
    ]
    search_fields = ["employee__nome_completo", "employee__matricula"]
    list_filter = ["unit", "funcao", "data_inicio"]
    ordering = ["-data_inicio"]
    date_hierarchy = "data_inicio"
    list_per_page = 50

    def has_add_permission(self, request):
        # Histórico é criado automaticamente pelo sistema, não pelo admin
        return False

    def has_change_permission(self, request, obj=None):
        # Histórico não deve ser editado manualmente
        return False
