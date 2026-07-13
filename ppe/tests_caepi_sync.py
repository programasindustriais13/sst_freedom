import os
import tempfile
import hashlib
import zipfile
import io
import socket
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.auth import get_user_model
from ppe.models import CertificadoAprovacao, CAEPISyncLog
from ppe.caepi_sync import CAEPISyncService, CAEPIClient, CAEPIParser, DryRunRollback

class CAEPISyncTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_tecnico = MagicMock()
        
        # Cria arquivos temporários mock de teste
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Conteúdo padrão estruturado do arquivo tgg_export_caepi.txt
        self.default_csv_content = (
            "NR Registro CA|DATA DE VALIDADE|SITUACAO|NR DO PROCESSO|CNPJ|RAZAO SOCIAL|NATUREZA|EQUIPAMENTO|DESCRICAO EQUIPAMENTO|MARCA CA|REFERENCIA|COR|APROVADO PARA LAUDO|RESTRICAO LAUDO|OBSERVACAO ANALISE LAUDO|CNPJ LABORATORIO|RAZAO SOCIAL LABORATORIO|NR LAUDO|NORMA\n"
            "12345|10/10/2030|VÁLIDO|46000.000001/2026-99|12345678000199|FABRICANTE A LTDA|Nacional|BOTA DE SEGURANÇA|Bota confeccionada em couro, biqueira de aço|MARCA A|REF-BOOT-01|Preta|Aprovado||Nenhuma observação|99999999000188|LAB TESTE S/A|L-01|ABNT NBR ISO 20345\n"
            "67890|01/01/2020|VENCIDO|46000.000002/2026-00|87654321000100|FABRICANTE B S/A|Importado|OCULOS DE PROTEÇÃO|Óculos com lentes cinza e hastes reguláveis|MARCA B|REF-GLASS-02|Cinza|Aprovado|Sem restrições||99999999000188|LAB TESTE S/A|L-02|ABNT NBR 16076\n"
        )
        
        # Cria arquivo local plano (.txt)
        self.txt_path = os.path.join(self.temp_dir.name, "caepi_test.txt")
        with open(self.txt_path, "w", encoding="utf-8") as f:
            f.write(self.default_csv_content)
            
        # Cria arquivo compactado (.zip)
        self.zip_path = os.path.join(self.temp_dir.name, "caepi_test.zip")
        with zipfile.ZipFile(self.zip_path, 'w') as z:
            z.writestr("tgg_export_caepi.txt", self.default_csv_content.encode('latin-1'))

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('ppe.caepi_sync.ftplib.FTP')
    def test_download_ftp_success(self, mock_ftp):
        # Configura mock do FTP
        ftp_instance = MagicMock()
        mock_ftp.return_value = ftp_instance
        
        # Quando retrbinary for chamado, grava os bytes mock no buffer destino
        def mock_retr(cmd, callback):
            callback(b"MOCK_ZIP_BYTES_DATA")
            return "226 Transfer complete"
            
        ftp_instance.retrbinary.side_effect = mock_retr
        
        client = CAEPIClient(url="ftp://ftp.mtps.gov.br/portal/caepi.zip", timeout=5, max_retries=1)
        path = client.download_to_temp(temp_dir=self.temp_dir.name)
        
        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.path.getsize(path), len("MOCK_ZIP_BYTES_DATA"))

    @patch('urllib.request.urlopen')
    def test_download_http_success(self, mock_urlopen):
        # Configura mock do HTTP
        response = MagicMock()
        response.read.return_value = b"MOCK_HTTP_BYTES_DATA"
        mock_urlopen.return_value.__enter__.return_value = response
        
        client = CAEPIClient(url="http://example.com/caepi.zip", timeout=5, max_retries=1)
        path = client.download_to_temp(temp_dir=self.temp_dir.name)
        
        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.path.getsize(path), len("MOCK_HTTP_BYTES_DATA"))

    @patch('urllib.request.urlopen')
    def test_download_timeout_and_retry(self, mock_urlopen):
        # Simula erro nas duas primeiras tentativas e sucesso na terceira
        success_response = MagicMock()
        success_response.read.return_value = b"RETRY_SUCCESS"
        success_response.__enter__.return_value = success_response
        
        mock_urlopen.side_effect = [
            socket.timeout("Timeout na conexão"),
            Exception("Erro de rede temporário"),
            success_response
        ]
        
        # Reduz o tempo de sleep do retry temporariamente para rodar rápido nos testes
        with patch('time.sleep', return_value=None):
            client = CAEPIClient(url="http://example.com/caepi.zip", timeout=5, max_retries=3)
            path = client.download_to_temp(temp_dir=self.temp_dir.name)
            
        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.path.getsize(path), len("RETRY_SUCCESS"))

    def test_parser_detects_encoding_utf8(self):
        content = "NR Registro CA|DATA DE VALIDADE\n12345|10/10/2030"
        bio = io.BytesIO(content.encode('utf-8'))
        parser = CAEPIParser(self.txt_path)
        encoding = parser.detect_encoding(bio)
        self.assertEqual(encoding, 'utf-8')

    def test_parser_detects_encoding_latin1(self):
        # Usamos caractere com acento que muda de representação binária
        content = "NR Registro CA|DATA DE VALIDADE|SITUAÇÃO\n12345|10/10/2030|VÁLIDO"
        bio = io.BytesIO(content.encode('latin-1'))
        parser = CAEPIParser(self.txt_path)
        encoding = parser.detect_encoding(bio)
        self.assertEqual(encoding, 'latin-1')

    def test_sync_first_load_success(self):
        # Executa carga inicial com o arquivo local zip
        log = CAEPISyncService.run_sync(
            tipo_execucao='MANUAL',
            arquivo_local=self.zip_path,
            verbose=False
        )
        
        self.assertEqual(log.status, 'CONCLUIDO')
        self.assertEqual(log.total_lido, 2)
        self.assertEqual(log.total_valido, 2)
        self.assertEqual(log.total_criados, 2)
        
        # Verifica persistência no banco
        ca_1 = CertificadoAprovacao.objects.get(numero="12345")
        self.assertEqual(ca_1.fabricante, "FABRICANTE A LTDA")
        self.assertEqual(ca_1.cnpj, "12345678000199")
        self.assertEqual(ca_1.situacao, "VÁLIDO")
        self.assertEqual(ca_1.presente_na_fonte, True)
        self.assertEqual(ca_1.versao_importacao, log.id)

    def test_sync_update_existing_and_idempotency(self):
        # Executa a primeira vez
        log1 = CAEPISyncService.run_sync(arquivo_local=self.zip_path)
        self.assertEqual(CertificadoAprovacao.objects.count(), 2)
        
        # Modifica o arquivo de teste para alterar um registro
        updated_csv = (
            "NR Registro CA|DATA DE VALIDADE|SITUACAO|NR DO PROCESSO|CNPJ|RAZAO SOCIAL|NATUREZA|EQUIPAMENTO|DESCRICAO EQUIPAMENTO|MARCA CA|REFERENCIA|COR|APROVADO PARA LAUDO|RESTRICAO LAUDO|OBSERVACAO ANALISE LAUDO|CNPJ LABORATORIO|RAZAO SOCIAL LABORATORIO|NR LAUDO|NORMA\n"
            "12345|10/10/2030|CANCELADO|46000.000001/2026-99|12345678000199|NOVO NOME FABRICANTE|Nacional|BOTA DE SEGURANÇA|Bota confeccionada em couro, biqueira de aço|MARCA A|REF-BOOT-01|Preta|Aprovado||Nenhuma observação|99999999000188|LAB TESTE S/A|L-01|ABNT NBR ISO 20345\n"
            "67890|01/01/2020|VENCIDO|46000.000002/2026-00|87654321000100|FABRICANTE B S/A|Importado|OCULOS DE PROTEÇÃO|Óculos com lentes cinza e hastes reguláveis|MARCA B|REF-GLASS-02|Cinza|Aprovado|Sem restrições||99999999000188|LAB TESTE S/A|L-02|ABNT NBR 16076\n"
        )
        zip_path_upd = os.path.join(self.temp_dir.name, "caepi_test_upd.zip")
        with zipfile.ZipFile(zip_path_upd, 'w') as z:
            z.writestr("tgg_export_caepi.txt", updated_csv.encode('latin-1'))
            
        # Executa a segunda vez forçando processamento do hash
        log2 = CAEPISyncService.run_sync(arquivo_local=zip_path_upd, forcar=True)
        
        self.assertEqual(log2.status, 'CONCLUIDO')
        self.assertEqual(log2.total_criados, 0)
        self.assertEqual(log2.total_atualizados, 1) # apenas o CA 12345 mudou
        self.assertEqual(log2.total_inalterados, 1) # o CA 67890 manteve os campos
        
        ca_1 = CertificadoAprovacao.objects.get(numero="12345")
        self.assertEqual(ca_1.fabricante, "NOVO NOME FABRICANTE")
        self.assertEqual(ca_1.situacao, "CANCELADO")
        self.assertEqual(ca_1.versao_importacao, log2.id)

    def test_sync_records_removed_from_source(self):
        # Executa a primeira vez para popular
        log1 = CAEPISyncService.run_sync(arquivo_local=self.zip_path)
        
        # Cria arquivo contendo apenas o CA 12345 (o CA 67890 sumiu da fonte)
        removed_csv = (
            "NR Registro CA|DATA DE VALIDADE|SITUACAO|NR DO PROCESSO|CNPJ|RAZAO SOCIAL|NATUREZA|EQUIPAMENTO|DESCRICAO EQUIPAMENTO\n"
            "12345|10/10/2030|VÁLIDO|46000.000001/2026-99|12345678000199|FABRICANTE A LTDA|Nacional|BOTA DE SEGURANÇA|Bota couro\n"
        )
        zip_path_rem = os.path.join(self.temp_dir.name, "caepi_test_rem.zip")
        with zipfile.ZipFile(zip_path_rem, 'w') as z:
            z.writestr("tgg_export_caepi.txt", removed_csv.encode('latin-1'))
            
        # Executa a segunda vez forçando (ignora proteção de ratio reduzindo a ratio mínima para caber no teste)
        with patch('ppe.caepi_sync.CAEPI_SYNC_MIN_RECORD_RATIO', 0.1):
            log2 = CAEPISyncService.run_sync(arquivo_local=zip_path_rem, forcar=True)
            
        self.assertEqual(log2.status, 'CONCLUIDO')
        self.assertEqual(log2.total_desativados, 1)
        
        # CA 67890 deve estar marcado como presente_na_fonte=False e status desatualizado
        ca_2 = CertificadoAprovacao.objects.get(numero="67890")
        self.assertFalse(ca_2.presente_na_fonte)
        self.assertEqual(ca_2.status_verificacao, 'DESATUALIZADO')
        
        # CA 12345 deve permanecer ativo
        ca_1 = CertificadoAprovacao.objects.get(numero="12345")
        self.assertTrue(ca_1.presente_na_fonte)

    def test_sync_dry_run_does_not_modify_database(self):
        # Executa com dry run
        log = CAEPISyncService.run_sync(
            tipo_execucao='MANUAL',
            arquivo_local=self.zip_path,
            dry_run=True
        )
        
        self.assertEqual(log.status, 'CONCLUIDO')
        self.assertEqual(log.total_criados, 2)
        self.assertEqual(log.total_valido, 2)
        
        # Nenhuma linha deve ser de fato criada na tabela CertificadoAprovacao
        self.assertEqual(CertificadoAprovacao.objects.count(), 0)

    def test_sync_rollback_on_failure(self):
        # Executa uma carga inicial com sucesso
        CAEPISyncService.run_sync(arquivo_local=self.zip_path)
        self.assertEqual(CertificadoAprovacao.objects.count(), 2)
        
        # Cria arquivo corrompido (sem coluna de validade obrigatória na linha 2)
        corrupted_csv = (
            "NR Registro CA|DATA DE VALIDADE|SITUACAO|NR DO PROCESSO|CNPJ|RAZAO SOCIAL|NATUREZA|EQUIPAMENTO\n"
            "12345|10/10/2030|VÁLIDO|46000.000001/2026-99|12345678000199|FABRICANTE A LTDA|Nacional|BOTA\n"
            "99999||VÁLIDO|46000.000002/2026-00|87654321000100|FABRICANTE C S/A|Importado|ÓCULOS\n"
        )
        zip_path_corr = os.path.join(self.temp_dir.name, "caepi_test_corr.zip")
        with zipfile.ZipFile(zip_path_corr, 'w') as z:
            z.writestr("tgg_export_caepi.txt", corrupted_csv.encode('latin-1'))
            
        # Simula erro de validação de datas
        with self.assertRaises(Exception):
            # O processamento deve abortar pois a ratio minima é 80%, mas a linha 99999 está inválida.
            # Se forçarmos para ignorar ratio mas exceder limite de invalidos:
            with patch('ppe.caepi_sync.CAEPI_SYNC_MAX_INVALID_PERCENT', 1.0):
                CAEPISyncService.run_sync(arquivo_local=zip_path_corr, forcar=True)
                
        # Garante que a base local permaneceu exatamente intacta (com 2 registros)
        self.assertEqual(CertificadoAprovacao.objects.count(), 2)
        self.assertEqual(CertificadoAprovacao.objects.filter(numero="99999").exists(), False)

    def test_sync_protection_against_record_ratio_reduction(self):
        # Executa carga inicial com 2 registros
        CAEPISyncService.run_sync(arquivo_local=self.zip_path)
        
        # Cria arquivo com apenas 1 registro (redução de 50%, menor que ratio padrão de 80%)
        small_csv = (
            "NR Registro CA|DATA DE VALIDADE|SITUACAO|NR DO PROCESSO|CNPJ|RAZAO SOCIAL|NATUREZA|EQUIPAMENTO|DESCRICAO EQUIPAMENTO\n"
            "12345|10/10/2030|VÁLIDO|46000.000001/2026-99|12345678000199|FABRICANTE A LTDA|Nacional|BOTA DE SEGURANÇA|Bota couro\n"
        )
        zip_path_small = os.path.join(self.temp_dir.name, "caepi_test_small.zip")
        with zipfile.ZipFile(zip_path_small, 'w') as z:
            z.writestr("tgg_export_caepi.txt", small_csv.encode('latin-1'))
            
        with self.assertRaises(ValidationError) as context:
            CAEPISyncService.run_sync(arquivo_local=zip_path_small, forcar=True)
            
        self.assertIn("Queda anormal de registros detectada", str(context.exception))
        self.assertEqual(CertificadoAprovacao.objects.count(), 2) # manteve os 2

    def test_sync_active_lock_prevents_concurrency(self):
        # Dispara sincronização que fica ativa
        CAEPISyncLog.objects.create(
            status='PROCESSANDO',
            tipo_execucao='MANUAL',
            fonte='ftp://test',
            start_time=timezone.now()
        )
        
        # Tenta rodar de novo concorrentemente
        with self.assertRaises(RuntimeError) as context:
            CAEPISyncService.run_sync(arquivo_local=self.zip_path)
            
        self.assertIn("Sincronização já em andamento", str(context.exception))

    @patch('ppe.ca_services.ConsultaCAClient.get_html', return_value="")
    def test_ca_consultar_ajax_view(self, mock_get_html):
        # Cria CA na base local
        CertificadoAprovacao.objects.create(
            numero="12345",
            numero_exibicao="CA 12345",
            fabricante="FABRICANTE TESTE",
            cnpj="11222333000144",
            equipamento="LUVA DE RASPA",
            situacao="VÁLIDO",
            data_validade=timezone.now().date() + timezone.timedelta(days=10)
        )
        
        # Faz login no client de teste
        User = get_user_model()
        user = User.objects.create_user(username="test_tecnico", password="pwd", profile_type="TECNICO_SST")
        self.client.login(username="test_tecnico", password="pwd")
        
        # Caso 1: CA encontrado
        response = self.client.get(reverse('ca_consultar_ajax') + '?q=CA-12345')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['found'])
        self.assertEqual(data['numero'], '12345')
        self.assertEqual(data['fabricante'], 'FABRICANTE TESTE')
        
        # Caso 2: CA não encontrado
        response = self.client.get(reverse('ca_consultar_ajax') + '?q=99999')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['found'])
        
        # Caso 3: parâmetro vazio ou inválido
        response = self.client.get(reverse('ca_consultar_ajax') + '?q=abc')
        self.assertEqual(response.status_code, 400)
