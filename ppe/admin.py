from django.contrib import admin
from .models import Product, ProductVariant, CertificadoAprovacao, PPEMatrix, ExtraordinaryPPE, PPEDelivery

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['nome', 'categoria', 'unidade_medida', 'fabricante', 'exige_ca', 'ativo']
    search_fields = ['nome', 'fabricante']
    list_filter = ['categoria', 'ativo', 'exige_ca']
    ordering = ['nome']
    inlines = [ProductVariantInline]

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'tamanho', 'sku', 'estoque_minimo', 'ativo']
    search_fields = ['sku', 'product__nome']
    list_filter = ['ativo']
    ordering = ['product', 'tamanho']

@admin.register(CertificadoAprovacao)
class CertificadoAprovacaoAdmin(admin.ModelAdmin):
    list_display = ['numero_exibicao', 'fabricante', 'situacao', 'data_validade', 'status_verificacao']
    search_fields = ['numero', 'numero_exibicao', 'fabricante']
    list_filter = ['situacao', 'status_verificacao', 'data_validade']
    ordering = ['-data_validade']
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(PPEMatrix)
class PPEMatrixAdmin(admin.ModelAdmin):
    list_display = ['funcao', 'product', 'obrigatorio', 'principal', 'vida_util_dias', 'ativo']
    search_fields = ['funcao__nome', 'product__nome']
    list_filter = ['obrigatorio', 'principal', 'ativo']
    ordering = ['funcao', 'product']

@admin.register(ExtraordinaryPPE)
class ExtraordinaryPPEAdmin(admin.ModelAdmin):
    list_display = ['employee', 'product', 'quantidade', 'vida_util_dias', 'data_inicio', 'data_fim', 'ativo']
    search_fields = ['employee__nome_completo', 'product__nome']
    list_filter = ['ativo', 'data_inicio']
    ordering = ['employee', 'product']

@admin.register(PPEDelivery)
class PPEDeliveryAdmin(admin.ModelAdmin):
    list_display = ['id', 'employee', 'product_variant', 'lot', 'quantidade', 'data_entrega', 'status_assinatura']
    search_fields = ['employee__nome_completo', 'product_variant__product__nome', 'lot__identificador']
    list_filter = ['status_assinatura', 'natureza_entrega', 'data_entrega']
    ordering = ['-data_entrega']
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
