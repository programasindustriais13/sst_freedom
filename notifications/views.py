from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils import timezone
from django.contrib import messages
from organizations.models import Unit
from .models import Alert

class AlertListView(LoginRequiredMixin, ListView):
    model = Alert
    template_name = "notifications/alert_list.html"
    context_object_name = "alerts"
    paginate_by = 30

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()
            
        return Alert.objects.filter(unit__in=user_units).exclude(status='RESOLVIDO')


def resolve_alert_view(request, pk):
    if request.method == 'POST':
        alert = get_object_or_404(Alert, pk=pk)
        
        # Valida unidade
        user_units = request.user.units.all()
        if not request.user.is_superuser and alert.unit not in user_units:
            raise PermissionDenied("Sem permissão sobre este alerta.")
            
        alert.status = 'RESOLVIDO'
        alert.resolved_at = timezone.now()
        alert.save()
        messages.success(request, "Alerta marcado como Resolvido.")
        
    return redirect('alert_list')
