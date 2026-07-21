from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.urls import reverse
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib import messages
from django.db import models
from organizations.models import Unit, InventoryLocation
from ppe.models import ProductVariant
from .models import Supplier, FiscalNote, Lot, StockMovement, StockTransfer, StockTransferItem
from .services import confirm_fiscal_note, cancel_fiscal_note, expedite_transfer, receive_transfer, get_stock_balance

class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    fields = ['razao_social', 'cnpj_cpf', 'contato', 'telefone', 'email', 'ativo']
    template_name = "organizations/form.html"
    success_url = reverse_lazy('fiscal_note_list') if 'reverse_lazy' in globals() else '/inventory/nfs/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Fornecedor"
        return context


class FiscalNoteListView(LoginRequiredMixin, ListView):
    model = FiscalNote
    template_name = "inventory/nfs_list.html"
    context_object_name = "notes"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        queryset = FiscalNote.objects.filter(unit__in=user_units).select_related('supplier', 'unit', 'centro_custo')

        numero = self.request.GET.get('numero', '').strip()
        if numero:
            queryset = queryset.filter(numero__icontains=numero)

        supplier_id = self.request.GET.get('supplier', '').strip()
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)

        data_inicio = self.request.GET.get('data_inicio', '').strip()
        if data_inicio:
            queryset = queryset.filter(data_recebimento__gte=data_inicio)

        data_fim = self.request.GET.get('data_fim', '').strip()
        if data_fim:
            queryset = queryset.filter(data_recebimento__lte=data_fim)

        cc_id = self.request.GET.get('centro_custo', '').strip()
        if cc_id:
            queryset = queryset.filter(centro_custo_id=cc_id)

        tipo = self.request.GET.get('tipo', '').strip()
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        status_nf = self.request.GET.get('status', '').strip()
        if status_nf:
            queryset = queryset.filter(status=status_nf)

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                models.Q(numero__icontains=q) |
                models.Q(chave_acesso__icontains=q) |
                models.Q(supplier__razao_social__icontains=q)
            )

        return queryset.order_by('-data_recebimento')

    def get_context_data(self, **kwargs):
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()

        from organizations.models import CostCenter
        context['suppliers'] = Supplier.objects.filter(ativo=True).order_by('razao_social')
        context['cost_centers'] = CostCenter.objects.filter(company__units__in=user_units).distinct().order_by('nome')
        context['tipo_choices'] = FiscalNote.TIPO_CHOICES
        context['status_choices'] = FiscalNote.STATUS_CHOICES
        
        context['filter_numero'] = self.request.GET.get('numero', '').strip()
        context['filter_supplier'] = self.request.GET.get('supplier', '').strip()
        context['filter_data_inicio'] = self.request.GET.get('data_inicio', '').strip()
        context['filter_data_fim'] = self.request.GET.get('data_fim', '').strip()
        context['filter_centro_custo'] = self.request.GET.get('centro_custo', '').strip()
        context['filter_tipo'] = self.request.GET.get('tipo', '').strip()
        context['filter_status'] = self.request.GET.get('status', '').strip()
        context['filter_q'] = self.request.GET.get('q', '').strip()
        return context


