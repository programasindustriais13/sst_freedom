from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from organizations.models import Company, Unit, Sector, CostCenter, Function, InventoryLocation
from employees.models import Employee
from inventory.models import Supplier, FiscalNote, Lot, StockMovement
from inventory.services import get_stock_balance
from ppe.models import Product, ProductVariant, PPEMatrix, PPEDelivery
from audit.models import AuditLog

User = get_user_model()

class PPESingleSelectorSpecTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(razao_social="Empresa Teste LTDA", nome_fantasia="Empresa Teste", cnpj="11111111000111")
        self.unit1 = Unit.objects.create(company=self.company, codigo="UN-01", nome="Unidade 1", cidade="Natal", estado="RN")
        self.unit2 = Unit.objects.create(company=self.company, codigo="UN-02", nome="Unidade 2", cidade="Mossoró", estado="RN")
        
        self.sector = Sector.objects.create(unit=self.unit1, nome="Manutenção", codigo="MAN-01")
        self.cc = CostCenter.objects.create(company=self.company, codigo="CC-01", nome="Centro de Custo 1")
        self.funcao = Function.objects.create(company=self.company, nome="Mecânico")

        # Estoques SST
        self.loc_sst1 = InventoryLocation.objects.create(unit=self.unit1, codigo="SST-01", nome="Estoque SST Unidade 1", tipo="SST")
        self.loc_sst2 = InventoryLocation.objects.create(unit=self.unit2, codigo="SST-02", nome="Estoque SST Unidade 2", tipo="SST")

        # Usuários
        self.user_sst = User.objects.create_user(username="tecnico_sst", password="pwd", profile_type="TECNICO_SST")
        self.user_sst.units.add(self.unit1)

        self.user_sem_unidade = User.objects.create_user(username="sem_acesso", password="pwd", profile_type="ALMOXARIFE")

        # Colaborador na Unidade 1
        self.emp = Employee.objects.create(
            company=self.company,
            unit=self.unit1,
            matricula="M-001",
            nome_completo="Carlos Eduardo",
            cpf="111.111.111-11",
            funcao=self.funcao,
            setor=self.sector,
            centro_custo=self.cc,
            situacao="ATIVO",
            data_admissao=timezone.now().date()
        )

        # Produto e Variantes
        self.product_protetor = Product.objects.create(nome="PROTETOR AUDITIVO", tipo_produto="EPI", exige_ca=True)
        self.variant_p = ProductVariant.objects.create(product=self.product_protetor, tamanho="P", sku="PROT-P")
        self.variant_g = ProductVariant.objects.create(product=self.product_protetor, tamanho="G", sku="PROT-G")

        # Fornecedor e Nota
        self.supplier = Supplier.objects.create(razao_social="Fornecedor EPIs", cnpj_cpf="22222222000122")
        self.note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit1,
            numero="1001",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cc,
            valor_total=500.0,
            usuario=self.user_sst,
            status="CONFERIDA"
        )

        # Lotes para Tamanho P (Dois lotes diferentes)
        self.lote_p1 = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant_p,
            identificador="NF-IO-C39D94",
            data_validade=timezone.now().date() + timedelta(days=100),
            quantidade_inicial=15,
            custo_unitario=10.0
        )
        self.lote_p2 = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant_p,
            identificador="NF-IO-C39D95",
            data_validade=timezone.now().date() + timedelta(days=200),
            quantidade_inicial=10,
            custo_unitario=10.0
        )

        # Lote para Tamanho G
        self.lote_g = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant_g,
            identificador="NF-IO-F92423",
            data_validade=timezone.now().date() + timedelta(days=150),
            quantidade_inicial=20,
            custo_unitario=12.0
        )

        # Lote sem saldo (saldo zero)
        self.lote_sem_saldo = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant_p,
            identificador="NF-EMPTY",
            data_validade=timezone.now().date() + timedelta(days=300),
            quantidade_inicial=5,
            custo_unitario=10.0
        )

        # Depositar saldo em SST1 para lote_p1, lote_p2 e lote_g
        StockMovement.objects.create(unit=self.unit1, location=self.loc_sst1, product_variant=self.variant_p, lot=self.lote_p1, quantity=15, cost_unit=10.0, movement_type="ENTRADA_COMPRA", user=self.user_sst)
        StockMovement.objects.create(unit=self.unit1, location=self.loc_sst1, product_variant=self.variant_p, lot=self.lote_p2, quantity=10, cost_unit=10.0, movement_type="ENTRADA_COMPRA", user=self.user_sst)
        StockMovement.objects.create(unit=self.unit1, location=self.loc_sst1, product_variant=self.variant_g, lot=self.lote_g, quantity=20, cost_unit=12.0, movement_type="ENTRADA_COMPRA", user=self.user_sst)

        # Matriz
        PPEMatrix.objects.create(funcao=self.funcao, product=self.product_protetor, quantidade_padrao=1, vida_util_dias=90, ativo=True)

    def test_1_single_visible_selector_in_form(self):
        """1. O formulário apresenta apenas um seletor visível para escolha do item/lote."""
        self.client.login(username="tecnico_sst", password="pwd")
        response = self.client.get(reverse('delivery_create'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        
        # Verifica presença de apenas um seletor visível (label EPI disponível no estoque SST)
        self.assertIn('EPI disponível no estoque SST', html)
        self.assertNotIn('EPI / Variante de Tamanho', html)

    def test_2_selector_shows_only_lots_with_sst_balance(self):
        """2. O seletor mostra apenas lotes com saldo SST disponível."""
        self.client.login(username="tecnico_sst", password="pwd")
        response = self.client.get(reverse('delivery_create'))
        form = response.context['form']
        lot_ids = [val for val, label in form.fields['lot'].choices if val != '']
        
        self.assertIn(self.lote_p1.id, lot_ids)
        self.assertIn(self.lote_p2.id, lot_ids)
        self.assertIn(self.lote_g.id, lot_ids)
        self.assertNotIn(self.lote_sem_saldo.id, lot_ids)

    def test_3_description_presents_epi_size_lot_validity_balance(self):
        """3. A descrição da opção apresenta EPI, tamanho, lote, validade e saldo."""
        self.client.login(username="tecnico_sst", password="pwd")
        response = self.client.get(reverse('delivery_create'))
        form = response.context['form']
        
        choices_dict = dict(form.fields['lot'].choices)
        p1_label = choices_dict[self.lote_p1.id]
        
        self.assertIn("PROTETOR AUDITIVO", p1_label)
        self.assertIn("Tamanho P", p1_label)
        self.assertIn("Lote NF-IO-C39D94", p1_label)
        self.assertIn("Validade " + self.lote_p1.data_validade.strftime('%d/%m/%Y'), p1_label)
        self.assertIn("Saldo: 15", p1_label)

    def test_4_selecting_lot_auto_links_variant(self):
        """4. Ao selecionar um lote, a variante correta é vinculada automaticamente."""
        self.client.login(username="tecnico_sst", password="pwd")
        post_data = {
            'employee': self.emp.id,
            'lot': self.lote_g.id,
            'quantidade': 1,
            'data_entrega': timezone.now().date().strftime('%Y-%m-%d'),
            'natureza_entrega': 'INICIAL',
            'motivo_substituicao': 'Teste auto link'
        }
        response = self.client.post(reverse('delivery_create'), post_data)
        self.assertEqual(response.status_code, 302)
        
        delivery = PPEDelivery.objects.filter(employee=self.emp, lot=self.lote_g).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.product_variant, self.variant_g)

    def test_5_incompatible_lot_and_variant_rejected(self):
        """5. Não é possível combinar lote e variante incompatíveis."""
        self.client.login(username="tecnico_sst", password="pwd")
        post_data = {
            'employee': self.emp.id,
            'lot': self.lote_g.id, # Lote é Tamanho G
            'product_variant': self.variant_p.id, # Enviado intencionalmente Tamanho P
            'quantidade': 1,
            'data_entrega': timezone.now().date().strftime('%Y-%m-%d'),
            'natureza_entrega': 'INICIAL',
            'motivo_substituicao': 'Tentativa maliciosa'
        }
        response = self.client.post(reverse('delivery_create'), post_data)
        self.assertEqual(response.status_code, 200) # Form com erro não redireciona
        html = response.content.decode('utf-8')
        self.assertIn("O lote selecionado não pertence ao EPI ou tamanho informado", html)

    def test_6_quantity_exceeding_balance_rejected(self):
        """6. Não é possível entregar quantidade superior ao saldo."""
        self.client.login(username="tecnico_sst", password="pwd")
        post_data = {
            'employee': self.emp.id,
            'lot': self.lote_p1.id, # Saldo = 15
            'quantidade': 99, # Solicitado 99
            'data_entrega': timezone.now().date().strftime('%Y-%m-%d'),
            'natureza_entrega': 'INICIAL',
            'motivo_substituicao': 'Quantidade em excesso'
        }
        response = self.client.post(reverse('delivery_create'), post_data)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertTrue("maior que o saldo disponível" in html or "Saldo insuficiente" in html)

    def test_7_delivery_reduces_stock_balance(self):
        """7. A entrega reduz corretamente o saldo do lote selecionado."""
        self.client.login(username="tecnico_sst", password="pwd")
        bal_before = get_stock_balance(self.loc_sst1, self.variant_p, self.lote_p1)
        self.assertEqual(bal_before, 15)
        
        post_data = {
            'employee': self.emp.id,
            'lot': self.lote_p1.id,
            'quantidade': 3,
            'data_entrega': timezone.now().date().strftime('%Y-%m-%d'),
            'natureza_entrega': 'INICIAL',
            'motivo_substituicao': 'Baixa de estoque teste'
        }
        response = self.client.post(reverse('delivery_create'), post_data)
        self.assertEqual(response.status_code, 302)
        
        bal_after = get_stock_balance(self.loc_sst1, self.variant_p, self.lote_p1)
        self.assertEqual(bal_after, 12)

    def test_8_two_lots_same_epi_and_size_appear_distinct(self):
        """8. Dois lotes do mesmo EPI e tamanho aparecem como opções distintas."""
        self.client.login(username="tecnico_sst", password="pwd")
        response = self.client.get(reverse('delivery_create'))
        form = response.context['form']
        choices_dict = dict(form.fields['lot'].choices)
        
        self.assertIn(self.lote_p1.id, choices_dict)
        self.assertIn(self.lote_p2.id, choices_dict)
        self.assertIn("NF-IO-C39D94", choices_dict[self.lote_p1.id])
        self.assertIn("NF-IO-C39D95", choices_dict[self.lote_p2.id])

    def test_9_different_sizes_properly_identified(self):
        """9. Lotes de tamanhos diferentes aparecem corretamente identificados."""
        self.client.login(username="tecnico_sst", password="pwd")
        response = self.client.get(reverse('delivery_create'))
        form = response.context['form']
        choices_dict = dict(form.fields['lot'].choices)
        
        self.assertIn("Tamanho P", choices_dict[self.lote_p1.id])
        self.assertIn("Tamanho G", choices_dict[self.lote_g.id])

    def test_10_historical_deliveries_display_normally(self):
        """10. As entregas históricas continuam sendo exibidas normalmente."""
        delivery_historica = PPEDelivery.objects.create(
            employee=self.emp,
            funcao=self.emp.funcao,
            setor=self.emp.setor,
            centro_custo=self.emp.centro_custo,
            unit=self.unit1,
            product_variant=self.variant_p,
            lot=self.lote_p1,
            validade_fisica=self.lote_p1.data_validade,
            quantidade=1,
            custo_unitario=10.0,
            data_entrega=timezone.now().date() - timedelta(days=30),
            vida_util_aplicada=90,
            data_prevista_troca=timezone.now().date() + timedelta(days=60),
            usuario_responsavel=self.user_sst,
            status_assinatura='REGISTRADO_OPERADOR'
        )
        self.client.login(username="tecnico_sst", password="pwd")
        response = self.client.get(reverse('delivery_list'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn(self.emp.nome_completo, html)
        self.assertIn(self.product_protetor.nome, html)

    def test_11_preselected_employee_workflow(self):
        """11. O fluxo com colaborador previamente selecionado continua funcionando."""
        self.client.login(username="tecnico_sst", password="pwd")
        url = f"{reverse('delivery_create')}?employee={self.emp.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.fields['employee'].initial, self.emp.id)

    def test_12_unauthorized_user_blocked(self):
        """12. Usuário sem permissão/sem unidade continua sem acesso aos lotes de outra unidade."""
        self.client.login(username="sem_acesso", password="pwd")
        response = self.client.get(reverse('delivery_create'))
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        lot_ids = [val for val, label in form.fields['lot'].choices if val != '']
        self.assertEqual(len(lot_ids), 0)

    def test_13_audit_and_stock_movements_logged(self):
        """13. As movimentações e registros de auditoria continuam sendo gerados corretamente."""
        self.client.login(username="tecnico_sst", password="pwd")
        post_data = {
            'employee': self.emp.id,
            'lot': self.lote_p1.id,
            'quantidade': 2,
            'data_entrega': timezone.now().date().strftime('%Y-%m-%d'),
            'natureza_entrega': 'INICIAL',
            'motivo_substituicao': 'Verificação de auditoria'
        }
        response = self.client.post(reverse('delivery_create'), post_data)
        self.assertEqual(response.status_code, 302)
        
        delivery = PPEDelivery.objects.filter(employee=self.emp, lot=self.lote_p1).order_by('-id').first()
        self.assertIsNotNone(delivery)
        
        # Verifica movimentação de estoque
        mov = StockMovement.objects.filter(correlation_id=f"DEL-{delivery.id}").first()
        self.assertIsNotNone(mov)
        self.assertEqual(mov.quantity, -2)
        self.assertEqual(mov.movement_type, 'ENTREGA_COLABORADOR')
        
        # Verifica auditoria
        audit = AuditLog.objects.filter(object_id=delivery.id, model_name="PPEDelivery").first()
        self.assertIsNotNone(audit)
        self.assertIn("Entrega individual de EPI", audit.action)
