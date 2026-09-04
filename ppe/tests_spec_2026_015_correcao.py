import logging
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from organizations.models import Company, Unit, Sector, CostCenter, Function, InventoryLocation
from employees.models import Employee
from employees.forms import EmployeeForm
from inventory.models import Lot, FiscalNote, Supplier
from ppe.models import Product, ProductVariant, PPEMatrix, SectorPPEMatrix, PPEDelivery, ExtraordinaryPPE
from ppe.forms import PPEMatrixItemForm, PPEMatrixSectorFormSet, PPEMatrixSectorChoiceForm
from ppe.services import resolve_employee_ppe_matrix, deliver_ppe

User = get_user_model()


def make_valid_cpf(seed=1):
    digits = [int(d) for d in f"{seed:09d}"]
    s1 = sum(digits[i] * (10 - i) for i in range(9))
    d1 = ((s1 * 10) % 11) % 10
    digits.append(d1)
    s2 = sum(digits[i] * (11 - i) for i in range(10))
    d2 = ((s2 * 10) % 11) % 10
    digits.append(d2)
    s = "".join(str(d) for d in digits)
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


class BaseSpec015CorrectionTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            razao_social="Pneus Freedom Indústria e Comércio LTDA",
            nome_fantasia="Pneus Freedom",
            cnpj="12.345.678/0001-90"
        )
        self.other_company = Company.objects.create(
            razao_social="Outra Empresa LTDA",
            nome_fantasia="Outra Empresa",
            cnpj="98.765.432/0001-10"
        )

        self.supplier = Supplier.objects.create(
            razao_social="Fornecedor Padrão LTDA",
            cnpj_cpf="11.222.333/0001-44"
        )

        self.unit = Unit.objects.create(
            company=self.company,
            codigo="UN-NAT",
            nome="Unidade Natal",
            cidade="Natal",
            estado="RN"
        )
        self.other_unit = Unit.objects.create(
            company=self.other_company,
            codigo="UN-REC",
            nome="Unidade Recife",
            cidade="Recife",
            estado="PE"
        )

        self.sector = Sector.objects.create(unit=self.unit, nome="Oficina Mecânica")
        self.other_sector = Sector.objects.create(unit=self.other_unit, nome="Usinagem Recife")

        self.cost_center = CostCenter.objects.create(company=self.company, codigo="CC-01", nome="Manutenção")
        self.other_cost_center = CostCenter.objects.create(company=self.other_company, codigo="CC-02", nome="Operação")

        self.funcao_legada = Function.objects.create(company=self.company, nome="Eletricista Industrial")

        self.loc_sst = InventoryLocation.objects.create(
            unit=self.unit,
            nome="Estoque SST Natal",
            codigo="SST-NAT",
            tipo="SST"
        )

        self.user_tecnico = User.objects.create_user(
            username="tecnico_sst",
            password="pwd",
            profile_type="TECNICO_SST"
        )
        self.user_tecnico.units.add(self.unit)

        self.user_almoxarife = User.objects.create_user(
            username="almoxarife_user",
            password="pwd",
            profile_type="ALMOXARIFE"
        )
        self.user_almoxarife.units.add(self.unit)

        self.product = Product.objects.create(
            nome="Óculos de Proteção Incolor",
            categoria="OCULOS",
            tipo_produto="EPI"
        )
        self.product2 = Product.objects.create(
            nome="Luva de Vaqueta",
            categoria="LUVAS",
            tipo_produto="EPI"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            tamanho="Único",
            sku="OC-001"
        )
        self.variant2 = ProductVariant.objects.create(
            product=self.product2,
            tamanho="G",
            sku="LV-002"
        )