class FiscalNoteCreateView(LoginRequiredMixin, CreateView):
    model = FiscalNote
    fields = ['tipo', 'supplier', 'unit', 'numero', 'serie', 'chave_acesso', 'data_emissao', 'data_recebimento', 'centro_custo', 'frete', 'desconto', 'valor_total', 'documento_anexo', 'observacoes']
    template_name = "inventory/nfs_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not user.is_superuser or user.units.exists():
            form.fields['unit'].queryset = user.units.all()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ppe.models import Product
        context['products'] = Product.objects.filter(ativo=True).order_by('nome')
        return context

    def form_valid(self, form):
        import json
        from django.db import transaction
        from .services import create_and_confirm_fiscal_note
        
        items_json = self.request.POST.get('items_json', '[]')
        try:
            items_data = json.loads(items_json)
        except ValueError:
            form.add_error(None, "JSON de itens inválido.")
            return self.form_invalid(form)
        
        if not items_data:
            form.add_error(None, "Você deve adicionar pelo menos um produto válido.")
            return self.form_invalid(form)
        
        try:
            with transaction.atomic():
                fiscal_note = form.save(commit=False)
                create_and_confirm_fiscal_note(fiscal_note, items_data, self.request.user)
                
                # Grava auditoria
                from audit.models import log_audit
                log_audit(
                    request=self.request,
                    action=f"Criação e Confirmação de Nota Fiscal: {fiscal_note.numero or 'S/N'} (Tipo: {fiscal_note.get_tipo_display()})",
                    model_name="FiscalNote",
                    object_id=fiscal_note.id,
                    before=None,
                    after={'status': 'CONFERIDA', 'valor_total': float(fiscal_note.valor_total), 'itens': len(items_data)}
                )
                
            messages.success(self.request, "Recebimento cadastrado e estoque atualizado no Almoxarifado com sucesso!")
            self.object = fiscal_note
            return redirect(self.get_success_url())
        except ValidationError as e:
            form.add_error(None, e.message if hasattr(e, 'message') else str(e))
            return self.form_invalid(form)
        except Exception as e:
            form.add_error(None, f"Erro ao processar recebimento: {str(e)}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('fiscal_note_detail', kwargs={'pk': self.object.pk})


class FiscalNoteDetailView(LoginRequiredMixin, DetailView):
    model = FiscalNote
    template_name = "inventory/nfs_detail.html"
    context_object_name = "note"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lots'] = self.object.lots.all().select_related('product_variant__product', 'ca')
        # Filtra variantes de EPI para o form de adicionar lote
        context['variants'] = ProductVariant.objects.filter(ativo=True).select_related('product')
        # Filtra C.A.s ativos/cadastrados para o seletor
        from ppe.models import CertificadoAprovacao
        context['cas'] = CertificadoAprovacao.objects.all().order_selection = ['numero_exibicao'] if hasattr(CertificadoAprovacao.objects.all(), 'order_selection') else CertificadoAprovacao.objects.all().order_by('numero_exibicao')
        # Calcula totais
        total_items = sum(lot.quantidade_inicial * lot.custo_unitario for lot in context['lots'])
        context['total_items'] = total_items
        context['divergencia'] = total_items != self.object.valor_total
        return context


class LotCreateView(LoginRequiredMixin, CreateView):
    model = Lot
    fields = ['product_variant', 'ca', 'identificador', 'data_fabricacao', 'data_validade', 'quantidade_inicial', 'custo_unitario']
    
    def post(self, request, *args, **kwargs):
        note_id = self.kwargs.get('note_pk')
        note = get_object_or_404(FiscalNote, pk=note_id)
        if note.status != 'RASCUNHO':
            messages.error(request, "Não é possível adicionar lotes a um documento já confirmado.")
            return redirect('fiscal_note_detail', pk=note_id)
            
        form = self.get_form()
        if form.is_valid():
            lot = form.save(commit=False)
            lot.fiscal_note = note
            lot.save()
            messages.success(request, f"Lote {lot.identificador} adicionado com sucesso.")
        else:
            messages.error(request, f"Erro ao adicionar lote: {form.errors.as_text()}")
        return redirect('fiscal_note_detail', pk=note_id)


class LotDeleteView(LoginRequiredMixin, CreateView):
    # Classe para excluir lote de documento em rascunho
    def post(self, request, *args, **kwargs):
        lot = get_object_or_404(Lot, pk=self.kwargs.get('pk'))
        note = lot.fiscal_note
        if note.status != 'RASCUNHO':
            messages.error(request, "Não é possível excluir lotes de um documento já confirmado.")
        else:
            lot_ident = lot.identificador
            lot.delete()
            messages.success(request, f"Item Lote {lot_ident} removido com sucesso.")
        return redirect('fiscal_note_detail', pk=note.id)


def confirm_fiscal_note_view(request, pk):
    if request.method == 'POST':
        note = get_object_or_404(FiscalNote, pk=pk)
        
        # Validação: nota não pode ser confirmada sem itens
        if not note.lots.exists():
            messages.error(request, "Não é possível confirmar um documento de recebimento sem itens cadastrados.")
            return redirect('fiscal_note_detail', pk=pk)
            
        # Validação: divergência de valores
        total_items = sum(lot.quantidade_inicial * lot.custo_unitario for lot in note.lots.all())
        if total_items != note.valor_total:
            if not note.observacoes or not note.observacoes.strip():
                messages.error(request, "Existe divergência entre o valor total informado e o calculado. Por favor, insira uma justificativa no campo 'Observações' antes de confirmar.")
                return redirect('fiscal_note_detail', pk=pk)
                
        try:
            confirm_fiscal_note(note, request.user)
            messages.success(request, "Recebimento confirmado! Entrada física de estoque gerada no Almoxarifado.")
            
            # Grava auditoria
            from audit.models import log_audit
            log_audit(
                request=request,
                action=f"Confirmação de Documento de Entrada: {note.numero or 'S/N'} (Tipo: {note.get_tipo_display()})",
                model_name="FiscalNote",
                object_id=note.id,
                before={'status': 'RASCUNHO'},
                after={'status': 'CONFERIDA', 'valor_total': float(note.valor_total)}
            )
        except Exception as e:
            messages.error(request, f"Erro ao confirmar recebimento: {str(e)}")
        return redirect('fiscal_note_detail', pk=pk)
    return redirect('fiscal_note_list')


class StockTransferListView(LoginRequiredMixin, ListView):
    model = StockTransfer
    template_name = "inventory/transfers_list.html"
    context_object_name = "transfers"

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()
        # usuário pode ver transferências cuja origem ou destino pertença às suas unidades
        return StockTransfer.objects.filter(unit__in=user_units).select_related('source_location', 'dest_location', 'criado_por', 'recebido_por')


class StockTransferCreateView(LoginRequiredMixin, CreateView):
    model = StockTransfer
    fields = ['unit', 'source_location', 'dest_location']
    template_name = "inventory/transfers_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not user.is_superuser or user.units.exists():
            form.fields['unit'].queryset = user.units.all()
            form.fields['source_location'].queryset = InventoryLocation.objects.filter(unit__in=user.units.all(), tipo='ALMOXARIFADO')
            form.fields['dest_location'].queryset = InventoryLocation.objects.filter(unit__in=user.units.all(), tipo='SST')
        return form

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        form.instance.status = 'RASCUNHO'
        response = super().form_valid(form)
        messages.success(self.request, "Transferência criada em Rascunho. Adicione os itens correspondentes.")
        return response

    def get_success_url(self):
        return reverse('transfer_detail', kwargs={'pk': self.object.pk})


class StockTransferDetailView(LoginRequiredMixin, DetailView):
    model = StockTransfer
    template_name = "inventory/transfers_detail.html"
    context_object_name = "transfer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all().select_related('product_variant__product', 'lot')
        
        # Filtra lotes disponíveis no local de origem
        # Para simplificar, listamos todos os lotes que possuem saldo positivo na origem
        available_lots = []
        lots = Lot.objects.all().select_related('product_variant__product')
        for lot in lots:
            bal = get_stock_balance(self.object.source_location, lot.product_variant, lot)
            if bal > 0:
                available_lots.append({
                    'id': lot.id,
                    'identificador': lot.identificador,
                    'product': lot.product_variant.product.nome,
                    'tamanho': lot.product_variant.tamanho,
                    'saldo': bal
                })
        context['available_lots'] = available_lots
        return context


class StockTransferItemCreateView(LoginRequiredMixin, CreateView):
    model = StockTransferItem
    fields = ['lot', 'quantity_sent']

    def post(self, request, *args, **kwargs):
        transfer_id = self.kwargs.get('transfer_pk')
        transfer = get_object_or_404(StockTransfer, pk=transfer_id)
        if transfer.status != 'RASCUNHO':
            messages.error(request, "Não é possível adicionar itens a uma transferência já confirmada.")
            return redirect('transfer_detail', pk=transfer_id)

        form = self.get_form()
        if form.is_valid():
            item = form.save(commit=False)
            item.transfer = transfer
            item.product_variant = item.lot.product_variant
            
            # Valida estoque na origem antes de salvar item no rascunho
            bal = get_stock_balance(transfer.source_location, item.product_variant, item.lot)
            if bal < item.quantity_sent:
                messages.error(request, f"Saldo insuficiente do lote na origem. Disponível: {bal}, Solicitado: {item.quantity_sent}")
            else:
                item.save()
                messages.success(request, f"Item adicionado à transferência.")
        else:
            messages.error(request, f"Erro ao adicionar item: {form.errors.as_text()}")
        return redirect('transfer_detail', pk=transfer_id)



def expedite_transfer_view(request, pk):
    if request.method == 'POST':
        transfer = get_object_or_404(StockTransfer, pk=pk)
        try:
            expedite_transfer(transfer, request.user)
            messages.success(request, "Transferência expedida com sucesso! Carga em trânsito.")
            
            # Grava auditoria
            from audit.models import log_audit
            log_audit(
                request=request,
                action=f"Expedição de Transferência: TR-{transfer.id} ({transfer.source_location.nome} -> {transfer.dest_location.nome})",
                model_name="StockTransfer",
                object_id=transfer.id,
                before={'status': 'RASCUNHO'},
                after={'status': 'EXPEDIDA'}
            )
        except Exception as e:
            messages.error(request, f"Erro ao expedir transferência: {str(e)}")
        return redirect('transfer_detail', pk=pk)
    return redirect('transfer_list')


def receive_transfer_view(request, pk):
    if request.method == 'POST':
        transfer = get_object_or_404(StockTransfer, pk=pk)
        
        # O Técnico do destino ou admin deve confirmar
        if not request.user.is_tecnico and not request.user.is_admin:
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem receber transferências.")

        recepcoes = {}
        for item in transfer.items.all():
            field_name = f"qty_rec_{item.id}"
            qty_rec = request.POST.get(field_name)
            if qty_rec is not None:
                try:
                    recepcoes[item.id] = int(qty_rec)
                except ValueError:
                    recepcoes[item.id] = item.quantity_sent
            else:
                recepcoes[item.id] = item.quantity_sent

        justificativa = request.POST.get('justificativa_divergencia')

        try:
            receive_transfer(transfer, request.user, recepcoes, justificativa)
            messages.success(request, "Transferência recebida no local de destino! Estoque SST atualizado.")
            
            # Grava auditoria
            from audit.models import log_audit
            log_audit(
                request=request,
                action=f"Recebimento de Transferência: TR-{transfer.id} (Status: {transfer.get_status_display()})",
                model_name="StockTransfer",
                object_id=transfer.id,
                before={'status': 'EXPEDIDA'},
                after={'status': transfer.status, 'justificativa': justificativa}
            )
        except Exception as e:
            messages.error(request, f"Erro ao receber transferência: {str(e)}")
        return redirect('transfer_detail', pk=pk)
    return redirect('transfer_list')


class MinimumStockListView(LoginRequiredMixin, ListView):
    template_name = "inventory/minimum_stock.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()

        locations = InventoryLocation.objects.filter(unit__in=user_units, ativo=True).select_related('unit')

        # Filtros
        q = self.request.GET.get('q', '').strip()
        location_id = self.request.GET.get('location', '').strip()
        unit_id = self.request.GET.get('unit', '').strip()
        situacao = self.request.GET.get('situacao', '').strip()

        if location_id:
            locations = locations.filter(id=location_id)
        if unit_id:
            locations = locations.filter(unit_id=unit_id)

        variants = ProductVariant.objects.filter(ativo=True).select_related('product')
        if q:
            variants = variants.filter(
                models.Q(product__nome__icontains=q) |
                models.Q(product__ca_numero__icontains=q) |
                models.Q(tamanho__icontains=q) |
                models.Q(sku__icontains=q)
            )

        from .services import get_location_minimum_stock
        items_data = []
        for var in variants:
            for loc in locations:
                bal = get_stock_balance(loc, var)
                min_val = get_location_minimum_stock(loc, var)

                if min_val == 0:
                    sit = 'SEM_MINIMO'
                elif bal < min_val:
                    sit = 'ABAIXO'
                elif bal == min_val:
                    sit = 'NO_LIMITE'
                else:
                    sit = 'NORMAL'

                if situacao == 'abaixo' and sit != 'ABAIXO':
                    continue
                elif situacao == 'no_limite' and sit != 'NO_LIMITE':
                    continue
                elif situacao == 'criticos' and sit not in ('ABAIXO', 'NO_LIMITE'):
                    continue
                elif situacao == 'sem_minimo' and sit != 'SEM_MINIMO':
                    continue
                elif situacao == 'normal' and sit != 'NORMAL':
                    continue

                items_data.append({
                    'variant': var,
                    'location': loc,
                    'saldo': bal,
                    'minimo': min_val,
                    'faltante': max(0, min_val - bal) if min_val > 0 else 0,
                    'situacao': sit
                })

        sit_order = {'ABAIXO': 1, 'NO_LIMITE': 2, 'SEM_MINIMO': 3, 'NORMAL': 4}
        items_data.sort(key=lambda x: (sit_order[x['situacao']], 0 if x['saldo'] == 0 else 1, -x['faltante'], x['variant'].product.nome))
        return items_data

    def get_context_data(self, **kwargs):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()

        queryset = self.get_queryset()
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'view': self,
            'page_obj': page_obj,
            'items': page_obj.object_list,
            'is_paginated': page_obj.has_other_pages(),
            'locations': InventoryLocation.objects.filter(unit__in=user_units, ativo=True),
            'units': user_units,
            'filter_q': self.request.GET.get('q', '').strip(),
            'filter_location': self.request.GET.get('location', '').strip(),
            'filter_unit': self.request.GET.get('unit', '').strip(),
            'filter_situacao': self.request.GET.get('situacao', '').strip(),
        }
        return context


