import os
import time
import socket
import hashlib
import zipfile
import urllib.request
import ftplib
import traceback
from datetime import datetime, date
from django.db import transaction, models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from ppe.models import CertificadoAprovacao, CAEPISyncLog

# Configurações com defaults seguros
CAEPI_SYNC_ENABLED = getattr(settings, 'CAEPI_SYNC_ENABLED', True)
CAEPI_SOURCE_URL = getattr(settings, 'CAEPI_SOURCE_URL', 'ftp://ftp.mtps.gov.br/portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/tgg_export_caepi.zip')
CAEPI_SYNC_TIMEOUT = getattr(settings, 'CAEPI_SYNC_TIMEOUT', 60)
CAEPI_SYNC_MAX_RETRIES = getattr(settings, 'CAEPI_SYNC_MAX_RETRIES', 3)
CAEPI_SYNC_BATCH_SIZE = getattr(settings, 'CAEPI_SYNC_BATCH_SIZE', 2000)
CAEPI_SYNC_MAX_INVALID_PERCENT = getattr(settings, 'CAEPI_SYNC_MAX_INVALID_PERCENT', 10.0)
CAEPI_SYNC_MIN_RECORD_RATIO = getattr(settings, 'CAEPI_SYNC_MIN_RECORD_RATIO', 0.8)
CAEPI_SYNC_TEMP_DIR = getattr(settings, 'CAEPI_SYNC_TEMP_DIR', None)

