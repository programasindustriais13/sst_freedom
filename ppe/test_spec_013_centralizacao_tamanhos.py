from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from ppe.models import Product, ProductVariant, CertificadoAprovacao, PPEDelivery
from inventory.models import StockMovement, Lot
from organizations.models import Company, Unit, InventoryLocation, Function, Sector, CostCenter
from employees.models import Employee
from ppe.services import sync_product_variants, normalize_size_string, variant_has_history_or_stock
from datetime import date

User = get_user_model()

class SPEC013CentralizacaoTamanhosTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin_spec13',
            email='admin@test.com',
            password='password123'
        )
        self.client.login(username='admin_spec13', password='password123')

        self.company = Company.objects.create(razao_social="Empresa Teste SPEC13", cnpj="11.111.111/0001-11")
        self.unit = Unit.objects.create(company=self.company, nome="Unidade Central", codigo="UC01")
        self.sector = Sector.objects.create(unit=self.unit, nome="Segurança")
        self.cost_center = CostCenter.objects.create(company=self.company, nome="CC01", codigo="101")
        self.function = Function.objects.create(company=self.company, nome="Técnico de Segurança")
        self.user.units.add(self.unit)

        self.location = InventoryLocation.objects.create(
            unit=self.unit,
            codigo="LOC01",
            nome="Almoxarifado Principal",
            tipo="ALMOXARIFADO",
            ativo=True
        )
        self.location_sst = InventoryLocation.objects.create(
            unit=self.unit,
            codigo="LOCSST01",
            nome="Estoque SST",
            tipo="SST",
            ativo=True
        )

        self.product = Product.objects.create(
            nome="Luva de Proteção",
            tipo_produto="EPI",
            ca_numero="12345",
            exige_ca=True,
            ativo=True
        )
        self.var_p = ProductVariant.objects.create(product=self.product, tamanho="P", sku="SKU-P", estoque_minimo=10, ativo=True)
        self.var_m = ProductVariant.objects.create(product=self.product, tamanho="M", sku="SKU-M", estoque_minimo=20, ativo=True)

    def test_01_card_adicionar_tamanho_nao_aparece_no_detalhe(self):
        url = reverse('product_detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Adicionar Tamanho/Grade")

    def test_02_formulario_antigo_nao_permanece_escondido_no_html(self):
        url = reverse('product_detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        self.assertNotContains(response, f"action=\"/ppe/{self.product.pk}/variants/add/\"")
        self.assertNotContains(response, "name=\"tamanho\"")

    def test_03_rota_antiga_redireciona_e_impede_cadastro(self):
        url = reverse('variant_create', kwargs={'product_pk': self.product.pk})
        response = self.client.post(url, {'tamanho': 'GG'})
        self.assertRedirects(response, reverse('product_update', kwargs={'pk': self.product.pk}))
        self.assertFalse(ProductVariant.objects.filter(product=self.product, tamanho='GG').exists())

    def test_04_formulario_edicao_apresenta_tamanhos_existentes(self):
        url = reverse('product_update', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="P, M"')

    def test_05_formulario_apresenta_apenas_tamanhos_do_epi_atual(self):
        other_product = Product.objects.create(nome="Outro EPI", tipo_produto="EPI", ca_numero="99999", ativo=True)
        ProductVariant.objects.create(product=other_product, tamanho="XGG", ativo=True)

        url = reverse('product_update', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        self.assertContains(response, 'value="P, M"')
        self.assertNotContains(response, 'value="XGG"')

    def test_06_salvar_sem_modificar_campo_nao_cria_duplicidades(self):
        url = reverse('product_update', kwargs={'pk': self.product.pk})
        data = {
            'nome': self.product.nome,
            'tipo_produto': self.product.tipo_produto,
            'categoria': self.product.categoria or 'OUTRO',
            'ca_numero': self.product.ca_numero,
            'unidade_medida': 'UND',
            'fabricante': self.product.fabricante or '',
            'tamanhos_str': 'P, M',
            'ativo': True
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '/ppe/')
        self.assertEqual(self.product.variants.filter(ativo=True).count(), 2)

    def test_07_adicionar_nova_variante_preserva_existentes(self):
        url = reverse('product_update', kwargs={'pk': self.product.pk})
        data = {
            'nome': self.product.nome,
            'tipo_produto': self.product.tipo_produto,
            'categoria': self.product.categoria or 'OUTRO',
            'ca_numero': self.product.ca_numero,
            'unidade_medida': 'UND',
            'tamanhos_str': 'P, M, G',
            'ativo': True
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '/ppe/')
        self.assertTrue(self.product.variants.filter(tamanho='G', ativo=True).exists())
        self.assertTrue(self.product.variants.filter(tamanho='P', ativo=True).exists())

    def test_08_espacos_e_valores_vazios_sao_ignorados(self):
        result = normalize_size_string(" P ,   , M ,  , G  ")
        self.assertEqual(result, ["P", "M", "G"])

    def test_09_valores_repetidos_sao_deduplicados(self):
        result = normalize_size_string("P, M, G, P, M, G, P")
        self.assertEqual(result, ["P", "M", "G"])

    def test_10_comparacao_nao_diferencia_maiusculas_e_minusculas(self):
        result = normalize_size_string("P, M, G, m, p, g, GG")
        self.assertEqual(result, ["P", "M", "G", "GG"])

    def test_11_sku_e_estoque_minimo_existentes_sao_preservados(self):
        sync_product_variants(self.product, "P, M, G")
        self.var_p.refresh_from_db()
        self.assertEqual(self.var_p.sku, "SKU-P")
        self.assertEqual(self.var_p.estoque_minimo, 10)

    def test_12_variante_com_estoque_nao_e_excluida(self):
        lot = Lot.objects.create(
            product_variant=self.var_p,
            identificador="LOTE-01",
            data_validade=date(2028, 1, 1),
            quantidade_inicial=100,
            custo_unitario=10.00
        )
        StockMovement.objects.create(
            unit=self.unit,
            location=self.location,
            product_variant=self.var_p,
            lot=lot,
            quantity=50,
            cost_unit=10.00,
            movement_type='ENTRADA_COMPRA',
            user=self.user
        )
        updated, warnings = sync_product_variants(self.product, "M")
        self.var_p.refresh_from_db()
        self.assertTrue(self.var_p.ativo)
        self.assertTrue(any("variante P não pode ser removida" in w for w in warnings))

    def test_13_variante_com_historico_de_entrega_nao_e_excluida(self):
        employee = Employee.objects.create(
            unit=self.unit,
            company=self.company,
            setor=self.sector,
            centro_custo=self.cost_center,
            funcao=self.function,
            nome_completo="João da Silva",
            cpf="529.982.247-25",
            matricula="MAT-01",
            data_admissao=date(2025, 1, 1),
            situacao="ATIVO"
        )
        lot = Lot.objects.create(
            product_variant=self.var_m,
            identificador="LOTE-02",
            data_validade=date(2028, 1, 1),
            quantidade_inicial=50,
            custo_unitario=15.00
        )
        PPEDelivery.objects.create(
            employee=employee,
            funcao=self.function,
            setor=self.sector,
            centro_custo=self.cost_center,
            unit=self.unit,
            product_variant=self.var_m,
            lot=lot,
            validade_fisica=lot.data_validade,
            quantidade=1,
            custo_unitario=lot.custo_unitario,
            data_entrega=date.today(),
            vida_util_aplicada=90,
            data_prevista_troca=date.today(),
            usuario_responsavel=self.user
        )
        updated, warnings = sync_product_variants(self.product, "P")
        self.var_m.refresh_from_db()
        self.assertTrue(self.var_m.ativo)
        self.assertTrue(any("variante M não pode ser removida" in w for w in warnings))

    def test_14_mensagem_de_bloqueio_apresentada_ao_usuario(self):
        lot = Lot.objects.create(
            product_variant=self.var_p,
            identificador="LOTE-03",
            data_validade=date(2028, 1, 1),
            quantidade_inicial=10,
            custo_unitario=5.00
        )
        StockMovement.objects.create(
            unit=self.unit,
            location=self.location,
            product_variant=self.var_p,
            lot=lot,
            quantity=10,
            cost_unit=5.00,
            movement_type='ENTRADA_COMPRA',
            user=self.user
        )

        url = reverse('product_update', kwargs={'pk': self.product.pk})
        data = {
            'nome': self.product.nome,
            'tipo_produto': self.product.tipo_produto,
            'categoria': self.product.categoria or 'OUTRO',
            'ca_numero': self.product.ca_numero,
            'unidade_medida': 'UND',
            'tamanhos_str': 'M',
            'ativo': True
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "A variante P não pode ser removida porque possui estoque ou histórico de movimentações.")

    def test_15_ca_ja_existente_bloqueia_novo_epi_principal(self):
        url = reverse('product_create')
        data = {
            'nome': "Outra Luva Duplicada",
            'tipo_produto': "EPI",
            'categoria': "PROTECAO_MEMBROS_SUP",
            'ca_numero': "12345",
            'unidade_medida': "UND",
            'ativo': True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        form_errors = response.context['form'].errors.get('ca_numero', [])
        self.assertTrue(any("Já existe um EPI cadastrado com o CA 12345" in err for err in form_errors))

    def test_16_edicao_do_proprio_epi_continua_permitida(self):
        url = reverse('product_update', kwargs={'pk': self.product.pk})
        data = {
            'nome': "Luva de Proteção Editada",
            'tipo_produto': "EPI",
            'categoria': "PROTECAO_MEMBROS_SUP",
            'ca_numero': "12345",
            'unidade_medida': "UND",
            'tamanhos_str': "P, M",
            'ativo': True
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, '/ppe/')
        self.product.refresh_from_db()
        self.assertEqual(self.product.nome, "Luva de Proteção Editada")

    def test_17_ca_vazio_nao_agrupa_registros_indevidamente(self):
        p1 = Product.objects.create(nome="Item Sem CA 1", tipo_produto="FERRAMENTA", ca_numero=None, exige_ca=False, ativo=True)
        p2 = Product.objects.create(nome="Item Sem CA 2", tipo_produto="FERRAMENTA", ca_numero=None, exige_ca=False, ativo=True)
        self.assertTrue(p1.pk and p2.pk)

    def test_18_consulta_automatica_ca_respeita_validacao_duplicidade(self):
        url = reverse('product_create')
        data = {
            'nome': "Novo Capacete",
            'tipo_produto': "EPI",
            'categoria': "PROTECAO_CABECA",
            'ca_numero': "  12345  ",
            'unidade_medida': "UND",
            'ativo': True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        form_errors = response.context['form'].errors.get('ca_numero', [])
        self.assertTrue(any("Já existe um EPI cadastrado com o CA 12345" in err for err in form_errors))

    def test_19_permissoes_atuais_continuam_funcionando(self):
        self.client.logout()
        url = reverse('product_detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
