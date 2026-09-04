from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import Company, Unit, Sector, Function
from ppe.models import Product, PPEMatrix, ProductVariant

User = get_user_model()

class PPEMatrixBulkTestCase(TestCase):
    """
    SPEC 2026-015: Atualizado para refletir a substituição da SPEC 2026-005.
    As rotas legadas de matriz por função agora redirecionam para a Matriz por Setor.
    """
    def setUp(self):
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        self.sector = Sector.objects.create(unit=self.unit, nome="Manutenção Elétrica")
        self.funcao = Function.objects.create(company=self.company, nome="Eletricista")

        self.product1 = Product.objects.create(nome="Bota de Couro com Biqueira", categoria="CALCADOS", exige_ca=True, tipo_produto="EPI")
        self.product2 = Product.objects.create(nome="Luva de Alta Tensão", categoria="LUVAS", exige_ca=True, tipo_produto="EPI")

        self.tecnico = User.objects.create_user(username="tecnico", password="pwd", profile_type="TECNICO_SST")
        self.tecnico.units.add(self.unit)

        self.almoxarife = User.objects.create_user(username="almoxarife", password="pwd", profile_type="ALMOXARIFE")
        self.almoxarife.units.add(self.unit)

    def test_legacy_matrix_list_redirects_to_sector_matrix_list(self):
        self.client.login(username="tecnico", password="pwd")
        response = self.client.get(reverse('matrix_list'), follow=True)
        self.assertRedirects(response, reverse('sector_matrix_list'))
        content = response.content.decode('utf-8')
        self.assertIn("A Matriz de EPI agora é gerenciada exclusivamente por Setor", content)

    def test_legacy_bulk_update_redirects(self):
        self.client.login(username="tecnico", password="pwd")
        response = self.client.get(reverse('matrix_bulk_update', kwargs={'function_pk': self.funcao.id}), follow=True)
        self.assertRedirects(response, reverse('sector_matrix_list'))

    def test_legacy_bulk_delete_redirects(self):
        self.client.login(username="tecnico", password="pwd")
        response = self.client.get(reverse('matrix_bulk_delete', kwargs={'function_pk': self.funcao.id}), follow=True)
        self.assertRedirects(response, reverse('sector_matrix_list'))

    def test_bulk_create_routes_to_sector_matrix_create(self):
        self.client.login(username="tecnico", password="pwd")
        url = reverse('matrix_bulk_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("Nova Matriz de EPI por Setor", content)

    def test_navigation_menu_visibility(self):
        self.client.login(username="tecnico", password="pwd")
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, "Matriz de EPI por Setor")

        self.client.login(username="almoxarife", password="pwd")
        response = self.client.get(reverse('dashboard'))
        self.assertNotContains(response, "Matriz de EPI por Setor")
