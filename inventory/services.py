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


def get_location_minimum_stock(location, product_variant):
    """
    Retorna o estoque mínimo configurado para a combinação de Local e Variante.
    Se houver registro específico em LocationStockMinimo, utiliza este valor.
    Caso contrário, retorna o estoque mínimo cadastrado na variante.
    """
    from .models import LocationStockMinimo
    min_obj = LocationStockMinimo.objects.filter(location=location, product_variant=product_variant).first()
    if min_obj:
        return min_obj.estoque_minimo
    return product_variant.estoque_minimo or 0



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


@transaction.atomic
def create_and_confirm_fiscal_note(fiscal_note, items_data, user):
    """
    Salva a Nota Fiscal diretamente com status 'CONFERIDA', cria os respectivos
    Lotes e gera as movimentações físicas de entrada no Almoxarifado central de forma atômica.
    """
    import decimal
    from ppe.models import Product, ProductVariant, CertificadoAprovacao

    if not items_data:
        raise ValidationError("Não é possível salvar um documento de recebimento sem itens.")

    # Valida e busca Local de Estoque Almoxarifado ativo
    loc_almox = InventoryLocation.objects.filter(unit=fiscal_note.unit, tipo='ALMOXARIFADO', ativo=True).first()
    if not loc_almox:
        raise ValidationError(f"A unidade {fiscal_note.unit.nome} não possui um Local de Estoque do tipo ALMOXARIFADO ativo.")

    # Configura metadados da Nota Fiscal
    fiscal_note.status = 'CONFERIDA'
    fiscal_note.usuario = user
    fiscal_note.save()

    total_calculated = decimal.Decimal('0.00')

    # Criação dos itens / lotes e movimentações
    for item in items_data:
        product_id = item.get('product_id')
        tamanho = item.get('tamanho', 'U').strip() or 'U'
        ca_numero = item.get('ca_numero', '').strip()
        identificador = item.get('identificador', '').strip()
        data_fabricacao = item.get('data_fabricacao') or None
        data_validade = item.get('data_validade')
        quantidade = int(item.get('quantidade', 0))
        custo_unitario = decimal.Decimal(str(item.get('custo_unitario', 0.0)))

        if quantidade <= 0:
            raise ValidationError("A quantidade dos itens deve ser maior que zero.")
        if custo_unitario < 0:
            raise ValidationError("O custo unitário não pode ser negativo.")

        # Autogerar lote e validade se não fornecidos pelo Almoxarife
        if not identificador:
            import uuid
            identificador = f"NF-{fiscal_note.numero or fiscal_note.id or 'SN'}-{uuid.uuid4().hex[:6].upper()}"

        if not data_validade:
            base_date = fiscal_note.data_recebimento or timezone.now().date()
            data_validade = base_date + timezone.timedelta(days=365*5)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError(f"Produto com ID {product_id} não existe.")

        # Encontra ou cria a variante correspondente ao tamanho
        variant, _ = ProductVariant.objects.get_or_create(
            product=product,
            tamanho=tamanho,
            defaults={'ativo': True, 'estoque_minimo': 0}
        )

        # Encontra ou cria o CertificadoAprovacao se for EPI e possuir C.A.
        ca_obj = None
        if product.tipo_produto == 'EPI' and ca_numero:
            num_norm = "".join([c for c in ca_numero if c.isdigit()])
            if num_norm:
                ca_obj, _ = CertificadoAprovacao.objects.get_or_create(
                    numero=num_norm,
                    defaults={
                        'numero_exibicao': ca_numero,
                        'fabricante': product.fabricante or 'Informado via NF',
                        'data_validade': timezone.now().date() + timezone.timedelta(days=365*2), # 2 anos padrão
                        'status_verificacao': 'INFORMADO_MANUALMENTE',
                        'justificativa_manual': 'Criado via recebimento de NF.'
                    }
                )

        # Cria o lote
        lot = Lot.objects.create(
            product_variant=variant,
            fiscal_note=fiscal_note,
            ca=ca_obj,
            identificador=identificador,
            data_fabricacao=data_fabricacao,
            data_validade=data_validade,
            quantidade_inicial=quantidade,
            custo_unitario=custo_unitario
        )

        # Incrementa o total calculado
        total_calculated += (quantidade * custo_unitario)

        # Cria a movimentação de estoque
        StockMovement.objects.create(
            unit=fiscal_note.unit,
            location=loc_almox,
            product_variant=variant,
            lot=lot,
            quantity=quantidade,
            cost_unit=custo_unitario,
            movement_type='ENTRADA_COMPRA',
            user=user,
            correlation_id=f"NF-{fiscal_note.id}",
            notes=f"Entrada automática pela confirmação da Nota Fiscal {fiscal_note.numero}."
        )

    # Validação de divergência de valores conforme regra existente
    if total_calculated != fiscal_note.valor_total:
        if not fiscal_note.observacoes or not fiscal_note.observacoes.strip():
            raise ValidationError("Existe divergência entre o valor total informado e o calculado. Por favor, insira uma justificativa no campo 'Observações'.")
