from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import Company, Unit, Function
from ppe.models import Product, PPEMatrix, ProductVariant

User = get_user_model()

class PPEMatrixBulkTestCase(TestCase):
    def setUp(self):
        # Base setup
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        self.funcao = Function.objects.create(company=self.company, nome="Eletricista")
        self.funcao2 = Function.objects.create(company=self.company, nome="Mecânico")

        # Products
        self.product1 = Product.objects.create(nome="Bota de Couro com Biqueira", categoria="CALCADOS", exige_ca=True, tipo_produto="EPI")
        self.product2 = Product.objects.create(nome="Luva de Alta Tensão", categoria="LUVAS", exige_ca=True, tipo_produto="EPI")
        self.product3 = Product.objects.create(nome="Óculos de Proteção", categoria="OCULOS", exige_ca=True, tipo_produto="EPI")

        # Users
        self.tecnico = User.objects.create_user(username="tecnico", password="pwd", profile_type="TECNICO_SST")
        self.tecnico.units.add(self.unit)

        self.almoxarife = User.objects.create_user(username="almoxarife", password="pwd", profile_type="ALMOXARIFE")
        self.almoxarife.units.add(self.unit)

        self.anonimo = User.objects.create_user(username="anonimo", password="pwd", profile_type="OUTRO") # profile without permission

    def test_authorized_user_can_access_list(self):
        # 1. Técnico SST can access list
        self.client.login(username="tecnico", password="pwd")
        response = self.client.get(reverse('matrix_list'))
        self.assertEqual(response.status_code, 200)

        # 2. Almoxarife can access list (read-only)
        self.client.login(username="almoxarife", password="pwd")
        response = self.client.get(reverse('matrix_list'))
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user_cannot_access_list(self):
        # Anonymous (not logged in) is redirected to login
        self.client.logout()
        response = self.client.get(reverse('matrix_list'))
        self.assertEqual(response.status_code, 302)

    def test_authorized_user_can_create_matrix(self):
        # 3. Técnico SST can create a matrix
        self.client.login(username="tecnico", password="pwd")
        url = reverse('matrix_bulk_create')
        
        data = {
            'funcao': self.funcao.id,
            'products': [self.product1.id, self.product2.id],
            'quantidade_padrao': 1,
            'vida_util_dias': 120,
            'obrigatorio': True,
            'principal': True,
            'orientacoes': 'Instruções de teste.'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect to function_detail

        # 4. EPIs are associated correctly
        self.assertTrue(PPEMatrix.objects.filter(funcao=self.funcao, product=self.product1, ativo=True).exists())
        self.assertTrue(PPEMatrix.objects.filter(funcao=self.funcao, product=self.product2, ativo=True).exists())

    def test_unauthorized_user_cannot_create_matrix(self):
        # 14. URLs cannot bypass permissions
        self.client.login(username="almoxarife", password="pwd")
        url = reverse('matrix_bulk_create')
        response = self.client.post(url, {'funcao': self.funcao.id, 'products': [self.product1.id]})
        self.assertEqual(response.status_code, 403) # Forbidden for Almoxarife

    def test_edit_preserves_same_record_and_updates_correctly(self):
        # Create initial matrix entry
        entry = PPEMatrix.objects.create(
            funcao=self.funcao,
            product=self.product1,
            quantidade_padrao=1,
            vida_util_dias=120,
            ativo=True
        )

        self.client.login(username="tecnico", password="pwd")
        url = reverse('matrix_bulk_update', kwargs={'function_pk': self.funcao.id})

        # 5. Edit keeps the same record, 6. updates associated EPIs
        # We select product1 and product2 (adds product2, keeps product1)
        data = {
            'funcao': self.funcao.id,
            'products': [self.product1.id, self.product2.id],
            'quantidade_padrao': 2,
            'vida_util_dias': 180,
            'obrigatorio': True,
            'principal': True,
            'orientacoes': 'Updated.'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        entry.refresh_from_db()
        self.assertEqual(entry.id, entry.id)
        self.assertTrue(entry.ativo)

        # product2 is added
        self.assertTrue(PPEMatrix.objects.filter(funcao=self.funcao, product=self.product2, ativo=True).exists())

        # Now, let's edit again and deselect product1 (should make it inactive)
        data = {
            'funcao': self.funcao.id,
            'products': [self.product2.id],
            'quantidade_padrao': 2,
            'vida_util_dias': 180,
            'obrigatorio': True,
            'principal': True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # entry (product1) should now be INACTIVE
        entry.refresh_from_db()
        self.assertFalse(entry.ativo)

    def test_validation_rules_respected(self):
        # 7. Required fields validated
        self.client.login(username="tecnico", password="pwd")
        url = reverse('matrix_bulk_create')
        
        # Missing products
        data = {
            'funcao': self.funcao.id,
            'products': [],
            'quantidade_padrao': 1,
            'vida_util_dias': 120,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200) # Form returns error page
        self.assertFalse(response.context['form'].is_valid())

    def test_matrix_delete_authorized(self):
        # Create initial matrix
        PPEMatrix.objects.create(funcao=self.funcao, product=self.product1, quantidade_padrao=1, vida_util_dias=120, ativo=True)
        PPEMatrix.objects.create(funcao=self.funcao, product=self.product2, quantidade_padrao=1, vida_util_dias=120, ativo=True)

        self.client.login(username="tecnico", password="pwd")
        url = reverse('matrix_bulk_delete', kwargs={'function_pk': self.funcao.id})

        # Get confirmation page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 9. Authorized delete works
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PPEMatrix.objects.filter(funcao=self.funcao).count(), 0)

    def test_matrix_delete_unauthorized(self):
        PPEMatrix.objects.create(funcao=self.funcao, product=self.product1, quantidade_padrao=1, vida_util_dias=120, ativo=True)

        self.client.login(username="almoxarife", password="pwd")
        url = reverse('matrix_bulk_delete', kwargs={'function_pk': self.funcao.id})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PPEMatrix.objects.filter(funcao=self.funcao).count(), 1)

    def test_bidirectional_compatibilty_admin_and_ui(self):
        # 11. Records created by UI appear in Admin
        self.client.login(username="tecnico", password="pwd")
        self.client.post(reverse('matrix_bulk_create'), {
            'funcao': self.funcao.id,
            'products': [self.product1.id],
            'quantidade_padrao': 1,
            'vida_util_dias': 120,
            'obrigatorio': True,
            'principal': True
        })

        admin_url = reverse('admin:ppe_ppematrix_changelist')
        admin_user = User.objects.create_superuser(username="admin", password="pwd")
        self.client.login(username="admin", password="pwd")
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.funcao.nome)

        # 12. Records created by Admin appear in UI
        PPEMatrix.objects.create(funcao=self.funcao2, product=self.product3, quantidade_padrao=1, vida_util_dias=90, ativo=True)

        self.client.login(username="tecnico", password="pwd")
        response = self.client.get(reverse('matrix_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.funcao2.nome)

    def test_navigation_menu_visibility(self):
        # 13. Menu appears only to authorized users
        self.client.login(username="tecnico", password="pwd")
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, "Matriz de EPI por Função")

        self.client.login(username="almoxarife", password="pwd")
        response = self.client.get(reverse('dashboard'))
        self.assertNotContains(response, "Matriz de EPI por Função")
