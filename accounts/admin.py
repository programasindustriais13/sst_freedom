from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'profile_type', 'is_staff', 'is_active']
    list_filter = ['profile_type', 'is_staff', 'is_active', 'units']
    fieldsets = UserAdmin.fieldsets + (
        ('Informações de Perfil', {'fields': ('profile_type', 'units')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações de Perfil', {'fields': ('profile_type', 'units')}),
    )
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']

admin.site.register(CustomUser, CustomUserAdmin)
