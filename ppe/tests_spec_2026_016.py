import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model

from organizations.models import Company, Unit, Sector, Function, InventoryLocation, CostCenter
from employees.models import Employee
from ppe.models import Product, ProductVariant, PPEMatrix, SectorPPEMatrix, PPEDelivery
from ppe.services import (
    canonical_size_key,
    normalize_size_label,
    normalize_size_string,
    sync_product_variants,
)
from ppe.forms import ProductForm
from inventory.models import Supplier, FiscalNote, Lot, StockMovement
from inventory.services import create_and_confirm_fiscal_note, get_stock_balance

User = get_user_model()


class SPEC2026016TestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.company = Company.objects.create(
            razao_social="Empresa Teste SPEC 016 LTDA",
            nome_fantasia="Empresa Teste 016",
            cnpj="12.345.678/0001-90"
        )
        self.unit1 = Unit.objects.create(
            company=self.company,
            nome="Unidade Fabril",
            codigo="UN-FAB"
        )
        self.unit2 = Unit.objects.create(
            company=self.company,
            nome="Unidade Secundária",
            codigo="UN-SEC"
        )
        self.sector = Sector.objects.create(
            unit=self.unit1,
            nome="Vulcanização",
            codigo="SEC-VULC"
        )
        self.funcao = Function.objects.create(
            company=self.company,
            nome="Operador de Vulcanização"
        )

        # Usuário Almoxarife com acesso à Unidade 1
        self.user_almoxarife = User.objects.create_user(
            username="almoxarife_016",
            password="pwd",
            profile_type="ALMOXARIFE"
        )
        self.user_almoxarife.units.add(self.unit1)

        # Usuário Técnico SST
        self.user_tecnico = User.objects.create_user(
            username="tecnico_016",
            password="pwd",
            profile_type="TECNICO_SST"
        )
        self.user_tecnico.units.add(self.unit1)

        # Locais de estoque
        self.loc_almox = InventoryLocation.objects.create(
            unit=self.unit1,
            codigo="LOC-ALMOX",
            nome="Almoxarifado Central",
            tipo="ALMOXARIFADO",
            ativo=True
        )
        self.loc_sst = InventoryLocation.objects.create(
            unit=self.unit1,
            codigo="LOC-SST",
            nome="Estoque SST",
            tipo="SST",
            ativo=True
        )

        self.cost_center = CostCenter.objects.create(
            company=self.company,
            nome="Operações Gerais",
            codigo="CC-OP"
        )

        # Fornecedor
        self.supplier = Supplier.objects.create(
            razao_social="Fornecedor de EPIs LTDA",
            cnpj_cpf="98.765.432/0001-10"
        )

        # EPI Luva com CA 39670
        self.luva = Product.objects.create(
            nome="LUVA PARA PROTEÇÃO CONTRA AGENTES TÉRMICOS E MECÂNICOS",
            categoria="LUVAS",
            tipo_produto="EPI",
            ca_numero="39670",
            unidade_medida="PAR",
            ativo=True
        )
        # Variantes P, M, G
        self.var_p = ProductVariant.objects.create(product=self.luva, tamanho="P", tamanho_normalizado="P")
        self.var_m = ProductVariant.objects.create(product=self.luva, tamanho="M", tamanho_normalizado="M")
        self.var_g = ProductVariant.objects.create(product=self.luva, tamanho="G", tamanho_normalizado="G")

        # Outro EPI para teste de rejeição cruzada
        self.oculos = Product.objects.create(
            nome="ÓCULOS DE SEGURANÇA",
            categoria="OCULOS",
            tipo_produto="EPI",
            ca_numero="12345",
            unidade_medida="UN",
            ativo=True
        )
        self.var_oculos_u = ProductVariant.objects.create(product=self.oculos, tamanho="Único", tamanho_normalizado="U")

        # Colaborador na Unidade 1
        self.employee = Employee.objects.create(
            company=self.company,
            unit=self.unit1,
            setor=self.sector,
            funcao=self.funcao,
            centro_custo=self.cost_center,
            nome_completo="JOÃO DA SILVA",
            cpf="123.456.789-09",
            matricula="MAT-001",
            situacao="ATIVO"
        )

    # -------------------------------------------------------------------------
    # 1. TESTES DE NORMALIZAÇÃO
    # -------------------------------------------------------------------------
    def test_canonical_size_key_variations(self):
        """Verifica a geração de chave canônica para diferentes entradas de tamanho."""
        self.assertEqual(canonical_size_key("G"), "G")
        self.assertEqual(canonical_size_key("g"), "G")
        self.assertEqual(canonical_size_key(" G "), "G")
        self.assertEqual(canonical_size_key("   g   "), "G")
        self.assertEqual(canonical_size_key("GG"), "GG")
        self.assertEqual(canonical_size_key("gg"), "GG")
        self.assertEqual(canonical_size_key("  xg  "), "XG")
        self.assertEqual(canonical_size_key("38"), "38")
        self.assertEqual(canonical_size_key("  40  "), "40")
        self.assertEqual(canonical_size_key("Único"), "U")
        self.assertEqual(canonical_size_key("unico"), "U")
        self.assertEqual(canonical_size_key("UNICO"), "U")
        self.assertEqual(canonical_size_key("U"), "U")
        self.assertEqual(canonical_size_key("u"), "U")
        self.assertEqual(canonical_size_key(""), "U")
        self.assertEqual(canonical_size_key(None), "U")

    def test_normalize_size_label(self):
        """Verifica formatação canônica de exibição."""
        self.assertEqual(normalize_size_label("g"), "G")
        self.assertEqual(normalize_size_label("  m  "), "M")
        self.assertEqual(normalize_size_label("39"), "39")
        self.assertEqual(normalize_size_label("unico"), "U")
        self.assertEqual(normalize_size_label("U"), "U")
        self.assertEqual(normalize_size_label(""), "U")

    # -------------------------------------------------------------------------
    # 2. TESTE DE RESTRIÇÃO DE UNICIDADE NO BANCO DE DADOS
    # -------------------------------------------------------------------------
    def test_unique_constraint_variant_duplicate(self):
        """Impede duplicidade de variante no mesmo EPI por tamanho normalizado."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.luva,
                    tamanho="g",
                    tamanho_normalizado="G"
                )

    # -------------------------------------------------------------------------
    # 3. TESTE DE CADASTRO DE EPI COM TAMANHOS DUPLICADOS
    # -------------------------------------------------------------------------
    def test_sync_product_variants_deduplication(self):
        """Garante que lista 'P, M, G, g, G' resulta apenas em P, M, G."""
        prod = Product.objects.create(
            nome="Luva Nitrílica",
            categoria="LUVAS",
            tipo_produto="EPI",
            ca_numero="99991",
            ativo=True
        )
        sync_product_variants(prod, "P, M, G, g, G")
        tamanhos = list(prod.variants.order_by('tamanho_normalizado').values_list('tamanho', flat=True))
        # Deve conter apenas P, M, G
        self.assertEqual(sorted(tamanhos), ["G", "M", "P"])
        self.assertEqual(prod.variants.count(), 3)

    def test_sync_product_variants_empty_creates_unico(self):
        """Quando não informado tamanho, cria variante canônica Único 'U'."""
        prod = Product.objects.create(
            nome="Protetor Auditivo Plug",
            categoria="AUDITIVO",
            tipo_produto="EPI",
            ca_numero="99992",
            ativo=True
        )
        sync_product_variants(prod, "")
        self.assertEqual(prod.variants.count(), 1)
        v = prod.variants.first()
        self.assertEqual(v.tamanho, "U")
        self.assertEqual(v.tamanho_normalizado, "U")

    # -------------------------------------------------------------------------
    # 4. TESTES DE ENDPOINTS AJAX DE VARIANTES
    # -------------------------------------------------------------------------
    def test_product_variants_ajax_success(self):
        """Endpoint retorna apenas variantes do EPI solicitado ordenadas."""
        self.client.force_login(self.user_almoxarife)
        url = reverse('product_variants_ajax')
        response = self.client.get(f"{url}?product_id={self.luva.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['product_id'], self.luva.id)
        self.assertEqual(len(data['variants']), 3)
        sizes = [v['tamanho'] for v in data['variants']]
        self.assertEqual(sizes, ["P", "M", "G"])

    def test_product_variants_ajax_requires_auth(self):
        """Endpoint rejeita acesso não autenticado."""
        url = reverse('product_variants_ajax')
        response = self.client.get(f"{url}?product_id={self.luva.id}")
        self.assertEqual(response.status_code, 401)

    def test_product_variants_ajax_does_not_create_records(self):
        """Endpoint é idempotente e de leitura estrita."""
        self.client.force_login(self.user_almoxarife)
        initial_count = ProductVariant.objects.count()
        url = reverse('product_variants_ajax')
        self.client.get(f"{url}?product_id={self.luva.id}")
        self.assertEqual(ProductVariant.objects.count(), initial_count)

    # -------------------------------------------------------------------------
    # 5. TESTES DE ENDPOINTS AJAX DE BUSCA DE PRODUTO E COLABORADOR
    # -------------------------------------------------------------------------
    def test_product_search_ajax(self):
        """Busca de produto por nome e C.A."""
        self.client.force_login(self.user_almoxarife)
        url = reverse('product_search_ajax')

        # Busca por CA
        res1 = self.client.get(f"{url}?q=39670")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(len(data1['results']), 1)
        self.assertEqual(data1['results'][0]['id'], self.luva.id)
        self.assertIn("39670", data1['results'][0]['text'])

        # Busca por Nome parcial
        res2 = self.client.get(f"{url}?q=MECÂNICOS")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(len(data2['results']), 1)
        self.assertEqual(data2['results'][0]['id'], self.luva.id)

    def test_employee_search_ajax_scoping_and_cpf_masking(self):
        """Busca de colaborador respeita unidade do usuário e mascara CPF."""
        # Colaborador na unidade 2
        sector_unit2 = Sector.objects.create(
            unit=self.unit2,
            nome="Montagem",
            codigo="SEC-MONT"
        )
        emp_unit2 = Employee.objects.create(
            company=self.company,
            unit=self.unit2,
            setor=sector_unit2,
            centro_custo=self.cost_center,
            nome_completo="CARLOS DE OUTRA UNIDADE",
            cpf="111.444.777-35",
            situacao="ATIVO"
        )

        self.client.force_login(self.user_almoxarife)
        url = reverse('employee_search_ajax')

        # Almoxarife tem acesso apenas à unit1
        res = self.client.get(f"{url}?q=SILVA")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data['results']), 1)
        # CPF deve vir mascarado no objeto e não exposto completo no text
        self.assertEqual(data['results'][0]['cpf_mascarado'], "***.456.789-**")
        self.assertNotIn("123.456.789-09", data['results'][0]['text'])

        # Busca por colaborador da outra unidade não deve retornar
        res_unit2 = self.client.get(f"{url}?q=CARLOS")
        data_unit2 = res_unit2.json()
        self.assertEqual(len(data_unit2['results']), 0)

    # -------------------------------------------------------------------------
    # 6. TESTE DE RECEBIMENTO DE COMPRA (ENTRADA DE NOTA FISCAL)
    # -------------------------------------------------------------------------
    def test_fiscal_note_receiving_increments_existing_variant_g(self):
        """Entrada no tamanho G incrementa o saldo de G existente sem criar 'g'."""
        initial_balance_g = get_stock_balance(self.loc_almox, self.var_g)
        self.assertEqual(initial_balance_g, 0)

        items_data = [
            {
                'product_id': self.luva.id,
                'variant_id': self.var_g.id,
                'quantidade': 1,
                'valor_unitario': Decimal('10.00'),
            }
        ]

        nf = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit1,
            usuario=self.user_almoxarife,
            numero="NF-001001",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('10.00'),
            status='PENDENTE'
        )

        create_and_confirm_fiscal_note(
            fiscal_note=nf,
            items_data=items_data,
            user=self.user_almoxarife
        )

        # Verifica que o saldo aumentou em 1
        new_balance_g = get_stock_balance(self.loc_almox, self.var_g)
        self.assertEqual(new_balance_g, 1)

        # Garante que não foi criada variante 'g'
        all_variants = list(self.luva.variants.values_list('tamanho', flat=True))
        self.assertEqual(sorted(all_variants), ["G", "M", "P"])
        self.assertNotIn("g", all_variants)

    def test_fiscal_note_receiving_rejects_foreign_variant(self):
        """Rejeita recebimento se variant_id não pertencer ao product_id."""
        items_data = [
            {
                'product_id': self.luva.id,
                'variant_id': self.var_oculos_u.id,  # Variante dos óculos!
                'quantidade': 5,
                'valor_unitario': Decimal('15.00'),
            }
        ]

        nf = FiscalNote.objects.create(
            supplier=self.supplier,
            unit=self.unit1,
            usuario=self.user_almoxarife,
            numero="NF-ADULTERADA",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('75.00'),
            status='PENDENTE'
        )

        with self.assertRaises(ValidationError) as ctx:
            create_and_confirm_fiscal_note(
                fiscal_note=nf,
                items_data=items_data,
                user=self.user_almoxarife
            )

        self.assertIn("O tamanho selecionado não pertence ao EPI informado.", str(ctx.exception))
        # Garante atomicidade: nenhuma movimentação gravada
        self.assertEqual(StockMovement.objects.filter(correlation_id__icontains="NF-ADULTERADA").count(), 0)

    def test_fiscal_note_atomic_rollback_on_partial_failure(self):
        """Se uma linha do recebimento for inválida, nada é persistido."""
        items_data = [
            {
                'product_id': self.luva.id,
                'variant_id': self.var_g.id,
                'quantidade': 10,
                'valor_unitario': Decimal('10.00'),
            },
            {
                'product_id': self.luva.id,
                'variant_id': 999999,  # ID inexistente
                'quantidade': 1,
                'valor_unitario': Decimal('5.00'),
            }
        ]

        # Instância não persistida (como form.save(commit=False))
        nf = FiscalNote(
            supplier=self.supplier,
            unit=self.unit1,
            usuario=self.user_almoxarife,
            numero="NF-FAIL",
            serie="1",
            data_emissao=timezone.now().date(),
            data_recebimento=timezone.now().date(),
            centro_custo=self.cost_center,
            valor_total=Decimal('105.00'),
            status='PENDENTE'
        )

        with self.assertRaises(ValidationError):
            create_and_confirm_fiscal_note(
                fiscal_note=nf,
                items_data=items_data,
                user=self.user_almoxarife
            )

        # Saldo de G continua 0 e a Nota Fiscal não deve existir no banco
        self.assertEqual(get_stock_balance(self.loc_almox, self.var_g), 0)
        self.assertFalse(FiscalNote.objects.filter(numero="NF-FAIL").exists())

    # -------------------------------------------------------------------------
    # 7. TESTE DE REGRESSÃO DAS TELAS
    # -------------------------------------------------------------------------
    def test_delivery_create_view_renders(self):
        """Tela de entrega renderiza com os novos selects pesquisáveis."""
        self.client.force_login(self.user_tecnico)
        url = reverse('delivery_create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'searchable-select')
        self.assertContains(res, reverse('employee_search_ajax'))

    def test_reports_views_render(self):
        """Relatórios carregam com o componente de select de EPI."""
        self.client.force_login(self.user_tecnico)
        for route_name in ['report_ppe_deliveries', 'report_ppe_consumption_cost', 'report_stock_position', 'report_stock_movements']:
            url = reverse(route_name)
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Falha na rota {route_name}")
            self.assertContains(res, 'searchable-select')
