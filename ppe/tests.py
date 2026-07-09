from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import timedelta
from organizations.models import Company, Unit, Sector, CostCenter, Function, InventoryLocation
from employees.models import Employee
from inventory.models import Supplier, FiscalNote, Lot, StockMovement
from inventory.services import confirm_fiscal_note, get_stock_balance, InsufficientStockError
from .models import Product, ProductVariant, PPEMatrix, PPEDelivery, ExtraordinaryPPE
from .services import deliver_ppe, confirm_delivery_signature, return_ppe, write_off_ppe

User = get_user_model()

class PPEServicesTestCase(TestCase):
    def setUp(self):
        # Base setup
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        self.sector = Sector.objects.create(unit=self.unit, nome="Manutenção", codigo="MAN-01")
        self.cc = CostCenter.objects.create(company=self.company, codigo="CC-01", nome="Centro de Custo 1")
        self.funcao = Function.objects.create(company=self.company, nome="Eletricista")
        
        # Estoque SST
        self.loc_sst = InventoryLocation.objects.create(unit=self.unit, codigo="SST-01", nome="Estoque SST", tipo="SST")

        # User
        self.user = User.objects.create_user(username="tecnico", password="pwd", profile_type="TECNICO_SST")
        self.user.units.add(self.unit)

        # Employee
        self.employee = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            matricula="M-999",
            nome_completo="João da Silva",
            cpf="111.222.333-44",
            funcao=self.funcao,
            setor=self.sector,
            centro_custo=self.cc,
            data_admissao=timezone.now().date()
        )

        # Product & Variant
        self.product = Product.objects.create(nome="Bota de Couro com Biqueira", categoria="CALCADOS", exige_ca=True)
        self.variant = ProductVariant.objects.create(product=self.product, tamanho="41", sku="BOT-41")

        # Supplier
        self.supplier = Supplier.objects.create(razao_social="Fornecedor Teste", cnpj_cpf="77777777000188")

        # Fiscal Note to give initial stock to SST (via Almox -> Transfer -> SST, or directly creating a Lot/Movement for brevity)
        self.note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            numero="888",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cc,
            valor_total=100.0,
            usuario=self.user,
            status="CONFERIDA"
        )
        self.lot = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant,
            identificador="LOT-BOOT-01",
            data_validade=timezone.now().date() + timedelta(days=180),
            quantidade_inicial=5,
            custo_unitario=20.0
        )
        
        # Directly put balance in SST location for the test
        StockMovement.objects.create(
            unit=self.unit,
            location=self.loc_sst,
            product_variant=self.variant,
            lot=self.lot,
            quantity=5,
            cost_unit=20.0,
            movement_type="ENTRADA_COMPRA",
            user=self.user
        )

        # Setup PPE Matrix
        self.matrix = PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product,
            quantidade_padrao=1,
            vida_util_dias=120,
            ativo=True
        )

    def test_deliver_ppe_matrix_success(self):
        # João should have 5 Boots in SST. Let's deliver 1 boot.
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 5)
        
        delivery = deliver_ppe(
            employee=self.employee,
            product_variant=self.variant,
            lot=self.lot,
            quantity=1,
            user=self.user,
            data_entrega=timezone.now().date(),
            natureza_entrega='FORNECIMENTO_INICIAL'
        )

        self.assertEqual(delivery.quantidade, 1)
        self.assertEqual(delivery.vida_util_aplicada, 120)  # matching matrix entry
        self.assertEqual(delivery.origem_necessidade, 'MATRIZ')
        self.assertEqual(delivery.status_assinatura, 'PENDENTE')

        # Stock balance in SST should be 4
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 4)

    def test_deliver_ppe_insufficient_stock(self):
        with self.assertRaises(InsufficientStockError):
            deliver_ppe(
                employee=self.employee,
                product_variant=self.variant,
                lot=self.lot,
                quantity=10, # only has 5
                user=self.user,
                data_entrega=timezone.now().date(),
                natureza_entrega='FORNECIMENTO_INICIAL'
            )

    def test_deliver_ppe_extraordinary(self):
        # Create an extraordinary PPE allowance of 60 days
        ExtraordinaryPPE.objects.create(
            employee=self.employee,
            product=self.product,
            quantidade=1,
            vida_util_dias=60,
            motivo="Ambiente úmido temporário",
            data_inicio=timezone.now().date()
        )

        delivery = deliver_ppe(
            employee=self.employee,
            product_variant=self.variant,
            lot=self.lot,
            quantity=1,
            user=self.user,
            data_entrega=timezone.now().date(),
            natureza_entrega='SUBSTITUICAO'
        )

        self.assertEqual(delivery.vida_util_aplicada, 60) # overrides matrix
        self.assertEqual(delivery.origem_necessidade, 'EXTRAORDINARIA')

    def test_confirm_signature_success(self):
        delivery = deliver_ppe(
            employee=self.employee,
            product_variant=self.variant,
            lot=self.lot,
            quantity=1,
            user=self.user,
            data_entrega=timezone.now().date(),
            natureza_entrega='FORNECIMENTO_INICIAL'
        )

        self.assertEqual(delivery.status_assinatura, 'PENDENTE')
        confirm_delivery_signature(delivery, "João da Silva")
        
        delivery.refresh_from_db()
        self.assertEqual(delivery.status_assinatura, 'ASSINADO')
        self.assertEqual(delivery.nome_trabalhador_confirmacao, "João da Silva")
        self.assertIsNotNone(delivery.recibo_hash)

    def test_return_reusable_ppe(self):
        delivery = deliver_ppe(
            employee=self.employee,
            product_variant=self.variant,
            lot=self.lot,
            quantity=2,
            user=self.user,
            data_entrega=timezone.now().date(),
            natureza_entrega='FORNECIMENTO_INICIAL'
        )
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 3)

        # João returns 1 boot reusable
        return_ppe(delivery, 1, 'REUTILIZAVEL', self.user)

        delivery.refresh_from_db()
        self.assertEqual(delivery.quantidade, 1) # reduced
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 4) # returned to SST

    def test_return_discarded_ppe(self):
        delivery = deliver_ppe(
            employee=self.employee,
            product_variant=self.variant,
            lot=self.lot,
            quantity=2,
            user=self.user,
            data_entrega=timezone.now().date(),
            natureza_entrega='FORNECIMENTO_INICIAL'
        )
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 3)

        # João returns 1 boot discarded (damaged)
        return_ppe(delivery, 1, 'DANIFICADO', self.user)

        delivery.refresh_from_db()
        self.assertEqual(delivery.quantidade, 1)
        # Should NOT return to SST usable stock, balance remains 3
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 3)

    def test_write_off_ppe_success(self):
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 5)
        
        write_off_ppe(
            unit=self.unit,
            location=self.loc_sst,
            product_variant=self.variant,
            lot=self.lot,
            quantity=2,
            reason='PERDA',
            user=self.user,
            notes="Extravio no vestiário."
        )

        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 3)
