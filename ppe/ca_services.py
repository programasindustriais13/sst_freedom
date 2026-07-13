import re
import urllib.parse
import requests
import logging
import datetime
from django.utils import timezone
from django.conf import settings
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from ppe.models import CertificadoAprovacao

logger = logging.getLogger('ppe.ca_services')

class ConsultaCAClient:
    """
    Client HTTP for ConsultaCA.
    Provides secure, time-bound queries and SSRF mitigations.
    """
    def __init__(self):
        self.enabled = getattr(settings, 'CONSULTACA_ENABLED', True)
        self.base_url = getattr(settings, 'CONSULTACA_BASE_URL', 'https://consultaca.com').rstrip('/')
        self.connect_timeout = getattr(settings, 'CONSULTACA_CONNECT_TIMEOUT', 3)
        self.read_timeout = getattr(settings, 'CONSULTACA_READ_TIMEOUT', 5)
        self.max_response_bytes = getattr(settings, 'CONSULTACA_MAX_RESPONSE_BYTES', 1048576) # 1MB

    def get_html(self, ca_number):
        """
        Queries the portal and returns HTML content as a string.
        Returns None if disabled or if query fails due to connectivity/timeouts.
        Raises ValueError for invalid CA format or SSRF violations.
        Raises requests.HTTPError for unexpected non-200 responses.
        """
        if not self.enabled:
            logger.info("ConsultaCA is disabled in settings.")
            return None

        # Validate that ca_number is digits only
        if not ca_number or not str(ca_number).isdigit():
            raise ValueError("O número do CA deve conter apenas dígitos.")

        # Construct URL safely using the fixed base_url and verified parameter
        url = f"{self.base_url}/{ca_number}"
        
        # Parse URL to confirm it belongs to the fixed domain (SSRF check)
        parsed_url = urllib.parse.urlparse(url)
        parsed_base = urllib.parse.urlparse(self.base_url)
        if parsed_url.netloc != parsed_base.netloc or parsed_url.scheme != 'https':
            raise ValueError("Destino de URL inválido ou não autorizado.")

        headers = {
            'User-Agent': 'SSTFreedom/1.0 (Contact: admin@sstfreedom.com)'
        }

        try:
            # Connect/Read timeout, do not automatically follow redirects to prevent SSRF redirection bypass
            response = requests.get(
                url,
                headers=headers,
                timeout=(self.connect_timeout, self.read_timeout),
                allow_redirects=False,
                stream=True
            )

            # SSRF Protection: Block any redirects
            if response.status_code in (301, 302, 303, 307, 308):
                logger.warning(f"Redirecionamento bloqueado de {url} para {response.headers.get('Location')}")
                raise ValueError("Redirecionamento externo bloqueado por motivos de segurança.")

            if response.status_code == 404:
                logger.info(f"CA {ca_number} não encontrado (404) no ConsultaCA.")
                return "" # Return empty string for not found to distinguish from network failures

            response.raise_for_status()

            # Validate Content-Type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                logger.warning(f"Content-Type inesperado: {content_type}")
                raise ValueError(f"Content-Type inesperado: {content_type}")

            # Read chunks to limit maximum response size and prevent denial of service (zip bomb/huge response)
            content_chunks = []
            bytes_received = 0
            for chunk in response.iter_content(chunk_size=8192):
                bytes_received += len(chunk)
                if bytes_received > self.max_response_bytes:
                    logger.error(f"Resposta excedeu o tamanho máximo permitido de {self.max_response_bytes} bytes.")
                    raise ValueError("Resposta do servidor excedeu o limite máximo de tamanho.")
                content_chunks.append(chunk)

            # Convert to string (handling correct encoding)
            html_bytes = b"".join(content_chunks)
            encoding = response.encoding or 'utf-8'
            return html_bytes.decode(encoding, errors='replace')

        except requests.Timeout as e:
            logger.warning(f"Timeout ao consultar CA {ca_number}: {str(e)}")
            return None
        except requests.RequestException as e:
            logger.warning(f"Erro de rede ao consultar CA {ca_number}: {str(e)}")
            return None


