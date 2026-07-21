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
            'ppe_matrix_entries-TOTAL_FORMS': '2',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-product': self.product1.id,
            'ppe_matrix_entries-0-vida_util_dias': 120,
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',
            'ppe_matrix_entries-1-product': self.product2.id,
            'ppe_matrix_entries-1-vida_util_dias': 60,
            'ppe_matrix_entries-1-obrigatorio': 'on',
            'ppe_matrix_entries-1-principal': 'on',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect to function_detail

        # 4. EPIs are associated correctly
        self.assertTrue(PPEMatrix.objects.filter(funcao=self.funcao, product=self.product1, ativo=True, vida_util_dias=120).exists())
        self.assertTrue(PPEMatrix.objects.filter(funcao=self.funcao, product=self.product2, ativo=True, vida_util_dias=60).exists())

    def test_unauthorized_user_cannot_create_matrix(self):
        # 14. URLs cannot bypass permissions
        self.client.login(username="almoxarife", password="pwd")
        url = reverse('matrix_bulk_create')
        response = self.client.post(url, {'funcao': self.funcao.id})
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

        # Edit keeps product1 and adds product2
        data = {
            'ppe_matrix_entries-TOTAL_FORMS': '2',
            'ppe_matrix_entries-INITIAL_FORMS': '1',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-id': entry.id,
            'ppe_matrix_entries-0-product': self.product1.id,
            'ppe_matrix_entries-0-vida_util_dias': 180,
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',
            'ppe_matrix_entries-1-id': '',
            'ppe_matrix_entries-1-product': self.product2.id,
            'ppe_matrix_entries-1-vida_util_dias': 90,
            'ppe_matrix_entries-1-obrigatorio': 'on',
            'ppe_matrix_entries-1-principal': 'on',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        entry.refresh_from_db()
        self.assertEqual(entry.vida_util_dias, 180)
        self.assertTrue(entry.ativo)

        # product2 is added
        entry2 = PPEMatrix.objects.filter(funcao=self.funcao, product=self.product2, ativo=True).first()
        self.assertIsNotNone(entry2)
        self.assertEqual(entry2.vida_util_dias, 90)

        # Now edit again and delete product1
        data = {
            'ppe_matrix_entries-TOTAL_FORMS': '2',
            'ppe_matrix_entries-INITIAL_FORMS': '2',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-id': entry.id,
            'ppe_matrix_entries-0-product': self.product1.id,
            'ppe_matrix_entries-0-vida_util_dias': 180,
            'ppe_matrix_entries-0-DELETE': 'on',
            'ppe_matrix_entries-1-id': entry2.id,
            'ppe_matrix_entries-1-product': self.product2.id,
            'ppe_matrix_entries-1-vida_util_dias': 90,
            'ppe_matrix_entries-1-obrigatorio': 'on',
            'ppe_matrix_entries-1-principal': 'on',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # product1 should now be removed/deleted
        self.assertFalse(PPEMatrix.objects.filter(id=entry.id).exists())

    def test_validation_rules_respected(self):
        # Required fields and positive vida util validated
        self.client.login(username="tecnico", password="pwd")
        url = reverse('matrix_bulk_create')
        
        # Zero or negative vida util
        data = {
            'funcao': self.funcao.id,
            'ppe_matrix_entries-TOTAL_FORMS': '1',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-product': self.product1.id,
            'ppe_matrix_entries-0-vida_util_dias': 0,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200) # Form returns error page
        self.assertFalse(response.context['formset'].is_valid())

    def test_matrix_delete_authorized(self):
        # Create initial matrix
        PPEMatrix.objects.create(funcao=self.funcao, product=self.product1, quantidade_padrao=1, vida_util_dias=120, ativo=True)
        PPEMatrix.objects.create(funcao=self.funcao, product=self.product2, quantidade_padrao=1, vida_util_dias=120, ativo=True)

        self.client.login(username="tecnico", password="pwd")
        url = reverse('matrix_bulk_delete', kwargs={'function_pk': self.funcao.id})

        # Get confirmation page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Authorized delete works
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
            'ppe_matrix_entries-TOTAL_FORMS': '1',
            'ppe_matrix_entries-INITIAL_FORMS': '0',
            'ppe_matrix_entries-MIN_NUM_FORMS': '0',
            'ppe_matrix_entries-MAX_NUM_FORMS': '1000',
            'ppe_matrix_entries-0-product': self.product1.id,
            'ppe_matrix_entries-0-vida_util_dias': 120,
            'ppe_matrix_entries-0-obrigatorio': 'on',
            'ppe_matrix_entries-0-principal': 'on',
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
