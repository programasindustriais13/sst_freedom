from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import Company, Unit
from ppe.models import Product, ProductVariant

User = get_user_model()

class PPEDetailSimplificationTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(razao_social="Indústria Teste LTDA", nome_fantasia="Indústria Teste", cnpj="12345678000199")
        self.unit = Unit.objects.create(company=self.company, codigo="UN-TEST", nome="Unidade Teste", cidade="Natal", estado="RN")
        
        # SST user (authorized)
        self.user = User.objects.create_user(username="tecnico", password="pwd", profile_type="TECNICO_SST")
        self.user.units.add(self.unit)
        
        # Product with variants
        self.product_with_variants = Product.objects.create(nome="EPI com Tamanhos", categoria="CALCADOS", exige_ca=False)
        self.variant = ProductVariant.objects.create(product=self.product_with_variants, tamanho="M", sku="SKU-M", estoque_minimo=10)
        self.variant2 = ProductVariant.objects.create(product=self.product_with_variants, tamanho="G", sku="SKU-G", estoque_minimo=5)
        
        # Product with no variants
        self.product_no_variants = Product.objects.create(nome="EPI sem Tamanhos", categoria="CALCADOS", exige_ca=False)

    def test_detail_page_success(self):
        self.client.login(username="tecnico", password="pwd")
        url = reverse('product_detail', kwargs={'pk': self.product_with_variants.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_detail_page_table_structure_with_variants(self):
        self.client.login(username="tecnico", password="pwd")
        url = reverse('product_detail', kwargs={'pk': self.product_with_variants.pk})
        response = self.client.get(url)
        html = response.content.decode('utf-8')
        
        # Table should not have "Status" column header
        self.assertNotIn('>Status</th>', html)
        self.assertNotIn('>Situação</th>', html)
        self.assertNotIn('>Inativo</th>', html)
        
        # Table lines should display sizes and min stocks
        self.assertIn('M', html)
        self.assertIn('SKU-M', html)
        self.assertIn('10', html)
        self.assertIn('G', html)
        self.assertIn('SKU-G', html)
        self.assertIn('5', html)
        
        # Table should not display Active/Inactive badges
        self.assertNotIn('<span class="badge bg-success">Ativo</span>', html)
        self.assertNotIn('<span class="badge bg-danger">Inativo</span>', html)

    def test_detail_page_table_colspan_empty_state(self):
        self.client.login(username="tecnico", password="pwd")
        url = reverse('product_detail', kwargs={'pk': self.product_no_variants.pk})
        response = self.client.get(url)
        html = response.content.decode('utf-8')
        
        # Colspan should be 3 in the empty state row of Grade de Tamanhos Cadastrados
        self.assertIn('<td colspan="3" class="text-center text-muted border-0 py-4">Nenhum tamanho cadastrado para este produto.</td>', html)

    def test_add_duplicate_variant_fails_gracefully(self):
        self.client.login(username="tecnico", password="pwd")
        url = reverse('variant_create', kwargs={'product_pk': self.product_with_variants.pk})
        
        # Tentando adicionar o tamanho "M" que já foi criado no setUp
        data = {
            'tamanho': 'M',
            'sku': 'SKU-M-NEW',
            'estoque_minimo': 2
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redireciona para o detalhe
        
        # Garante que não foi criada outra variante
        self.assertEqual(ProductVariant.objects.filter(product=self.product_with_variants, tamanho='M').count(), 1)
