from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.db import models
from django.utils import timezone
from inventory.models import StockMovement, StockTransfer, InventoryLocation
from inventory.services import get_stock_balance
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

        # EPIs abaixo ou no limite do estoque mínimo
        below_min = []
        variants = ProductVariant.objects.filter(ativo=True).select_related('product')
        locations = InventoryLocation.objects.filter(unit__in=user_units, ativo=True).select_related('unit')
        
        from inventory.services import get_location_minimum_stock
        for var in variants:
            for loc in locations:
                bal = get_stock_balance(loc, var)
                min_val = get_location_minimum_stock(loc, var)
                if min_val > 0 and bal <= min_val:
                    deficit = min_val - bal
                    below_min.append({
                        'product': var.product.nome,
                        'ca': var.product.ca_numero or '',
                        'tamanho': var.tamanho,
                        'location': loc.nome,
                        'unit': loc.unit.codigo,
                        'saldo': bal,
                        'minimo': min_val,
                        'faltante': max(0, deficit),
                        'situacao': 'ABAIXO' if bal < min_val else 'NO_LIMITE'
                    })

        # Ordenação por criticidade: (1) Saldo 0 primeiro, (2) Maior quantidade faltante, (3) Menor saldo
        below_min.sort(key=lambda x: (0 if x['saldo'] == 0 else 1, -x['faltante'], x['saldo']))

        context.update({
            'bal_almox': bal_almox,
            'bal_sst': bal_sst,
            'cost_month': cost_month,
            'cost_year': cost_year,
            'alerts_count': active_alerts.count(),
            'transfers_count': pending_transfers.count(),
            'active_alerts': active_alerts[:5],
            'below_min': below_min[:10],
            'active_alerts_count': active_alerts.count(),
        })
        return context


class ReportListView(LoginRequiredMixin, TemplateView):
    template_name = "reports/list.html"


class ReportStockPositionView(LoginRequiredMixin, ListView):
    model = ProductVariant
    template_name = "reports/stock_position.html"
    context_object_name = "balances"
    paginate_by = 20

    def get_queryset(self):
        return ProductVariant.objects.all().order_by('product__nome', 'tamanho')

    def get_context_data(self, **kwargs):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        locations = InventoryLocation.objects.filter(unit__in=user_units, ativo=True).select_related('unit')
        
        q = self.request.GET.get('q', '').strip().lower()
        location_id = self.request.GET.get('location', '').strip()
        unit_id = self.request.GET.get('unit', '').strip()
        product_id = self.request.GET.get('product', '').strip()
        situacao_saldo = self.request.GET.get('situacao_saldo', '').strip()

        if location_id:
            locations = locations.filter(id=location_id)
        if unit_id:
            locations = locations.filter(unit_id=unit_id)

        variants = ProductVariant.objects.filter(ativo=True).select_related('product')
        if product_id:
            variants = variants.filter(product_id=product_id)

        stock_data = []
        for var in variants:
            for loc in locations:
                bal = get_stock_balance(loc, var)
                
                if situacao_saldo == 'abaixo_minimo' and bal >= var.estoque_minimo:
                    continue
                elif situacao_saldo == 'com_saldo' and bal <= 0:
                    continue
                elif situacao_saldo == 'sem_saldo' and bal != 0:
                    continue

                if q:
                    match_product = q in var.product.nome.lower()
                    match_location = q in loc.nome.lower() or q in loc.unit.codigo.lower()
                    if not (match_product or match_location):
                        continue

                stock_data.append({
                    'product': var.product.nome,
                    'tamanho': var.tamanho,
                    'location': loc.nome,
                    'unit': loc.unit.codigo,
                    'saldo': bal,
                    'minimo': var.estoque_minimo
                })

        from django.core.paginator import Paginator
        paginator = Paginator(stock_data, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        from ppe.models import Product
        context = {
            'view': self,
            'page_obj': page_obj,
            'stock_data': page_obj.object_list,
            'is_paginated': page_obj.has_other_pages(),
            'locations': InventoryLocation.objects.filter(unit__in=user_units, ativo=True),
            'units': user_units,
            'products': Product.objects.filter(ativo=True).order_by('nome'),
            'filter_q': self.request.GET.get('q', '').strip(),
            'filter_location': location_id,
            'filter_unit': unit_id,
            'filter_product': product_id,
            'filter_situacao_saldo': situacao_saldo,
        }
        return context


class ReportStockMovementsView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = "reports/stock_movements.html"
    context_object_name = "movements"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        queryset = StockMovement.objects.filter(unit__in=user_units).select_related(
            'product_variant__product', 'location', 'lot', 'user', 'unit'
        )

        data_inicio = self.request.GET.get('data_inicio', '').strip()
        if data_inicio:
            queryset = queryset.filter(created_at__date__gte=data_inicio)

        data_fim = self.request.GET.get('data_fim', '').strip()
        if data_fim:
            queryset = queryset.filter(created_at__date__lte=data_fim)

        mov_type = self.request.GET.get('movement_type', '').strip()
        if mov_type:
            queryset = queryset.filter(movement_type=mov_type)

        product_id = self.request.GET.get('product', '').strip()
        if product_id:
            queryset = queryset.filter(product_variant__product_id=product_id)

        location_id = self.request.GET.get('location', '').strip()
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        unit_id = self.request.GET.get('unit', '').strip()
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)

        doc = self.request.GET.get('documento', '').strip()
        if doc:
            queryset = queryset.filter(models.Q(reference_doc__icontains=doc) | models.Q(id__icontains=doc))

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        from ppe.models import Product
        context.update({
            'movement_types': StockMovement.TYPE_CHOICES,
            'products': Product.objects.filter(ativo=True).order_by('nome'),
            'locations': InventoryLocation.objects.filter(unit__in=user_units, ativo=True),
            'units': user_units,
            'filter_data_inicio': self.request.GET.get('data_inicio', '').strip(),
            'filter_data_fim': self.request.GET.get('data_fim', '').strip(),
            'filter_movement_type': self.request.GET.get('movement_type', '').strip(),
            'filter_product': self.request.GET.get('product', '').strip(),
            'filter_location': self.request.GET.get('location', '').strip(),
            'filter_unit': self.request.GET.get('unit', '').strip(),
            'filter_documento': self.request.GET.get('documento', '').strip(),
        })
        return context


