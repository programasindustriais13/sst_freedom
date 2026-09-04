from django.core.management.base import BaseCommand
from organizations.models import Company, Unit, Sector, Function
from employees.models import Employee
from ppe.models import PPEMatrix, SectorPPEMatrix


class Command(BaseCommand):
    help = "Audita de forma segura e somente leitura o estado das Matrizes de EPI por Setor e do legado por Função."

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=int,
            help='ID opcional da Empresa para filtrar o escopo da auditoria'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
        self.stdout.write(self.style.MIGRATE_HEADING("AUDITORIA DAS MATRIZES DE EPI POR SETOR E LEGADO POR FUNCAO"))
        self.stdout.write(self.style.MIGRATE_HEADING("Operacao Somente Leitura (Idempotente) - SST Freedom"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))

        company_id = options.get('company')
        companies = Company.objects.filter(ativo=True)
        if company_id:
            companies = companies.filter(pk=company_id)

        total_setores = 0
        total_setores_ativos = 0
        total_setores_elaboracao = 0
        total_setores_sem_matriz = 0
        total_setores_fallback = 0

        for comp in companies:
            self.stdout.write(f"\n[EMPRESA] {comp.nome_fantasia} (CNPJ: {comp.cnpj})")
            units = comp.units.filter(ativo=True).order_by('codigo')
            
            for unit in units:
                self.stdout.write(f"  +-- [UNIDADE] {unit.codigo} - {unit.nome}")
                sectors = unit.sectors.filter(ativo=True).order_by('nome')
                
                for sector in sectors:
                    total_setores += 1
                    config = getattr(sector, 'ppe_matrix_config', None)
                    sector_status = config.status if config else 'SEM_MATRIZ'
                    
                    if sector_status == 'ATIVA':
                        total_setores_ativos += 1
                        status_styled = self.style.SUCCESS(f"ATIVA (ativada em {config.ativado_em.strftime('%d/%m/%Y %H:%M') if config.ativado_em else 'N/A'})")
                    elif sector_status == 'EM_ELABORACAO':
                        total_setores_elaboracao += 1
                        status_styled = self.style.WARNING("EM ELABORACAO")
                    else:
                        total_setores_sem_matriz += 1
                        status_styled = self.style.NOTICE("SEM CONFIGURACAO")

                    emp_count = Employee.objects.filter(setor=sector, situacao='ATIVO').count()
                    sector_items = PPEMatrix.objects.filter(setor=sector, ativo=True)
                    sector_items_count = sector_items.count()

                    self.stdout.write(f"      +-- [SETOR] {sector.nome}")
                    self.stdout.write(f"      |   +-- Status Matriz Setor: {status_styled}")
                    self.stdout.write(f"      |   +-- Colaboradores Ativos: {emp_count}")
                    self.stdout.write(f"      |   +-- EPIs Ativos no Setor: {sector_items_count}")

                    # Lista itens da matriz do setor
                    if sector_items_count > 0:
                        for it in sector_items:
                            tipo_str = "Principal" if it.principal else "Secundario"
                            self.stdout.write(f"      |   |   * {it.product.nome} ({tipo_str}, {it.vida_util_dias} dias)")

                    # Analisa funções dos colaboradores deste setor
                    funcoes_setor = Function.objects.filter(employees__setor=sector, employees__situacao='ATIVO').distinct()
                    if funcoes_setor.exists():
                        self.stdout.write(f"      |   +-- Funcoes Presentes no Setor: {funcoes_setor.count()}")
                        
                        # Verifica se há dependência de fallback
                        if sector_status != 'ATIVA':
                            has_legacy_matrix = False
                            for func in funcoes_setor:
                                legacy_count = PPEMatrix.objects.filter(funcao=func, ativo=True).count()
                                if legacy_count > 0:
                                    has_legacy_matrix = True
                                    self.stdout.write(f"      |   |   * Funcao: {func.nome} -> Matriz Legada: {legacy_count} EPI(s)")
                            if has_legacy_matrix:
                                total_setores_fallback += 1
                                self.stdout.write(self.style.WARNING("      |   |   [AVISO] SETOR DEPENDENTE DE FALLBACK TRANSITORIO DE FUNCAO"))
                    else:
                        self.stdout.write("      |   +-- Nenhuma funcao associada a colaboradores ativos.")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.MIGRATE_HEADING("RESUMO CONSOLIDADO DA AUDITORIA"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total de Setores Analisados: {total_setores}")
        self.stdout.write(self.style.SUCCESS(f"  * Matrizes Ativas: {total_setores_ativos}"))
        self.stdout.write(self.style.WARNING(f"  * Matrizes em Elaboracao: {total_setores_elaboracao}"))
        self.stdout.write(self.style.NOTICE(f"  * Setores sem Matriz: {total_setores_sem_matriz}"))
        self.stdout.write(self.style.WARNING(f"  * Setores com Fallback Transitorio Ativo: {total_setores_fallback}"))
        self.stdout.write("=" * 80 + "\n")
