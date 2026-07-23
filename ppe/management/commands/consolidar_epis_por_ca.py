import sys
import json
import csv
from django.core.management.base import BaseCommand, CommandError
from ppe.consolidation_service import EPIConsolidationService

class Command(BaseCommand):
    help = "Audita e consolida com segurança EPIs cadastrados duplicados pelo número do CA."

    def add_arguments(self, parser):
        parser.add_argument(
            '--report',
            action='store_true',
            help="Gera relatório detalhado de duplicidades agrupadas por CA sem alterar o banco de dados."
        )
        parser.add_argument(
            '--ca',
            type=str,
            help="Número do Certificado de Aprovação (CA) a ser auditado ou consolidado."
        )
        parser.add_argument(
            '--canonical-id',
            type=int,
            help="ID do EPI principal/canônico que receberá os históricos e variantes dos duplicados."
        )
        parser.add_argument(
            '--size-map',
            type=str,
            help="Mapeamento de tamanhos no formato 'ID_DUPLICADO=TAMANHO,ID_DUPLICADO=TAMANHO' (ex: '19=P,20=M,21=G')."
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,
            help="Modo de simulação seguro. Não altera o banco de dados (padrão)."
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help="Executa a consolidação efetiva no banco de dados. Exige --ca e --canonical-id."
        )
        parser.add_argument(
            '--output',
            type=str,
            help="Caminho do arquivo local (JSON ou CSV) para exportar o relatório de auditoria."
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help="Executa a aplicação sem solicitar confirmação interativa no terminal."
        )

    def parse_size_map(self, size_map_str):
        if not size_map_str:
            return {}
        result = {}
        pairs = size_map_str.split(',')
        for pair in pairs:
            if '=' in pair:
                parts = pair.split('=')
                try:
                    k = int(parts[0].strip())
                    v = parts[1].strip()
                    result[k] = v
                except ValueError:
                    raise CommandError(f"Formato inválido em --size-map: '{pair}'. Use 'ID=TAMANHO'.")
        return result

    def handle(self, *args, **options):
        ca = options.get('ca')
        canonical_id = options.get('canonical_id')
        size_map_str = options.get('size_map')
        apply_flag = options.get('apply')
        dry_run = not apply_flag
        report_flag = options.get('report') or not apply_flag
        output_file = options.get('output')
        no_input = options.get('no_input')

        size_map = self.parse_size_map(size_map_str)

        # 1. Se for modo relatório ou se não passou --apply
        if not apply_flag:
            self.stdout.write(self.style.SUCCESS("\n=================================================="))
            self.stdout.write(self.style.SUCCESS("  AUDITORIA DE EPIS DUPLICADOS POR CA (RELATÓRIO)  "))
            self.stdout.write(self.style.SUCCESS("==================================================\n"))

            report_data = EPIConsolidationService.generate_report(ca_filter=ca)
            if not report_data:
                self.stdout.write(self.style.SUCCESS("Nenhum grupo de EPI duplicado por CA foi localizado."))
            else:
                self.stdout.write(f"Total de CAs duplicados encontrados: {len(report_data)}\n")
                for grp in report_data:
                    self.stdout.write(self.style.WARNING(f"--- CA: {grp['ca_original']} (Normalizado: {grp['ca_normalizado']}) ---"))
                    self.stdout.write(f"EPIs no grupo: {grp['total_epis']} | Saldo Total em Estoque: {grp['saldo_total_grupo']}")
                    
                    if grp['conflitos']:
                        self.stdout.write(self.style.ERROR(f"Conflitos Detectados: {'; '.join(grp['conflitos'])}"))
                    if grp['candidato_canonico_sugerido']:
                        cand = grp['candidato_canonico_sugerido']
                        self.stdout.write(self.style.SUCCESS(f"Sugestão de Canônico: ID {cand['id']} - '{cand['nome']}' ({cand['motivo']})"))

                    self.stdout.write("Detalhes dos EPIs duplicados:")
                    for epi in grp['epis']:
                        v_str = ", ".join([f"{v['tamanho']} (Saldo: {v['saldo_estoque']})" for v in epi['variantes']]) or "Sem variante"
                        self.stdout.write(
                            f"  - ID {epi['id']}: {epi['nome']} | Fabricante: {epi['fabricante'] or 'N/I'} | "
                            f"Ativo: {epi['ativo']} | Variantes: [{v_str}] | "
                            f"Vínculos (Entregas: {epi['entregas']}, Movs: {epi['movimentacoes']}, Lotes: {epi['lotes']}, Matrizes: {epi['matrizes']})"
                        )
                    self.stdout.write("")

            # Exportação de arquivo se solicitado
            if output_file and report_data:
                if output_file.endswith('.json'):
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(report_data, f, indent=2, ensure_ascii=False)
                    self.stdout.write(self.style.SUCCESS(f"Relatório exportado em JSON: {output_file}"))
                elif output_file.endswith('.csv'):
                    with open(output_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['CA', 'CA_Normalizado', 'EPI_ID', 'Nome', 'Fabricante', 'Categoria', 'Saldo_Estoque', 'Entregas', 'Movimentacoes', 'Lotes', 'Matrizes'])
                        for grp in report_data:
                            for epi in grp['epis']:
                                writer.writerow([grp['ca_original'], grp['ca_normalizado'], epi['id'], epi['nome'], epi['fabricante'], epi['categoria'], epi['saldo_estoque_total'], epi['entregas'], epi['movimentacoes'], epi['lotes'], epi['matrizes']])
                    self.stdout.write(self.style.SUCCESS(f"Relatório exportado em CSV: {output_file}"))

            self.stdout.write(self.style.NOTICE("\nPara executar a consolidação efetiva, utilize:"))
            self.stdout.write(self.style.NOTICE("python manage.py consolidar_epis_por_ca --ca <CA> --canonical-id <ID> --size-map \"<ID>=<TAMANHO>\" --apply\n"))
            return

        # 2. Se passou --apply: Executa a Consolidação Efetiva
        if apply_flag:
            if not ca or not canonical_id:
                raise CommandError("A opção --apply exige informar obrigatoriamente --ca <NUMERO_CA> e --canonical-id <ID>.")

            self.stdout.write(self.style.WARNING("\n=================================================="))
            self.stdout.write(self.style.WARNING("  CONSOLIDAÇÃO EFETIVA DE EPIS POR CA (APPLY)     "))
            self.stdout.write(self.style.WARNING("=================================================="))
            self.stdout.write(f"CA Alvo:             {ca}")
            self.stdout.write(f"EPI Canônico ID:     {canonical_id}")
            self.stdout.write(f"Mapeamento Tamanhos: {size_map or 'Automático/Extraído'}\n")

            if not no_input:
                confirm = input("Confirma a consolidação dos EPIs duplicados no EPI Canônico selecionado? (s/N): ")
                if confirm.lower() != 's':
                    self.stdout.write(self.style.NOTICE("Operação cancelada pelo usuário."))
                    return

            try:
                summary = EPIConsolidationService.consolidate_group(
                    ca_number=ca,
                    canonical_id=canonical_id,
                    size_map=size_map,
                    dry_run=False,
                    user=None
                )

                self.stdout.write(self.style.SUCCESS("\n=================================================="))
                self.stdout.write(self.style.SUCCESS("  CONSOLIDAÇÃO CONCLUÍDA COM SUCESSO!            "))
                self.stdout.write(self.style.SUCCESS("=================================================="))
                self.stdout.write(f"EPI Canônico:            ID {summary['canonical_id']} ({summary['canonical_nome']})")
                self.stdout.write(f"EPIs Incorporados:       IDs {summary['incorporated_ids']} (marcados como inativos)")
                self.stdout.write(f"Variantes Criadas:       {summary['variantes_criadas']}")
                self.stdout.write(f"Variantes Reutilizadas:   {summary['variantes_reutilizadas']}")
                self.stdout.write(f"Vínculos Atualizados:    {summary['relacionamentos_atualizados']}")
                self.stdout.write(f"Saldo Estoque Antes:     {summary['estoque_total_antes']}")
                self.stdout.write(f"Saldo Estoque Depois:    {summary['estoque_total_depois']}")
                self.stdout.write(self.style.SUCCESS("Invariantes de estoque e histórico validados com 100% de exatidão.\n"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nERRO CRÍTICO DURANTE A CONSOLIDAÇÃO: {str(e)}"))
                self.stdout.write(self.style.ERROR("Toda a transação foi revertida (rollback integral). Nenhum dado foi alterado.\n"))
                sys.exit(1)
