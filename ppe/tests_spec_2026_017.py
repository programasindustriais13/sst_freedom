from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import Company, Unit, Sector, CostCenter, InventoryLocation
from ppe.models import Product, ProductVariant, PPEMatrix, PPEDelivery, CertificadoAprovacao
from employees.models import Employee
from decimal import Decimal
from django.utils import timezone

from inventory.models import Supplier, FiscalNote, Lot

User = get_user_model()

class Spec2026017ComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Usuário Admin
        self.admin_user = User.objects.create_user(
            username='admin_spec17',
            email='admin17@freedom.com',
            password='Password123!',
            is_staff=True,
            is_superuser=True
        )

        # Usuário Operador com unidade restrita
        self.operator_user = User.objects.create_user(
            username='operator_spec17',
            email='operator17@freedom.com',
            password='Password123!',
            is_staff=False,
            is_superuser=False
        )

        # Empresas
        self.company1 = Company.objects.create(
            razao_social="PNEUS FREEDOM LTDA",
            nome_fantasia="FREEDOM",
            cnpj="11.222.333/0001-44",
            ativo=True
        )
        self.company2 = Company.objects.create(
            razao_social="OUTRA EMPRESA S/A",
            nome_fantasia="OUTRA",
            cnpj="99.888.777/0001-66",
            ativo=True
        )

        # Unidades
        self.unit1 = Unit.objects.create(
            company=self.company1,
            codigo="UN01",
            nome="Unidade Matriz",
            cidade="Curitiba",
            estado="PR",
            ativo=True
        )
        self.unit2 = Unit.objects.create(
            company=self.company2,
            codigo="UN02",
            nome="Unidade Filial Outra",
            cidade="Joinville",
            estado="SC",
            ativo=True
        )

        # Vincula unit1 ao operador
        self.operator_user.units.add(self.unit1)

        # Setores
        self.sector1 = Sector.objects.create(
            unit=self.unit1,
            codigo="SEC01",
            nome=" vulcanização ",
            ativo=True
        )
        self.sector2 = Sector.objects.create(
            unit=self.unit2,
            codigo="SEC02",
            nome="Montagem Filial",
            ativo=True
        )

        # Locais de Estoque
        self.loc1 = InventoryLocation.objects.create(
            unit=self.unit1,
            codigo="LOC01",
            nome="Almoxarifado Geral",
            tipo="ALMOXARIFADO",
            ativo=True
        )

        # Produtos (EPI)
        self.product1 = Product.objects.create(
            nome="Luva de Vaqueta",
            tipo_produto="EPI",
            ca_numero="12345",
            fabricante="EPI Brasil",
            ativo=True
        )
        self.variant1_u = ProductVariant.objects.create(
            product=self.product1,
            tamanho="U",
            ativo=True
        )

        self.product2 = Product.objects.create(
            nome="Óculos de Proteção Ampla Visão",
            tipo_produto="EPI",
            ca_numero="39670",
            fabricante="Vision Safe",
            ativo=True
        )
        self.variant2_u = ProductVariant.objects.create(
            product=self.product2,
            tamanho="U",
            ativo=True
        )

        # Centros de Custo
        self.cc1 = CostCenter.objects.create(
            company=self.company1,
            codigo="CC01",
            nome="Centro Geral",
            ativo=True
        )

        # Colaborador
        self.employee1 = Employee.objects.create(
            company=self.company1,
            unit=self.unit1,
            setor=self.sector1,
            centro_custo=self.cc1,
            nome_completo="Danilo Pereira Silva",
            cpf="52998224725",
            matricula="MAT-001",
            situacao="ATIVO"
        )

        # Entrega de EPI para relatório
        self.ca1 = CertificadoAprovacao.objects.create(
            numero="12345",
            numero_exibicao="12345",
            fabricante="EPI Brasil",
            data_validade=timezone.now().date() + timezone.timedelta(days=365),
            situacao="VÁLIDO"
        )
        self.supplier = Supplier.objects.create(
            razao_social="Fornecedor Teste",
            cnpj_cpf="77.777.777/0001-88"
        )
        self.note = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit1,
            numero="888",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cc1,
            valor_total=Decimal("155.00"),
            usuario=self.admin_user,
            status="CONFERIDA"
        )
        self.lot = Lot.objects.create(
            fiscal_note=self.note,
            product_variant=self.variant1_u,
            identificador="LOT-01",
            data_validade=timezone.now().date() + timezone.timedelta(days=180),
            quantidade_inicial=10,
            custo_unitario=Decimal("15.50")
        )
        self.delivery1 = PPEDelivery.objects.create(
            employee=self.employee1,
            unit=self.unit1,
            setor=self.sector1,
            centro_custo=self.cc1,
            product_variant=self.variant1_u,
            ca_entregue=self.ca1,
            lot=self.lot,
            validade_fisica=timezone.now().date() + timezone.timedelta(days=180),
            quantidade=2,
            custo_unitario=Decimal("15.50"),
            natureza_entrega="INICIAL",
            status_assinatura="ASSINADO",
            data_entrega=timezone.now().date(),
            vida_util_aplicada=180,
            data_prevista_troca=timezone.now().date() + timezone.timedelta(days=180),
            usuario_responsavel=self.admin_user
        )

    # -------------------------------------------------------------
    # 1. TESTES DE MATRIZ DE EPI POR SETOR
    # -------------------------------------------------------------
    def test_matrix_create_view_get_and_template(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('sector_matrix_create'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # Verifica presença do template de empty_form
        self.assertIn('id="empty-form-template"', content)
        self.assertIn('ppe_matrix_entries-__prefix__-product', content)

    def test_matrix_create_multi_items_post_valid(self):
        self.client.force_login(self.admin_user)
        post_data = {
            'setor': self.sector1.id,
            'ppe_matrix_entries-TOTAL_FORMS': '2',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            
            'ppe_matrix_entries-0-product': self.product1.id,
            'ppe_matrix_entries-0-quantidade_padrao': '1',
            'ppe_matrix_entries-0-vida_util_dias': '180',
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',

            'ppe_matrix_entries-1-product': self.product2.id,
            'ppe_matrix_entries-1-quantidade_padrao': '2',
            'ppe_matrix_entries-1-vida_util_dias': '365',
            'ppe_matrix_entries-1-obrigatorio': 'on',
            'ppe_matrix_entries-1-principal': 'off',
        }
        response = self.client.post(reverse('sector_matrix_create'), post_data)
        self.assertEqual(response.status_code, 302)
        # Verifica se ambos foram persistidos para o setor
        matrices = PPEMatrix.objects.filter(setor=self.sector1)
        self.assertEqual(matrices.count(), 2)

    def test_matrix_duplicate_ppe_rejected(self):
        self.client.force_login(self.admin_user)
        post_data = {
            'setor': self.sector1.id,
            'ppe_matrix_entries-TOTAL_FORMS': '2',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            
            'ppe_matrix_entries-0-product': self.product1.id,
            'ppe_matrix_entries-0-quantidade_padrao': '1',
            'ppe_matrix_entries-0-vida_util_dias': '180',

            'ppe_matrix_entries-1-product': self.product1.id, # Duplicado!
            'ppe_matrix_entries-1-quantidade_padrao': '1',
            'ppe_matrix_entries-1-vida_util_dias': '180',
        }
        response = self.client.post(reverse('sector_matrix_create'), post_data)
        self.assertEqual(response.status_code, 200) # Re-renderiza form com erro
        # Não pode ter salvo nada
        self.assertEqual(PPEMatrix.objects.filter(setor=self.sector1).count(), 0)
        self.assertIn("mais de uma vez neste setor", response.content.decode('utf-8'))

    # -------------------------------------------------------------
    # 2. TESTES DE ESTRUTURA ORGANIZACIONAL & UNIDADE
    # -------------------------------------------------------------
    def test_unit_create_view_get_returns_200_without_cnpj_error(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('unit_create'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn('Unknown field(s) (cnpj)', content)

    def test_unit_create_post_valid_and_invalid(self):
        self.client.force_login(self.admin_user)
        # POST válido
        post_data = {
            'company': self.company1.id,
            'codigo': 'UN_TEST',
            'nome': 'Unidade de Teste Criada',
            'cidade': 'Londrina',
            'estado': 'PR',
            'ativo': 'on'
        }
        response = self.client.post(reverse('unit_create'), post_data)
        self.assertEqual(response.status_code, 302)
        created_unit = Unit.objects.filter(codigo='UN_TEST').first()
        self.assertIsNotNone(created_unit)

        # GET edição da unidade criada
        response_edit = self.client.get(reverse('unit_update', kwargs={'pk': created_unit.pk}))
        self.assertEqual(response_edit.status_code, 200)

        # POST inválido (faltando campos obrigatórios como nome e codigo)
        response_inv = self.client.post(reverse('unit_create'), {})
        self.assertEqual(response_inv.status_code, 200)
        self.assertFalse(response_inv.context['form'].is_valid())

    def test_organizations_dashboard_cards_and_legible_names(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('organization_dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        # Card de empresas presente
        self.assertIn('<h4 class="mb-3 text-info"><i class="bi bi-buildings"></i> Empresas</h4>', content)
        self.assertIn(self.company1.nome_fantasia, content)
        self.assertIn(self.company1.cnpj, content)

        # Nome legível da unidade nos cards (não apenas o ID ou código bruto)
        self.assertIn(self.unit1.nome, content)
        # Verifica se o setor exibe o nome da unidade
        self.assertIn(f'<td class="border-secondary">{self.unit1.nome}</td>', content)

    def test_organizations_dashboard_scoped_companies_for_restricted_user(self):
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('organization_dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # Operador vinculado apenas à unit1 (company1 FREEDOM) não deve ver company2 OUTRA
        self.assertIn(self.company1.nome_fantasia, content)
        self.assertNotIn(self.company2.nome_fantasia, content)

    # -------------------------------------------------------------
    # 3. TESTES DO RELATÓRIO DE CONSUMO E CUSTO DE EPIS
    # -------------------------------------------------------------
    def test_report_ppe_consumption_cost_filtering(self):
        self.client.force_login(self.admin_user)
        
        # Filtro por ID do colaborador
        res_emp = self.client.get(reverse('report_ppe_consumption_cost'), {'employee': str(self.employee1.id)})
        self.assertEqual(res_emp.status_code, 200)
        self.assertEqual(res_emp.context['selected_employee'], self.employee1)
        self.assertEqual(len(res_emp.context['object_list']), 1)

        # Filtro por nome do colaborador (compatibilidade textual)
        res_emp_text = self.client.get(reverse('report_ppe_consumption_cost'), {'employee': 'Danilo'})
        self.assertEqual(res_emp_text.status_code, 200)
        self.assertEqual(len(res_emp_text.context['object_list']), 1)

        # Filtro por EPI (ID)
        res_prod = self.client.get(reverse('report_ppe_consumption_cost'), {'product': str(self.product1.id)})
        self.assertEqual(res_prod.status_code, 200)
        self.assertEqual(res_prod.context['selected_product'], self.product1)
        self.assertEqual(len(res_prod.context['object_list']), 1)

        # Filtro por EPI que não teve entrega
        res_none = self.client.get(reverse('report_ppe_consumption_cost'), {'product': str(self.product2.id)})
        self.assertEqual(res_none.status_code, 200)
        self.assertEqual(len(res_none.context['object_list']), 0)

        # Filtros combinados
        res_comb = self.client.get(reverse('report_ppe_consumption_cost'), {
            'company': str(self.company1.id),
            'unit': str(self.unit1.id),
            'setor': str(self.sector1.id),
            'employee': str(self.employee1.id),
            'product': str(self.product1.id)
        })
        self.assertEqual(res_comb.status_code, 200)
        self.assertEqual(len(res_comb.context['object_list']), 1)

    # -------------------------------------------------------------
    # 4. TESTES DOS ENDPOINTS DE AUTOCOMPLETE / BUSCA AJAX
    # -------------------------------------------------------------
    def test_product_api_search_authentication_and_results(self):
        # Deslogado deve dar 401
        res_unauth = self.client.get(reverse('product_api_search'))
        self.assertEqual(res_unauth.status_code, 401)

        # Logado
        self.client.force_login(self.admin_user)
        
        # Busca por nome
        res = self.client.get(reverse('product_api_search'), {'q': 'Vaqueta'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['id'], self.product1.id)

        # Busca por C.A.
        res_ca = self.client.get(reverse('product_api_search'), {'q': '39670'})
        self.assertEqual(res_ca.status_code, 200)
        data_ca = res_ca.json()
        self.assertEqual(len(data_ca['results']), 1)
        self.assertEqual(data_ca['results'][0]['id'], self.product2.id)

    def test_employee_api_search_authentication_and_lgpd(self):
        # Deslogado deve dar 401
        res_unauth = self.client.get(reverse('employee_api_search'))
        self.assertEqual(res_unauth.status_code, 401)

        # Logado
        self.client.force_login(self.admin_user)
        res = self.client.get(reverse('employee_api_search'), {'q': 'Danilo'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['results']), 1)
        emp_res = data['results'][0]
        self.assertEqual(emp_res['id'], self.employee1.id)
        # Garante mascaramento LGPD (CPF completo não exposto)
        self.assertNotIn('52998224725', emp_res['cpf_mascarado'])
        self.assertIn('***.', emp_res['cpf_mascarado'])
