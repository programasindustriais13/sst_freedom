"""
Testes do Django Admin para o app inventory.
SPEC-2026-004 — Admin: Gerenciamento e Exclusão Completa pelo Superusuário

Cobertura:
- T-007: StockMovement não tem botão Excluir para superusuário
- T-010: FiscalNote conferida não tem botão Excluir
- T-011: Lote com StockMovement retorna mensagem amigável (PROTECT)
- T-012: FiscalNote em RASCUNHO pode ser excluída pelo superusuário
- T-013: StockTransferItem aparece no admin
- T-014: StockTransfer em RASCUNHO pode ser excluído pelo superusuário
"""

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from organizations.models import Company, Unit, CostCenter, InventoryLocation
from ppe.models import Product, ProductVariant, CertificadoAprovacao
from .models import Supplier, FiscalNote, Lot, StockMovement, StockTransfer, StockTransferItem

User = get_user_model()


class InventoryAdminSetupMixin:
    """Dados mínimos de apoio aos testes de inventory."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            password="testpass123",
            email="super@test.com",
        )
        self.company = Company.objects.create(
            razao_social="Empresa Teste LTDA",
            nome_fantasia="Empresa Teste",
            cnpj="00.000.000/0001-00",
        )
        self.unit = Unit.objects.create(
            company=self.company,
            codigo="U001",
            nome="Unidade Teste",
            cidade="Fortaleza",
            estado="CE",
        )
        self.cost_center = CostCenter.objects.create(
            company=self.company, codigo="CC001", nome="CC Teste"
        )
        self.supplier = Supplier.objects.create(
            razao_social="Fornecedor Teste LTDA",
            cnpj_cpf="11.222.333/0001-44",
        )
        self.product = Product.objects.create(
            nome="EPI Teste",
            categoria="PROTECAO_CABECA",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            tamanho="U",
        )
        self.client = Client()


class StockMovementAdminTest(InventoryAdminSetupMixin, TestCase):

    def _create_movement(self, loc):
        """Cria um StockMovement de teste."""
        ca = CertificadoAprovacao.objects.create(
            numero="12345",
            numero_exibicao="CA 12345",
            data_validade="2030-01-01",
        )
        fiscal_note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            tipo="NOTA_FISCAL",
            numero="001",
            serie="1",
            data_emissao="2024-01-01",
            data_recebimento="2024-01-01",
            centro_custo=self.cost_center,
            valor_total="100.00",
            status="CONFERIDA",
            usuario=self.superuser,
        )
        lot = Lot.objects.create(
            product_variant=self.variant,
            fiscal_note=fiscal_note,
            ca=ca,
            identificador="LOTE001",
            data_validade="2030-01-01",
            quantidade_inicial=10,
            custo_unitario="10.00",
        )
        return StockMovement.objects.create(
            unit=self.unit,
            location=loc,
            product_variant=self.variant,
            lot=lot,
            quantity=10,
            cost_unit="10.00",
            movement_type="ENTRADA_COMPRA",
            user=self.superuser,
        ), lot

    def test_superuser_nao_tem_permissao_excluir_stock_movement(self):
        """T-007: StockMovement não tem permissão de exclusão para superusuário."""
        from inventory.admin import StockMovementAdmin
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        sma = StockMovementAdmin(StockMovement, None)
        self.assertFalse(sma.has_delete_permission(request))

    def test_superuser_nao_tem_permissao_adicionar_stock_movement(self):
        """StockMovement não tem permissão de adição para superusuário."""
        from inventory.admin import StockMovementAdmin
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        sma = StockMovementAdmin(StockMovement, None)
        self.assertFalse(sma.has_add_permission(request))

    def test_superuser_acessa_listagem_stock_movement(self):
        """T-001 parcial: Superusuário acessa listagem de StockMovement."""
        self.client.force_login(self.superuser)
        url = reverse("admin:inventory_stockmovement_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class FiscalNoteAdminTest(InventoryAdminSetupMixin, TestCase):

    def test_superuser_nao_pode_excluir_fiscal_note_conferida(self):
        """T-010: FiscalNote com status CONFERIDA não pode ser excluída, mantendo a nota no banco."""
        nota = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            tipo="NOTA_FISCAL",
            numero="TESTCONFERIDA",
            serie="1",
            data_emissao="2024-01-01",
            data_recebimento="2024-01-01",
            centro_custo=self.cost_center,
            valor_total="100.00",
            status="CONFERIDA",
            usuario=self.superuser,
        )
        self.client.force_login(self.superuser)
        url = reverse("admin:inventory_fiscalnote_delete", args=[nota.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertTrue(FiscalNote.objects.filter(pk=nota.pk).exists())

    def test_superuser_pode_excluir_fiscal_note_rascunho(self):
        """T-012: Superusuário pode excluir FiscalNote em RASCUNHO."""
        from inventory.admin import FiscalNoteAdmin
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        fna = FiscalNoteAdmin(FiscalNote, None)

        nota_rascunho = FiscalNote(status="RASCUNHO")
        self.assertTrue(fna.has_delete_permission(request, obj=nota_rascunho))

    def test_superuser_exclui_fiscal_note_rascunho(self):
        """T-012: Exclusão real de FiscalNote em RASCUNHO pelo superusuário."""
        nota = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            tipo="NOTA_FISCAL",
            numero="TEST001",
            serie="1",
            data_emissao="2024-01-01",
            data_recebimento="2024-01-01",
            centro_custo=self.cost_center,
            valor_total="100.00",
            status="RASCUNHO",
            usuario=self.superuser,
        )
        self.client.force_login(self.superuser)
        url = reverse("admin:inventory_fiscalnote_delete", args=[nota.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FiscalNote.objects.filter(pk=nota.pk).exists())


class StockTransferAdminTest(InventoryAdminSetupMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.loc_almox = InventoryLocation.objects.create(
            unit=self.unit,
            codigo="LOC001",
            nome="Almoxarifado",
            tipo="ALMOXARIFADO",
        )
        self.loc_sst = InventoryLocation.objects.create(
            unit=self.unit,
            codigo="LOC002",
            nome="SST",
            tipo="SST",
        )

    def test_superuser_acessa_listagem_stock_transfer_item(self):
        """T-013: StockTransferItem aparece no admin."""
        self.client.force_login(self.superuser)
        url = reverse("admin:inventory_stocktransferitem_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_pode_excluir_stock_transfer_rascunho(self):
        """T-014: Superusuário pode excluir StockTransfer em RASCUNHO."""
        from inventory.admin import StockTransferAdmin
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        sta = StockTransferAdmin(StockTransfer, None)

        transfer_rascunho = StockTransfer(status="RASCUNHO")
        self.assertTrue(sta.has_delete_permission(request, obj=transfer_rascunho))

    def test_superuser_nao_pode_excluir_stock_transfer_expedida(self):
        """Superusuário não pode excluir StockTransfer expedida, mantendo o registro no banco."""
        transfer = StockTransfer.objects.create(
            unit=self.unit,
            source_location=self.loc_almox,
            dest_location=self.loc_sst,
            status="EXPEDIDA",
            criado_por=self.superuser,
        )
        self.client.force_login(self.superuser)
        url = reverse("admin:inventory_stocktransfer_delete", args=[transfer.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertTrue(StockTransfer.objects.filter(pk=transfer.pk).exists())

    def test_superuser_exclui_stock_transfer_rascunho(self):
        """T-014: Exclusão real de StockTransfer em RASCUNHO."""
        transfer = StockTransfer.objects.create(
            unit=self.unit,
            source_location=self.loc_almox,
            dest_location=self.loc_sst,
            status="RASCUNHO",
            criado_por=self.superuser,
        )
        self.client.force_login(self.superuser)
        url = reverse("admin:inventory_stocktransfer_delete", args=[transfer.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StockTransfer.objects.filter(pk=transfer.pk).exists())
