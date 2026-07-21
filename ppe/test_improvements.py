from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from organizations.models import Company, Unit, Sector, CostCenter, Function, InventoryLocation
from employees.models import Employee
from ppe.models import Product, ProductVariant, CertificadoAprovacao, PPEDelivery
from inventory.models import Supplier, FiscalNote, Lot, StockMovement, LocationStockMinimo
from inventory.services import get_stock_balance, get_location_minimum_stock

User = get_user_model()

class SSTFreedomImprovementsTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(razao_social="Indústria Freedom LTDA", nome_fantasia="Freedom Ind", cnpj="99888777000166")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-01", nome="Unidade Matriz", cidade="Fortaleza", estado="CE")
        self.unit2 = Unit.objects.create(company=self.company, codigo="UN-02", nome="Unidade Filial", cidade="Caucaia", estado="CE")
        
        self.sector = Sector.objects.create(unit=self.unit, nome="Manutenção")
        self.cost_center = CostCenter.objects.create(company=self.company, codigo="CC-101", nome="Operacional")
        self.function = Function.objects.create(company=self.company, nome="Mecânico")
        
        # Locais de estoque
        self.loc_almox = InventoryLocation.objects.create(unit=self.unit, codigo="ALM-01", nome="Almoxarifado Central", tipo='ALMOXARIFADO')
        self.loc_sst = InventoryLocation.objects.create(unit=self.unit, codigo="SST-01", nome="Estoque SST", tipo='SST')
        
        # Usuários
        self.tecnico = User.objects.create_user(username="tecnico_sst", password="pwd", profile_type="TECNICO_SST")
        self.tecnico.units.add(self.unit)
        
        self.almoxarife = User.objects.create_user(username="almoxarife_user", password="pwd", profile_type="ALMOXARIFE")
        self.almoxarife.units.add(self.unit)

        # Colaborador ativo
        self.emp_ativo = Employee.objects.create(
            company=self.company,
            nome_completo="João Silva",
            cpf="11122233344",
            matricula="MAT-001",
            unit=self.unit,
            setor=self.sector,
            funcao=self.function,
            centro_custo=self.cost_center,
            situacao="ATIVO",
            data_admissao=timezone.now().date()
        )
        
        # Colaborador inativo
        self.emp_desligado = Employee.objects.create(
            company=self.company,
            nome_completo="Carlos Souza",
            cpf="55566677788",
            matricula="MAT-002",
            unit=self.unit,
            setor=self.sector,
            funcao=self.function,
            centro_custo=self.cost_center,
            situacao="DESLIGADO",
            data_admissao=timezone.now().date()
        )

        # Produtos e variantes
        self.product = Product.objects.create(nome="Luva de Proteção", tipo_produto="EPI", exige_ca=False)
        self.variant_p = ProductVariant.objects.create(product=self.product, tamanho="P", estoque_minimo=10)
        self.variant_m = ProductVariant.objects.create(product=self.product, tamanho="M", estoque_minimo=5)

        # Lote de estoque
        self.ca = CertificadoAprovacao.objects.create(numero="12345", numero_exibicao="CA 12345", data_validade=timezone.now().date() + timedelta(days=365))
        self.supplier = Supplier.objects.create(razao_social="Fornecedor EPI", cnpj_cpf="11222333000144")
        self.lot_p = Lot.objects.create(product_variant=self.variant_p, ca=self.ca, identificador="LOTE-P01", data_validade=timezone.now().date() + timedelta(days=365), quantidade_inicial=50, custo_unitario=15.00)
        self.lot_m = Lot.objects.create(product_variant=self.variant_m, ca=self.ca, identificador="LOTE-M01", data_validade=timezone.now().date() + timedelta(days=365), quantidade_inicial=20, custo_unitario=18.00)

        # Movimentos iniciais no estoque SST
        StockMovement.objects.create(unit=self.unit, location=self.loc_sst, product_variant=self.variant_p, lot=self.lot_p, quantity=15, cost_unit=15.00, movement_type="ENTRADA_COMPRA", user=self.tecnico)
        StockMovement.objects.create(unit=self.unit, location=self.loc_sst, product_variant=self.variant_m, lot=self.lot_m, quantity=2, cost_unit=18.00, movement_type="ENTRADA_COMPRA", user=self.tecnico)

    # 1. Quick Delivery Button na lista de colaboradores
    def test_employee_list_quick_delivery_button(self):
        self.client.login(username="tecnico_sst", password="pwd")
        response = self.client.get(reverse('employee_list'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn(f"/ppe/deliveries/add/?employee={self.emp_ativo.id}", html)
        self.assertIn("Entregar EPI", html)

    # 2. Pré-seleção e validação do colaborador no formulário de entrega
    def test_delivery_create_preselect_valid_employee(self):
        self.client.login(username="tecnico_sst", password="pwd")
        url = f"{reverse('delivery_create')}?employee={self.emp_ativo.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.fields['employee'].initial, self.emp_ativo.id)

    def test_delivery_create_preselect_inactive_employee(self):
        self.client.login(username="tecnico_sst", password="pwd")
        url = f"{reverse('delivery_create')}?employee={self.emp_desligado.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn("não pode receber entregas de EPI", html)

    def test_delivery_create_invalid_employee_id(self):
        self.client.login(username="tecnico_sst", password="pwd")
        url = f"{reverse('delivery_create')}?employee=999999"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn("não foi encontrado ou não pertence ao seu escopo", html)

    # 3. Conclusão de entrega sem assinatura (status REGISTRADO_OPERADOR e baixa de estoque)
    def test_delivery_completion_without_signature(self):
        self.client.login(username="tecnico_sst", password="pwd")
        initial_bal = get_stock_balance(self.loc_sst, self.variant_p, self.lot_p)
        
        post_data = {
            'employee': self.emp_ativo.id,
            'product_variant': self.variant_p.id,
            'lot': self.lot_p.id,
            'quantidade': 2,
            'data_entrega': timezone.now().date().strftime('%Y-%m-%d'),
            'natureza_entrega': 'INICIAL',
            'motivo_substituicao': 'Fornecimento padrão'
        }
        response = self.client.post(reverse('delivery_create'), post_data)
        self.assertEqual(response.status_code, 302) # Redireciona para employee_detail
        
        # Garante que a entrega foi criada com status REGISTRADO_OPERADOR
        delivery = PPEDelivery.objects.filter(employee=self.emp_ativo, product_variant=self.variant_p).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.status_assinatura, 'REGISTRADO_OPERADOR')
        self.assertIsNone(delivery.nome_trabalhador_confirmacao) # Nenhuma assinatura fictícia criada
        
        # Garante que o estoque foi debitado uma única vez
        new_bal = get_stock_balance(self.loc_sst, self.variant_p, self.lot_p)
        self.assertEqual(new_bal, initial_bal - 2)

    # 4. Rota antiga de assinatura (/ppe/deliveries/<id>/sign/) redireciona com segurança
    def test_legacy_sign_route_safe_redirect(self):
        self.client.login(username="tecnico_sst", password="pwd")
        delivery = PPEDelivery.objects.create(
            employee=self.emp_ativo,
            funcao=self.function,
            setor=self.sector,
            centro_custo=self.cost_center,
            unit=self.unit,
            product_variant=self.variant_p,
            lot=self.lot_p,
            validade_fisica=self.lot_p.data_validade,
            quantidade=1,
            custo_unitario=15.00,
            data_entrega=timezone.now().date(),
            vida_util_aplicada=90,
            data_prevista_troca=timezone.now().date() + timedelta(days=90),
            usuario_responsavel=self.tecnico,
            status_assinatura='REGISTRADO_OPERADOR'
        )
        url = reverse('delivery_sign', kwargs={'pk': delivery.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redireciona com segurança sem 500

    # 5. Integridade das entregas antigas assinadas
    def test_historical_signed_deliveries_integrity(self):
        signed_delivery = PPEDelivery.objects.create(
            employee=self.emp_ativo,
            funcao=self.function,
            setor=self.sector,
            centro_custo=self.cost_center,
            unit=self.unit,
            product_variant=self.variant_p,
            lot=self.lot_p,
            validade_fisica=self.lot_p.data_validade,
            quantidade=1,
            custo_unitario=15.00,
            data_entrega=timezone.now().date() - timedelta(days=10),
            vida_util_aplicada=90,
            data_prevista_troca=timezone.now().date() + timedelta(days=80),
            usuario_responsavel=self.tecnico,
            nome_trabalhador_confirmacao="João Silva",
            confirmacao_data_hora=timezone.now(),
            recibo_hash="HASH123456",
            status_assinatura='ASSINADO'
        )
        self.assertEqual(signed_delivery.status_assinatura, 'ASSINADO')
        self.assertEqual(signed_delivery.recibo_hash, "HASH123456")

    # 6. Configuração e consulta de Estoque Mínimo por Local (LocationStockMinimo)
    def test_location_stock_minimum(self):
        self.client.login(username="tecnico_sst", password="pwd")
        # Define estoque mínimo específico para o local SST
        LocationStockMinimo.objects.create(product_variant=self.variant_m, location=self.loc_sst, estoque_minimo=5)
        
        min_val = get_location_minimum_stock(self.loc_sst, self.variant_m)
        self.assertEqual(min_val, 5)

    # 7. Dashboard exibição e ordenação por criticidade
    def test_dashboard_critical_stock_sorting(self):
        self.client.login(username="tecnico_sst", password="pwd")
        
        # variant_m tem saldo 2 e mínimo 5 (saldo < mínimo) no Estoque SST
        LocationStockMinimo.objects.create(product_variant=self.variant_m, location=self.loc_sst, estoque_minimo=5)
        
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        below_min = response.context['below_min']
        
        self.assertTrue(len(below_min) > 0)
        
        # Valida que o item com saldo 0 vem primeiro na ordenação por criticidade
        first_item = below_min[0]
        self.assertEqual(first_item['saldo'], 0)
        
        # Valida que o item do Estoque SST com saldo 2 e mínimo 5 está presente com a situação correta
        sst_items = [item for item in below_min if item['location'] == self.loc_sst.nome and item['tamanho'] == 'M']
        self.assertEqual(len(sst_items), 1)
        self.assertEqual(sst_items[0]['situacao'], 'ABAIXO')
        self.assertEqual(sst_items[0]['faltante'], 3)

