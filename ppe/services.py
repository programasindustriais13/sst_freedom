import hashlib
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from inventory.services import get_stock_balance, InsufficientStockError
from inventory.models import StockMovement, Lot
from organizations.models import InventoryLocation
from .models import PPEDelivery, PPEMatrix, ExtraordinaryPPE, CertificadoAprovacao

@transaction.atomic
def deliver_ppe(employee, product_variant, lot, quantity, user, data_entrega, natureza_entrega, motivo_substituicao=None, manual_vida_util=None):
    """
    Registra o fornecimento individual de um EPI ao colaborador.
    Debita o estoque no local SST da unidade do colaborador.
    Calcula a próxima troca preventiva com base na matriz ou exceções extraordinárias.
    """
    # 1. Valida se a variante pertence ao lote informado
    if lot:
        if product_variant and lot.product_variant != product_variant:
            raise ValidationError("O lote selecionado não pertence ao EPI ou tamanho informado.")
        product_variant = lot.product_variant

    # 2. Localiza o estoque SST da unidade
    loc_sst = InventoryLocation.objects.filter(unit=employee.unit, tipo='SST', ativo=True).first()
    if not loc_sst:
        raise ValidationError(f"A unidade {employee.unit.nome} não possui um Local de Estoque SST cadastrado e ativo.")

    # 3. Valida o saldo disponível
    current_bal = get_stock_balance(loc_sst, product_variant, lot)
    if current_bal < quantity:
        raise InsufficientStockError(f"Saldo insuficiente no estoque SST para o Lote {lot.identificador}. Disponível: {current_bal}, Solicitado: {quantity}")

    # 3. Determina a origem da necessidade e a vida útil em dias
    origem_necessidade = 'MATRIZ'
    vida_util = 90  # default fallback

    # Verifica se existe autorização extraordinária ativa
    ext_ppe = ExtraordinaryPPE.objects.filter(
        employee=employee,
        product=product_variant.product,
        ativo=True,
        data_inicio__lte=data_entrega
    ).first()

    if ext_ppe:
        origem_necessidade = 'EXTRAORDINARIA'
        vida_util = ext_ppe.vida_util_dias
    else:
        # Busca na matriz por função
        matrix_entry = PPEMatrix.objects.filter(
            funcao=employee.funcao,
            product=product_variant.product,
            ativo=True
        ).first()
        if matrix_entry:
            vida_util = matrix_entry.vida_util_dias
        elif manual_vida_util is not None:
            vida_util = manual_vida_util
            origem_necessidade = 'EXTRAORDINARIA'
        else:
            # Se não está na matriz e não há manual_vida_util, exige justificativa
            if not motivo_substituicao:
                raise ValidationError("Justificativa obrigatória para fornecimento de item fora da matriz da função.")

    # Próxima troca
    data_prevista_troca = data_entrega + timedelta(days=vida_util)

    # Busca um C.A. adequado
    ca_candidate = None
    if product_variant.product.fabricante:
        ca_candidate = CertificadoAprovacao.objects.filter(
            fabricante__icontains=product_variant.product.fabricante,
            situacao='VÁLIDO'
        ).first()
    if not ca_candidate:
        ca_candidate = CertificadoAprovacao.objects.filter(situacao='VÁLIDO').first()
    if not ca_candidate:
        ca_candidate = CertificadoAprovacao.objects.first()

    # 4. Cria o registro de entrega
    delivery = PPEDelivery.objects.create(
        employee=employee,
        funcao=employee.funcao,
        setor=employee.setor,
        centro_custo=employee.centro_custo,
        unit=employee.unit,
        product_variant=product_variant,
        ca_entregue=ca_candidate,
        lot=lot,
        validade_fisica=lot.data_validade,
        quantidade=quantity,
        custo_unitario=lot.custo_unitario,
        data_entrega=data_entrega,
        vida_util_aplicada=vida_util,
        data_prevista_troca=data_prevista_troca,
        origem_necessidade=origem_necessidade,
        natureza_entrega=natureza_entrega,
        motivo_substituicao=motivo_substituicao,
        usuario_responsavel=user,
        status_assinatura='REGISTRADO_OPERADOR'
    )

    # 5. Gera a movimentação de saída do estoque SST
    StockMovement.objects.create(
        unit=employee.unit,
        location=loc_sst,
        product_variant=product_variant,
        lot=lot,
        quantity=-quantity,
        cost_unit=lot.custo_unitario,
        movement_type='ENTREGA_COLABORADOR',
        user=user,
        correlation_id=f"DEL-{delivery.id}",
        notes=f"Saída por fornecimento individual ao colaborador {employee.nome_completo}."
    )

    return delivery


