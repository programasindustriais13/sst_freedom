from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from organizations.models import Company, Unit, CostCenter, InventoryLocation
from ppe.models import Product, ProductVariant
from inventory.models import Supplier, FiscalNote, Lot, StockMovement

User = get_user_model()

class FiscalNoteSimplificationTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        self.cc = CostCenter.objects.create(company=self.company, codigo="CC-01", nome="Centro de Custo 1")
        self.loc_almox = InventoryLocation.objects.create(unit=self.unit, codigo="ALM-01", nome="Almoxarifado Geral", tipo="ALMOXARIFADO")
        
        # Almoxarife user (authorized)
        self.almoxarife = User.objects.create_user(username="almoxarife", password="pwd", profile_type="ALMOXARIFE")
        self.almoxarife.units.add(self.unit)
        
        # Standard employee (unauthorized)
        self.unauthorized_user = User.objects.create_user(username="employee", password="pwd", profile_type="COLABORADOR")
        
        # Product & Variant
        self.product = Product.objects.create(nome="Bota de Couro", categoria="CALCADOS", exige_ca=False)
        self.variant = ProductVariant.objects.create(product=self.product, tamanho="41", sku="BOT-41")
        self.product2 = Product.objects.create(nome="Óculos de Proteção", categoria="OCULOS", exige_ca=False)
        self.variant2 = ProductVariant.objects.create(product=self.product2, tamanho="U", sku="OCU-U")

        # Supplier
        self.supplier = Supplier.objects.create(razao_social="Fornecedor de EPIs LTDA", cnpj_cpf="98765432100019")

    def test_add_page_accessible_to_authorized(self):
        self.client.login(username="almoxarife", password="pwd")
        response = self.client.get(reverse('fiscal_note_create'))
        self.assertEqual(response.status_code, 200)

    def test_add_page_unauthorized_denied(self):
        # Usuário não autenticado deve ser redirecionado
        response = self.client.get(reverse('fiscal_note_create'))
        self.assertEqual(response.status_code, 302)

    def test_html_does_not_contain_novo_button_or_lote_validade_inputs(self):
        self.client.login(username="almoxarife", password="pwd")
        response = self.client.get(reverse('fiscal_note_create'))
        html = response.content.decode('utf-8')
        
        # Verifica se o botão "Novo" (que aciona a modal de criação rápida) foi removido
        self.assertNotIn('onclick="openNewProductModalFor', html)
        self.assertNotIn('title="Cadastrar Novo Produto"', html)
        
        # Verifica se os inputs de Lote e Validade foram removidos
        self.assertNotIn('id="prod_lote_', html)
        self.assertNotIn('id="prod_validade_', html)
        self.assertNotIn('>Validade</th>', html)
        self.assertNotIn('>Lote Fabr.</th>', html)

    def test_save_fiscal_note_without_lote_and_validade_success(self):
        self.client.login(username="almoxarife", password="pwd")
        
        import json
        items_data = [
            {
                'product_id': self.product.id,
                'tamanho': '41',
                'ca_numero': '',
                'identificador': '',
                'data_validade': '',
                'quantidade': 10,
                'custo_unitario': 25.0
            }
        ]
        
        data = {
            'tipo': 'NOTA_FISCAL',
            'supplier': self.supplier.id,
            'unit': self.unit.id,
            'numero': '555666',
            'serie': '1',
            'centro_custo': self.cc.id,
            'data_emissao': timezone.now().date().isoformat(),
            'data_recebimento': timezone.now().date().isoformat(),
            'frete': '0.00',
            'desconto': '0.00',
            'valor_total': '250.00',
            'items_json': json.dumps(items_data)
        }
        
        response = self.client.post(reverse('fiscal_note_create'), data)
        self.assertEqual(response.status_code, 302)
        
        fn = FiscalNote.objects.get(numero='555666')
        self.assertEqual(fn.status, 'CONFERIDA')
        
        lot = fn.lots.get(product_variant=self.variant)
        self.assertTrue(lot.identificador.startswith('NF-555666-'))
        self.assertEqual(lot.quantidade_inicial, 10)
        self.assertEqual(lot.custo_unitario, 25.0)
        self.assertIsNotNone(lot.data_validade)
        
        movement = StockMovement.objects.get(lot=lot, movement_type='ENTRADA_COMPRA')
        self.assertEqual(movement.quantity, 10)
        self.assertEqual(movement.location, self.loc_almox)

    def test_save_fiscal_note_multiple_items_success(self):
        self.client.login(username="almoxarife", password="pwd")
        
        import json
        items_data = [
            {
                'product_id': self.product.id,
                'tamanho': '41',
                'ca_numero': '',
                'identificador': '',
                'data_validade': '',
                'quantidade': 10,
                'custo_unitario': 25.0
            },
            {
                'product_id': self.product2.id,
                'tamanho': 'U',
                'ca_numero': '',
                'identificador': '',
                'data_validade': '',
                'quantidade': 5,
                'custo_unitario': 10.0
            }
        ]
        
        data = {
            'tipo': 'NOTA_FISCAL',
            'supplier': self.supplier.id,
            'unit': self.unit.id,
            'numero': '777888',
            'serie': '1',
            'centro_custo': self.cc.id,
            'data_emissao': timezone.now().date().isoformat(),
            'data_recebimento': timezone.now().date().isoformat(),
            'frete': '0.00',
            'desconto': '0.00',
            'valor_total': '300.00',
            'items_json': json.dumps(items_data)
        }
        
        response = self.client.post(reverse('fiscal_note_create'), data)
        self.assertEqual(response.status_code, 302)
        
        fn = FiscalNote.objects.get(numero='777888')
        self.assertEqual(fn.lots.count(), 2)
        
        for lot in fn.lots.all():
            self.assertTrue(lot.identificador.startswith('NF-777888-'))
