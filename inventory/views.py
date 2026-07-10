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
    
    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            from organizations.models import Unit
            user_units = Unit.objects.all()
        return FiscalNote.objects.filter(unit__in=user_units).select_related('supplier', 'unit', 'centro_custo')


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

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.status = 'RASCUNHO'
        response = super().form_valid(form)
        messages.success(self.request, "Documento de entrada criado em Rascunho. Adicione os itens correspondentes.")
        return response

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
