import os
import io
from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from PIL import Image

from organizations.models import Company, Unit, Sector, Function, CostCenter
from employees.models import Employee
from ppe.models import Product, ProductVariant, PPEMatrix, SectorPPEMatrix, PPEDelivery, CertificadoAprovacao
from ppe.services import resolve_employee_ppe_matrix, deliver_ppe
from inventory.models import Supplier, FiscalNote, Lot, InventoryLocation, StockMovement, LocationStockMinimo

User = get_user_model()


class SPEC2026015ImplementationTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            razao_social="Empresa Teste SPEC 015 LTDA",
            nome_fantasia="Empresa Teste",
            cnpj="11.222.333/0001-99"
        )
        self.unit = Unit.objects.create(
            company=self.company,
            nome="Unidade Matriz",
            codigo="UN-01"
        )
        self.sector = Sector.objects.create(
            unit=self.unit,
            nome="Oficina Central",
            codigo="OFI-01"
        )
        self.funcao = Function.objects.create(
            company=self.company,
            nome="Mecânico Geral"
        )
        self.cost_center = CostCenter.objects.create(
            company=self.company,
            nome="Operações",
            codigo="CC-100"
        )

        self.user = User.objects.create_user(
            username="tecnico_teste",
            password="pwd",
            profile_type="TECNICO_SST"
        )
        self.user.units.add(self.unit)

        self.product = Product.objects.create(
            nome="Óculos de Proteção Incolor",
            categoria="OCULOS",
            tipo_produto="EPI",
            exige_ca=False
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            tamanho="Único",
            sku="OC-001"
        )

        self.loc_sst = InventoryLocation.objects.create(
            unit=self.unit,
            nome="Estoque SST",
            codigo="SST-LOC",
            tipo="SST"
        )

        self.supplier = Supplier.objects.create(
            razao_social="Fornecedor EPIs",
            cnpj_cpf="22.333.444/0001-55"
        )

    # -------------------------------------------------------------
    # 1. Simplificação do Cadastro de Colaborador
    # -------------------------------------------------------------
    def test_employee_simplified_fields_nullable_and_display(self):
        # Colaborador cadastrado sem matrícula, função e admissão
        emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Carlos Sem Matricula",
            cpf="999.888.777-66",
            matricula=None,
            funcao=None,
            data_admissao=None
        )
        self.assertIsNone(emp.matricula)
        self.assertIsNone(emp.funcao)
        self.assertIsNone(emp.data_admissao)
        self.assertIn(f"#{emp.id}", emp.identificacao_display)
        self.assertIn(f"#{emp.id}", str(emp))

    def test_employee_matricula_empty_string_normalized_to_none(self):
        emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Maria Normalizada",
            cpf="999.888.777-55",
            matricula="   "
        )
        self.assertIsNone(emp.matricula)

    # -------------------------------------------------------------
    # 2. Matriz de EPI por Setor & Resolução com Fallback Transitório
    # -------------------------------------------------------------
    def test_resolve_ppe_matrix_sector_active_takes_precedence(self):
        # Cria matriz por setor com status ATIVA
        sec_config = SectorPPEMatrix.objects.create(
            sector=self.sector,
            status='ATIVA',
            ativado_por=self.user
        )
        matrix_sector = PPEMatrix.objects.create(
            setor=self.sector,
            product=self.product,
            vida_util_dias=180,
            ativo=True
        )

        # Cria matriz legada por função
        matrix_funcao = PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product,
            vida_util_dias=90,
            ativo=True
        )

        emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            funcao=self.funcao,
            nome_completo="Roberto Operador",
            cpf="111.111.111-22"
        )

        qs, origin = resolve_employee_ppe_matrix(emp)
        self.assertEqual(origin, 'SETOR')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().vida_util_dias, 180)

    def test_sector_matrix_no_fallback_to_function(self):
        # Setor em elaboração (não ativo): mesmo que haja função com matriz legada no banco,
        # resolve_employee_ppe_matrix NÃO consulta a função e retorna vazio e None
        sec_config = SectorPPEMatrix.objects.create(
            sector=self.sector,
            status='EM_ELABORACAO'
        )
        matrix_funcao = PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product,
            vida_util_dias=120,
            ativo=True
        )

        emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            funcao=self.funcao,
            nome_completo="Ana Sem Fallback",
            cpf="222.222.222-33"
        )

        qs, origin = resolve_employee_ppe_matrix(emp)
        self.assertIsNone(origin)
        self.assertEqual(qs.count(), 0)

    def test_sector_matrix_exclusive_constraint(self):
        from django.core.exceptions import ValidationError
        # Não pode ter ambos setor e funcao
        item = PPEMatrix(
            setor=self.sector,
            funcao=self.funcao,
            product=self.product,
            vida_util_dias=60
        )
        with self.assertRaises(ValidationError):
            item.clean()

    # -------------------------------------------------------------
    # 3. Relatório de Consumo e Custo de EPIs
    # -------------------------------------------------------------
    def test_report_ppe_consumption_cost_view(self):
        emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Lucas Consumo",
            cpf="333.333.333-44"
        )

        # Cria lote com custo
        note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            numero="NF-100",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('150.00'),
            usuario=self.user,
            status="CONFERIDA"
        )
        lot = Lot.objects.create(
            fiscal_note=note,
            product_variant=self.variant,
            identificador="LOTE-01",
            data_validade=timezone.now().date() + timezone.timedelta(days=365),
            quantidade_inicial=10,
            custo_unitario=Decimal('15.00')
        )

        # Entrega 3 unidades
        delivery = PPEDelivery.objects.create(
            unit=self.unit,
            employee=emp,
            setor=self.sector,
            centro_custo=self.cost_center,
            product_variant=self.variant,
            lot=lot,
            quantidade=3,
            custo_unitario=Decimal('15.00'),
            vida_util_aplicada=180,
            usuario_responsavel=self.user,
            data_entrega=timezone.now().date(),
            data_prevista_troca=timezone.now().date() + timezone.timedelta(days=180),
            validade_fisica=timezone.now().date() + timezone.timedelta(days=180),
            origem_necessidade="EXTRAORDINARIA",
            status_assinatura="ASSINADO"
        )

        self.client.login(username="tecnico_teste", password="pwd")
        url = reverse('report_ppe_consumption_cost')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_pecas'], 3)
        self.assertEqual(response.context['total_custo'], Decimal('45.00'))
        self.assertEqual(response.context['itens_sem_custo'], 0)
        self.assertContains(response, "Oficina Central")
        self.assertContains(response, "Lucas Consumo")

    # -------------------------------------------------------------
    # 4. Anexo de Nota Fiscal / Recibo e Download Seguro
    # -------------------------------------------------------------
    def test_fiscal_note_attachment_validation_and_download(self):
        # Validação de PDF legítimo
        pdf_content = b"%PDF-1.4\n%test pdf content\n%%EOF"
        pdf_file = SimpleUploadedFile("nota.pdf", pdf_content, content_type="application/pdf")

        note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            numero="NF-ANEXO-1",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('50.00'),
            usuario=self.user,
            status="RASCUNHO",
            documento_anexo=pdf_file
        )
        self.assertTrue(note.documento_anexo)

        self.client.login(username="tecnico_teste", password="pwd")
        download_url = reverse('fiscal_note_download_attachment', kwargs={'pk': note.pk})
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        response.close()

        # Teste de exclusão de anexo em nota rascunho
        delete_url = reverse('fiscal_note_delete_attachment', kwargs={'pk': note.pk})
        del_resp = self.client.post(delete_url)
        self.assertEqual(del_resp.status_code, 302)
        note.refresh_from_db()
        self.assertFalse(note.documento_anexo)

    def test_fiscal_note_attachment_invalid_content_rejected(self):
        from django.core.exceptions import ValidationError
        fake_pdf = SimpleUploadedFile("fake.pdf", b"NOT A REAL PDF HEADER", content_type="application/pdf")
        note = FiscalNote(
            supplier=self.supplier,
            unit=self.unit,
            numero="NF-FAKE",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('10.00'),
            usuario=self.user,
            documento_anexo=fake_pdf
        )
        with self.assertRaises(ValidationError):
            note.clean()

    # -------------------------------------------------------------
    # 5. Usabilidade do Estoque Mínimo (AJAX e Fallback de Âncora)
    # -------------------------------------------------------------
    def test_minimum_stock_update_ajax(self):
        self.client.login(username="tecnico_teste", password="pwd")
        url = reverse('minimum_stock_update')
        post_data = {
            'variant_id': self.variant.id,
            'location_id': self.loc_sst.id,
            'estoque_minimo': '25'
        }
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['minimo'], 25)
        self.assertEqual(data['variant_id'], self.variant.id)

        # Verifica persistência no banco
        min_obj = LocationStockMinimo.objects.get(product_variant=self.variant, location=self.loc_sst)
        self.assertEqual(min_obj.estoque_minimo, 25)

    def test_minimum_stock_update_fallback_redirect_with_anchor(self):
        self.client.login(username="tecnico_teste", password="pwd")
        url = reverse('minimum_stock_update')
        post_data = {
            'variant_id': self.variant.id,
            'location_id': self.loc_sst.id,
            'estoque_minimo': '30',
            'next': '/inventory/minimum-stock/'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        expected_anchor = f"#item-{self.variant.id}-{self.loc_sst.id}"
        self.assertIn(expected_anchor, response.url)
