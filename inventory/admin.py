from django.contrib import admin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Supplier, FiscalNote, Lot, StockMovement, StockTransfer, StockTransferItem


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


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["razao_social", "cnpj_cpf", "contato", "telefone", "ativo"]
    search_fields = ["razao_social", "cnpj_cpf"]
    list_filter = ["ativo"]
    ordering = ["razao_social"]


class LotInline(admin.TabularInline):
    model = Lot
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        if obj and obj.status != "RASCUNHO":
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.status != "RASCUNHO":
            return False
        return True


@admin.register(FiscalNote)
class FiscalNoteAdmin(SuperUserDeleteMixin, admin.ModelAdmin):
    list_display = [
        "numero",
        "tipo",
        "supplier",
        "unit",
        "data_recebimento",
        "valor_total",
        "status",
    ]
    search_fields = ["numero", "supplier__razao_social", "chave_acesso"]
    list_filter = ["status", "tipo", "unit", "data_recebimento"]
    ordering = ["-data_recebimento"]
    date_hierarchy = "data_recebimento"
    inlines = [LotInline]
    list_per_page = 50

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and obj.status != "RASCUNHO":
            self.message_user(
                request,
                "Esta Nota Fiscal não pode ser excluída porque já foi conferida ou cancelada. "
                "Notas processadas são mantidas para integridade do livro-razão.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect("..")
        return super().delete_view(request, object_id, extra_context)

    def delete_queryset(self, request, queryset):
        if queryset.exclude(status="RASCUNHO").exists():
            self.message_user(
                request,
                "Uma ou mais Notas Fiscais selecionadas não puderam ser excluídas porque já foram conferidas ou canceladas.",
                level=messages.ERROR,
            )
            queryset = queryset.filter(status="RASCUNHO")
        if queryset.exists():
            super().delete_queryset(request, queryset)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != "RASCUNHO":
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)


@admin.register(Lot)
class LotAdmin(SuperUserDeleteMixin, admin.ModelAdmin):
    list_display = [
        "identificador",
        "product_variant",
        "fiscal_note",
        "ca",
        "quantidade_inicial",
        "custo_unitario",
        "data_validade",
    ]
    search_fields = ["identificador", "product_variant__product__nome"]
    list_filter = ["product_variant__product", "data_validade"]
    ordering = ["-criado_em"]
    date_hierarchy = "data_validade"
    list_per_page = 50

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.fiscal_note and obj.fiscal_note.status != "RASCUNHO":
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Sobrescrito para tratar ProtectedError caso o lote possua movimentações vinculadas.
        O banco de dados bloqueia a exclusão via on_delete=PROTECT em StockMovement e PPEDelivery.
        """
        try:
            return super(SuperUserDeleteMixin, self).delete_view(
                request, object_id, extra_context
            )
        except ProtectedError:
            self.message_user(
                request,
                "Este lote não pode ser excluído porque está vinculado a "
                "movimentações de estoque ou entregas de EPI. "
                "Registros de movimentação são imutáveis por integridade do sistema.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(".")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """
    StockMovement é o livro-razão imutável do estoque.
    Nenhum usuário, incluindo superusuário, pode adicionar, alterar ou excluir movimentações.
    Constitution §9.2 — Imutabilidade.
    """

    list_display = [
        "created_at",
        "movement_type",
        "unit",
        "location",
        "product_variant",
        "quantity",
        "user",
    ]
    search_fields = [
        "product_variant__product__nome",
        "lot__identificador",
        "correlation_id",
    ]
    list_filter = ["movement_type", "unit", "location", "created_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    list_per_page = 100

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        if obj and obj.status != "RASCUNHO":
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.status != "RASCUNHO":
            return False
        return True


@admin.register(StockTransfer)
class StockTransferAdmin(SuperUserDeleteMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "unit",
        "source_location",
        "dest_location",
        "status",
        "criado_por",
        "criado_em",
    ]
    search_fields = ["id", "source_location__nome", "dest_location__nome"]
    list_filter = ["status", "unit", "criado_em"]
    ordering = ["-criado_em"]
    date_hierarchy = "criado_em"
    inlines = [StockTransferItemInline]
    list_per_page = 50

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and obj.status != "RASCUNHO":
            self.message_user(
                request,
                "Esta transferência não pode ser excluída porque já foi expedida ou recebida. "
                "Registros de transferências concluídas são mantidos para integridade do livro-razão.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect("..")
        return super().delete_view(request, object_id, extra_context)

    def delete_queryset(self, request, queryset):
        if queryset.exclude(status="RASCUNHO").exists():
            self.message_user(
                request,
                "Uma ou mais transferências selecionadas não puderam ser excluídas porque já foram expedidas ou recebidas.",
                level=messages.ERROR,
            )
            queryset = queryset.filter(status="RASCUNHO")
        if queryset.exists():
            super().delete_queryset(request, queryset)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != "RASCUNHO":
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)


@admin.register(StockTransferItem)
class StockTransferItemAdmin(SuperUserDeleteMixin, admin.ModelAdmin):
    """
    Admin próprio para StockTransferItem.
    Facilita visualização e limpeza de dados de teste.
    Exclusão permitida apenas para superusuário quando a transferência-pai estiver em RASCUNHO.
    """

    list_display = [
        "transfer",
        "product_variant",
        "lot",
        "quantity_sent",
        "quantity_received",
    ]
    search_fields = [
        "product_variant__product__nome",
        "lot__identificador",
        "transfer__id",
    ]
    list_filter = ["transfer__status", "transfer__unit"]
    ordering = ["-transfer__criado_em"]
    list_per_page = 50

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and obj.transfer.status != "RASCUNHO":
            self.message_user(
                request,
                "Este item de transferência não pode ser excluído porque a transferência associada já foi expedida ou recebida.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect("..")
        return super().delete_view(request, object_id, extra_context)

    def delete_queryset(self, request, queryset):
        if queryset.exclude(transfer__status="RASCUNHO").exists():
            self.message_user(
                request,
                "Um ou mais itens selecionados não puderam ser excluídos porque a transferência associada já foi expedida ou recebida.",
                level=messages.ERROR,
            )
            queryset = queryset.filter(transfer__status="RASCUNHO")
        if queryset.exists():
            super().delete_queryset(request, queryset)

    def has_add_permission(self, request):
        # Itens são gerenciados pelo admin da transferência-pai
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.transfer.status != "RASCUNHO":
            return False
        return request.user.is_superuser
