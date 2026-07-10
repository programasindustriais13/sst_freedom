from django.contrib import admin
from .models import Alert

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'unit', 'status', 'created_at', 'resolved_at']
    search_fields = ['title', 'message']
    list_filter = ['severity', 'status', 'unit', 'created_at']
    ordering = ['-created_at']
