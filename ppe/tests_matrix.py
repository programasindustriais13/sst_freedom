from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import Company, Unit, Function
from ppe.models import Product, ProductVariant, PPEMatrix

User = get_user_model()

class PPEMatrixViewsTestCase(TestCase):
    """
    SPEC 2026-015: Garante que as antigas rotas operacionais de matriz por função
    redirecionam para o fluxo canônico de Matriz por Setor.
    """
    def setUp(self):
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        self.funcao = Function.objects.create(company=self.company, nome="Eletricista")
        
        self.product = Product.objects.create(nome="Bota de Couro com Biqueira", categoria="CALCADOS", exige_ca=True, tipo_produto="EPI")
        self.variant = ProductVariant.objects.create(product=self.product, tamanho="41", sku="BOT-41")
        
        # User profiles
        self.tecnico = User.objects.create_user(username="tecnico", password="pwd", profile_type="TECNICO_SST")
        self.tecnico.units.add(self.unit)
        
        self.almoxarife = User.objects.create_user(username="almoxarife", password="pwd", profile_type="ALMOXARIFE")
        self.almoxarife.units.add(self.unit)

    def test_legacy_create_matrix_redirects_to_sector_matrix(self):
        self.client.login(username="tecnico", password="pwd")
        url = reverse('ppe_matrix_create', kwargs={'function_pk': self.funcao.id})
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse('sector_matrix_list'))
        content = response.content.decode('utf-8')
        self.assertIn("A Matriz de EPI agora é gerenciada exclusivamente por Setor", content)

    def test_legacy_toggle_active_redirects_to_sector_matrix(self):
        entry = PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product,
            quantidade_padrao=1,
            vida_util_dias=120,
            ativo=True
        )
        self.client.login(username="tecnico", password="pwd")
        url = reverse('ppe_matrix_toggle_active', kwargs={'pk': entry.id})
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse('sector_matrix_list'))