# ==============================================================================
# GRUPO A: FORMULÁRIO DE COLABORADOR (16 TESTES)
# ==============================================================================
class TestGroupAEmployeeForm(BaseSpec015CorrectionTestCase):

    def test_01_form_fields_no_matricula(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertNotIn('matricula', form.fields)

    def test_02_form_fields_no_telefone(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertNotIn('telefone', form.fields)

    def test_03_form_fields_no_email(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertNotIn('email', form.fields)

    def test_04_form_fields_no_unit(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertNotIn('unit', form.fields)

    def test_05_form_fields_no_funcao(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertNotIn('funcao', form.fields)

    def test_06_form_fields_no_data_admissao(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertNotIn('data_admissao', form.fields)

    def test_07_form_fields_has_company(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertIn('company', form.fields)

    def test_08_form_fields_has_setor(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertIn('setor', form.fields)

    def test_09_form_fields_has_nome_completo(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertIn('nome_completo', form.fields)

    def test_10_form_fields_has_cpf(self):
        form = EmployeeForm(user=self.user_tecnico)
        self.assertIn('cpf', form.fields)

    def test_11_unit_derived_from_setor_unit(self):
        valid_cpf = make_valid_cpf(11)
        form_data = {
            'company': self.company.id,
            'setor': self.sector.id,
            'centro_custo': self.cost_center.id,
            'nome_completo': "João Derivado",
            'cpf': valid_cpf,
            'turno': "TURNO_1",
            'situacao': "ATIVO"
        }
        form = EmployeeForm(data=form_data, user=self.user_tecnico)
        self.assertTrue(form.is_valid(), form.errors)
        emp = form.save()
        self.assertEqual(emp.unit, self.sector.unit)
        self.assertEqual(emp.unit.id, self.unit.id)

    def test_12_validation_company_mismatch_rejected(self):
        valid_cpf = make_valid_cpf(12)
        form_data = {
            'company': self.other_company.id,
            'setor': self.sector.id,
            'centro_custo': self.cost_center.id,
            'nome_completo': "Mário Divergente",
            'cpf': valid_cpf,
            'turno': "TURNO_1",
            'situacao': "ATIVO"
        }
        form = EmployeeForm(data=form_data, user=self.user_tecnico)
        self.assertFalse(form.is_valid())
        self.assertTrue('company' in form.errors or 'setor' in form.errors)

    def test_13_validation_setor_outside_user_units_rejected(self):
        valid_cpf = make_valid_cpf(13)
        form_data = {
            'company': self.other_company.id,
            'setor': self.other_sector.id,
            'centro_custo': self.other_cost_center.id,
            'nome_completo': "Paulo Invasor",
            'cpf': valid_cpf,
            'turno': "TURNO_1",
            'situacao': "ATIVO"
        }
        form = EmployeeForm(data=form_data, user=self.user_tecnico)
        self.assertFalse(form.is_valid())

    def test_14_edit_preserves_legacy_fields(self):
        valid_cpf = make_valid_cpf(14)
        emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Carlos Antigo",
            cpf=valid_cpf,
            matricula="MAT-9999",
            funcao=self.funcao_legada,
            data_admissao=timezone.now().date(),
            telefone="(84) 99999-0000",
            email="carlos@empresa.com"
        )
        form_data = {
            'company': self.company.id,
            'setor': self.sector.id,
            'centro_custo': self.cost_center.id,
            'nome_completo': "Carlos Antigo Atualizado",
            'cpf': valid_cpf,
            'turno': "ADM",
            'situacao': "ATIVO"
        }
        form = EmployeeForm(data=form_data, instance=emp, user=self.user_tecnico)
        self.assertTrue(form.is_valid(), form.errors)
        saved_emp = form.save()
        self.assertEqual(saved_emp.matricula, "MAT-9999")
        self.assertEqual(saved_emp.funcao, self.funcao_legada)
        self.assertEqual(saved_emp.telefone, "(84) 99999-0000")
        self.assertEqual(saved_emp.email, "carlos@empresa.com")
        self.assertEqual(saved_emp.nome_completo, "Carlos Antigo Atualizado")

    def test_15_create_saves_legacy_fields_as_none(self):
        valid_cpf = make_valid_cpf(15)
        form_data = {
            'company': self.company.id,
            'setor': self.sector.id,
            'centro_custo': self.cost_center.id,
            'nome_completo': "Novo Colaborador 2026",
            'cpf': valid_cpf,
            'turno': "TURNO_1",
            'situacao': "ATIVO"
        }
        form = EmployeeForm(data=form_data, user=self.user_tecnico)
        self.assertTrue(form.is_valid(), form.errors)
        emp = form.save()
        self.assertIsNone(emp.matricula)
        self.assertIsNone(emp.funcao)
        self.assertIsNone(emp.telefone)
        self.assertIsNone(emp.email)
        self.assertIsNone(emp.data_admissao)

    def test_16_normalization_cpf_and_whitespace(self):
        valid_cpf = make_valid_cpf(16)
        form_data = {
            'company': self.company.id,
            'setor': self.sector.id,
            'centro_custo': self.cost_center.id,
            'nome_completo': "  Nome Com Espaços   ",
            'cpf': f" {valid_cpf} ",
            'turno': "TURNO_1",
            'situacao': "ATIVO"
        }
        form = EmployeeForm(data=form_data, user=self.user_tecnico)
        self.assertTrue(form.is_valid(), form.errors)
        emp = form.save()
        self.assertEqual(emp.nome_completo, "Nome Com Espaços")
        self.assertEqual(emp.cpf, valid_cpf)


# ==============================================================================
# GRUPO B: VISUALIZAÇÃO E LISTAGEM DE COLABORADORES (6 TESTES)
# ==============================================================================
class TestGroupBEmployeeViews(BaseSpec015CorrectionTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(username="tecnico_sst", password="pwd")
        self.emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Severino Silva",
            cpf=make_valid_cpf(280)
        )

    def test_17_html_form_no_removed_fields_inputs(self):
        response = self.client.get(reverse('employee_create'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        for fld in ['name="matricula"', 'name="telefone"', 'name="email"', 'name="unit"', 'name="funcao"', 'name="data_admissao"']:
            self.assertNotIn(fld, content)

    def test_18_employee_detail_shows_company_and_derived_unit(self):
        response = self.client.get(reverse('employee_detail', kwargs={'pk': self.emp.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("Pneus Freedom", content)
        self.assertIn("UN-NAT", content)

    def test_19_employee_detail_no_funcao_badge_or_field(self):
        response = self.client.get(reverse('employee_detail', kwargs={'pk': self.emp.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("Função / Cargo", content)
        self.assertNotIn("Função:", content)

    def test_20_employee_detail_no_legacy_origin_badge(self):
        response = self.client.get(reverse('employee_detail', kwargs={'pk': self.emp.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("Função (Legado Transitório)", content)
        self.assertNotIn("FUNCAO_LEGADO", content)

    def test_21_employee_detail_shows_setor_sem_matriz_ativa(self):
        response = self.client.get(reverse('employee_detail', kwargs={'pk': self.emp.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("Setor sem Matriz de EPI ativa", content)

    def test_22_employee_list_no_funcao_nor_matricula_columns(self):
        response = self.client.get(reverse('employee_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("<th>Função</th>", content)
        self.assertNotIn("<th>Matrícula</th>", content)


# ==============================================================================
# GRUPO C: MATRIZ EXCLUSIVAMENTE POR SETOR — BACKEND E SERVIÇO (23 TESTES)
# ==============================================================================
class TestGroupCSectorMatrixBackend(BaseSpec015CorrectionTestCase):

    def setUp(self):
        super().setUp()
        self.emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Raimundo Soldador",
            cpf=make_valid_cpf(344),
            funcao=self.funcao_legada
        )
        self.lot = Lot.objects.create(
            fiscal_note=FiscalNote.objects.create(
                supplier=self.supplier,
                unit=self.unit,
                numero="NF-01",
                serie="1",
                data_emissao=timezone.now().date(),
                data_recebimento=timezone.now().date(),
                centro_custo=self.cost_center,
                valor_total=Decimal('100.00'),
                usuario=self.user_tecnico,
                status="CONFERIDA"
            ),
            product_variant=self.variant,
            identificador="L01",
            data_validade=timezone.now().date() + timezone.timedelta(days=365),
            quantidade_inicial=50,
            custo_unitario=Decimal('20.00')
        )
        from inventory.models import StockMovement
        StockMovement.objects.create(
            unit=self.unit,
            location=self.loc_sst,
            product_variant=self.variant,
            lot=self.lot,
            movement_type='RECEBIMENTO_NF',
            quantity=50,
            cost_unit=Decimal('20.00'),
            user=self.user_tecnico
        )

    def test_23_resolve_returns_items_when_sector_matrix_active(self):
        SectorPPEMatrix.objects.create(sector=self.sector, status='ATIVA', ativado_por=self.user_tecnico)
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=180, ativo=True)
        qs, origin = resolve_employee_ppe_matrix(self.emp)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().product, self.product)

    def test_24_resolve_returns_origin_setor(self):
        SectorPPEMatrix.objects.create(sector=self.sector, status='ATIVA', ativado_por=self.user_tecnico)
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=180, ativo=True)
        qs, origin = resolve_employee_ppe_matrix(self.emp)
        self.assertEqual(origin, 'SETOR')

    def test_25_resolve_returns_empty_and_none_when_em_elaboracao(self):
        SectorPPEMatrix.objects.create(sector=self.sector, status='EM_ELABORACAO')
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=180, ativo=True)
        qs, origin = resolve_employee_ppe_matrix(self.emp)
        self.assertIsNone(origin)
        self.assertEqual(qs.count(), 0)

    def test_26_resolve_returns_empty_and_none_when_no_config(self):
        qs, origin = resolve_employee_ppe_matrix(self.emp)
        self.assertIsNone(origin)
        self.assertEqual(qs.count(), 0)

    def test_27_resolve_no_fallback_to_funcao_legacy_in_db(self):
        PPEMatrix.objects.create(funcao=self.funcao_legada, product=self.product, vida_util_dias=90, ativo=True)
        qs, origin = resolve_employee_ppe_matrix(self.emp)
        self.assertIsNone(origin)
        self.assertEqual(qs.count(), 0)

    def test_28_resolve_does_not_emit_fallback_warning(self):
        with self.assertLogs('ppe.services', level='WARNING') as cm:
            logging.getLogger('ppe.services').warning("dummy trigger to avoid no logs exception")
            resolve_employee_ppe_matrix(self.emp)
        # Verify no log message contains 'Fallback'
        self.assertFalse(any('Fallback' in msg for msg in cm.output if 'dummy' not in msg))

    def test_29_resolve_employee_without_setor_returns_none(self):
        self.emp.setor = None
        self.emp.setor_id = None
        qs, origin = resolve_employee_ppe_matrix(self.emp)
        self.assertIsNone(origin)
        self.assertEqual(qs.count(), 0)

    def test_30_deliver_ppe_with_active_matrix_origin_matriz(self):
        SectorPPEMatrix.objects.create(sector=self.sector, status='ATIVA', ativado_por=self.user_tecnico)
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=120, ativo=True)
        delivery = deliver_ppe(
            employee=self.emp,
            product_variant=self.variant,
            lot=self.lot,
            quantity=1,
            user=self.user_tecnico,
            data_entrega=timezone.now().date(),
            natureza_entrega='INICIAL'
        )
        self.assertEqual(delivery.origem_necessidade, 'MATRIZ')
        self.assertEqual(delivery.vida_util_aplicada, 120)

    def test_31_deliver_ppe_no_active_matrix_rejected_without_justification(self):
        with self.assertRaises(ValidationError):
            deliver_ppe(
                employee=self.emp,
                product_variant=self.variant,
                lot=self.lot,
                quantity=1,
                user=self.user_tecnico,
                data_entrega=timezone.now().date(),
                natureza_entrega='INICIAL'
            )

    def test_32_deliver_ppe_no_active_matrix_approved_with_justification(self):
        delivery = deliver_ppe(
            employee=self.emp,
            product_variant=self.variant,
            lot=self.lot,
            quantity=1,
            user=self.user_tecnico,
            data_entrega=timezone.now().date(),
            natureza_entrega='EXTRAORDINARIA',
            motivo_substituicao="Fornecimento justificado formalmente para setor em estruturação."
        )
        self.assertEqual(delivery.origem_necessidade, 'EXTRAORDINARIA')

    def test_33_deliver_ppe_never_saves_funcao_legado(self):
        PPEMatrix.objects.create(funcao=self.funcao_legada, product=self.product, vida_util_dias=90, ativo=True)
        delivery = deliver_ppe(
            employee=self.emp,
            product_variant=self.variant,
            lot=self.lot,
            quantity=1,
            user=self.user_tecnico,
            data_entrega=timezone.now().date(),
            natureza_entrega='EXTRAORDINARIA',
            motivo_substituicao="Item extraordinário justificado."
        )
        self.assertNotEqual(delivery.origem_necessidade, 'FUNCAO_LEGADO')
        self.assertEqual(delivery.origem_necessidade, 'EXTRAORDINARIA')

    def test_34_deliver_ppe_with_extraordinary_ppe_uses_extraordinary_vida_util(self):
        ExtraordinaryPPE.objects.create(
            employee=self.emp,
            product=self.product,
            quantidade=1,
            vida_util_dias=45,
            motivo="Risco específico de solda",
            data_inicio=timezone.now().date(),
            ativo=True
        )
        delivery = deliver_ppe(
            employee=self.emp,
            product_variant=self.variant,
            lot=self.lot,
            quantity=1,
            user=self.user_tecnico,
            data_entrega=timezone.now().date(),
            natureza_entrega='EXTRAORDINARIA'
        )
        self.assertEqual(delivery.origem_necessidade, 'EXTRAORDINARIA')
        self.assertEqual(delivery.vida_util_aplicada, 45)

    def test_35_ppe_matrix_linked_to_setor_has_null_funcao(self):
        entry = PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=100, ativo=True)
        self.assertIsNotNone(entry.setor)
        self.assertIsNone(entry.funcao)

    def test_36_ppe_matrix_cannot_have_both_setor_and_funcao(self):
        entry = PPEMatrix(setor=self.sector, funcao=self.funcao_legada, product=self.product, vida_util_dias=100)
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_37_ppe_matrix_unique_product_per_sector(self):
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=100, ativo=True)
        formset_data = {
            'ppe_matrix_entries-TOTAL_FORMS': '2',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-product': self.product.id,
            'ppe_matrix_entries-0-quantidade_padrao': 1,
            'ppe_matrix_entries-0-vida_util_dias': 90,
            'ppe_matrix_entries-1-product': self.product.id,
            'ppe_matrix_entries-1-quantidade_padrao': 1,
            'ppe_matrix_entries-1-vida_util_dias': 90,
        }
        formset = PPEMatrixSectorFormSet(formset_data, instance=self.sector)
        self.assertFalse(formset.is_valid())

    def test_38_sector_matrix_activate_view_sets_ativa(self):
        self.client.login(username="tecnico_sst", password="pwd")
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=180, ativo=True)
        cfg = SectorPPEMatrix.objects.create(sector=self.sector, status='EM_ELABORACAO')
        url = reverse('sector_matrix_activate', kwargs={'sector_pk': self.sector.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        cfg.refresh_from_db()
        self.assertEqual(cfg.status, 'ATIVA')

    def test_39_activation_logs_audit_with_user_and_timestamp(self):
        self.client.login(username="tecnico_sst", password="pwd")
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=180, ativo=True)
        cfg = SectorPPEMatrix.objects.create(sector=self.sector, status='EM_ELABORACAO')
        url = reverse('sector_matrix_activate', kwargs={'sector_pk': self.sector.pk})
        self.client.post(url)
        cfg.refresh_from_db()
        self.assertEqual(cfg.ativado_por, self.user_tecnico)
        self.assertIsNotNone(cfg.ativado_em)

    def test_40_activation_blocked_for_sector_without_items(self):
        self.client.login(username="tecnico_sst", password="pwd")
        cfg = SectorPPEMatrix.objects.create(sector=self.sector, status='EM_ELABORACAO')
        url = reverse('sector_matrix_activate', kwargs={'sector_pk': self.sector.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        cfg.refresh_from_db()
        self.assertEqual(cfg.status, 'EM_ELABORACAO')

    def test_41_deactivation_sets_em_elaboracao(self):
        self.client.login(username="tecnico_sst", password="pwd")
        PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=180, ativo=True)
        cfg = SectorPPEMatrix.objects.create(sector=self.sector, status='ATIVA', ativado_por=self.user_tecnico)
        url = reverse('sector_matrix_deactivate', kwargs={'sector_pk': self.sector.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        cfg.refresh_from_db()
        self.assertEqual(cfg.status, 'EM_ELABORACAO')

    def test_42_deactivation_removes_immediate_matrix_requirement(self):
        cfg = SectorPPEMatrix.objects.create(sector=self.sector, status='EM_ELABORACAO')
        qs, origin = resolve_employee_ppe_matrix(self.emp)
        self.assertIsNone(origin)
        self.assertEqual(qs.count(), 0)

    def test_43_create_items_via_create_view_saves_correct_sector(self):
        self.client.login(username="tecnico_sst", password="pwd")
        url = reverse('sector_matrix_create')
        data = {
            'setor': self.sector.id,
            'ppe_matrix_entries-TOTAL_FORMS': '1',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-product': self.product.id,
            'ppe_matrix_entries-0-quantidade_padrao': 2,
            'ppe_matrix_entries-0-vida_util_dias': 180,
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        entry = PPEMatrix.objects.filter(setor=self.sector, product=self.product).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.quantidade_padrao, 2)
        self.assertEqual(entry.vida_util_dias, 180)

    def test_44_edit_items_via_edit_view_updates_and_deletes(self):
        entry1 = PPEMatrix.objects.create(setor=self.sector, product=self.product, vida_util_dias=100, ativo=True)
        entry2 = PPEMatrix.objects.create(setor=self.sector, product=self.product2, vida_util_dias=120, ativo=True)
        self.client.login(username="tecnico_sst", password="pwd")
        url = reverse('sector_matrix_edit', kwargs={'sector_pk': self.sector.pk})
        data = {
            'ppe_matrix_entries-TOTAL_FORMS': '2',
            'ppe_matrix_entries-INITIAL_FORMS': '2',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-id': entry1.id,
            'ppe_matrix_entries-0-product': self.product.id,
            'ppe_matrix_entries-0-quantidade_padrao': 1,
            'ppe_matrix_entries-0-vida_util_dias': 250,
            'ppe_matrix_entries-1-id': entry2.id,
            'ppe_matrix_entries-1-product': self.product2.id,
            'ppe_matrix_entries-1-quantidade_padrao': 1,
            'ppe_matrix_entries-1-vida_util_dias': 120,
            'ppe_matrix_entries-1-DELETE': 'on'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        entry1.refresh_from_db()
        self.assertEqual(entry1.vida_util_dias, 250)
        self.assertFalse(PPEMatrix.objects.filter(id=entry2.id).exists())

    def test_45_formset_validates_required_fields_and_positive_vida_util(self):
        data = {
            'product': self.product.id,
            'quantidade_padrao': -1,
            'vida_util_dias': 0,
        }
        form = PPEMatrixItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantidade_padrao', form.errors)
        self.assertIn('vida_util_dias', form.errors)


# ==============================================================================
# GRUPO D: MATRIZ EXCLUSIVAMENTE POR SETOR — INTERFACE E REDIRECIONAMENTOS (11 TESTES)
# ==============================================================================
class TestGroupDSectorMatrixUIAndRedirects(BaseSpec015CorrectionTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(username="tecnico_sst", password="pwd")

    def test_46_matrices_list_shows_sectors_with_status(self):
        SectorPPEMatrix.objects.create(sector=self.sector, status='ATIVA', ativado_por=self.user_tecnico)
        response = self.client.get(reverse('sector_matrix_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("Oficina Mecânica", content)
        self.assertIn("Ativa", content)

    def test_47_matrices_list_has_canonical_create_button(self):
        response = self.client.get(reverse('sector_matrix_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("Nova Matriz por Setor", content)
        self.assertIn(reverse('sector_matrix_create'), content)

    def test_48_matrices_list_no_legacy_functions_button(self):
        response = self.client.get(reverse('sector_matrix_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("Matrizes Legadas por Função", content)

    def test_49_matrices_list_no_legacy_tabs(self):
        response = self.client.get(reverse('sector_matrix_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("Legado por Função", content)

    def test_50_matrices_add_opens_sector_matrix_create_view(self):
        response = self.client.get(reverse('sector_matrix_create'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("Nova Matriz de EPI por Setor", content)

    def test_51_matrices_add_no_function_selection_field(self):
        response = self.client.get(reverse('sector_matrix_create'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn('name="funcao"', content)
        self.assertNotIn("Selecione a Função", content)

    def test_52_matrices_add_only_allows_sectors_in_user_units(self):
        response = self.client.get(reverse('sector_matrix_create'))
        self.assertEqual(response.status_code, 200)
        sector_form = response.context['sector_form']
        allowed_sector_ids = list(sector_form.fields['setor'].queryset.values_list('id', flat=True))
        self.assertIn(self.sector.id, allowed_sector_ids)
        self.assertNotIn(self.other_sector.id, allowed_sector_ids)

    def test_53_legacy_functions_url_redirects_with_message(self):
        response = self.client.get('/ppe/matrices/legacy-functions/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('sector_matrix_list'))
        content = response.content.decode('utf-8')
        self.assertIn("A Matriz de EPI agora é gerenciada exclusivamente por Setor", content)

    def test_54_legacy_function_edit_url_redirects(self):
        response = self.client.get(f'/ppe/matrices/function/{self.funcao_legada.pk}/edit/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('sector_matrix_list'))
        content = response.content.decode('utf-8')
        self.assertIn("A Matriz de EPI agora é gerenciada exclusivamente por Setor", content)

    def test_55_legacy_function_delete_url_redirects(self):
        response = self.client.get(f'/ppe/matrices/function/{self.funcao_legada.pk}/delete/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('sector_matrix_list'))

    def test_56_deactivate_confirm_message_does_not_mention_fallback(self):
        SectorPPEMatrix.objects.create(sector=self.sector, status='ATIVA', ativado_por=self.user_tecnico)
        response = self.client.get(reverse('sector_matrix_list'))
        content = response.content.decode('utf-8')
        self.assertNotIn("fallback transitório de função", content)


# ==============================================================================
# GRUPO E: RELATÓRIO DE CONSUMO E CUSTO DE EPIS (5 TESTES)
# ==============================================================================
class TestGroupEReportPPEConsumptionCost(BaseSpec015CorrectionTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(username="tecnico_sst", password="pwd")
        self.emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Antônio Relatório",
            cpf=make_valid_cpf(722)
        )
        self.note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            numero="NF-50",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('200.00'),
            usuario=self.user_tecnico,
            status="CONFERIDA"
        )
        self.lot = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant,
            identificador="L50",
            data_validade=timezone.now().date() + timezone.timedelta(days=365),
            quantidade_inicial=20,
            custo_unitario=Decimal('25.50')
        )
        self.delivery = PPEDelivery.objects.create(
            unit=self.unit,
            employee=self.emp,
            setor=self.sector,
            centro_custo=self.cost_center,
            product_variant=self.variant,
            lot=self.lot,
            quantidade=4,
            custo_unitario=Decimal('25.50'),
            vida_util_aplicada=90,
            usuario_responsavel=self.user_tecnico,
            data_entrega=timezone.now().date(),
            data_prevista_troca=timezone.now().date() + timezone.timedelta(days=90),
            validade_fisica=timezone.now().date() + timezone.timedelta(days=365),
            origem_necessidade="EXTRAORDINARIA",
            status_assinatura="ASSINADO"
        )

    def test_57_report_consumption_cost_renders_200(self):
        response = self.client.get(reverse('report_ppe_consumption_cost'))
        self.assertEqual(response.status_code, 200)

    def test_58_report_consumption_cost_no_legado_terms(self):
        response = self.client.get(reverse('report_ppe_consumption_cost'))
        content = response.content.decode('utf-8')
        self.assertNotIn("legado", content.lower())
        self.assertNotIn("funcao_legado", content.lower())

    def test_59_report_consumption_cost_groups_by_historical_sector_and_employee(self):
        response = self.client.get(reverse('report_ppe_consumption_cost'))
        self.assertIn('resumo_setores', response.context)
        self.assertIn('resumo_colaboradores', response.context)
        self.assertEqual(len(response.context['resumo_setores']), 1)
        self.assertEqual(len(response.context['resumo_colaboradores']), 1)
        self.assertEqual(response.context['resumo_setores'][0]['setor'], self.sector)
        self.assertEqual(response.context['resumo_colaboradores'][0]['employee'], self.emp)

    def test_60_report_detail_table_correct_unit_and_total_costs(self):
        response = self.client.get(reverse('report_ppe_consumption_cost'))
        content = response.content.decode('utf-8')
        # Custo unitário: 25.50 | Custo total: 4 * 25.50 = 102.00
        self.assertIn("25,50", content)
        self.assertIn("102,00", content)

    def test_61_report_consolidated_totals_match_mathematically(self):
        response = self.client.get(reverse('report_ppe_consumption_cost'))
        self.assertEqual(response.context['total_pecas'], 4)
        self.assertEqual(response.context['total_custo'], Decimal('102.00'))


# ==============================================================================
# GRUPO F: RELATÓRIOS E LISTAGENS DE ENTREGAS (4 TESTES)
# ==============================================================================
class TestGroupFDeliveriesReportsAndLists(BaseSpec015CorrectionTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(username="tecnico_sst", password="pwd")
        self.emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Marcos Entregas",
            cpf=make_valid_cpf(806)
        )
        self.lot = Lot.objects.create(
            fiscal_note=FiscalNote.objects.create(
                supplier=self.supplier,
                unit=self.unit,
                numero="NF-60",
                serie="1",
                data_emissao=timezone.now().date(),
                data_recebimento=timezone.now().date(),
                centro_custo=self.cost_center,
                valor_total=Decimal('100.00'),
                usuario=self.user_tecnico,
                status="CONFERIDA"
            ),
            product_variant=self.variant,
            identificador="L60",
            data_validade=timezone.now().date() + timezone.timedelta(days=365),
            quantidade_inicial=10,
            custo_unitario=Decimal('10.00')
        )
        self.delivery = PPEDelivery.objects.create(
            unit=self.unit,
            employee=self.emp,
            setor=self.sector,
            centro_custo=self.cost_center,
            product_variant=self.variant,
            lot=self.lot,
            quantidade=1,
            custo_unitario=Decimal('10.00'),
            vida_util_aplicada=90,
            usuario_responsavel=self.user_tecnico,
            data_entrega=timezone.now().date(),
            data_prevista_troca=timezone.now().date() + timezone.timedelta(days=90),
            validade_fisica=timezone.now().date() + timezone.timedelta(days=365),
            origem_necessidade="EXTRAORDINARIA",
            status_assinatura="ASSINADO"
        )

    def test_62_report_deliveries_no_funcao_filter(self):
        response = self.client.get(reverse('report_ppe_deliveries'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn('name="funcao"', content)
        self.assertNotIn("Função / Cargo", content)

    def test_63_ppe_deliveries_list_no_funcao_filter(self):
        response = self.client.get(reverse('delivery_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn('name="funcao"', content)
        self.assertNotIn("Função / Cargo", content)

    def test_64_filter_by_sector_works_correctly(self):
        response = self.client.get(reverse('delivery_list'), {'setor': self.sector.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['deliveries']), 1)
        response_other = self.client.get(reverse('delivery_list'), {'setor': self.other_sector.id})
        self.assertEqual(len(response_other.context['deliveries']), 0)

    def test_65_filter_by_employee_works_correctly(self):
        response = self.client.get(reverse('delivery_list'), {'q': 'Marcos Entregas'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['deliveries']), 1)
        response_none = self.client.get(reverse('delivery_list'), {'q': 'Inexistente'})
        self.assertEqual(len(response_none.context['deliveries']), 0)


# ==============================================================================
# GRUPO G: RETIRADA OPERACIONAL DE FUNÇÕES/CARGOS (10 TESTES)
# ==============================================================================
class TestGroupGOperationalRetirementOfFunctions(BaseSpec015CorrectionTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(username="tecnico_sst", password="pwd")

    def test_66_org_dashboard_no_card_funcoes_e_cargos(self):
        response = self.client.get(reverse('organization_dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("Funções e Cargos", content)

    def test_67_org_dashboard_no_button_add_funcao(self):
        response = self.client.get(reverse('organization_dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn("+ Função", content)

    def test_68_org_dashboard_grid_balanced_with_5_categories(self):
        response = self.client.get(reverse('organization_dashboard'))
        content = response.content.decode('utf-8')
        self.assertIn("Unidades", content)
        self.assertIn("Setores", content)
        self.assertIn("Centros de Custo", content)
        self.assertIn("Locais de Estoque", content)

    def test_69_org_functions_urls_redirect_to_dashboard_with_message(self):
        for url in ['/organizations/function/add/', '/organizations/functions/add/']:
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertRedirects(response, reverse('organization_dashboard'))
            content = response.content.decode('utf-8')
            self.assertIn("O cadastro de Funções/Cargos não faz mais parte do fluxo atual", content)

    def test_70_org_function_edit_url_redirects_with_message(self):
        response = self.client.get(f'/organizations/function/{self.funcao_legada.pk}/edit/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('organization_dashboard'))
        content = response.content.decode('utf-8')
        self.assertIn("O cadastro de Funções/Cargos não faz mais parte do fluxo atual", content)

    def test_71_navbar_no_link_to_funcoes_cargos(self):
        response = self.client.get(reverse('dashboard'))
        content = response.content.decode('utf-8')
        self.assertNotIn("href=\"/organizations/functions/\"", content)
        self.assertNotIn("Funções / Cargos", content)

    def test_72_menus_and_dropdowns_no_link_to_funcoes_cargos(self):
        response = self.client.get(reverse('dashboard'))
        content = response.content.decode('utf-8')
        self.assertNotIn("function_list", content)

    def test_73_historical_function_records_remain_in_database(self):
        # O model e a tabela continuam existindo e os registros não são apagados
        self.assertTrue(Function.objects.filter(pk=self.funcao_legada.pk).exists())
        self.assertEqual(Function.objects.get(pk=self.funcao_legada.pk).nome, "Eletricista Industrial")

    def test_74_historical_deliveries_with_function_maintain_referential_integrity(self):
        emp = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            setor=self.sector,
            centro_custo=self.cost_center,
            nome_completo="Histórico Íntegro",
            cpf=make_valid_cpf(940),
            funcao=self.funcao_legada
        )
        note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit,
            numero="NF-74",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('100.00'),
            usuario=self.user_tecnico,
            status="CONFERIDA"
        )
        lot = Lot.objects.create(
            fiscal_note=note,
            product_variant=self.variant,
            identificador="L74",
            data_validade=timezone.now().date() + timezone.timedelta(days=365),
            quantidade_inicial=10,
            custo_unitario=Decimal('10.00')
        )
        delivery = PPEDelivery.objects.create(
            unit=self.unit,
            employee=emp,
            setor=self.sector,
            centro_custo=self.cost_center,
            funcao=self.funcao_legada,
            product_variant=self.variant,
            lot=lot,
            quantidade=1,
            custo_unitario=Decimal('10.00'),
            vida_util_aplicada=60,
            usuario_responsavel=self.user_tecnico,
            data_entrega=timezone.now().date(),
            data_prevista_troca=timezone.now().date() + timezone.timedelta(days=60),
            validade_fisica=timezone.now().date() + timezone.timedelta(days=365),
            origem_necessidade="MATRIZ",
            status_assinatura="ASSINADO"
        )
        self.assertEqual(delivery.funcao, self.funcao_legada)
        self.assertEqual(delivery.employee.funcao, self.funcao_legada)

    def test_75_non_technical_user_forbidden_from_managing_sector_matrices(self):
        self.client.login(username="almoxarife_user", password="pwd")
        # Almoxarife tenta acessar a criação de matriz
        response_create = self.client.get(reverse('sector_matrix_create'))
        self.assertEqual(response_create.status_code, 403)
        # Almoxarife tenta ativar matriz
        response_activate = self.client.post(reverse('sector_matrix_activate', kwargs={'sector_pk': self.sector.pk}))
        self.assertEqual(response_activate.status_code, 403)
        # Almoxarife tenta editar matriz
        response_edit = self.client.get(reverse('sector_matrix_edit', kwargs={'sector_pk': self.sector.pk}))
        self.assertEqual(response_edit.status_code, 403)