@transaction.atomic
def confirm_delivery_signature(delivery, nome_confirmacao):
    """
    Registra a ciência/confirmação simples da entrega pelo colaborador.
    Gera um hash criptográfico do recibo para auditoria de integridade.
    """
    if delivery.status_assinatura == 'ASSINADO':
        raise ValidationError("Esta entrega já foi confirmada anteriormente.")

    delivery.status_assinatura = 'ASSINADO'
    delivery.nome_trabalhador_confirmacao = nome_confirmacao
    delivery.confirmacao_data_hora = timezone.now()

    # Gera hash para recibo
    hash_payload = f"{delivery.id}-{delivery.employee.cpf}-{delivery.product_variant.sku}-{delivery.data_entrega}-{nome_confirmacao}-{delivery.confirmacao_data_hora}"
    delivery.recibo_hash = hashlib.sha256(hash_payload.encode('utf-8')).hexdigest()
    
    delivery.save()
    return delivery


@transaction.atomic
def return_ppe(delivery, quantity, condition, user, notes=None):
    """
    Registra a devolução de um EPI fornecido anteriormente.
    Se a condição for REUTILIZÁVEL, o estoque retorna ao local SST da unidade do colaborador.
    """
    if quantity <= 0 or quantity > delivery.quantidade:
        raise ValidationError(f"Quantidade de devolução inválida. Deve ser entre 1 e {delivery.quantidade}.")

    employee = delivery.employee
    loc_sst = InventoryLocation.objects.filter(unit=employee.unit, tipo='SST', ativo=True).first()
    if not loc_sst:
        raise ValidationError(f"A unidade {employee.unit.nome} não possui um Local de Estoque SST cadastrado e ativo.")

    # Se reutilizável, devolve ao estoque SST
    if condition == 'REUTILIZAVEL':
        StockMovement.objects.create(
            unit=employee.unit,
            location=loc_sst,
            product_variant=delivery.product_variant,
            lot=delivery.lot,
            quantity=quantity,
            cost_unit=delivery.lot.custo_unitario,
            movement_type='DEVOLUCAO_COLABORADOR',
            user=user,
            correlation_id=f"RET-{delivery.id}",
            notes=f"Retorno ao estoque por devolução de EPI. Observações: {notes}"
        )
    else:
        # Se for danificado/descartado, registra a devolução física sem aumentar o saldo utilizável
        # ou registra a devolução e faz uma baixa imediata de dano/perda
        StockMovement.objects.create(
            unit=employee.unit,
            location=loc_sst,
            product_variant=delivery.product_variant,
            lot=delivery.lot,
            quantity=quantity,
            cost_unit=delivery.lot.custo_unitario,
            movement_type='DEVOLUCAO_COLABORADOR',
            user=user,
            correlation_id=f"RET-{delivery.id}",
            notes=f"Devolução de item {condition}. (Entrada para descarte)."
        )
        # Baixa imediata de estoque do item descartado
        StockMovement.objects.create(
            unit=employee.unit,
            location=loc_sst,
            product_variant=delivery.product_variant,
            lot=delivery.lot,
            quantity=-quantity,
            cost_unit=delivery.lot.custo_unitario,
            movement_type='BAIXA_DANO' if condition == 'DANIFICADO' else 'BAIXA_PERDA',
            user=user,
            correlation_id=f"RET-BAIXA-{delivery.id}",
            notes=f"Baixa automática de descarte referente à devolução de EPI. Observações: {notes}"
        )

    # Deduz a quantidade entregue ativa
    delivery.quantidade -= quantity
    delivery.save()


@transaction.atomic
def write_off_ppe(unit, location, product_variant, lot, quantity, reason, user, notes=None):
    """
    Registra uma baixa definitiva de estoque de um local por dano, perda ou vencimento.
    """
    if quantity <= 0:
        raise ValidationError("A quantidade para baixa deve ser maior que zero.")

    # Valida saldo disponível
    current_bal = get_stock_balance(location, product_variant, lot)
    if current_bal < quantity:
        raise InsufficientStockError(f"Saldo insuficiente para realizar baixa. Disponível: {current_bal}, Solicitado: {quantity}")

    # Determina tipo de movimento de baixa
    mov_type = 'BAIXA_DANO'
    if reason == 'PERDA':
        mov_type = 'BAIXA_PERDA'
    elif reason == 'VENCIMENTO':
        mov_type = 'BAIXA_VENCIMENTO'

    StockMovement.objects.create(
        unit=unit,
        location=location,
        product_variant=product_variant,
        lot=lot,
        quantity=-quantity,
        cost_unit=lot.custo_unitario,
        movement_type=mov_type,
        user=user,
        notes=notes
    )