class ReportPPEDeliveriesView(LoginRequiredMixin, ListView):
    model = PPEDelivery
    template_name = "reports/ppe_deliveries.html"
    context_object_name = "deliveries"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        queryset = PPEDelivery.objects.filter(unit__in=user_units).select_related(
            'employee', 'product_variant__product', 'ca_entregue', 'lot', 'usuario_responsavel', 'setor', 'funcao', 'unit'
        )

        data_inicio = self.request.GET.get('data_inicio', '').strip()
        if data_inicio:
            queryset = queryset.filter(data_entrega__gte=data_inicio)

        data_fim = self.request.GET.get('data_fim', '').strip()
        if data_fim:
            queryset = queryset.filter(data_entrega__lte=data_fim)

        q = self.request.GET.get('q', '').strip()
        if q:
            q_clean = "".join([c for c in q if c.isdigit()])
            queryset = queryset.filter(
                models.Q(employee__nome_completo__icontains=q) |
                models.Q(employee__matricula__icontains=q) |
                models.Q(employee__cpf__icontains=q_clean or q)
            )

        product_id = self.request.GET.get('product', '').strip()
        if product_id:
            queryset = queryset.filter(product_variant__product_id=product_id)

        setor_id = self.request.GET.get('setor', '').strip()
        if setor_id:
            queryset = queryset.filter(setor_id=setor_id)

        funcao_id = self.request.GET.get('funcao', '').strip()
        if funcao_id:
            queryset = queryset.filter(funcao_id=funcao_id)

        unit_id = self.request.GET.get('unit', '').strip()
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)

        status_ass = self.request.GET.get('status_assinatura', '').strip()
        if status_ass:
            queryset = queryset.filter(status_assinatura=status_ass)

        return queryset.order_by('-data_entrega')

    def get_context_data(self, **kwargs):
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        from ppe.models import Product
        from organizations.models import Sector, Function
        context.update({
            'products': Product.objects.filter(ativo=True).order_by('nome'),
            'sectors': Sector.objects.filter(unit__in=user_units).order_by('nome'),
            'functions': Function.objects.filter(ativo=True).order_by('nome'),
            'units': user_units,
            'status_choices': PPEDelivery.SIGN_STATUS,
            'filter_data_inicio': self.request.GET.get('data_inicio', '').strip(),
            'filter_data_fim': self.request.GET.get('data_fim', '').strip(),
            'filter_q': self.request.GET.get('q', '').strip(),
            'filter_product': self.request.GET.get('product', '').strip(),
            'filter_setor': self.request.GET.get('setor', '').strip(),
            'filter_funcao': self.request.GET.get('funcao', '').strip(),
            'filter_unit': self.request.GET.get('unit', '').strip(),
            'filter_status_assinatura': self.request.GET.get('status_assinatura', '').strip(),
        })
        return context


class ReportCAValidityView(LoginRequiredMixin, ListView):
    model = CertificadoAprovacao
    template_name = "reports/ca_validity.html"
    context_object_name = "cas"
    paginate_by = 20

    def get_queryset(self):
        queryset = CertificadoAprovacao.objects.all()

        ca_num = self.request.GET.get('numero', '').strip()
        if ca_num:
            ca_clean = "".join([c for c in ca_num if c.isdigit()])
            queryset = queryset.filter(models.Q(numero__icontains=ca_clean) | models.Q(numero_exibicao__icontains=ca_num))

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                models.Q(equipamento__icontains=q) |
                models.Q(fabricante__icontains=q) |
                models.Q(aprovado_para__icontains=q)
            )

        fabricante = self.request.GET.get('fabricante', '').strip()
        if fabricante:
            queryset = queryset.filter(fabricante__icontains=fabricante)

        situacao = self.request.GET.get('situacao', '').strip()
        today = timezone.now().date()
        if situacao == 'VENCIDO':
            queryset = queryset.filter(data_validade__lt=today)
        elif situacao == 'PROXIMO':
            limit = today + timezone.timedelta(days=60)
            queryset = queryset.filter(data_validade__gte=today, data_validade__lte=limit)
        elif situacao == 'VALIDO':
            queryset = queryset.filter(data_validade__gte=today)

        data_inicio = self.request.GET.get('data_inicio', '').strip()
        if data_inicio:
            queryset = queryset.filter(data_validade__gte=data_inicio)

        data_fim = self.request.GET.get('data_fim', '').strip()
        if data_fim:
            queryset = queryset.filter(data_validade__lte=data_fim)

        return queryset.order_by('data_validade')

    def get_context_data(self, **kwargs):
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        context.update({
            'filter_numero': self.request.GET.get('numero', '').strip(),
            'filter_q': self.request.GET.get('q', '').strip(),
            'filter_fabricante': self.request.GET.get('fabricante', '').strip(),
            'filter_situacao': self.request.GET.get('situacao', '').strip(),
            'filter_data_inicio': self.request.GET.get('data_inicio', '').strip(),
            'filter_data_fim': self.request.GET.get('data_fim', '').strip(),
        })
        return context

