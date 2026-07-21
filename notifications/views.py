from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils import timezone
from django.contrib import messages
from django.db import models
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
            
        queryset = Alert.objects.filter(unit__in=user_units)

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(models.Q(title__icontains=q) | models.Q(message__icontains=q))

        alert_type = self.request.GET.get('alert_type', '').strip()
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        status_val = self.request.GET.get('status', '').strip()
        if status_val:
            queryset = queryset.filter(status=status_val)
        else:
            queryset = queryset.exclude(status='RESOLVIDO')

        data_inicio = self.request.GET.get('data_inicio', '').strip()
        if data_inicio:
            queryset = queryset.filter(created_at__date__gte=data_inicio)

        data_fim = self.request.GET.get('data_fim', '').strip()
        if data_fim:
            queryset = queryset.filter(created_at__date__lte=data_fim)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        from django.db import models
        context['alert_type_choices'] = Alert.ALERT_TYPES if hasattr(Alert, 'ALERT_TYPES') else []
        context['status_choices'] = Alert.STATUS_CHOICES if hasattr(Alert, 'STATUS_CHOICES') else []
        context['filter_q'] = self.request.GET.get('q', '').strip()
        context['filter_alert_type'] = self.request.GET.get('alert_type', '').strip()
        context['filter_status'] = self.request.GET.get('status', '').strip()
        context['filter_data_inicio'] = self.request.GET.get('data_inicio', '').strip()
        context['filter_data_fim'] = self.request.GET.get('data_fim', '').strip()
        return context


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
