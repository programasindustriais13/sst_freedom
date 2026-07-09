from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from organizations.models import Unit, InventoryLocation
from inventory.models import Lot, StockMovement
from inventory.services import get_stock_balance
from ppe.models import ProductVariant, PPEDelivery, CertificadoAprovacao
from notifications.models import Alert

class Command(BaseCommand):
    help = "Processa e atualiza os alertas do sistema (estoque baixo, vencimento de lote, validade de C.A., trocas preventivas, etc.)"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando processamento de alertas...")
        
        today = timezone.now().date()
        now = timezone.now()

        # 1. Estoque Baixo
        variants = ProductVariant.objects.filter(ativo=True).select_related('product')
        locations = InventoryLocation.objects.filter(ativo=True).select_related('unit')
        
        for var in variants:
            for loc in locations:
                bal = get_stock_balance(loc, var)
                if bal < var.estoque_minimo:
                    # Gera alerta de estoque baixo
                    alert_title = f"Estoque Baixo: {var.product.nome} ({var.tamanho})"
                    alert_msg = f"O local {loc.nome} possui saldo de {bal} unidades, abaixo do estoque mínimo de {var.estoque_minimo}."
                    
                    # Deduplica
                    Alert.objects.get_or_create(
                        unit=loc.unit,
                        alert_type='ESTOQUE_BAIXO',
                        title=alert_title,
                        status='NOVO',
                        defaults={
                            'severity': 'WARNING',
                            'message': alert_msg,
                            'content_type': ContentType.objects.get_for_model(var),
                            'object_id': var.id
                        }
                    )

        # 2. Vencimento / Validade de Lotes
        lots = Lot.objects.filter(data_validade__isnull=False).select_related('product_variant__product', 'fiscal_note__unit')
        for lot in lots:
            # Verifica se ainda possui saldo ativo em algum local daquela unidade
            # Se sim, avisa
            days_to_expire = (lot.data_validade - today).days
            unit = lot.fiscal_note.unit if lot.fiscal_note else None
            
            if days_to_expire < 0:
                # Lote Vencido
                alert_title = f"Lote Vencido: Lote {lot.identificador}"
                alert_msg = f"O Lote {lot.identificador} de {lot.product_variant.product.nome} (Tamanho {lot.product_variant.tamanho}) venceu em {lot.data_validade.strftime('%d/%m/%Y')}."
                
                Alert.objects.get_or_create(
                    unit=unit,
                    alert_type='LOTE_VENCIDO',
                    title=alert_title,
                    status='NOVO',
                    defaults={
                        'severity': 'CRITICAL',
                        'message': alert_msg,
                        'content_type': ContentType.objects.get_for_model(lot),
                        'object_id': lot.id
                    }
                )
            elif days_to_expire <= 30:
                # Lote próximo do vencimento
                alert_title = f"Lote Próximo ao Vencimento: Lote {lot.identificador}"
                alert_msg = f"O Lote {lot.identificador} de {lot.product_variant.product.nome} vence em {lot.data_validade.strftime('%d/%m/%Y')} ({days_to_expire} dias restantes)."
                
                Alert.objects.get_or_create(
                    unit=unit,
                    alert_type='LOTE_VENCIMENTO',
                    title=alert_title,
                    status='NOVO',
                    defaults={
                        'severity': 'WARNING',
                        'message': alert_msg,
                        'content_type': ContentType.objects.get_for_model(lot),
                        'object_id': lot.id
                    }
                )

        # 3. Validade de Certificados de Aprovação (C.A.)
        cas = CertificadoAprovacao.objects.filter(data_validade__isnull=False)
        for ca in cas:
            days_to_expire = (ca.data_validade - today).days
            if days_to_expire < 0:
                alert_title = f"C.A. Vencido: Nº {ca.numero_exibicao}"
                alert_msg = f"O Certificado de Aprovação Nº {ca.numero_exibicao} ({ca.fabricante}) venceu em {ca.data_validade.strftime('%d/%m/%Y')}."
                
                Alert.objects.get_or_create(
                    alert_type='CA_VENCIDO',
                    title=alert_title,
                    status='NOVO',
                    defaults={
                        'severity': 'CRITICAL',
                        'message': alert_msg,
                        'content_type': ContentType.objects.get_for_model(ca),
                        'object_id': ca.id
                    }
                )
            elif days_to_expire <= 30:
                alert_title = f"C.A. Próximo ao Vencimento: Nº {ca.numero_exibicao}"
                alert_msg = f"O Certificado de Aprovação Nº {ca.numero_exibicao} vence em {ca.data_validade.strftime('%d/%m/%Y')} ({days_to_expire} dias restantes)."
                
                Alert.objects.get_or_create(
                    alert_type='CA_VENCIMENTO',
                    title=alert_title,
                    status='NOVO',
                    defaults={
                        'severity': 'WARNING',
                        'message': alert_msg,
                        'content_type': ContentType.objects.get_for_model(ca),
                        'object_id': ca.id
                    }
                )

        # 4. Trocas Preventivas de Colaboradores
        # Entregas ativas (quantidade > 0)
        deliveries = PPEDelivery.objects.filter(quantidade__gt=0).select_related('employee', 'product_variant__product')
        for d in deliveries:
            days_to_exchange = (d.data_prevista_troca - today).days
            if days_to_exchange < 0:
                alert_title = f"Troca de EPI Vencida: {d.employee.nome_completo}"
                alert_msg = f"A troca do EPI {d.product_variant.product.nome} do colaborador {d.employee.nome_completo} venceu em {d.data_prevista_troca.strftime('%d/%m/%Y')}."
                
                Alert.objects.get_or_create(
                    unit=d.unit,
                    alert_type='TROCA_VENCIDA',
                    title=alert_title,
                    status='NOVO',
                    defaults={
                        'severity': 'CRITICAL',
                        'message': alert_msg,
                        'content_type': ContentType.objects.get_for_model(d),
                        'object_id': d.id
                    }
                )
            elif days_to_exchange <= 10:
                alert_title = f"Troca de EPI Próxima: {d.employee.nome_completo}"
                alert_msg = f"A troca do EPI {d.product_variant.product.nome} do colaborador {d.employee.nome_completo} está prevista para {d.data_prevista_troca.strftime('%d/%m/%Y')} ({days_to_exchange} dias restantes)."
                
                Alert.objects.get_or_create(
                    unit=d.unit,
                    alert_type='TROCA_BREVE',
                    title=alert_title,
                    status='NOVO',
                    defaults={
                        'severity': 'INFO',
                        'message': alert_msg,
                        'content_type': ContentType.objects.get_for_model(d),
                        'object_id': d.id
                    }
                )

        # 5. Falta de Ciência / Assinatura (entrega pendente de assinatura a mais de 48h)
        cutoff_time = now - timedelta(hours=48)
        unsigned_deliveries = PPEDelivery.objects.filter(status_assinatura='PENDENTE', data_entrega__lte=cutoff_time.date()).select_related('employee', 'product_variant__product')
        for ud in unsigned_deliveries:
            alert_title = f"Pendente de Assinatura: {ud.employee.nome_completo}"
            alert_msg = f"O fornecimento do EPI {ud.product_variant.product.nome} realizado em {ud.data_entrega.strftime('%d/%m/%Y')} para {ud.employee.nome_completo} ainda não foi assinado eletronicamente."
            
            Alert.objects.get_or_create(
                unit=ud.unit,
                alert_type='FALTA_CIENCIA',
                title=alert_title,
                status='NOVO',
                defaults={
                    'severity': 'WARNING',
                    'message': alert_msg,
                    'content_type': ContentType.objects.get_for_model(ud),
                    'object_id': ud.id
                }
            )

        self.stdout.write(self.style.SUCCESS("Processamento de alertas finalizado com sucesso!"))
