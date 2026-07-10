from django.contrib import admin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Product, ProductVariant, CertificadoAprovacao, PPEMatrix, ExtraordinaryPPE, PPEDelivery


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


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "nome",
        "categoria",
        "unidade_medida",
        "fabricante",
        "exige_ca",
        "ativo",
    ]
    search_fields = ["nome", "fabricante"]
    list_filter = ["categoria", "ativo", "exige_ca"]
    ordering = ["nome"]
    inlines = [ProductVariantInline]
    list_per_page = 50


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["product", "tamanho", "sku", "estoque_minimo", "ativo"]
    search_fields = ["sku", "product__nome"]
    list_filter = ["ativo"]
    ordering = ["product", "tamanho"]
    list_per_page = 50


@admin.register(CertificadoAprovacao)
class CertificadoAprovacaoAdmin(SuperUserDeleteMixin, admin.ModelAdmin):
    list_display = [
        "numero_exibicao",
        "fabricante",
        "situacao",
        "data_validade",
        "status_verificacao",
    ]
    search_fields = ["numero", "numero_exibicao", "fabricante"]
    list_filter = ["situacao", "status_verificacao", "data_validade"]
    ordering = ["-data_validade"]
    date_hierarchy = "data_validade"
    list_per_page = 50


@admin.register(PPEMatrix)
class PPEMatrixAdmin(admin.ModelAdmin):
    list_display = [
        "funcao",
        "product",
        "obrigatorio",
        "principal",
        "vida_util_dias",
        "ativo",
    ]
    search_fields = ["funcao__nome", "product__nome"]
    list_filter = ["obrigatorio", "principal", "ativo"]
    ordering = ["funcao", "product"]
    list_per_page = 50


@admin.register(ExtraordinaryPPE)
class ExtraordinaryPPEAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "product",
        "quantidade",
        "vida_util_dias",
        "data_inicio",
        "data_fim",
        "ativo",
    ]
    search_fields = ["employee__nome_completo", "product__nome"]
    list_filter = ["ativo", "data_inicio"]
    ordering = ["employee", "product"]
    date_hierarchy = "data_inicio"
    list_per_page = 50


@admin.register(PPEDelivery)
class PPEDeliveryAdmin(admin.ModelAdmin):
    """
    PPEDelivery é registro histórico imutável de natureza legal e trabalhista.
    Nenhum usuário, incluindo superusuário, pode adicionar, alterar ou excluir entregas.
    Constitution §10.5 — Entrega; §9.2 — Imutabilidade.
    """

    list_display = [
        "id",
        "employee",
        "product_variant",
        "lot",
        "quantidade",
        "data_entrega",
        "status_assinatura",
    ]
    search_fields = [
        "employee__nome_completo",
        "product_variant__product__nome",
        "lot__identificador",
    ]
    list_filter = ["status_assinatura", "natureza_entrega", "data_entrega"]
    ordering = ["-data_entrega"]
    date_hierarchy = "data_entrega"
    list_per_page = 100

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
