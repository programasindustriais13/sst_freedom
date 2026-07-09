from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.db import models
from django.utils import timezone
from inventory.models import StockMovement, StockTransfer, InventoryLocation
from notifications.models import Alert
from ppe.models import ProductVariant, PPEDelivery, CertificadoAprovacao

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Filtra locais e movimentos permitidos pela unidade do usuário
        user_units = user.units.all()
        
        # Se for superuser/admin e não tiver unidades vinculadas, pega todas
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        # Locais
        locs_almox = InventoryLocation.objects.filter(unit__in=user_units, tipo='ALMOXARIFADO')
        locs_sst = InventoryLocation.objects.filter(unit__in=user_units, tipo='SST')
        
        # Saldos
        bal_almox = StockMovement.objects.filter(location__in=locs_almox).aggregate(total=models.Sum('quantity'))['total'] or 0
        bal_sst = StockMovement.objects.filter(location__in=locs_sst).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        # Custos (mês e ano)
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Custos baseados em entregas a colaboradores nas unidades permitidas
        deliveries = StockMovement.objects.filter(
            unit__in=user_units,
            movement_type='ENTREGA_COLABORADOR'
        )
        
        # Quantidades entregues são negativas, então multiplicamos por -1
        cost_month = sum(abs(m.quantity) * m.cost_unit for m in deliveries.filter(created_at__gte=start_of_month))
        cost_year = sum(abs(m.quantity) * m.cost_unit for m in deliveries.filter(created_at__gte=start_of_year))

        # Alertas ativos
        active_alerts = Alert.objects.filter(unit__in=user_units, status='NOVO')
        
        # Transferências pendentes
        pending_transfers = StockTransfer.objects.filter(unit__in=user_units, status='EXPEDIDA')

        # EPIs abaixo do estoque mínimo
        below_min = []
        variants = ProductVariant.objects.filter(ativo=True)
        for var in variants:
            # Para cada local Almoxarifado / SST nas unidades do usuário
            for unit in user_units:
                for loc in InventoryLocation.objects.filter(unit=unit, ativo=True):
                    # Calcula saldo
                    bal = StockMovement.objects.filter(location=loc, product_variant=var).aggregate(total=models.Sum('quantity'))['total'] or 0
                    if bal < var.estoque_minimo:
                        below_min.append({
                            'product': var.product.nome,
                            'tamanho': var.tamanho,
                            'location': loc.nome,
                            'unit': unit.codigo,
                            'saldo': bal,
                            'minimo': var.estoque_minimo
                        })

        context.update({
            'bal_almox': bal_almox,
            'bal_sst': bal_sst,
            'cost_month': cost_month,
            'cost_year': cost_year,
            'alerts_count': active_alerts.count(),
            'transfers_count': pending_transfers.count(),
            'active_alerts': active_alerts[:5],
            'below_min': below_min[:5],
            'active_alerts_count': active_alerts.count(),
        })
        return context


class ReportListView(LoginRequiredMixin, TemplateView):
    template_name = "reports/list.html"


class ReportStockPositionView(LoginRequiredMixin, ListView):
    model = ProductVariant
    template_name = "reports/stock_position.html"
    context_object_name = "balances"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        locations = InventoryLocation.objects.filter(unit__in=user_units, ativo=True)
        variants = ProductVariant.objects.filter(ativo=True).select_related('product')
        
        stock_data = []
        for var in variants:
            for loc in locations:
                bal = get_stock_balance(loc, var)
                if bal > 0:
                    stock_data.append({
                        'product': var.product.nome,
                        'tamanho': var.tamanho,
                        'location': loc.nome,
                        'unit': loc.unit.codigo,
                        'saldo': bal,
                        'minimo': var.estoque_minimo
                    })
        context['stock_data'] = stock_data
        return context


class ReportStockMovementsView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = "reports/stock_movements.html"
    context_object_name = "movements"

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()
        return StockMovement.objects.filter(unit__in=user_units).select_related('product_variant__product', 'location', 'lot', 'user')


class ReportPPEDeliveriesView(LoginRequiredMixin, ListView):
    model = PPEDelivery
    template_name = "reports/ppe_deliveries.html"
    context_object_name = "deliveries"

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()
        return PPEDelivery.objects.filter(unit__in=user_units).select_related('employee', 'product_variant__product', 'ca_entregue', 'lot', 'usuario_responsavel')


class ReportCAValidityView(LoginRequiredMixin, ListView):
    model = CertificadoAprovacao
    template_name = "reports/ca_validity.html"
    context_object_name = "cas"
    queryset = CertificadoAprovacao.objects.all().order_by('data_validade')

