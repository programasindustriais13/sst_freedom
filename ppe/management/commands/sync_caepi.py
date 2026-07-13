import os
import sys
from django.core.management.base import BaseCommand, CommandError
from ppe.caepi_sync import CAEPISyncService

class Command(BaseCommand):
    help = "Sincroniza os Certificados de Aprovação (C.A.) a partir da base oficial do CAEPI/MTE."

    def add_arguments(self, parser):
        parser.add_argument(
            '--arquivo',
            type=str,
            help="Caminho do arquivo local (ZIP ou TXT) para importar diretamente sem acessar a internet."
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Apenas simula a importação, fazendo rollback de todas as alterações ao final."
        )
        parser.add_argument(
            '--forcar',
            action='store_true',
            help="Força a importação mesmo se o hash do arquivo coincidir com a última sincronização concluída."
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help="Exibe logs detalhados do processamento no terminal."
        )

    def handle(self, *args, **options):
        arquivo = options.get('arquivo')
        dry_run = options.get('dry_run')
        forcar = options.get('forcar')
        verbose = options.get('verbose')

        if verbose:
            self.stdout.write("Iniciando rotina de sincronização CAEPI...")
            if dry_run:
                self.stdout.write(self.style.WARNING("Modo DRY-RUN ativo. Nenhuma gravação definitiva será realizada."))

        try:
            # Invoca o serviço de sincronização
            log = CAEPISyncService.run_sync(
                tipo_execucao='MANUAL',
                usuario=None, # Pode ser associado via Admin se rodasse via web
                arquivo_local=arquivo,
                forcar=forcar,
                verbose=verbose,
                dry_run=dry_run
            )

            # Formata o relatório detalhado exigido
            self.stdout.write(self.style.SUCCESS("\n=========================================="))
            self.stdout.write(self.style.SUCCESS("  RELATÓRIO DE SINCRONIZAÇÃO CAEPI/MTE    "))
            self.stdout.write(self.style.SUCCESS("=========================================="))
            self.stdout.write(f"Situação Final:          {log.status}")
            self.stdout.write(f"Início:                  {log.start_time.strftime('%d/%m/%Y %H:%M:%S')}")
            self.stdout.write(f"Término:                 {log.end_time.strftime('%d/%m/%Y %H:%M:%S') if log.end_time else 'N/A'}")
            self.stdout.write(f"Duração Total:           {f'{log.duracao_segundos:.2f}s' if log.duracao_segundos else 'N/A'}")
            self.stdout.write(f"Fonte Utilizada:         {log.fonte}")
            self.stdout.write(f"Arquivo Identificado:    {log.arquivo_nome or 'N/A'}")
            self.stdout.write(f"Tamanho do Arquivo:      {f'{log.arquivo_tamanho} Bytes' if log.arquivo_tamanho else 'N/A'}")
            self.stdout.write(f"Hash SHA-256:            {log.arquivo_hash or 'N/A'}")
            self.stdout.write(self.style.SUCCESS("------------------------------------------"))
            self.stdout.write(f"Total Linhas Lidas:      {log.total_lido}")
            self.stdout.write(f"Registros Válidos:       {log.total_valido}")
            self.stdout.write(f"Registros Inválidos:     {log.total_invalido}")
            self.stdout.write(f"Registros Criados:       {log.total_criados}")
            self.stdout.write(f"Registros Atualizados:   {log.total_atualizados}")
            self.stdout.write(f"Registros Sem Alteração: {log.total_inalterados}")
            self.stdout.write(f"Registros Desativados:   {log.total_desativados}")
            if log.erro_mensagem:
                self.stdout.write(self.style.WARNING(f"Mensagem/Observação:     {log.erro_mensagem}"))
            self.stdout.write(self.style.SUCCESS("==========================================\n"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nErro crítico durante a sincronização: {str(e)}"))
            sys.exit(1)
