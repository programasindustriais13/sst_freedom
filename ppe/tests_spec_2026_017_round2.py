import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from organizations.models import Company, Unit, Sector, InventoryLocation
from ppe.models import (
    Product, ProductVariant, PPEMatrix, SectorPPEMatrix, CertificadoAprovacao
)
from ppe.forms import ProductForm
from ppe.constants import (
    UNIDADE_MEDIDA_CHOICES, CANONICAL_SIZES_BY_GROUP, ALL_CANONICAL_SIZES, get_size_sort_key
)

User = get_user_model()


class Spec2026017Round2ComprehensiveTests(TestCase):
    """
    Testes automatizados completos para a homologação rodada 2 da SPEC 2026-017:
    - AC01 a AC04: Menu lateral (destaque único, relatórios, alertas, ppe, matrizes)
    - AC05 a AC11: Fluxo de ativação da Matriz de EPI (elaboração vs ativação, validações, POST)
    - AC12 a AC14: Padronização e normalização de Unidade de Medida
    - AC15 a AC19: Variantes, decisão Único vs Múltiplos, catálogo canônico de tamanhos
    - AC20 a AC23: Unicidade de C.A. e prevenção de duplicidade de EPI
    - AC24 a AC32: Acessibilidade, integridade, e não-regressão de estoques e compras
    """

    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin_user = User.objects.create_user(
            username='admin_r2',
            email='admin_r2@freedom.com',
            password='Password123!',
            is_staff=True,
            is_superuser=True
        )

        # Regular operator user
        self.operator_user = User.objects.create_user(
            username='operator_r2',
            email='operator_r2@freedom.com',
            password='Password123!',
            is_staff=False,
            is_superuser=False
        )

        # Company & Unit
        self.company = Company.objects.create(
            razao_social="TEST INDUSTRY FREEDOM LTDA",
            nome_fantasia="FREEDOM TEST",
            cnpj="12.345.678/0001-99",
            ativo=True
        )
        self.unit = Unit.objects.create(
            company=self.company,
            codigo="UN01",
            nome="Unidade Central",
            cidade="Curitiba",
            estado="PR",
            ativo=True
        )
        self.operator_user.units.add(self.unit)

        # Sector
        self.sector = Sector.objects.create(
            unit=self.unit,
            codigo="SEC01",
            nome="Usinagem",
            ativo=True
        )

        # Inventory Location
        self.inventory_loc = InventoryLocation.objects.create(
            unit=self.unit,
            codigo="ALM01",
            nome="Almoxarifado Principal",
            tipo="ALMOXARIFADO",
            ativo=True
        )

        # Base Product
        self.product = Product.objects.create(
            nome="Luva de Vaqueta Térmica",
            tipo_produto="EPI",
            ca_numero="39670",
            fabricante="Vaqueta Top",
            unidade_medida="PAR",
            ativo=True
        )
        self.var_p = ProductVariant.objects.create(product=self.product, tamanho="P", ativo=True)
        self.var_m = ProductVariant.objects.create(product=self.product, tamanho="M", ativo=True)
        self.var_g = ProductVariant.objects.create(product=self.product, tamanho="G", ativo=True)

    # =========================================================================
    # 1. MENU LATERAL TESTS (AC01 - AC04)
    # =========================================================================

    def test_reports_menu_active_only(self):
        """AC01 & AC03: /reports/ppe-consumption-cost/ ativa apenas Relatórios."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/reports/ppe-consumption-cost/')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertIn('aria-current="page"', content)
        # Verify Relatórios is active
        self.assertIn('href="/reports/"', content)
        # Ensure EPIs / Catálogo does not have active class
        self.assertNotIn('href="/ppe/" class="nav-link-premium active"', content)

    def test_notifications_menu_active_only(self):
        """AC02: /notifications/ ativa apenas Alertas."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        # Alertas must have active class and aria-current
        self.assertIn('class="nav-link-premium active"', content)
        self.assertIn('aria-current="page"', content)
        self.assertIn('href="/notifications/"', content)
        # EPIs must NOT have active
        self.assertNotIn('href="/ppe/" class="nav-link-premium active"', content)

    def test_ppe_add_menu_active_only(self):
        """AC04: /ppe/add/ ativa apenas EPIs / Catálogo."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/ppe/add/')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertIn('href="/ppe/"', content)
        self.assertIn('class="nav-link-premium active"', content)
        self.assertNotIn('href="/reports/" class="nav-link-premium active"', content)
        self.assertNotIn('href="/notifications/" class="nav-link-premium active"', content)

    def test_sector_matrices_menu_active_only(self):
        """AC04: /ppe/matrices/ ativa apenas Matriz de EPI por Setor."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/ppe/matrices/')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertIn('href="/ppe/matrices/"', content)
        self.assertIn('class="nav-link-premium active"', content)
        self.assertNotIn('href="/ppe/" class="nav-link-premium active"', content)

    # =========================================================================
    # 2. MATRIZ DE EPI POR SETOR (AC05 - AC11)
    # =========================================================================

    def test_matrix_save_as_draft(self):
        """AC05: 'Salvar como elaboração' salva e mantém o status EM_ELABORACAO."""
        self.client.force_login(self.admin_user)
        url = reverse('sector_matrix_edit', args=[self.sector.id])

        post_data = {
            'action': 'save_draft',
            'ppe_matrix_entries-TOTAL_FORMS': '1',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-product': str(self.product.id),
            'ppe_matrix_entries-0-quantidade_padrao': '2',
            'ppe_matrix_entries-0-vida_util_dias': '90',
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',
        }

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        config = SectorPPEMatrix.objects.get(sector=self.sector)
        self.assertEqual(config.status, 'EM_ELABORACAO')
        self.assertTrue(PPEMatrix.objects.filter(setor=self.sector, product=self.product).exists())

    def test_matrix_save_and_activate_success(self):
        """AC06 & AC10: 'Salvar e ativar' valida os dados e ativa a matriz na mesma operação."""
        self.client.force_login(self.admin_user)
        url = reverse('sector_matrix_edit', args=[self.sector.id])

        post_data = {
            'action': 'save_and_activate',
            'ppe_matrix_entries-TOTAL_FORMS': '1',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-product': str(self.product.id),
            'ppe_matrix_entries-0-quantidade_padrao': '1',
            'ppe_matrix_entries-0-vida_util_dias': '60',
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',
        }

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        config = SectorPPEMatrix.objects.get(sector=self.sector)
        self.assertEqual(config.status, 'ATIVA')
        self.assertIn("Matriz do setor ativada com sucesso.", [m.message for m in response.context['messages']])

    def test_matrix_activate_rejected_without_epis(self):
        """AC09: Ativação sem nenhum EPI válido é rejeitada."""
        self.client.force_login(self.admin_user)
        url = reverse('sector_matrix_edit', args=[self.sector.id])

        post_data = {
            'action': 'save_and_activate',
            'ppe_matrix_entries-TOTAL_FORMS': '0',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
        }

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        config = SectorPPEMatrix.objects.filter(sector=self.sector).first()
        if config:
            self.assertNotEqual(config.status, 'ATIVA')
        self.assertIn("Não foi possível ativar a matriz. Adicione pelo menos um EPI.", [m.message for m in response.context['messages']])

    def test_matrix_list_activate_button_post(self):
        """AC07 & AC08: O botão Ativar da listagem utiliza POST e altera status para ATIVA."""
        self.client.force_login(self.admin_user)
        config = SectorPPEMatrix.objects.create(
            sector=self.sector,
            status='EM_ELABORACAO'
        )
        PPEMatrix.objects.create(
            setor=self.sector,
            product=self.product,
            variant=self.var_m,
            quantidade_padrao=1,
            vida_util_dias=30,
            ativo=True
        )

        url = reverse('sector_matrix_activate', args=[self.sector.id])
        # Test GET rejected
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 405)

        # Test POST succeeds
        post_response = self.client.post(url, follow=True)
        self.assertEqual(post_response.status_code, 200)

        config.refresh_from_db()
        self.assertEqual(config.status, 'ATIVA')

    def test_matrix_edit_active_keeps_active(self):
        """AC11: Salvar alterações de uma matriz ativa mantém-na ativa."""
        self.client.force_login(self.admin_user)
        config = SectorPPEMatrix.objects.create(
            sector=self.sector,
            status='ATIVA'
        )
        matrix_item = PPEMatrix.objects.create(
            setor=self.sector,
            product=self.product,
            variant=self.var_p,
            quantidade_padrao=1,
            vida_util_dias=30,
            ativo=True
        )

        url = reverse('sector_matrix_edit', args=[self.sector.id])
        post_data = {
            'action': 'save_changes',
            'ppe_matrix_entries-TOTAL_FORMS': '1',
            'ppe_matrix_entries-INITIAL_FORMS': '1',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-id': str(matrix_item.id),
            'ppe_matrix_entries-0-product': str(self.product.id),
            'ppe_matrix_entries-0-quantidade_padrao': '3',
            'ppe_matrix_entries-0-vida_util_dias': '45',
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',
        }

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        config.refresh_from_db()
        self.assertEqual(config.status, 'ATIVA')

    # =========================================================================
    # 3. UNIDADE DE MEDIDA TESTS (AC12 - AC14)
    # =========================================================================

    def test_unidade_medida_choices_valid(self):
        """AC12 & AC13: Unidade deve aceitar apenas códigos canônicos válidos."""
        form_data = {
            'nome': 'Capacete de Segurança Teste',
            'tipo_produto': 'EPI',
            'ca_numero': '11111',
            'categoria': 'PROTECAO_CABECA',
            'unidade_medida': 'UND',
            'tem_variacao_tamanho': 'nao',
            'tamanhos_str': 'U'
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_unidade_medida_rejects_arbitrary_text(self):
        """AC12 & AC20: Unidade rejeita texto arbitrário (ex: 'banana', 'abc')."""
        form_data = {
            'nome': 'Capacete de Segurança Teste',
            'tipo_produto': 'EPI',
            'ca_numero': '11112',
            'categoria': 'PROTECAO_CABECA',
            'unidade_medida': 'TEXTO_LIVRE_INVALIDO',
            'tem_variacao_tamanho': 'nao',
            'tamanhos_str': 'U'
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('unidade_medida', form.errors)

    def test_unidade_medida_normalizes_synonym(self):
        """AC14: Sinônimos minúsculos ou variantes são normalizados para código canônico."""
        prod = Product(
            nome="Óculos Amplo Espectro",
            tipo_produto="EPI",
            ca_numero="22222",
            unidade_medida="unidade",
            categoria="PROTECAO_OCULAR"
        )
        prod.clean()
        self.assertEqual(prod.unidade_medida, "UND")

        prod_par = Product(
            nome="Bota de Segurança",
            tipo_produto="EPI",
            ca_numero="22223",
            unidade_medida="pares",
            categoria="PROTECAO_MEMBROS_INF"
        )
        prod_par.clean()
        self.assertEqual(prod_par.unidade_medida, "PAR")

    # =========================================================================
    # 4. VARIANTES E TAMANHOS (AC15 - AC19)
    # =========================================================================

    def test_single_size_creates_only_unique_variant(self):
        """AC16: Tamanho único cria somente a variante canônica 'U'."""
        self.client.force_login(self.admin_user)
        url = reverse('product_create')

        post_data = {
            'nome': 'Óculos de Proteção Incolor',
            'tipo_produto': 'EPI',
            'ca_numero': '33333',
            'categoria': 'PROTECAO_OCULAR',
            'unidade_medida': 'UND',
            'tem_variacao_tamanho': 'nao',
            'tamanhos_str': 'U'
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        created_prod = Product.objects.get(ca_numero='33333')
        variants = list(created_prod.variants.values_list('tamanho', flat=True))
        self.assertEqual(variants, ['U'])

    def test_single_size_cannot_coexist_with_other_sizes(self):
        """AC18: A opção 'Único' não pode ser combinada com outros tamanhos."""
        form_data = {
            'nome': 'Respirador Semi-Facial',
            'tipo_produto': 'EPI',
            'ca_numero': '44444',
            'categoria': 'PROTECAO_RESPIRATORIA',
            'unidade_medida': 'UND',
            'tem_variacao_tamanho': 'sim',
            'tamanhos_str': 'Único, P, M'
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('tamanhos_str', form.errors)
        self.assertIn("A opção 'Único' não pode ser utilizada junto com outros tamanhos.", form.errors['tamanhos_str'][0])

    def test_multiple_sizes_selection_p_m_g(self):
        """AC17 & AC22: Um único EPI pode possuir P, M e G simultaneamente."""
        self.client.force_login(self.admin_user)
        url = reverse('product_create')

        post_data = {
            'nome': 'Luva Nitrílica Verde',
            'tipo_produto': 'EPI',
            'ca_numero': '55555',
            'categoria': 'PROTECAO_MEMBROS_SUP',
            'unidade_medida': 'PAR',
            'tem_variacao_tamanho': 'sim',
            'tamanhos_str': 'P, M, G'
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        created_prod = Product.objects.get(ca_numero='55555')
        variants = sorted(list(created_prod.variants.values_list('tamanho', flat=True)), key=get_size_sort_key)
        self.assertEqual(variants, ['P', 'M', 'G'])

    def test_reject_size_outside_canonical_catalog(self):
        """AC19: Backend rejeita tamanho não pertencente ao catálogo."""
        form_data = {
            'nome': 'Calçado Antiderrapante',
            'tipo_produto': 'EPI',
            'ca_numero': '66666',
            'categoria': 'PROTECAO_MEMBROS_INF',
            'unidade_medida': 'PAR',
            'tem_variacao_tamanho': 'sim',
            'tamanhos_str': '38, 39, TAMANHO_INVALIDO'
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('tamanhos_str', form.errors)
        self.assertIn("não pertence ao catálogo permitido", form.errors['tamanhos_str'][0])

    def test_case_insensitive_sizes_do_not_duplicate(self):
        """AC19: G e g não podem coexistir e são deduplicados na forma canônica."""
        form_data = {
            'nome': 'Avental de Raspa',
            'tipo_produto': 'EPI',
            'ca_numero': '77777',
            'categoria': 'PROTECAO_MEMBROS_SUP',
            'unidade_medida': 'UND',
            'tem_variacao_tamanho': 'sim',
            'tamanhos_str': 'g, G, M'
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        cleaned_list = form.cleaned_data['tamanhos_list']
        self.assertEqual(cleaned_list, ['M', 'G'])

    # =========================================================================
    # 5. UNICIDADE DE C.A. (AC20 - AC23)
    # =========================================================================

    def test_existing_ca_prevents_duplicate_product_form(self):
        """AC20 & AC21: Tentar cadastrar um C.A. existente rejeita e orienta a edição."""
        form_data = {
            'nome': 'Outra Luva Com Mesmo CA',
            'tipo_produto': 'EPI',
            'ca_numero': '39670', # Já pertence a self.product
            'categoria': 'PROTECAO_MEMBROS_SUP',
            'unidade_medida': 'PAR',
            'tem_variacao_tamanho': 'sim',
            'tamanhos_str': 'GG'
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('ca_numero', form.errors)
        self.assertIn("Este C.A. já está cadastrado no sistema.", form.errors['ca_numero'][0])
        self.assertIn("Para incluir outro tamanho, edite o cadastro existente", form.errors['ca_numero'][0])

    def test_existing_ca_database_constraint(self):
        """AC20 & AC40: Constraint de banco impede duplicidade de C.A."""
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                nome="Tentativa Duplicada no Banco",
                tipo_produto="EPI",
                ca_numero="39670",
                unidade_medida="PAR"
            )

    def test_ca_consultar_ajax_returns_already_registered(self):
        """AC21: Endpoint ca_consultar_ajax detecta C.A. cadastrado e retorna info para o frontend."""
        self.client.force_login(self.admin_user)
        url = reverse('ca_consultar_ajax') + '?q=39670'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data.get('already_registered'))
        self.assertEqual(data['existing_product']['id'], self.product.id)
        self.assertIn(reverse('product_update', args=[self.product.id]), data['existing_product']['edit_url'])
        self.assertIn('P', data['existing_product']['variantes'])

    def test_ca_consultar_ajax_with_exclude_id(self):
        """AC21: Ao editar o próprio produto, exclude_id impede falso positivo de duplicidade."""
        self.client.force_login(self.admin_user)
        url = reverse('ca_consultar_ajax') + f'?q=39670&exclude_id={self.product.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertFalse(data.get('already_registered', False))

    def test_empty_ca_allowed_for_non_epi(self):
        """AC42: Produtos não-EPI podem ter C.A. vazio sem violar restrição de unicidade."""
        p1 = Product.objects.create(
            nome="Creme Protetor Grupo 3",
            tipo_produto="OUTRO",
            ca_numero=None,
            unidade_medida="TB"
        )
        p2 = Product.objects.create(
            nome="Detergente Industrial",
            tipo_produto="OUTRO",
            ca_numero="",
            unidade_medida="L"
        )
        self.assertIsNotNone(p1.id)
        self.assertIsNotNone(p2.id)

    # =========================================================================
    # 6. NÃO-REGRESSÃO E SEGURANÇA (AC27 - AC32)
    # =========================================================================

    def test_variant_with_movement_cannot_be_deleted(self):
        """AC27: Variante com histórico de estoque não é excluída silenciosamente."""
        # Vincula a variante G a uma recomendação de matriz
        PPEMatrix.objects.create(
            setor=self.sector,
            product=self.product,
            variant=self.var_g,
            quantidade_padrao=1,
            vida_util_dias=30,
            ativo=True
        )

        from ppe.services import sync_product_variants
        # Tenta sincronizar removendo G (enviando apenas P e M)
        new_variants, warnings = sync_product_variants(self.product, ['P', 'M'])
        
        self.var_g.refresh_from_db()
        # A variante G ainda deve existir no banco e estar ativa por ter histórico
        self.assertTrue(ProductVariant.objects.filter(id=self.var_g.id).exists())
        self.assertTrue(self.var_g.ativo)
        self.assertTrue(any("não pode ser removida" in w for w in warnings))

    def test_purchase_receiving_uses_existing_variants(self):
        """AC28: Entrada de compra consulta variantes cadastradas."""
        self.client.force_login(self.admin_user)
        url = reverse('product_variants_ajax') + f'?product_id={self.product.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        variants_returned = [v['tamanho'] for v in data.get('variants', [])]
        self.assertIn('P', variants_returned)
        self.assertIn('M', variants_returned)
        self.assertIn('G', variants_returned)
