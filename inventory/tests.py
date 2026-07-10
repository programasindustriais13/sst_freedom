from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import timedelta
from organizations.models import Company, Unit, CostCenter, InventoryLocation
from ppe.models import Product, ProductVariant
from .models import Supplier, FiscalNote, Lot, StockMovement, StockTransfer, StockTransferItem
from .services import confirm_fiscal_note, cancel_fiscal_note, expedite_transfer, receive_transfer, get_stock_balance, InsufficientStockError

User = get_user_model()

class InventoryServicesTestCase(TestCase):
    def setUp(self):
        # Setup basic company structure
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        self.cc = CostCenter.objects.create(company=self.company, codigo="CC-01", nome="Centro de Custo 1")
        
        # Locations
        self.loc_almox = InventoryLocation.objects.create(unit=self.unit, codigo="ALM-01", nome="Almoxarifado Geral", tipo="ALMOXARIFADO")
        self.loc_sst = InventoryLocation.objects.create(unit=self.unit, codigo="SST-01", nome="Estoque SST", tipo="SST")
        
        # User
        self.user = User.objects.create_user(username="almoxarife", password="pwd", profile_type="ALMOXARIFE")
        self.user.units.add(self.unit)

        # Product
        self.product = Product.objects.create(nome="Óculos de Proteção", categoria="OCULOS", exige_ca=True)
        self.variant = ProductVariant.objects.create(product=self.product, tamanho="Único", sku="OCU-UNI", estoque_minimo=5)

        # Supplier
        self.supplier = Supplier.objects.create(razao_social="Fornecedor de EPIs LTDA", cnpj_cpf="98765432100019")

        # Fiscal Note
        self.note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            numero="100200",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cc,
            valor_total=150.0,
            usuario=self.user,
            status="RASCUNHO"
        )

        # Lot
        self.lot = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant,
            identificador="LOT-001",
            data_validade=timezone.now().date() + timedelta(days=365),
            quantidade_inicial=10,
            custo_unitario=15.0
        )

    def test_get_stock_balance_empty(self):
        balance = get_stock_balance(self.loc_almox, self.variant, self.lot)
        self.assertEqual(balance, 0)

    def test_confirm_fiscal_note_success(self):
        self.assertEqual(self.note.status, "RASCUNHO")
        confirm_fiscal_note(self.note, self.user)
        
        # Reload Note
        self.note.refresh_from_db()
        self.assertEqual(self.note.status, "CONFERIDA")

        # Verify stock movement entry
        balance = get_stock_balance(self.loc_almox, self.variant, self.lot)
        self.assertEqual(balance, 10)

    def test_cancel_fiscal_note_success(self):
        confirm_fiscal_note(self.note, self.user)
        cancel_fiscal_note(self.note, self.user, "Cancelamento solicitado pelo técnico.")
        
        self.note.refresh_from_db()
        self.assertEqual(self.note.status, "CANCELADA")
        
        # Verify balance back to zero
        balance = get_stock_balance(self.loc_almox, self.variant, self.lot)
        self.assertEqual(balance, 0)

    def test_cancel_fiscal_note_insufficient_stock(self):
        confirm_fiscal_note(self.note, self.user)
        
        # Simulates a delivery or reduction that leaves stock insufficient to cancel
        StockMovement.objects.create(
            unit=self.unit,
            location=self.loc_almox,
            product_variant=self.variant,
            lot=self.lot,
            quantity=-5,
            cost_unit=15.0,
            movement_type="OUTROS",
            user=self.user
        )
        
        # Try to cancel
        with self.assertRaises(InsufficientStockError):
            cancel_fiscal_note(self.note, self.user, "Erro de digitação.")

    def test_transfer_workflow_success(self):
        # 1. Give stock to Almoxarifado
        confirm_fiscal_note(self.note, self.user)
        
        # 2. Create Stock Transfer
        transfer = StockTransfer.objects.create(
            unit=self.unit,
            source_location=self.loc_almox,
            dest_location=self.loc_sst,
            criado_por=self.user,
            status="RASCUNHO"
        )
        
        # 3. Add Item to transfer
        item = StockTransferItem.objects.create(
            transfer=transfer,
            product_variant=self.variant,
            lot=self.lot,
            quantity_sent=4
        )

        # 4. Expedite Transfer
        expedite_transfer(transfer, self.user)
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, "EXPEDIDA")

        # Almoxarifado stock should be reduced by 4, but SST stock is not yet increased
        self.assertEqual(get_stock_balance(self.loc_almox, self.variant, self.lot), 6)
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 0)

        # 5. Receive Transfer
        receive_transfer(transfer, self.user, {item.id: 4})
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, "RECEBIDA")
        
        # SST Stock increases by 4
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 4)

    def test_transfer_with_discrepancy(self):
        confirm_fiscal_note(self.note, self.user)
        transfer = StockTransfer.objects.create(
            unit=self.unit,
            source_location=self.loc_almox,
            dest_location=self.loc_sst,
            criado_por=self.user,
            status="RASCUNHO"
        )
        item = StockTransferItem.objects.create(
            transfer=transfer,
            product_variant=self.variant,
            lot=self.lot,
            quantity_sent=5
        )
        
        expedite_transfer(transfer, self.user)
        
        # Receives only 3 (2 lost/discrepant)
        receive_transfer(transfer, self.user, {item.id: 3}, "Duas unidades danificadas no transporte.")
        
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, "RECEBIDA_COM_DIVERGENCIA")
        self.assertEqual(get_stock_balance(self.loc_sst, self.variant, self.lot), 3)
        # Note that the lost units are written off from transit, so Almox is still reduced by 5, SST has 3.
        self.assertEqual(get_stock_balance(self.loc_almox, self.variant, self.lot), 5)


from audit.models import AuditLog

class FiscalNoteAndAuditTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        self.cc = CostCenter.objects.create(company=self.company, codigo="CC-01", nome="Centro de Custo 1")
        self.user = User.objects.create_user(username="almoxarife2", password="pwd", profile_type="ALMOXARIFE")
        self.supplier = Supplier.objects.create(razao_social="Fornecedor de EPIs LTDA", cnpj_cpf="98765432100019")

    def test_create_receipt_without_number_success(self):
        note = FiscalNote(
            supplier=self.supplier,
            unit=self.unit,
            tipo="RECIBO",
            numero=None,
            serie=None,
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cc,
            valor_total=100.0,
            usuario=self.user,
            status="RASCUNHO"
        )
        try:
            note.full_clean()
            note.save()
        except ValidationError:
            self.fail("ValidationError lançada para recibo sem número/série!")
        self.assertIsNotNone(note.id)

    def test_create_invoice_without_number_fails(self):
        note = FiscalNote(
            supplier=self.supplier,
            unit=self.unit,
            tipo="NOTA_FISCAL",
            numero=None,
            serie=None,
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cc,
            valor_total=100.0,
            usuario=self.user,
            status="RASCUNHO"
        )
        with self.assertRaises(ValidationError):
            note.full_clean()

    def test_audit_log_login_failed(self):
        AuditLog.objects.all().delete()
        self.client.post('/accounts/login/', {'username': 'usuario_inexistente', 'password': 'senha_errada'})
        logs = AuditLog.objects.filter(action__icontains="Tentativa de login falha")
        self.assertTrue(logs.exists())