class ConsultaCAParser:
    """
    Parser for extracting data from ConsultaCA HTML.
    Does not render HTML, only processes text.
    """
    @staticmethod
    def clean_text(text):
        if not text:
            return ''
        # Replace multiple spaces/newlines with a single space
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\xa0', ' ')
        return text.strip()

    @classmethod
    def parse(cls, html_content, ca_number):
        """
        Parses HTML content and returns a dictionary of extracted fields.
        If html_content is empty string, returns fields with 'found' as False.
        """
        if not html_content:
            return {
                'success': True,
                'found': False,
                'numero': ca_number,
            }

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Description (first <h1> whose text is not 'Avalie este EPI' and not empty)
        descricao_oficial = ''
        for h1 in soup.find_all('h1'):
            txt = cls.clean_text(h1.get_text())
            if txt and txt.lower() != 'avalie este epi':
                descricao_oficial = txt
                break

        # 2. Grupo de proteção (element with class 'grupo-epi-desc')
        grupo_tag = soup.find(class_='grupo-epi-desc')
        grupo_protecao = cls.clean_text(grupo_tag.get_text()) if grupo_tag else ''

        # Helper to search for values after <strong> labels
        def get_field_by_strong(label):
            for strong in soup.find_all('strong'):
                strong_text = cls.clean_text(strong.get_text()).replace('º', '°').replace('Nº', 'N°')
                if label.lower() in strong_text.lower():
                    # Collect text siblings until we hit another structured tag or <strong>
                    parts = []
                    for sib in strong.next_siblings:
                        if sib.name in ['strong', 'p', 'div', 'h3', 'table']:
                            break
                        if sib.name == 'br':
                            continue
                        if sib.name in ['span', 'a']:
                            parts.append(sib.get_text())
                        elif hasattr(sib, 'get_text'):
                            parts.append(sib.get_text())
                        else:
                            parts.append(str(sib))
                    val = "".join(parts)
                    return cls.clean_text(val)
            return ''

        situacao = get_field_by_strong('Situação')
        validade_raw = get_field_by_strong('Validade')
        processo = get_field_by_strong('N° Processo')
        natureza = get_field_by_strong('Natureza')
        fabricante = get_field_by_strong('Razão Social')
        cnpj_raw = get_field_by_strong('CNPJ')
        nome_fantasia = get_field_by_strong('Nome Fantasia')
        cidade_uf = get_field_by_strong('Cidade/UF')
        aprovado_para = get_field_by_strong('Aprovado Para')

        # If we couldn't find the CA number in the page text to verify it matches
        page_ca = get_field_by_strong('N° CA')
        page_ca_norm = re.sub(r'\D', '', page_ca) if page_ca else ''
        
        # Check if the page is a 'not found' warning or doesn't contain matching CA number
        body_text = soup.get_text()
        if "não localizado" in body_text.lower() or "não foi localizado" in body_text.lower() or "não encontrado" in body_text.lower() or not page_ca_norm:
            return {
                'success': True,
                'found': False,
                'numero': ca_number,
            }

        # Extract only date (dd/mm/aaaa) from validity
        validade = ''
        if validade_raw:
            match = re.search(r'(\d{2}/\d{2}/\d{4})', validade_raw)
            if match:
                validade = match.group(1)

        # Normalize CNPJ
        cnpj = re.sub(r'\D', '', cnpj_raw) if cnpj_raw else ''

        return {
            'success': True,
            'found': True,
            'numero': ca_number,
            'descricao_oficial': descricao_oficial,
            'grupo_protecao': grupo_protecao,
            'situacao': situacao.upper() if situacao else 'DESCONHECIDA',
            'validade': validade,
            'processo': processo,
            'natureza': natureza,
            'fabricante': fabricante,
            'cnpj': cnpj,
            'nome_fantasia': nome_fantasia,
            'cidade_uf': cidade_uf,
            'aprovado_para': aprovado_para,
        }


