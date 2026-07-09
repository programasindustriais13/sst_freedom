from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import FiscalNote, Lot, StockMovement, StockTransfer, StockTransferItem
from organizations.models import InventoryLocation

class InsufficientStockError(ValidationError):
    pass

def get_stock_balance(location, product_variant, lot=None):
    """
    Retorna o saldo atual do estoque de uma variante (e opcionalmente lote) em um local específico.
    """
    movements = StockMovement.objects.filter(location=location, product_variant=product_variant)
    if lot:
        movements = movements.filter(lot=lot)
    
    balance = movements.aggregate(total=models.Sum('quantity'))['total']
    return balance if balance is not None else 0


@transaction.atomic
def confirm_fiscal_note(fiscal_note, user):
    """
    Confirma o recebimento de uma nota fiscal, alterando seu status para CONFERIDA
    e gerando as movimentações de entrada física de estoque no local de entrada.
    """
    if fiscal_note.status != 'RASCUNHO':
        raise ValidationError("Apenas notas fiscais em Rascunho podem ser confirmadas.")

    # Altera status da nota
    fiscal_note.status = 'CONFERIDA'
    fiscal_note.usuario = user
    fiscal_note.save()

    # Gera movimentações de estoque para cada lote associado
    for lot in fiscal_note.lots.all():
        loc_almox = InventoryLocation.objects.filter(unit=fiscal_note.unit, tipo='ALMOXARIFADO', ativo=True).first()
        if not loc_almox:
            raise ValidationError(f"A unidade {fiscal_note.unit.nome} não possui um Local de Estoque do tipo ALMOXARIFADO ativo.")

        StockMovement.objects.create(
            unit=fiscal_note.unit,
            location=loc_almox,
            product_variant=lot.product_variant,
            lot=lot,
            quantity=lot.quantidade_inicial,
            cost_unit=lot.custo_unitario,
            movement_type='ENTRADA_COMPRA',
            user=user,
            correlation_id=f"NF-{fiscal_note.id}",
            notes=f"Entrada automática pela confirmação da Nota Fiscal {fiscal_note.numero}."
        )


@transaction.atomic
def cancel_fiscal_note(fiscal_note, user, justificativa):
    """
    Cancela uma nota fiscal confirmada, realizando o estorno das movimentações de estoque.
    """
    if fiscal_note.status != 'CONFERIDA':
        raise ValidationError("Apenas notas fiscais Conferidas podem ser canceladas.")

    # Para cancelar, devemos validar se o estoque que entrou ainda está disponível (não foi transferido ou entregue)
    for lot in fiscal_note.lots.all():
        loc = InventoryLocation.objects.filter(unit=fiscal_note.unit, tipo='ALMOXARIFADO', ativo=True).first()
        if not loc:
            raise ValidationError(f"A unidade {fiscal_note.unit.nome} não possui um Local de Estoque do tipo ALMOXARIFADO ativo.")
        current_bal = get_stock_balance(loc, lot.product_variant, lot)
        if current_bal < lot.quantidade_inicial:
            raise InsufficientStockError(f"Não é possível cancelar a nota: o lote {lot.identificador} já possui movimentações de saída e saldo insuficiente.")

    fiscal_note.status = 'CANCELADA'
    fiscal_note.save()

    # Gera movimentos negativos de estorno
    for lot in fiscal_note.lots.all():
        loc = InventoryLocation.objects.filter(unit=fiscal_note.unit, tipo='ALMOXARIFADO', ativo=True).first()
        StockMovement.objects.create(
            unit=fiscal_note.unit,
            location=loc,
            product_variant=lot.product_variant,
            lot=lot,
            quantity=-lot.quantidade_inicial,
            cost_unit=lot.custo_unitario,
            movement_type='ESTORNO',
            user=user,
            correlation_id=f"NF-CANCEL-{fiscal_note.id}",
            notes=f"Estorno de entrada por cancelamento de Nota Fiscal. Justificativa: {justificativa}"
        )


@transaction.atomic
def expedite_transfer(transfer, user):
    """
    Expede a transferência do local de origem.
    O estoque é debitado na origem e a transferência passa a constar como EXPEDIDA.
    """
    if transfer.status != 'RASCUNHO':
        raise ValidationError("Apenas transferências em Rascunho podem ser expedidas.")

    # Trava e valida o estoque de origem
    for item in transfer.items.all():
        # lock for update to prevent concurrent race conditions
        # check current balance
        bal = get_stock_balance(transfer.source_location, item.product_variant, item.lot)
        if bal < item.quantity_sent:
            raise InsufficientStockError(f"Estoque insuficiente no local de origem para o item {item.product_variant} no Lote {item.lot.identificador}. Disponível: {bal}, Solicitado: {item.quantity_sent}")

    transfer.status = 'EXPEDIDA'
    transfer.criado_por = user
    transfer.criado_em = timezone.now()
    transfer.save()

    # Gera saídas no local de origem
    for item in transfer.items.all():
        StockMovement.objects.create(
            unit=transfer.unit,
            location=transfer.source_location,
            product_variant=item.product_variant,
            lot=item.lot,
            quantity=-item.quantity_sent,
            cost_unit=item.lot.custo_unitario,
            movement_type='TRANSFERENCIA_SAIDA',
            user=user,
            correlation_id=f"TR-{transfer.id}",
            notes=f"Expedição de transferência física para local {transfer.dest_location.nome}."
        )


@transaction.atomic
def receive_transfer(transfer, user, item_recepcoes, justificativa=None):
    """
    Confirma o recebimento da transferência no destino.
    item_recepcoes deve ser um dicionário: {item_id: quantidade_recebida}
    """
    if transfer.status != 'EXPEDIDA':
        raise ValidationError("Apenas transferências Expedidas podem ser recebidas.")

    possui_divergencia = False
    
    # Atualiza as quantidades recebidas e checa divergências
    for item in transfer.items.all():
        received_qty = item_recepcoes.get(item.id, item.quantity_sent)
        if received_qty < 0:
            raise ValidationError("Quantidade recebida não pode ser negativa.")
        
        item.quantity_received = received_qty
        item.save()

        if received_qty != item.quantity_sent:
            possui_divergencia = True

    # Atualiza status e metadados da transferência
    transfer.status = 'RECEBIDA_COM_DIVERGENCIA' if possui_divergencia else 'RECEBIDA'
    transfer.recebido_por = user
    transfer.recebido_em = timezone.now()
    transfer.justificativa_divergencia = justificativa
    transfer.save()

    # Gera entradas no local de destino
    for item in transfer.items.all():
        qty_to_add = item.quantity_received if item.quantity_received is not None else item.quantity_sent
        if qty_to_add > 0:
            StockMovement.objects.create(
                unit=transfer.unit,
                location=transfer.dest_location,
                product_variant=item.product_variant,
                lot=item.lot,
                quantity=qty_to_add,
                cost_unit=item.lot.custo_unitario,
                movement_type='TRANSFERENCIA_ENTRADA',
                user=user,
                correlation_id=f"TR-{transfer.id}",
                notes=f"Recebimento de transferência física originada em {transfer.source_location.nome}."
            )