def minimum_stock_update_view(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Acesso não autorizado.")
        
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        location_id = request.POST.get('location_id')
        estoque_minimo = request.POST.get('estoque_minimo')

        try:
            val = int(estoque_minimo)
            if val < 0:
                messages.error(request, "O estoque mínimo não pode ser negativo.")
                return redirect(request.META.get('HTTP_REFERER', 'minimum_stock_list'))
        except (ValueError, TypeError):
            messages.error(request, "Valor de estoque mínimo inválido.")
            return redirect(request.META.get('HTTP_REFERER', 'minimum_stock_list'))

        variant = get_object_or_404(ProductVariant, pk=variant_id)
        location = get_object_or_404(InventoryLocation, pk=location_id)

        from .models import LocationStockMinimo
        min_obj, created = LocationStockMinimo.objects.get_or_create(
            product_variant=variant,
            location=location,
            defaults={'estoque_minimo': val}
        )
        old_val = min_obj.estoque_minimo
        if not created:
            min_obj.estoque_minimo = val
            min_obj.save()

        variant.estoque_minimo = val
        variant.save()

        from audit.models import log_audit
        log_audit(
            request=request,
            action=f"Atualização de Estoque Mínimo: {variant.product.nome} ({variant.tamanho}) no local {location.nome} para {val}",
            model_name="LocationStockMinimo",
            object_id=min_obj.id,
            before={'estoque_minimo': old_val},
            after={'estoque_minimo': val}
        )

        messages.success(request, f"Estoque mínimo atualizado para {val} unidades em {location.nome}.")
        return redirect(request.META.get('HTTP_REFERER', 'minimum_stock_list'))

    return redirect('minimum_stock_list')