class ConsultaCAService:
    """
    Coordinates cache, database persistence and online queries.
    """
    @classmethod
    def get_or_query(cls, ca_number, force=False):
        """
        Gets CA details. Checks DB cache first, then queries online if needed.
        Returns a dict of normalized fields.
        """
        # Normalize to digits only
        ca_norm = re.sub(r'\D', '', str(ca_number))
        if not ca_norm:
            return {'success': False, 'error': 'Número de CA inválido.'}

        # Cache timeouts
        cache_timeout_seconds = getattr(settings, 'CONSULTACA_CACHE_TIMEOUT', 86400)
        not_found_timeout_seconds = getattr(settings, 'CONSULTACA_NOT_FOUND_CACHE_TIMEOUT', 3600)

        now = timezone.now()

        # Check DB
        ca_obj = CertificadoAprovacao.objects.filter(numero=ca_norm).first()
        if ca_obj and not force:
            age = (now - ca_obj.ultima_sincronizacao).total_seconds()
            
            # If not found CA cached
            if ca_obj.status_verificacao == 'NAO_ENCONTRADO':
                if age < not_found_timeout_seconds:
                    logger.info(f"Cache HIT (negativo) para CA {ca_norm}.")
                    return {
                        'success': True,
                        'found': False,
                        'numero': ca_norm,
                    }
            else:
                # Cache hit valid CA
                if age < cache_timeout_seconds:
                    logger.info(f"Cache HIT (positivo) para CA {ca_norm}.")
                    return cls._to_dict(ca_obj)

        # Cache miss or expired or forced: Query online
        logger.info(f"Cache MISS ou consulta forçada para CA {ca_norm}. Iniciando consulta online.")
        client = ConsultaCAClient()
        html = client.get_html(ca_norm)

        # If online query was down/timeout (returns None)
        if html is None:
            logger.warning(f"ConsultaCA indisponível para CA {ca_norm}.")
            # Return expired cache if we have one, otherwise return unavailable
            if ca_obj:
                res = cls._to_dict(ca_obj)
                res['indisponivel'] = True
                res['stale'] = True
                return res
            return {
                'success': False,
                'indisponivel': True,
                'error': 'Não foi possível conectar ao ConsultaCA. Tente novamente mais tarde.',
            }

        # Parse html
        parsed = ConsultaCAParser.parse(html, ca_norm)

        if not parsed.get('found', False):
            # Save "Not Found" entry in the database cache to prevent rapid retries
            CertificadoAprovacao.objects.update_or_create(
                numero=ca_norm,
                defaults={
                    'numero_exibicao': f"CA {ca_norm}",
                    'fabricante': 'Não encontrado',
                    'equipamento': 'EPI Não Encontrado',
                    'situacao': 'NÃO ENCONTRADO',
                    'data_validade': datetime.date(1900, 1, 1),
                    'status_verificacao': 'NAO_ENCONTRADO',
                    'presente_na_fonte': False,
                    'fonte': 'ConsultaCA',
                }
            )
            return {
                'success': True,
                'found': False,
                'numero': ca_norm,
            }

        # Convert date string (dd/mm/aaaa) to date object
        validade_date = datetime.date(1900, 1, 1)
        if parsed.get('validade'):
            try:
                validade_date = datetime.datetime.strptime(parsed['validade'], '%d/%m/%Y').date()
            except ValueError:
                pass

        # Split cidade_uf safely
        cidade_uf = parsed.get('cidade_uf', '')
        cidade = ''
        uf = ''
        if cidade_uf:
            if '/' in cidade_uf:
                parts = cidade_uf.split('/')
                cidade = parts[0].strip()
                uf = parts[1].strip()
            elif '-' in cidade_uf:
                parts = cidade_uf.split('-')
                cidade = parts[0].strip()
                uf = parts[1].strip()
            else:
                cidade = cidade_uf.strip()

        # Save to DB cache
        ca_obj, created = CertificadoAprovacao.objects.update_or_create(
            numero=ca_norm,
            defaults={
                'numero_exibicao': f"CA {ca_norm}",
                'fabricante': parsed.get('fabricante', '') or 'Não informado',
                'cnpj': parsed.get('cnpj', '') or '',
                'equipamento': parsed.get('descricao_oficial', '') or 'EPI',
                'natureza_protecao': f"{parsed.get('grupo_protecao', '')} - {parsed.get('aprovado_para', '')}".strip(' -'),
                'situacao': parsed.get('situacao', 'VÁLIDO'),
                'data_validade': validade_date,
                'status_verificacao': 'VERIFICADO_BASE_OFICIAL',
                'presente_na_fonte': True,
                'fonte': 'ConsultaCA',
                'grupo_protecao': parsed.get('grupo_protecao', '') or '',
                'processo': parsed.get('processo', '') or '',
                'natureza': parsed.get('natureza', '') or '',
                'nome_fantasia': parsed.get('nome_fantasia', '') or '',
                'cidade': cidade,
                'uf': uf,
                'aprovado_para': parsed.get('aprovado_para', '') or '',
            }
        )

        return cls._to_dict(ca_obj)

    @classmethod
    def _to_dict(cls, ca_obj):
        return {
            'success': True,
            'found': ca_obj.status_verificacao != 'NAO_ENCONTRADO',
            'numero': ca_obj.numero,
            'numero_exibicao': ca_obj.numero_exibicao,
            'fabricante': ca_obj.fabricante or '',
            'cnpj': ca_obj.cnpj or '',
            'equipamento': ca_obj.equipamento or '',
            'natureza_protecao': ca_obj.natureza_protecao or '',
            'situacao': ca_obj.situacao or '',
            'data_validade': ca_obj.data_validade.strftime('%d/%m/%Y') if ca_obj.data_validade and ca_obj.data_validade.year > 1900 else '',
            'presente_na_fonte': ca_obj.presente_na_fonte,
            'status_verificacao': ca_obj.get_status_verificacao_display(),
            'grupo_protecao': ca_obj.grupo_protecao or '',
            'processo': ca_obj.processo or '',
            'natureza': ca_obj.natureza or '',
            'nome_fantasia': ca_obj.nome_fantasia or '',
            'cidade': ca_obj.cidade or '',
            'uf': ca_obj.uf or '',
            'aprovado_para': ca_obj.aprovado_para or '',
            'fonte': ca_obj.fonte or '',
            'ultima_sincronizacao': ca_obj.ultima_sincronizacao.strftime('%d/%m/%Y %H:%M:%S') if ca_obj.ultima_sincronizacao else '',
        }
