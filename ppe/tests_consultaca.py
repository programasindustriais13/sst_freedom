import datetime
from unittest.mock import patch, MagicMock
import requests
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from ppe.models import CertificadoAprovacao, Product
from ppe.ca_services import ConsultaCAClient, ConsultaCAParser, ConsultaCAService
from ppe.forms import ProductForm

User = get_user_model()

class ConsultaCATestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_tecnico = User.objects.create_user(username="tecnico", password="pwd", profile_type="TECNICO_SST")
        self.user_almoxarife = User.objects.create_user(username="almoxarife", password="pwd", profile_type="ALMOXARIFE")
        
        # Simple HTML fixture representing CA 11223
        self.html_fixture_11223 = """
        <!DOCTYPE html>
        <html>
        <head><title>CA 11223 - RESPIRADOR DE ADUÇÃO DE AR</title></head>
        <body>
            <span class="grupo-epi-desc">Proteção Respiratória</span>
            <h1>RESPIRADOR DE ADUÇÃO DE AR TIPO LINHA DE AR COMPRIMIDO DE FLUXO CONTÍNUO</h1>
            <p class="num_ca"><strong>N° CA:</strong><span>11223</span></p>
            <p><strong>Situação:</strong><br /><span>VENCIDO</span></p>
            <p><strong>Validade:</strong><br /><span class="validade_ca vencido">18/12/2005</span><span class="validade_ca_dias">venceu há 7512 dias</span></p>
            <p><strong>N° Processo:</strong><br />460000147930064</p>
            <p><strong>Natureza:</strong><br />Nacional</p>
            <p><strong>Razão Social:</strong><br /><a href="/fabricante/72">BUNZL EQUIPAMENTOS PARA PROTECAO INDIVIDUAL LTDA</a></p>
            <p><strong>CNPJ:</strong><br />43.854.777/0001-26</p>
            <p><strong>Nome Fantasia:</strong><br />PROT-CAP</p>
            <p><strong>Cidade/UF:</strong><br />GUARULHOS/SP</p>
            <p><strong>Aprovado Para:</strong><br />PROTEÇÃO RESPIRATÓRIA DO USUÁRIO EM AMBIENTES NÃO IMEDIATAMENTE PERIGOSOS.</p>
        </body>
        </html>
        """

    def test_client_validation_ca_number(self):
        client = ConsultaCAClient()
        with self.assertRaises(ValueError):
            client.get_html("123a")
        with self.assertRaises(ValueError):
            client.get_html("")

    @patch('requests.get')
    def test_client_ssrf_and_redirect_blocking(self, mock_get):
        # Setup mock response to behave like redirect
        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_response.headers = {'Location': 'https://malicious-site.com'}
        mock_get.return_value = mock_response

        client = ConsultaCAClient()
        with self.assertRaises(ValueError):
            client.get_html("11223")

    @patch('requests.get')
    def test_client_large_response_blocking(self, mock_get):
        # Mock chunk streaming exceeding limit
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        # Return chunks
        mock_response.iter_content.return_value = [b"a" * 8192] * 200 # 1.6MB total
        mock_get.return_value = mock_response

        client = ConsultaCAClient()
        with patch.object(client, 'max_response_bytes', 10000):
            with self.assertRaises(ValueError) as ctx:
                client.get_html("11223")
            self.assertIn("excedeu o limite", str(ctx.exception))

    @patch('requests.get')
    def test_client_unexpected_content_type(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.iter_content.return_value = [b"{}"]
        mock_get.return_value = mock_response

        client = ConsultaCAClient()
        with self.assertRaises(ValueError) as ctx:
            client.get_html("11223")
        self.assertIn("Content-Type", str(ctx.exception))

    def test_parser_ca_11223(self):
        parsed = ConsultaCAParser.parse(self.html_fixture_11223, "11223")
        self.assertTrue(parsed['found'])
        self.assertEqual(parsed['numero'], '11223')
        self.assertEqual(parsed['descricao_oficial'], 'RESPIRADOR DE ADUÇÃO DE AR TIPO LINHA DE AR COMPRIMIDO DE FLUXO CONTÍNUO')
        self.assertEqual(parsed['grupo_protecao'], 'Proteção Respiratória')
        self.assertEqual(parsed['situacao'], 'VENCIDO')
        self.assertEqual(parsed['validade'], '18/12/2005')
        self.assertEqual(parsed['processo'], '460000147930064')
        self.assertEqual(parsed['natureza'], 'Nacional')
        self.assertEqual(parsed['fabricante'], 'BUNZL EQUIPAMENTOS PARA PROTECAO INDIVIDUAL LTDA')
        self.assertEqual(parsed['cnpj'], '43854777000126')
        self.assertEqual(parsed['nome_fantasia'], 'PROT-CAP')
        self.assertEqual(parsed['cidade_uf'], 'GUARULHOS/SP')
        self.assertEqual(parsed['aprovado_para'], 'PROTEÇÃO RESPIRATÓRIA DO USUÁRIO EM AMBIENTES NÃO IMEDIATAMENTE PERIGOSOS.')

    def test_parser_not_found(self):
        html_not_found = "<html><body><h1>CA não localizado</h1></body></html>"
        parsed = ConsultaCAParser.parse(html_not_found, "99999")
        self.assertFalse(parsed['found'])

    @patch('ppe.ca_services.ConsultaCAClient.get_html')
    def test_service_caching_and_expiration(self, mock_get_html):
        mock_get_html.return_value = self.html_fixture_11223
        
        # Cache Miss - first query
        res = ConsultaCAService.get_or_query("11223")
        self.assertTrue(res['found'])
        self.assertEqual(mock_get_html.call_count, 1)

        # Cache Hit - second query immediately
        res2 = ConsultaCAService.get_or_query("11223")
        self.assertTrue(res2['found'])
        # call_count should still be 1
        self.assertEqual(mock_get_html.call_count, 1)

        # Expire cache manually
        CertificadoAprovacao.objects.filter(numero="11223").update(
            ultima_sincronizacao=timezone.now() - datetime.timedelta(days=2)
        )

        # Cache Miss again after 24h
        res3 = ConsultaCAService.get_or_query("11223")
        self.assertTrue(res3['found'])
        self.assertEqual(mock_get_html.call_count, 2)

    @patch('ppe.ca_services.ConsultaCAClient.get_html')
    def test_service_negative_caching_not_found(self, mock_get_html):
        mock_get_html.return_value = "" # mock empty response representing not found
        
        # Cache Miss
        res = ConsultaCAService.get_or_query("88888")
        self.assertFalse(res['found'])
        self.assertEqual(mock_get_html.call_count, 1)

        # Cache Hit (negative)
        res2 = ConsultaCAService.get_or_query("88888")
        self.assertFalse(res2['found'])
        self.assertEqual(mock_get_html.call_count, 1)

        # Expire negative cache (1 hour)
        CertificadoAprovacao.objects.filter(numero="88888").update(
            ultima_sincronizacao=timezone.now() - datetime.timedelta(hours=2)
        )

        # Cache Miss again
        res3 = ConsultaCAService.get_or_query("88888")
        self.assertFalse(res3['found'])
        self.assertEqual(mock_get_html.call_count, 2)

    @patch('ppe.ca_services.ConsultaCAClient.get_html')
    def test_service_external_down_fallback(self, mock_get_html):
        # Simulates network down (returns None)
        mock_get_html.return_value = None

        # Miss with no record in DB
        res = ConsultaCAService.get_or_query("77777")
        self.assertFalse(res.get('success', True))
        self.assertTrue(res.get('indisponivel'))

        # Let's write an expired record to DB
        ca = CertificadoAprovacao.objects.create(
            numero="77777",
            numero_exibicao="CA 77777",
            fabricante="FABRICANTE ANTIGO",
            equipamento="EPI ANTIGO",
            situacao="VÁLIDO",
            data_validade=timezone.now().date(),
            status_verificacao='VERIFICADO_BASE_OFICIAL',
        )
        CertificadoAprovacao.objects.filter(id=ca.id).update(
            ultima_sincronizacao=timezone.now() - datetime.timedelta(days=2)
        )

        # Miss with expired record -> returns expired record with indisponivel flag
        res2 = ConsultaCAService.get_or_query("77777")
        self.assertTrue(res2['success'])
        self.assertTrue(res2['found'])
        self.assertTrue(res2['indisponivel'])
        self.assertEqual(res2['fabricante'], "FABRICANTE ANTIGO")

    def test_endpoint_authentication_and_authorization(self):
        url = reverse('ca_consultar_ajax') + "?q=11223"
        
        # 1. Unauthenticated -> 401
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        # 2. Authenticated -> 200 (since we mock, let's mock the service)
        self.client.login(username="tecnico", password="pwd")
        with patch('ppe.ca_services.ConsultaCAService.get_or_query') as mock_query:
            mock_query.return_value = {'success': True, 'found': True, 'numero': '11223'}
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])

        # 3. Invalid params -> 400
        url_invalid = reverse('ca_consultar_ajax') + "?q=11223a"
        response = self.client.get(url_invalid)
        self.assertEqual(response.status_code, 400)

    @patch('ppe.ca_services.ConsultaCAService.get_or_query')
    def test_form_normalization_and_save(self, mock_get_or_query):
        mock_get_or_query.return_value = {
            'success': True,
            'found': True,
            'fabricante': 'BUNZL AUTOMATIC',
            'situacao': 'VENCIDO',
            'data_validade': '18/12/2005'
        }

        form_data = {
            'nome': 'Novo Respirador',
            'tipo_produto': 'EPI',
            'categoria': 'PROTECAO_RESPIRATORIA',
            'ca_numero': 'CA-11223', # with prefix
            'unidade_medida': 'UND',
            'exige_ca': True,
            'controlado_individualmente': True,
            'ativo': True
        }

        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Normalized ca_numero
        self.assertEqual(form.cleaned_data['ca_numero'], '11223')
        
        # Auto-populated fabricante if left blank
        self.assertEqual(form.cleaned_data['fabricante'], 'BUNZL AUTOMATIC')

        # If user pre-filled fabricante, it shouldn't overwrite
        form_data_manual = form_data.copy()
        form_data_manual['fabricante'] = 'MANUAL FAB'
        form_manual = ProductForm(data=form_data_manual)
        self.assertTrue(form_manual.is_valid())
        self.assertEqual(form_manual.cleaned_data['fabricante'], 'MANUAL FAB')
