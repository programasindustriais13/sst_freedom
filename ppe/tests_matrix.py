from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import Company, Unit, Function
from ppe.models import Product, ProductVariant, PPEMatrix

User = get_user_model()

class PPEMatrixViewsTestCase(TestCase):
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

    def test_tecnico_can_add_ppe_to_matrix(self):
        self.client.login(username="tecnico", password="pwd")
        url = reverse('ppe_matrix_create', kwargs={'function_pk': self.funcao.id})
        
        data = {
            'product': self.product.id,
            'variant': self.variant.id,
            'obrigatorio': True,
            'principal': True,
            'quantidade_padrao': 1,
            'vida_util_dias': 120,
            'ativo': True
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect to function_detail
        
        self.assertTrue(PPEMatrix.objects.filter(funcao=self.funcao, product=self.product).exists())

    def test_almoxarife_cannot_add_ppe_to_matrix(self):
        self.client.login(username="almoxarife", password="pwd")
        url = reverse('ppe_matrix_create', kwargs={'function_pk': self.funcao.id})
        
        data = {
            'product': self.product.id,
            'variant': self.variant.id,
            'obrigatorio': True,
            'principal': True,
            'quantidade_padrao': 1,
            'vida_util_dias': 120,
            'ativo': True
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 403) # PermissionDenied

    def test_duplicate_ppe_matrix_prevented(self):
        # Create initial entry
        PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product,
            quantidade_padrao=1,
            vida_util_dias=120,
            ativo=True
        )
        
        self.client.login(username="tecnico", password="pwd")
        url = reverse('ppe_matrix_create', kwargs={'function_pk': self.funcao.id})
        
        data = {
            'product': self.product.id,
            'obrigatorio': True,
            'principal': True,
            'quantidade_padrao': 2,
            'vida_util_dias': 180,
            'ativo': True
        }
        
        # Post duplicate
        response = self.client.post(url, data)
        # Should render form again with errors (status code 200, not redirect)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'product', "Este EPI já está cadastrado na matriz de recomendação para esta função.")

    def test_tecnico_can_toggle_ppe_matrix_status(self):
        entry = PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product,
            quantidade_padrao=1,
            vida_util_dias=120,
            ativo=True
        )
        
        self.client.login(username="tecnico", password="pwd")
        url = reverse('ppe_matrix_toggle_active', kwargs={'pk': entry.id})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        entry.refresh_from_db()
        self.assertFalse(entry.ativo)

    def test_almoxarife_cannot_toggle_ppe_matrix_status(self):
        entry = PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product,
            quantidade_padrao=1,
            vida_util_dias=120,
            ativo=True
        )
        
        self.client.login(username="almoxarife", password="pwd")
        url = reverse('ppe_matrix_toggle_active', kwargs={'pk': entry.id})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        
        entry.refresh_from_db()
        self.assertTrue(entry.ativo)
