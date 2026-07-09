import os
import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from ppe.models import CertificadoAprovacao

class Command(BaseCommand):
    help = "Sincroniza os Certificados de Aprovação (C.A.) a partir de um arquivo CSV ou Excel (MTE/CAEPI)"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help="Caminho do arquivo CSV ou Excel (.xlsx)")
        parser.add_argument('--dry-run', action='store_true', help="Apenas simula a importação sem gravar no banco de dados")

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']

        if not os.path.exists(file_path):
            raise CommandError(f"Arquivo não encontrado: {file_path}")

        self.stdout.write(f"Iniciando leitura do arquivo: {file_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo DRY-RUN ativo. Nenhuma alteração será gravada."))

        rows = []
        ext = os.path.splitext(file_path)[1].lower()

        # 1. Leitura do arquivo
        try:
            if ext in ['.xlsx', '.xls']:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                sheet = wb.active
                # Lê linhas do sheet
                header = None
                for r in sheet.iter_rows(values_only=True):
                    if not r or all(v is None for v in r):
                        continue
                    if not header:
                        header = [str(x).strip().lower() for x in r if x is not None]
                        continue
                    # Monta dict
                    row_dict = {}
                    for idx, val in enumerate(r):
                        if idx < len(header):
                            row_dict[header[idx]] = val
                    rows.append(row_dict)
            else:
                # Trata como CSV
                with open(file_path, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    # Tenta com vírgula se ponto e vírgula não separar
                    sample = f.read(1024)
                    f.seek(0)
                    if sample and ',' in sample and ';' not in sample:
                        reader = csv.DictReader(f, delimiter=',')
                    for row in reader:
                        # Normaliza chaves
                        normalized_row = {k.strip().lower() if k else '': v for k, v in row.items()}
                        rows.append(normalized_row)
        except Exception as e:
            raise CommandError(f"Erro ao ler arquivo: {str(e)}")

        self.stdout.write(f"Total de linhas lidas do arquivo: {len(rows)}")

        # 2. Mapeamento de colunas flexível
        # Espera chaves comuns como 'ca', 'numero', 'numero ca', 'numero_ca', 'validade', 'data_validade', 'fabricante', 'situacao', 'equipamento'
        created_count = 0
        updated_count = 0
        invalid_count = 0

        with transaction.atomic():
            for idx, r in enumerate(rows, start=1):
                # Obtém o número do CA
                ca_raw = r.get('ca') or r.get('numero') or r.get('numero ca') or r.get('numero_ca') or r.get('nº ca') or r.get('nº do ca')
                if not ca_raw:
                    # Tenta pegar o primeiro valor da linha se chaves não baterem
                    ca_raw = list(r.values())[0] if r.values() else None

                if not ca_raw:
                    invalid_count += 1
                    continue

                ca_str = str(ca_raw).strip()
                ca_norm = "".join([c for c in ca_str if c.isdigit()])

                if not ca_norm:
                    invalid_count += 1
                    continue

                # Obtém fabricante
                fabricante = r.get('fabricante') or r.get('razao_social') or r.get('empresa') or ''
                fabricante = str(fabricante).strip() if fabricante else ''

                # Obtém validade
                validade_raw = r.get('validade') or r.get('data_validade') or r.get('data') or r.get('vencimento')
                validade_date = None
                if validade_raw:
                    if isinstance(validade_raw, datetime):
                        validade_date = validade_raw.date()
                    elif isinstance(validade_raw, str):
                        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                            try:
                                validade_date = datetime.strptime(validade_raw.strip(), fmt).date()
                                break
                            except ValueError:
                                pass

                if not validade_date:
                    # fallback: data atual mais 1 ano se em branco, ou None
                    validade_date = timezone.now().date()

                # Obtém equipamento/natureza da proteção
                natureza = r.get('natureza_protecao') or r.get('natureza') or r.get('equipamento') or r.get('descricao') or ''
                natureza = str(natureza).strip() if natureza else ''

                # Obtém situação
                situacao_raw = r.get('situacao') or r.get('status') or 'VÁLIDO'
                situacao = str(situacao_raw).strip().upper()
                if situacao not in ['VÁLIDO', 'VENCIDO', 'CANCELADO']:
                    # Calcula pela validade
                    situacao = 'VÁLIDO' if validade_date >= timezone.now().date() else 'VENCIDO'

                # Grava no banco se não for dry-run
                if not dry_run:
                    ca_obj, created = CertificadoAprovacao.objects.update_or_create(
                        numero=ca_norm,
                        defaults={
                            'numero_exibicao': ca_str,
                            'fabricante': fabricante,
                            'natureza_protecao': natureza,
                            'data_validade': validade_date,
                            'situacao': situacao,
                            'status_verificacao': 'VERIFICADO_BASE_OFICIAL',
                            'data_verificacao': timezone.now()
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                else:
                    # Simula
                    exists = CertificadoAprovacao.objects.filter(numero=ca_norm).exists()
                    if not exists:
                        created_count += 1
                    else:
                        updated_count += 1

            if dry_run:
                # Se for dry run, a transação faz rollback ao final para garantir segurança imutável
                # Django BaseCommand não faz rollback automático no dry_run, mas podemos levantar uma exceção ou simplesmente deixar passar já que não alteramos o banco.
                # Como apenas lemos e simulamos, não precisamos forçar exceção, pois não salvamos nada se dry_run for True.
                pass

        self.stdout.write(self.style.SUCCESS(f"Sincronização concluída!"))
        self.stdout.write(f"Criados: {created_count}")
        self.stdout.write(f"Atualizados: {updated_count}")
        self.stdout.write(f"Linhas Inválidas/Ignoradas: {invalid_count}")