class CAEPIClient:
    """
    Cliente para download resiliente da base oficial do CAEPI.
    Suporta protocolos FTP e HTTP/HTTPS.
    """
    def __init__(self, url=None, timeout=None, max_retries=None, verbose=False):
        self.url = url or CAEPI_SOURCE_URL
        self.timeout = timeout or CAEPI_SYNC_TIMEOUT
        self.max_retries = max_retries or CAEPI_SYNC_MAX_RETRIES
        self.verbose = verbose
        socket.setdefaulttimeout(self.timeout)

    def download_to_temp(self, temp_dir=None):
        """
        Faz o download do arquivo para um diretório temporário e retorna o caminho local.
        """
        temp_dir = temp_dir or CAEPI_SYNC_TEMP_DIR or os.environ.get('TEMP') or '/tmp'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Gera nome temporário único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = '.zip' if self.url.lower().endswith('.zip') else '.txt'
        dest_path = os.path.join(temp_dir, f'caepi_{timestamp}{file_ext}')
        
        attempt = 0
        backoff = 2
        
        while attempt < self.max_retries:
            attempt += 1
            if self.verbose:
                print(f"Tentativa {attempt} de download de {self.url}...")
            try:
                if self.url.lower().startswith('ftp://'):
                    self._download_ftp(self.url, dest_path)
                else:
                    self._download_http(self.url, dest_path)
                
                # Valida que o arquivo não está vazio
                if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                    if self.verbose:
                        print(f"Download concluído com sucesso: {dest_path} ({os.path.getsize(dest_path)} bytes)")
                    return dest_path
            except Exception as e:
                if self.verbose:
                    print(f"Erro na tentativa {attempt}: {str(e)}")
                if attempt >= self.max_retries:
                    raise e
                time.sleep(backoff)
                backoff *= 2
        
        raise RuntimeError("Falha no download após todas as tentativas.")

    def _download_ftp(self, ftp_url, dest_path):
        # Exemplo: ftp://ftp.mtps.gov.br/portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/tgg_export_caepi.zip
        # Parse URL
        url_clean = ftp_url.replace('ftp://', '')
        parts = url_clean.split('/', 1)
        host = parts[0]
        path = parts[1] if len(parts) > 1 else ''
        
        filename = os.path.basename(path)
        dir_path = os.path.dirname(path)
        
        ftp = ftplib.FTP(host, timeout=self.timeout)
        ftp.login() # anonymous
        
        if dir_path:
            ftp.cwd(dir_path)
            
        with open(dest_path, 'wb') as f:
            ftp.retrbinary(f'RETR {filename}', f.write)
            
        ftp.quit()

    def _download_http(self, http_url, dest_path):
        req = urllib.request.Request(
            http_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            with open(dest_path, 'wb') as f:
                f.write(response.read())

class CAEPIParser:
    """
    Parser robusto para extração e leitura das linhas da base oficial CAEPI.
    Garante que o arquivo inteiro não seja carregado em memória.
    """
    CA_HEADERS = ['nr registro ca', 'ca', 'numero', 'numero ca', 'nº ca']
    VALIDADE_HEADERS = ['data de validade', 'validade', 'data_validade', 'data', 'vencimento']
    SITUACAO_HEADERS = ['situacao', 'status', 'situação']
    FABRICANTE_HEADERS = ['razao social', 'fabricante', 'empresa', 'razão social']
    CNPJ_HEADERS = ['cnpj']
    EQUIPAMENTO_HEADERS = ['equipamento', 'descricao', 'descrição', 'descricao equipamento']
    NATUREZA_HEADERS = ['natureza', 'natureza_protecao']
    OBSERVACOES_HEADERS = ['restricao laudo', 'observacao analise laudo', 'observacoes', 'restrição laudo']

    def __init__(self, file_path, separator='|', verbose=False):
        self.file_path = file_path
        self.separator = separator
        self.verbose = verbose
        self.is_zip = file_path.lower().endswith('.zip')

    def detect_encoding(self, f_obj):
        # Tenta UTF-8 e Latin-1
        sample = f_obj.read(4096)
        f_obj.seek(0)
        try:
            sample.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            return 'latin-1'

    def read_rows_generator(self):
        """
        Lê e yields linhas estruturadas como dicionários usando mapeamento flexível de cabeçalhos.
        """
        if self.is_zip:
            with zipfile.ZipFile(self.file_path) as z:
                namelist = z.namelist()
                if not namelist:
                    raise ValueError("Arquivo ZIP vazio.")
                txt_filename = [n for n in namelist if n.endswith('.txt')][0]
                with z.open(txt_filename) as f:
                    encoding = self.detect_encoding(f)
                    # Abre em modo texto com decodificador correto
                    wrapper = io_text_wrapper(f, encoding)
                    yield from self._parse_lines(wrapper)
        else:
            with open(self.file_path, 'rb') as f:
                encoding = self.detect_encoding(f)
            with open(self.file_path, 'r', encoding=encoding) as f:
                yield from self._parse_lines(f)

    def _parse_lines(self, file_obj):
        header_line = file_obj.readline()
        if not header_line:
            return
            
        headers = [h.strip().lower() for h in header_line.split(self.separator)]
        
        mapping = {}
        for idx, h in enumerate(headers):
            if h in self.CA_HEADERS:
                mapping['ca'] = idx
            elif h in self.VALIDADE_HEADERS:
                mapping['validade'] = idx
            elif h in self.SITUACAO_HEADERS:
                mapping['situacao'] = idx
            elif h in self.FABRICANTE_HEADERS:
                mapping['fabricante'] = idx
            elif h in self.CNPJ_HEADERS:
                mapping['cnpj'] = idx
            elif h in self.EQUIPAMENTO_HEADERS:
                mapping['equipamento'] = idx
            elif h in self.NATUREZA_HEADERS:
                mapping['natureza'] = idx
            elif h in self.OBSERVACOES_HEADERS:
                mapping['observacoes'] = idx
        
        # Se não achou mapeamento básico de CA e Validade, aborta
        if 'ca' not in mapping or 'validade' not in mapping:
            raise ValidationError("Cabeçalhos obrigatórios (CA e Validade) não encontrados no arquivo.")
            
        for line_num, line in enumerate(file_obj, start=2):
            line_str = line.strip()
            if not line_str:
                continue
                
            parts = line_str.split(self.separator)
            
            # Monta row dict
            row = {}
            for field, idx in mapping.items():
                if idx < len(parts):
                    row[field] = parts[idx].strip()
                else:
                    row[field] = ''
            
            row['_line_num'] = line_num
            yield row

def io_text_wrapper(binary_file, encoding):
    """
    Wrapper simples para ler arquivo binário do zip como texto linha por linha.
    """
    import io
    return io.TextIOWrapper(binary_file, encoding=encoding, line_buffering=True)

class CAEPISyncService:
    """
    Serviço centralizador para orquestrar a sincronização segura da base CAEPI.
    Garante idempotência, concorrência e integridade das transações.
    """
    @classmethod
    def get_active_lock(cls):
        """
        Retorna se existe alguma sincronização em andamento (menos de 2 horas de início).
        """
        two_hours_ago = timezone.now() - timezone.timedelta(hours=2)
        return CAEPISyncLog.objects.filter(
            status__in=['INICIADO', 'BAIXANDO', 'PROCESSANDO'],
            start_time__gte=two_hours_ago
        ).first()

class DryRunRollback(Exception):
    """
    Exceção usada para abortar a transação e forçar o rollback no modo dry-run.
    """
    pass

class CAEPISyncService:
    """
    Serviço centralizador para orquestrar a sincronização segura da base CAEPI.
    Garante idempotência, concorrência e integridade das transações.
    """
    @classmethod
    def get_active_lock(cls):
        """
        Retorna se existe alguma sincronização em andamento (menos de 2 horas de início).
        """
        two_hours_ago = timezone.now() - timezone.timedelta(hours=2)
        return CAEPISyncLog.objects.filter(
            status__in=['INICIADO', 'BAIXANDO', 'PROCESSANDO'],
            start_time__gte=two_hours_ago
        ).first()

    @classmethod
    def run_sync(cls, tipo_execucao='MANUAL', usuario=None, arquivo_local=None, forcar=False, verbose=False, dry_run=False):
        """
        Executa a rotina completa de sincronização de CAs.
        """
        start_time = timezone.now()
        
        # 1. Verifica Lock
        active_lock = cls.get_active_lock()
        if active_lock:
            msg = f"Sincronização já em andamento (iniciada em {active_lock.start_time.strftime('%d/%m/%Y %H:%M')})."
            if verbose:
                print(msg)
            raise RuntimeError(msg)

        # 2. Cria o log inicial (que atua como Lock)
        sync_log = CAEPISyncLog.objects.create(
            status='INICIADO',
            tipo_execucao=tipo_execucao,
            usuario=usuario,
            fonte=arquivo_local or CAEPI_SOURCE_URL,
            start_time=start_time
        )
        
        temp_file_path = None
        
        total_lido = 0
        total_valido = 0
        total_invalido = 0
        total_criados = 0
        total_atualizados = 0
        total_inalterados = 0
        total_desativados = 0
        
        try:
            # 3. Download do arquivo
            if not arquivo_local:
                sync_log.status = 'BAIXANDO'
                sync_log.save(update_fields=['status'])
                
                client = CAEPIClient(verbose=verbose)
                temp_file_path = client.download_to_temp()
                file_to_parse = temp_file_path
            else:
                file_to_parse = arquivo_local
                
            # 4. Calcula Hash do arquivo para detecção de alterações
            sha256 = hashlib.sha256()
            with open(file_to_parse, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            file_hash = sha256.hexdigest()
            file_size = os.path.getsize(file_to_parse)
            
            sync_log.arquivo_nome = os.path.basename(file_to_parse)
            sync_log.arquivo_tamanho = file_size
            sync_log.arquivo_hash = file_hash
            sync_log.save(update_fields=['arquivo_nome', 'arquivo_tamanho', 'arquivo_hash'])
            
            # Verifica se o arquivo já foi processado
            if not forcar and not dry_run:
                last_done = CAEPISyncLog.objects.filter(
                    status='CONCLUIDO',
                    arquivo_hash=file_hash
                ).exclude(id=sync_log.id).first()
                if last_done:
                    sync_log.status = 'IGNORADO'
                    sync_log.end_time = timezone.now()
                    sync_log.duracao_segundos = (sync_log.end_time - start_time).total_seconds()
                    sync_log.save(update_fields=['status', 'end_time', 'duracao_segundos'])
                    if verbose:
                        print("Arquivo já processado anteriormente. Abortando sem alterar a base local.")
                    return sync_log

            # 5. Processamento dos registros
            sync_log.status = 'PROCESSANDO'
            sync_log.save(update_fields=['status'])
            
            parser = CAEPIParser(file_to_parse, verbose=verbose)
            
            # Conta total de linhas para validação prévia
            try:
                for _ in parser.read_rows_generator():
                    total_lido += 1
            except Exception as e:
                raise ValidationError(f"Erro ao validar integridade estrutural do arquivo: {str(e)}")
            
            sync_log.total_lido = total_lido
            sync_log.save(update_fields=['total_lido'])
            
            if total_lido == 0:
                raise ValidationError("O arquivo recebido está vazio.")

            # Proteção contra redução anormal do banco
            current_count = CertificadoAprovacao.objects.count()
            if current_count > 0:
                ratio = total_lido / current_count
                if ratio < CAEPI_SYNC_MIN_RECORD_RATIO:
                    raise ValidationError(
                        f"Queda anormal de registros detectada. "
                        f"Novo arquivo contém {total_lido} registros, enquanto a base local possui {current_count} "
                        f"(Razão de {ratio:.2f}, menor que o limite seguro de {CAEPI_SYNC_MIN_RECORD_RATIO})."
                    )

            batch = []
            
            # Para otimizar bulk checks, usaremos transação única
            with transaction.atomic():
                for row in parser.read_rows_generator():
                    ca_str = row.get('ca', '').strip()
                    ca_norm = "".join([c for c in ca_str if c.isdigit()])
                    
                    # Validação mínima por linha
                    if not ca_norm:
                        total_invalido += 1
                        continue
                    
                    row['ca_norm'] = ca_norm
                    batch.append(row)
                    
                    if len(batch) >= CAEPI_SYNC_BATCH_SIZE:
                        # Processa lote
                        c_qty, u_qty, s_qty, v_qty, inv_qty = cls._process_batch(batch, sync_log.id)
                        total_criados += c_qty
                        total_atualizados += u_qty
                        total_inalterados += s_qty
                        total_valido += v_qty
                        total_invalido += inv_qty
                        batch = []
                
                # Processa lote restante
                if batch:
                    c_qty, u_qty, s_qty, v_qty, inv_qty = cls._process_batch(batch, sync_log.id)
                    total_criados += c_qty
                    total_atualizados += u_qty
                    total_inalterados += s_qty
                    total_valido += v_qty
                    total_invalido += inv_qty

                # Valida percentual de inválidos
                if total_lido > 0:
                    invalid_percent = (total_invalido / total_lido) * 100
                    if invalid_percent > CAEPI_SYNC_MAX_INVALID_PERCENT:
                        raise ValidationError(
                            f"Percentual de registros inválidos ({invalid_percent:.2f}%) ultrapassa o limite seguro de {CAEPI_SYNC_MAX_INVALID_PERCENT}%."
                        )

                # 6. Registros Removidos da Fonte (Ausentes na nova importação)
                total_desativados = CertificadoAprovacao.objects.filter(
                    presente_na_fonte=True
                ).exclude(versao_importacao=sync_log.id).count()
                
                # Só executa o update se não for dry_run
                if not dry_run:
                    CertificadoAprovacao.objects.filter(
                        presente_na_fonte=True
                    ).exclude(versao_importacao=sync_log.id).update(
                        presente_na_fonte=False,
                        status_verificacao='DESATUALIZADO'
                    )

                if dry_run:
                    raise DryRunRollback()

            # Tudo certo! Salva os totais e finaliza (Somente se não for dry_run)
            end_time = timezone.now()
            sync_log.status = 'CONCLUIDO'
            sync_log.end_time = end_time
            sync_log.duracao_segundos = (end_time - start_time).total_seconds()
            sync_log.total_valido = total_valido
            sync_log.total_invalido = total_invalido
            sync_log.total_criados = total_criados
            sync_log.total_atualizados = total_atualizados
            sync_log.total_inalterados = total_inalterados
            sync_log.total_desativados = total_desativados
            sync_log.save()
            
            if verbose:
                print(f"Sincronização concluída com sucesso em {sync_log.duracao_segundos:.2f}s!")
            return sync_log

        except DryRunRollback:
            # Em caso de dry-run, a transação foi revertida com sucesso.
            # Atualiza o log fora da transação.
            end_time = timezone.now()
            sync_log.status = 'CONCLUIDO'
            sync_log.end_time = end_time
            sync_log.duracao_segundos = (end_time - start_time).total_seconds()
            sync_log.total_valido = total_valido
            sync_log.total_invalido = total_invalido
            sync_log.total_criados = total_criados
            sync_log.total_atualizados = total_atualizados
            sync_log.total_inalterados = total_inalterados
            sync_log.total_desativados = total_desativados
            sync_log.erro_mensagem = "Modo DRY-RUN ativo. Nenhuma alteração foi gravada no banco."
            sync_log.save()
            
            if verbose:
                print(f"DRY-RUN concluído! Simulação executada com sucesso em {sync_log.duracao_segundos:.2f}s.")
            return sync_log

        except Exception as e:
            # Falha geral: grava no log e levanta exceção
            end_time = timezone.now()
            sync_log.status = 'FALHOU'
            sync_log.end_time = end_time
            sync_log.duracao_segundos = (end_time - start_time).total_seconds()
            sync_log.erro_mensagem = str(e)[:1000]
            sync_log.traceback = traceback.format_exc()
            sync_log.save()
            
            if verbose:
                print(f"Falha na sincronização: {str(e)}")
            raise e
        finally:
            # Limpa arquivo temporário
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass

    @classmethod
    def _process_batch(cls, batch, sync_version):
        """
        Processa um lote de dicionários de linha vindos do parser, executando persistência em lote.
        """
        ca_numbers = [r['ca_norm'] for r in batch]
        
        # Consulta CAs existentes neste lote
        existing_objs = CertificadoAprovacao.objects.filter(numero__in=ca_numbers)
        existing_map = {obj.numero: obj for obj in existing_objs}
        
        to_create = []
        to_update = []
        
        c_qty = 0
        u_qty = 0
        s_qty = 0
        v_qty = 0
        inv_qty = 0
        
        for r in batch:
            ca_norm = r['ca_norm']
            
            # Parse Validade
            validade_raw = r.get('validade', '')
            validade_date = None
            if validade_raw:
                if isinstance(validade_raw, (date, datetime)):
                    validade_date = validade_raw
                else:
                    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                        try:
                            validade_date = datetime.strptime(validade_raw, fmt).date()
                            break
                        except ValueError:
                            pass
            
            # Se não tem validade válida, marca como inválido
            if not validade_date:
                inv_qty += 1
                continue
                
            v_qty += 1
            
            # Trunca e normaliza campos para caber nos limites do banco
            fabricante = r.get('fabricante', '') or 'Não informado'
            fabricante = str(fabricante).strip()[:255]
            
            cnpj = r.get('cnpj', '')
            cnpj = "".join([c for c in cnpj if c.isdigit()])[:20]
            
            equipamento = r.get('equipamento', '') or 'EPI'
            equipamento = str(equipamento).strip()[:255]
            
            natureza = r.get('natureza', '')
            natureza_detalhe = r.get('observacoes', '')
            natureza_protecao = f"{natureza} - {natureza_detalhe}".strip(' -')
            
            situacao = r.get('situacao', 'VÁLIDO').strip().upper()
            if situacao not in ['VÁLIDO', 'VENCIDO', 'CANCELADO', 'SUSPENSO', 'INTERDITADO']:
                # Calcula baseando-se na data de validade
                situacao = 'VÁLIDO' if validade_date >= timezone.now().date() else 'VENCIDO'

            # Verifica se já existe
            if ca_norm in existing_map:
                obj = existing_map[ca_norm]
                
                # Verifica se houve alteração
                changed = (
                    obj.fabricante != fabricante or
                    obj.cnpj != cnpj or
                    obj.equipamento != equipamento or
                    obj.natureza_protecao != natureza_protecao or
                    obj.situacao != situacao or
                    obj.data_validade != validade_date or
                    not obj.presente_na_fonte
                )
                
                if changed:
                    obj.fabricante = fabricante
                    obj.cnpj = cnpj
                    obj.equipamento = equipamento
                    obj.natureza_protecao = natureza_protecao
                    obj.situacao = situacao
                    obj.data_validade = validade_date
                    obj.presente_na_fonte = True
                    obj.versao_importacao = sync_version
                    obj.status_verificacao = 'VERIFICADO_BASE_OFICIAL'
                    to_update.append(obj)
                    u_qty += 1
                else:
                    # Apenas atualiza a versão para não ser inativado
                    obj.versao_importacao = sync_version
                    obj.presente_na_fonte = True
                    to_update.append(obj)
                    s_qty += 1
            else:
                # Novo registro
                obj = CertificadoAprovacao(
                    numero=ca_norm,
                    numero_exibicao=f"CA {ca_norm}",
                    fabricante=fabricante,
                    cnpj=cnpj,
                    equipamento=equipamento,
                    natureza_protecao=natureza_protecao,
                    situacao=situacao,
                    data_validade=validade_date,
                    fonte='CAEPI_MTE',
                    status_verificacao='VERIFICADO_BASE_OFICIAL',
                    presente_na_fonte=True,
                    versao_importacao=sync_version
                )
                to_create.append(obj)
                c_qty += 1
                
        if to_create:
            CertificadoAprovacao.objects.bulk_create(to_create)
        if to_update:
            CertificadoAprovacao.objects.bulk_update(to_update, fields=[
                'fabricante', 'cnpj', 'equipamento', 'natureza_protecao', 
                'situacao', 'data_validade', 'presente_na_fonte', 
                'versao_importacao', 'status_verificacao'
            ])
            
        return c_qty, u_qty, s_qty, v_qty, inv_qty
