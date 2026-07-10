from django.contrib import admin
from .models import Supplier, FiscalNote, Lot, StockMovement, StockTransfer, StockTransferItem

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'cnpj_cpf', 'contato', 'telefone', 'ativo']
    search_fields = ['razao_social', 'cnpj_cpf']
    list_filter = ['ativo']
    ordering = ['razao_social']

class LotInline(admin.TabularInline):
    model = Lot
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        if obj and obj.status != 'RASCUNHO':
            return False
        return True
    def has_change_permission(self, request, obj=None):
        if obj and obj.status != 'RASCUNHO':
            return False
        return True

@admin.register(FiscalNote)
class FiscalNoteAdmin(admin.ModelAdmin):
    list_display = ['numero', 'tipo', 'supplier', 'unit', 'data_recebimento', 'valor_total', 'status']
    search_fields = ['numero', 'supplier__razao_social', 'chave_acesso']
    list_filter = ['status', 'tipo', 'unit', 'data_recebimento']
    ordering = ['-data_recebimento']
    inlines = [LotInline]
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != 'RASCUNHO':
            # Se já conferido ou cancelado, tudo vira somente leitura
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ['identificador', 'product_variant', 'ca', 'quantidade_inicial', 'custo_unitario', 'data_validade']
    search_fields = ['identificador', 'product_variant__product__nome']
    list_filter = ['product_variant__product', 'data_validade']
    ordering = ['-criado_em']
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.fiscal_note and obj.fiscal_note.status != 'RASCUNHO':
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'movement_type', 'unit', 'location', 'product_variant', 'quantity', 'user']
    search_fields = ['product_variant__product__nome', 'lot__identificador', 'correlation_id']
    list_filter = ['movement_type', 'unit', 'location', 'created_at']
    ordering = ['-created_at']
    
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
        if obj and obj.status != 'RASCUNHO':
            return False
        return True
    def has_change_permission(self, request, obj=None):
        if obj and obj.status != 'RASCUNHO':
            return False
        return True

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ['id', 'unit', 'source_location', 'dest_location', 'status', 'criado_por', 'criado_em']
    search_fields = ['id', 'source_location__nome', 'dest_location__nome']
    list_filter = ['status', 'unit', 'criado_em']
    ordering = ['-criado_em']
    inlines = [StockTransferItemInline]
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != 'RASCUNHO':
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        return False
