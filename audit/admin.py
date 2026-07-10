from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'action', 'model_name', 'object_id', 'ip_address']
    search_fields = ['action', 'model_name', 'object_id', 'user__username', 'ip_address']
    list_filter = ['created_at', 'model_name', 'action']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
