from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.core.exceptions import PermissionDenied
from django.contrib.admin.utils import unquote
from core.services import collect_dependencies, execute_cascade_delete

class CascadeDeleteAdminMixin:
    """
    Mixin for Django ModelAdmin to enable controlled administrative cascade deletion
    for authorized users when protected relationships exist.
    """
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            actions['delete_selected'] = (
                self.__class__.delete_selected,
                'delete_selected',
                actions['delete_selected'][2]
            )
        return actions

    def has_force_cascade_delete_permission(self, request):
        """
        Check if the user has the explicit permission to force cascade delete.
        """
        return request.user.is_superuser or request.user.has_perm('organizations.can_force_cascade_delete')

    def delete_view(self, request, object_id, extra_context=None):
        opts = self.model._meta
        obj = self.get_object(request, unquote(object_id))
        
        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, opts, object_id)
            
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied
            
        # Collect all dependencies
        collected = collect_dependencies([obj])
        
        # Check if there are related objects (excluding the target object itself)
        total_related = sum(len(instances) for model_class, instances in collected.items()) - 1
        
        # If there are no dependencies or the user doesn't have the permission,
        # fallback to standard Django Admin behavior
        if total_related == 0 or not self.has_force_cascade_delete_permission(request):
            return super().delete_view(request, object_id, extra_context)
            
        error_msg = None
        if request.method == 'POST':
            # Check confirmation word
            confirmation = request.POST.get('confirmation_word', '')
            if confirmation == 'EXCLUIR':
                try:
                    total_deleted = execute_cascade_delete([obj], request=request)
                    self.message_user(
                        request,
                        format_html(
                            _('Sucesso: "{}" e todos os {} objetos relacionados foram excluídos em cascata.'),
                            str(obj),
                            total_deleted - 1
                        ),
                        messages.SUCCESS
                    )
                    return redirect(reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist'))
                except Exception as e:
                    error_msg = f"Erro técnico ao executar exclusão em cascata: {str(e)}"
            else:
                error_msg = "Palavra de confirmação incorreta. Digite EXCLUIR para confirmar."
                
        # Group collected objects by model
        object_summary = []
        for model_class, instances in collected.items():
            object_summary.append({
                'model_name': model_class._meta.verbose_name_plural,
                'count': len(instances),
                'items': [str(inst) for inst in instances.values()][:100],
                'has_more': len(instances) > 100
            })
            
        context = {
            **self.admin_site.each_context(request),
            'object_name': str(obj),
            'object': obj,
            'opts': opts,
            'object_summary': object_summary,
            'total_related': total_related,
            'error_msg': error_msg,
            'is_bulk': False,
            'cancel_url': reverse(f'admin:{opts.app_label}_{opts.model_name}_change', args=[object_id]),
            'title': "Confirmar exclusão administrativa em cascata",
        }
        
        return render(request, 'admin/cascade_delete_confirmation.html', context)

    def delete_selected(self, request, queryset):
        opts = self.model._meta
        
        # Check permissions
        if not self.has_delete_permission(request):
            raise PermissionDenied
            
        has_cascade_perm = self.has_force_cascade_delete_permission(request)
        
        # Collect dependencies for the entire queryset
        collected = collect_dependencies(queryset)
        
        # Check if there are related objects
        total_related = sum(len(instances) for model_class, instances in collected.items()) - queryset.count()
        
        # If there are no related objects or the user doesn't have the permission,
        # fallback to standard Django delete_selected action.
        if total_related == 0 or not has_cascade_perm:
            from django.contrib.admin.actions import delete_selected
            return delete_selected(self, request, queryset)
            
        error_msg = None
        if request.method == 'POST' and request.POST.get('post_confirmed') == 'yes':
            confirmation = request.POST.get('confirmation_word', '')
            if confirmation == 'EXCLUIR':
                try:
                    total_deleted = execute_cascade_delete(queryset, request=request)
                    self.message_user(
                        request,
                        format_html(
                            _('Sucesso: {} registros selecionados e todos os {} objetos relacionados foram excluídos em cascata.'),
                            queryset.count(),
                            total_deleted - queryset.count()
                        ),
                        messages.SUCCESS
                    )
                    return redirect(reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist'))
                except Exception as e:
                    error_msg = f"Erro técnico ao executar exclusão em cascata: {str(e)}"
            else:
                error_msg = "Palavra de confirmação incorreta. Digite EXCLUIR para confirmar."
                
        # Group collected objects by model
        object_summary = []
        for model_class, instances in collected.items():
            object_summary.append({
                'model_name': model_class._meta.verbose_name_plural,
                'count': len(instances),
                'items': [str(inst) for inst in instances.values()][:100],
                'has_more': len(instances) > 100
            })
            
        context = {
            **self.admin_site.each_context(request),
            'queryset': queryset,
            'opts': opts,
            'object_summary': object_summary,
            'total_related': total_related,
            'error_msg': error_msg,
            'is_bulk': True,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'cancel_url': reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist'),
            'title': "Confirmar exclusão administrativa em cascata em massa",
        }
        
        return render(request, 'admin/cascade_delete_confirmation.html', context)
