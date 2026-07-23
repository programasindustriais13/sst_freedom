# SPEC_2026_014 — Auditoria e Consolidação Segura dos EPIs Duplicados pelo Número do CA

> Esta SPEC segue estritamente o modelo de `contexto/SPEC_TEMPLATE.md` e as regras de `contexto/constitution.md`.  
> Nenhuma implementação pode ser iniciada antes da aprovação do QA (`APROVADA_PARA_IMPLEMENTAÇÃO`).

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-014` |
| Título | Auditoria e Consolidação Segura dos EPIs Duplicados pelo Número do CA |
| Tipo | `FEATURE / REFACTOR / MIGRATION / SECURITY` |
| Módulo principal | `ppe` / `inventory` |
| Fase/Roadmap | `Fase 1 — Gestão de EPIs e Estoque` |
| Autor da SPEC | `Arquiteto` |
| Data de criação | `23/07/2026` |
| Última atualização | `23/07/2026 15:00` |
| Versão | `1.0.0` |
| Status | `APROVADA_PARA_IMPLEMENTAÇÃO` |
| Prioridade | `CRÍTICA` |
| Risco | `ALTO` |
| Demanda de origem | `Ferramenta segura (Management Command Django) para identificar, auditar e consolidar EPIs cadastrados separadamente por tamanho com o mesmo número de CA, transferindo todos os relacionamentos e históricos para um EPI canônico sem alteração de totais ou perda de dados.` |
| SPEC substituída | `Não` |
| SPECs relacionadas | `contexto/SPEC_2026_008_melhoria_cadastro_epi.md`, `contexto/SPEC_2026_013_centralizacao_tamanhos_variantes_epi.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 23/07/2026 | Arquiteto | Rascunho inicial | RASCUNHO |
| 1.0.0 | 23/07/2026 | Arquiteto / QA | Aprovação arquitetural e validação de invariantes e segurança | APROVADA_PARA_IMPLEMENTAÇÃO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADO` | 23/07/2026 | Mapeamento completo de ForeignKeys, transações atômicas e conferência de invariantes. |
| Revisão pré-implementação | QA | `APROVADO` | 23/07/2026 | 29 cenários de QA definidos e validados. |
| Implementação | Backend | `PENDENTE` |  | Executar somente após conclusão e aprovação do QA da SPEC 1. |
| QA final | QA | `PENDENTE` |  |  |

---

## 1. Resumo executivo

Em ambiente operacional/produção, cadastros legados foram realizados criando um `Product` (EPI) separado para cada tamanho (ex: "Luva P — CA 12345", "Luva M — CA 12345", "Luva G — CA 12345") em vez de registrar um único EPI "Luva de Segurança" com o CA 12345 e suas variantes de tamanho.

Esta SPEC especifica a criação de uma ferramenta de gerenciamento do Django (`python manage.py consolidar_epis_por_ca`) extremamente segura e auditável. A ferramenta opera por padrão em modo **Auditoria/Relatório** (`--report` / `--dry-run`), permitindo analisar duplicidades por CA normalizado e simular a consolidação sem alterar o banco de dados.

A aplicação efetiva (`--apply`) exige obrigatoriamente a especificação do CA, do ID do EPI Canônico (`--canonical-id`) e do mapeamento explícito das variantes (`--size-map`). Durante a consolidação, todos os relacionamentos históricos (lotes, saldos, movimentações, entregas, devoluções, matrizes, notas fiscais, alertas, auditoria) são transferidos com `transaction.atomic()` e `select_for_update()`, e a integridade de todos os saldos e totais é conferida antes e depois. Caso qualquer divergência seja detectada, a operação realiza rollback integral. Os EPIs duplicados incorporados são inativados (`ativo = False`), preservando seu histórico sem exclusão física.

---

## 2. Contexto da demanda

### 2.1 Mapeamento de relacionamentos a serem preservados

O Arquiteto mapeou todos os modelos e ForeignKeys do sistema ligados a `Product` e `ProductVariant`:

1. `ProductVariant`:
   - `product` (ForeignKey -> `Product`, `CASCADE`)
2. `PPEMatrix` (Matriz de EPI por Função):
   - `product` (ForeignKey -> `Product`, `PROTECT`)
   - `variant` (ForeignKey -> `ProductVariant`, `PROTECT`, nulo permitido)
   - Unique Constraint: `('funcao', 'product')`
3. `ExtraordinaryPPE` (EPI Extraordinário):
   - `product` (ForeignKey -> `Product`, `PROTECT`)
   - `variant` (ForeignKey -> `ProductVariant`, `PROTECT`, nulo permitido)
4. `PPEDelivery` (Entrega de EPI):
   - `product_variant` (ForeignKey -> `ProductVariant`, `PROTECT`)
5. `Lot` (Lote de Fabricante):
   - `product_variant` (ForeignKey -> `ProductVariant`, `PROTECT`)
   - `ca` (ForeignKey -> `CertificadoAprovacao`, `PROTECT`)
   - Unique Constraint: `('product_variant', 'identificador')`
6. `StockMovement` (Livro-Razão de Movimentações de Estoque):
   - `product_variant` (ForeignKey -> `ProductVariant`, `PROTECT`)
7. `StockTransferItem` (Itens de Transferência entre Locais):
   - `product_variant` (ForeignKey -> `ProductVariant`, `PROTECT`)
   - Unique Constraint: `('transfer', 'product_variant', 'lot')`
8. `LocationStockMinimo` (Estoque Mínimo por Local):
   - `product_variant` (ForeignKey -> `ProductVariant`, `CASCADE`)
   - Unique Constraint: `('product_variant', 'location')`

---

## 3. Requisitos funcionais

### RF-001 — Interface do Management Command
**Nome do comando:** `consolidar_epis_por_ca`  
**Opções obrigatórias e parâmetros:**
- `--report`: Exibe o relatório de duplicidades agrupado por CA normalizado. (Modo padrão se `--ca` não for informado).
- `--dry-run`: Simula todo o processo sem persistir alterações no banco de dados. (Modo padrão para execuções).
- `--ca <NUMERO_CA>`: Especifica o CA a ser auditado ou consolidado.
- `--canonical-id <ID>`: ID do `Product` selecionado como o EPI canônico principal.
- `--size-map "<ID_DUPLICADO>=<TAMANHO>,..."`: Mapeamento explícito do tamanho para os EPIs duplicados incorretos.
- `--apply`: Executa a consolidação efetiva no banco de dados dentro de transação atômica.
- `--output <CAMINHO_ARQUIVO>`: Salva o relatório em formato JSON ou CSV.

### RF-002 — Modo de Auditoria / Relatório
O relatório deve agrupar apenas produtos do tipo `EPI` com `ca_numero` preenchido, normalizado (dígitos apenas).
Para cada grupo com mais de 1 EPI:
- Exibir CA original e normalizado.
- Exibir IDs dos EPIs, nomes, fabricantes, categorias, status ativo/inativo.
- Exibir variantes, SKUs, estoques mínimos, saldos totais, saldos por local, saldos por variante.
- Exibir quantidade de lotes, itens de NFs, movimentações, entregas, matrizes de EPI, registros de auditoria.
- Destacar conflitos (fabricantes divergentes, descrições diferentes, SKUs sobrepostos, etc.).

### RF-003 — Validação Rigorosa da Seleção Canônica
Antes de qualquer consolidação:
1. Validar que o EPI canônico existe e está ativo.
2. Validar que o EPI canônico e todos os EPIs duplicados do grupo possuem exatamente o mesmo CA normalizado.
3. Impedir inclusão de EPIs de outros CAs ou sem CA.
4. Validar que o grupo possui efetivamente > 1 EPI.

### RF-004 — Mapeamento e Transferência de Variantes
1. Para cada EPI duplicado do grupo, determinar a variante/tamanho apropriado usando (em ordem):
   - Variantes ativas vinculadas ao próprio registro duplicado.
   - `--size-map` fornecido na CLI (ex: `--size-map "19=P,20=M,21=G"`).
   - Extração não ambígua do nome/descrição.
2. No EPI canônico:
   - Reutilizar variante existente se já houver com o mesmo tamanho.
   - Criar nova variante somente se não existir.
   - Preservar SKU e estoque mínimo se não houver conflito.

### RF-005 — Transferência Segura dos Relacionamentos
Sob `transaction.atomic()` e `select_for_update()`:
- Redirecionar todas as entregas (`PPEDelivery`), movimentações (`StockMovement`), lotes (`Lot`), transferências (`StockTransferItem`), estoques mínimos (`LocationStockMinimo`), matrizes (`PPEMatrix`) e autorizações extraordinárias (`ExtraordinaryPPE`) dos EPIs duplicados para a variante correspondente do EPI canônico.
- Caso existam constraints únicas (ex: `PPEMatrix` por função ou `LocationStockMinimo` por local), consolidar e recalcular mantendo o registro do canônico e inativando/excluindo a duplicidade da matriz/mínimo.
- **Jamais** alterar datas de movimentação, custos históricos, responsáveis ou recriar entregas.

### RF-006 — Conferência de Invariantes e Rollback Integral
Antes e depois da transferência, calcular no banco:
- Saldo total em estoque do grupo.
- Saldo de estoque por local (Almoxarifado, SST, etc.).
- Saldo por lote e quantidade por lote.
- Total de entradas, saídas, entregas e devoluções.
- Total de registros históricos vinculados.
Se qualquer total diferir antes e depois:
- Lançar exceção `ValidationError`.
- Disparar rollback transacional automático.
- Manter todos os registros duplicados inalterados.

### RF-007 — Destino dos EPIs Incorporados
- **Não excluir fisicamente** os registros `Product` duplicados incorporados.
- Marcar `ativo = False` no `Product` incorporado.
- Adicionar anotação na descrição: `[INCORPORADO AO EPI CANÔNICO ID <canonical_id>]`.
- Registrar evento completo em `AuditLog` via `log_action`.

---

## 4. Estratégia de testes da SPEC 2

Criar suíte de testes dedicados em `ppe/tests_consolidation.py` cobrindo todos os 29 cenários obrigatórios:
1. Grupos são identificados pelo CA normalizado.
2. EPIs com CAs diferentes não são agrupados.
3. EPIs sem CA não são consolidados automaticamente.
4. Dry-run não altera nenhum registro no banco.
5. Dry-run apresenta o plano completo de consolidação.
6. A aplicação exige a flag `--apply`.
7. A aplicação exige `--canonical-id`.
8. O canônico precisa pertencer ao mesmo CA normalizado.
9. Mapeamento ambíguo de tamanho bloqueia a operação.
10. Variantes existentes no canônico são reutilizadas.
11. Novas variantes são criadas apenas quando necessário.
12. Variantes duplicadas não são criadas no mesmo EPI.
13. Conflitos de SKU são detectados e informados.
14. Lotes permanecem associados corretamente ao novo variant.
15. Itens de NF permanecem preservados.
16. Movimentações permanecem preservadas.
17. Entregas permanecem preservadas.
18. Devoluções permanecem preservadas.
19. Matrizes permanecem preservadas.
20. Quantidades não são alteradas.
21. Totais globais e por local antes e depois são estritamente iguais.
22. Falha de invariante causa rollback total imediato.
23. Erro no meio da operação causa rollback total imediato.
24. EPIs incorporados não são excluídos fisicamente.
25. EPIs incorporados deixam de aparecer em novos fluxos operacionais (`ativo=False`).
26. O EPI canônico permanece disponível e ativo.
27. O log de auditoria registra a consolidação com todos os detalhes.
28. Nenhuma migration executa consolidação automaticamente.
29. Os testes atuais do projeto continuam passando (sem regressão).

**Cenário Integrado Completo:**
- Criar 3 EPIs duplicados com CA 12345 ("Luva P", "Luva M", "Luva G").
- Criar estoques distribuídos em locais de Almoxarifado e SST, lotes, notas fiscais, movimentações, entregas a colaboradores e 1 matriz por função.
- Executar `consolidar_epis_por_ca --ca 12345 --canonical-id <ID_P> --size-map "<ID_P>=P,<ID_M>=M,<ID_G>=G" --apply`.
- Validar a preservação integral dos totais globais, do histórico e da integridade referencial.
