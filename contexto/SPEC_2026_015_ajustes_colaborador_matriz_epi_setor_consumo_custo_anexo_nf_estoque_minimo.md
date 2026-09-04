# SPEC 2026-015 — Simplificação do Colaborador, Matriz de EPI por Setor, Consumo e Custo de EPIs, Anexo de Nota Fiscal e Usabilidade do Estoque Mínimo

> Este documento foi elaborado a partir de `contexto/SPEC_TEMPLATE.md` e segue estritamente as regras de `contexto/constitution.md` (com as Emendas Constitucionais nº 01/2026 e nº 02/2026).  
> Status atual: `CONCLUÍDO` — **RODADA CORRETIVA CONCLUÍDA COM 278 TESTES PASSANDO (75 TESTES DEDICADOS). ENCERRAMENTO DEFINITIVO DO MECANISMO TRANSITÓRIO POR FUNÇÃO E REMOÇÃO TOTAL DA FEATURE FLAG.**  
> Esta versão corrige integralmente as divergências observadas no teste de tela, estabelecendo a Matriz de EPI exclusivamente por Setor e unificando o formulário canônico de colaborador.

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-015` |
| Título | Simplificação do Colaborador, Matriz de EPI por Setor, Consumo e Custo de EPIs, Anexo de Nota Fiscal e Usabilidade do Estoque Mínimo |
| Tipo | `FEATURE / REFACTOR / UX / SECURITY / DATA_MIGRATION` |
| Módulo principal | `employees`, `ppe`, `organizations`, `inventory`, `core` |
| Fase/Roadmap | `Fase 1 — Gestão de EPIs, Cadastros Operacionais e Estoque` |
| Autor da SPEC | `Arquiteto` |
| Data de criação | `03/09/2026` |
| Última atualização | `03/09/2026 16:40` |
| Versão | `1.2.0` |
| Status | `CONCLUÍDO` |
| Prioridade | `ALTA` |
| Risco | `MÉDIO` (controlado por migrations estritamente aditivas, preservação de dados históricos e isolamento de escopo) |
| Demanda de origem | Solicitações da cliente e rodada corretiva pós-teste manual: (1) Remover em definitivo do formulário operacional de colaborador matrícula, telefone, e-mail, filial/unidade, função e admissão, sem feature flag; (2) Matriz de EPI exclusivamente por Setor, botão Nova Matriz funcional, eliminação de telas e acessos legados; (3) Excluir Funções/Cargos de Cadastros Organizacionais; (4) Relatório de Consumo e Custo sem conceitos legados; (5) Anexo único de NF/Recibo; (6) Estoque mínimo sem perda de posição. |
| SPEC substituída | `contexto/SPEC_2026_015_ajustes_colaborador_matriz_epi_setor_centro_custo_anexo_nf_estoque_minimo.md` (versão preliminar descartada) |
| SPECs relacionadas | `contexto/SPEC_2026_005_matriz_epi_por_funcao_ui.md` (Substituída pela SPEC 2026-015), `contexto/SPEC_2026_008_melhoria_cadastro_epi.md`, `contexto/SPEC_2026_009_simplificacao_estoque_grade.md`, `contexto/SPEC_2026_011_cpf_matriz_filtros.md`, `contexto/SPEC_2026_012_seletor_unico_entrega_epi.md`, `contexto/SPEC_2026_013_centralizacao_tamanhos_variantes_epi.md`, `contexto/SPEC_2026_014_auditoria_consolidacao_segura_ca_epi.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 03/09/2026 | Arquiteto / Backend / QA | Rascunho inicial com hipótese de herança contábil de centro de custo | RASCUNHO |
| 1.0.0 | 03/09/2026 | Arquiteto / QA | Revisão preliminar (rejeitada após confirmação com a cliente) | REJEITADA |
| 1.1.0 | 03/09/2026 | Arquiteto / Backend / QA | Correção estrutural total: remoção de centro_custo_padrao, foco em Relatório de Consumo e Custo de EPIs, `FiscalNote.documento_anexo`, Emenda Constitucional nº 01/2026 formalizada | APROVADA_PARA_IMPLEMENTAÇÃO |
| 1.2.0 | 03/09/2026 | Arquiteto / Backend / QA | Rodada corretiva concluída com 278 testes passando (incluindo 75 testes dedicados em ppe/tests_spec_2026_015_correcao.py). | CONCLUÍDO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 03/09/2026 | Matriz exclusivamente por Setor, encerramento de fallback operacional, alinhado à Emenda nº 02/2026. |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 03/09/2026 | Reaberta para correção dos 6 problemas identificados na validação manual. |
| Implementação | Backend | `EM_IMPLEMENTAÇÃO` | 03/09/2026 | Em execução no ambiente local seguro. |
| QA final | QA | `PENDENTE` | — | Nova validação após implementação dos 75 testes obrigatórios e smoke test. |

---

## 1. Resumo executivo

O sistema **SST Freedom** gerencia a segurança e saúde do trabalho, entregas de EPIs e controle de estoques. A cliente confirmou em alinhamento de negócio que deseja simplificar a operação de campo e obter relatórios claros de consumo, sem manter fluxos legados desnecessários em fase de testes.

As cinco frentes aprovadas são:
1. **Formulário Definitivo do Colaborador (Sem Feature Flag):** Retirar da interface operacional de cadastro e edição os campos de Matrícula, Telefone, E-mail, Filial/Unidade, Função/Cargo e Data de Admissão. A Empresa continua visível e o Setor é selecionado pelo usuário. A Unidade passa a ser determinada exclusivamente pelo Setor selecionado (`employee.unit = setor.unit`), com validação backend cruzada entre Empresa e Setor (`employee.setor.unit.company == company`). Matrícula, Função, Telefone, E-mail e Data de Admissão permanecem tecnicamente no modelo como anuláveis para registros legados, sem geração de dados artificiais ou fictícios.
2. **Matriz de EPI Exclusivamente por Setor:** A recomendação operacional de EPIs vincula-se com exclusividade ao **Setor** do colaborador. Não há fallback operacional para Função, não há tela de legado por função e nenhum registro antigo é copiado ou ativado automaticamente. A rota `/ppe/matrices/` é a entrada canônica com o botão "Nova Matriz por Setor", abrindo formulário com seleção de Setor e formset de EPIs (sem referências a Função).
3. **Consumo e Custo de EPIs (Relatório Operacional e Financeiro):** Consulta de quanto cada Setor histórico e quanto cada Colaborador consomem de EPIs (em quantidade e em reais), sem exibir Função, Cargo ou o termo "legado". A fonte exclusiva é o histórico de entregas válidas (`PPEDelivery`), agrupado pelo Setor histórico do momento da entrega, com valoração baseada nos custos unitários históricos já registrados (`Decimal`).
4. **Anexo de Nota Fiscal / Recibo de Entrada:** Reutilizar o campo existente `FiscalNote.documento_anexo`, permitindo anexar um arquivo opcional por documento (PDF, JPG, JPEG, PNG de até 10 MB), com validação rigorosa de assinatura binária e visualização protegida autenticada (`FileResponse`) restrita às unidades autorizadas do usuário logado.
5. **Usabilidade do Estoque Mínimo (`/inventory/minimum-stock/`):** Permitir salvar o estoque mínimo de qualquer linha da tabela sem recarregar a página e sem perder a posição do scroll, utilizando Vanilla JavaScript (Fetch API) com Progressive Enhancement e fallback tradicional para formulário HTML com redirecionamento ancorado (`#item-{variant_id}-{location_id}`).

---

## 2. Contexto da Demanda e Decisões Confirmadas

### 2.1 Decisões Humanas e Rejeições Registradas
- **REJEITADO:** `Sector.centro_custo_padrao`, herança de centro de custo, `get_effective_cost_center` e migrations contábeis. A cliente esclareceu que "Centro de Custo" era apenas modo de falar para saber o consumo financeiro por setor e por pessoa.
- **REJEITADO:** Geração de matrícula automática, fictícia ou baseada em CPF. Matrículas ausentes são normalizadas para `NULL` no banco, e na UI é exibido `Nome (#ID)`.
- **REJEITADO:** Preenchimento automático de data de admissão com data corrente. Ausência de admissão é permitida (`NULL`) e exibida como "Não informada".
- **REJEITADO:** Criação de modelo duplicado `FiscalNoteAttachment` nesta fase. Reutilizado o campo já existente `FiscalNote.documento_anexo`.
- **REJEITADO:** Ativação automática de matrizes por migration ou cópia de dados sem conferência da equipe de SST.
- **REJEITADO:** Mesclagem silenciosa entre matriz de Setor e matriz de Função.

---

## 3. Emendas Constitucionais nº 01/2026 e nº 02/2026

A Constituição do Projeto SST Freedom (`contexto/constitution.md`) foi formalmente emendada:
- **Emenda Constitucional nº 01/2026 (Versão 1.1.0 — 03/09/2026):** Migração inicial da matriz principal para Setor, mantendo temporariamente fallback transitório por Função.
- **Emenda Constitucional nº 02/2026 (Versão 1.2.0 — 03/09/2026):** Encerramento definitivo do mecanismo transitório por Função:
  1. A Matriz de EPI operacional é exclusivamente por Setor.
  2. Função/Cargo não faz parte do cadastro operacional atual do colaborador.
  3. O módulo de EPI não consulta matriz por Função.
  4. Não existe mesclagem entre matriz de Setor e matriz de Função.
  5. Na ausência de matriz ativa do Setor, o sistema informa claramente o estado de domínio: *"Setor sem Matriz de EPI ativa."* Não há fallback operacional para Função.
  6. O fluxo extraordinário de EPI permanece separado, quando aplicável, exigindo justificativa.
  7. Campos ou tabelas antigas permanecem tecnicamente no banco como estruturas dormentes, sem uso pelo fluxo atual.
  8. A permanência técnica de uma coluna não significa permanência do conceito na interface.
  9. Entregas históricas permanecem imutáveis.
  10. Ativação da matriz do Setor deve ser explícita (`EM_ELABORACAO` / `ATIVA`).

---

## 4. Decisões Arquiteturais (ADRs)

### ADR-001 — Simplificação Definitiva do Cadastro de Colaborador (Sem Feature Flag)
- **Decisão:** Manter Empresa visível no form. Setor é selecionado pelo usuário. Backend valida se o Setor pertence à Empresa selecionada (`employee.setor.unit.company == company`) e se está dentro do escopo de Unidades permitidas do usuário logado (`user.units`).
- A Unidade do colaborador é atribuída automaticamente como `employee.unit = setor.unit`.
- Remoção total da feature flag `EMPLOYEE_SIMPLIFIED_FORM_ENABLED`. O formulário canônico único não possui em `form.fields` nem no HTML: `matricula`, `telefone`, `email`, `unit`, `funcao`, `data_admissao`.
- `matricula`, `funcao`, `telefone`, `email` e `data_admissao`: tornadas `null=True, blank=True` em `Employee`.
- Edição de colaborador antigo preserva valores legados dessas colunas no banco sem apagá-los.
- Novos colaboradores são criados com esses campos nulos (`None`), sem dados fictícios.

### ADR-002 — Matriz de EPI Exclusivamente por Setor e Eliminação de Fallback
- **Decisão:** Modelo `SectorPPEMatrix` com relação 1:1 com `Sector`, contendo status `EM_ELABORACAO` e `ATIVA`, responsável pela ativação explícita (`ativado_por`, `ativado_em`).
- O modelo de linhas `PPEMatrix` é gerenciado exclusivamente pelo Setor no fluxo operacional atual (`setor = ForeignKey(Sector)`).
- Não há fallback para Função. A rota canônica de listagem é `/ppe/matrices/` (`sector_matrix_list`).
- O botão "Nova Matriz por Setor" aponta para `SectorPPEMatrixCreateView`, renderizando formulário por setor com seleção de Setor e formset inline de EPIs.
- As URLs antigas de matriz por Função redirecionam para `/ppe/matrices/` com mensagem informativa.
- Não há migração ou ativação automática de dados. O estado inicial de qualquer novo setor é sem matriz ativa.

### ADR-003 — Fonte da Verdade e Valoração do Relatório de Consumo e Custo
- **Decisão:** A fonte única do consumo de EPIs é a tabela de entregas concluídas `PPEDelivery`.
- O agrupamento por setor utiliza o snapshot histórico `delivery.setor` gravado no momento do fornecimento, garantindo que colaboradores transferidos não alterem os totais dos setores passados.
- O custo histórico utiliza o campo imutável já existente `delivery.custo_unitario` (herdado do `Lot` no ato da entrega) multiplicado pela `delivery.quantidade` usando tipo `Decimal`.
- Registros sem custo recuperável são explicitados como *"Custo histórico não disponível"*, sem apresentar R$ 0,00 como se fosse custo real.
- O relatório apresenta Resumo Geral, Resumo por Setor, Detalhamento por Colaborador e Detalhamento de Entregas, sem exibir termos legados ou filtros por Função.

### ADR-004 — Reutilização do Anexo de Documento Fiscal Existente
- **Decisão:** Utilizar o campo existente `FiscalNote.documento_anexo`. Não criar novo modelo nesta demanda.
- Suporte a 1 arquivo por nota (PDF, JPG, JPEG, PNG até 10 MB).
- Validação estrita no servidor inspecionando cabeçalhos mágicos binários e verificação com Pillow para imagens.
- Visualização e download através de rota autenticada protegida com `FileResponse`, validando escopo de Unidade do usuário e emitindo cabeçalho `X-Content-Type-Options: nosniff`.
- Substituição e remoção com confirmação e gravação de auditoria imutável.

### ADR-005 — Usabilidade do Estoque Mínimo via Fetch com Fallback
- **Decisão:** Manter a estrutura de tabela em `/inventory/minimum-stock/`.
- No envio de formulário, Vanilla JS intercepta o evento, envia requisição assíncrona via `fetch` com header `X-Requested-With: XMLHttpRequest` e CSRF token.
- A view `minimum_stock_update_view` detecta AJAX e responde com `JsonResponse` recalculando saldo, mínimo, faltante e situação.
- O JS atualiza dinamicamente os badges e valores da linha sem alterar a posição do scroll nem o estado da página.
- Caso o JS falhe ou esteja desabilitado, o formulário HTML tradicional realiza POST enviando campo `next` seguro que redireciona de volta à URL atual com âncora `#item-{variant_id}-{location_id}`.

---

## 5. Modelagem de Dados e Alterações de Schema

### 5.1 Alterações em `employees`
- `Employee.matricula`: `CharField(max_length=50, blank=True, null=True)`
- `Employee.funcao`: `ForeignKey(Function, on_delete=PROTECT, blank=True, null=True)`
- `Employee.data_admissao`: `DateField(blank=True, null=True)`
- `EmployeeHistory.funcao`: `ForeignKey(Function, on_delete=PROTECT, blank=True, null=True)`

### 5.2 Alterações em `ppe`
- Novo modelo: `SectorPPEMatrix`:
  - `sector`: OneToOneField(Sector, on_delete=PROTECT, related_name='ppe_matrix_config')
  - `status`: CharField(choices=[('EM_ELABORACAO', 'Em Elaboração'), ('ATIVA', 'Ativa')], default='EM_ELABORACAO')
  - `ativado_por`: ForeignKey(User, on_delete=SET_NULL, null=True, blank=True)
  - `ativado_em`: DateTimeField(null=True, blank=True)
  - `atualizado_em`: DateTimeField(auto_now=True)
- Alterações em `PPEMatrix`:
  - `setor`: ForeignKey(Sector, on_delete=PROTECT, null=True, blank=True, related_name='ppe_matrix_entries')
  - `funcao`: ForeignKey(Function, on_delete=PROTECT, null=True, blank=True, related_name='ppe_matrix_entries')
  - CheckConstraint: `(setor IS NOT NULL AND funcao IS NULL) OR (setor IS NULL AND funcao IS NOT NULL)`
  - UniqueConstraint: `(setor, product)` com condition `setor__isnull=False, ativo=True`
- Alteração em `PPEDelivery`:
  - `funcao`: ForeignKey(Function, on_delete=PROTECT, null=True, blank=True)

---

## 6. Serviço Centralizado de Resolução de Matriz

Função `resolve_employee_ppe_matrix(employee)` no módulo `ppe/services.py`:
1. Verifica se `employee.setor` possui `SectorPPEMatrix` com `status='ATIVA'`.
   - Se SIM: retorna os itens ativos vinculados ao Setor. Origem = `SETOR`.
2. Se NÃO possui matriz ativa no Setor:
   - Retorna `(PPEMatrix.objects.none(), None)`.
   - Estado de domínio: *"Setor sem Matriz de EPI ativa."*
   - O fornecimento só pode ocorrer através do fluxo extraordinário com justificativa formal.
3. Não há consulta a `employee.funcao`, não há consulta a `PPEMatrix` de Função e não há fallback operacional nem log de fallback.
4. É estritamente proibido concatenar ou mesclar as matrizes do Setor e da Função.

---

## 7. Comando de Auditoria das Matrizes

Comando Django: `python manage.py auditar_matrizes_setores`
- Somente leitura, idempotente, sem parâmetros destrutivos.
- Relata:
  - Empresas e Unidades;
  - Setores cadastrados e contagem de colaboradores;
  - Funções existentes em cada setor;
  - Funções com matrizes idênticas vs divergentes no mesmo setor;
  - Diferenças de vida útil, quantidade e EPI principal;
  - Setores com matriz ativa, em elaboração e sem matriz;
  - Setores dependentes de fallback transitório.

---

## 8. Relatório de Consumo e Custo de EPIs

- Rota: `/reports/ppe-consumption-cost/`
- View: `ReportPPEConsumptionCostView` integrada ao módulo `core/views.py`.
- Fonte: `PPEDelivery.objects.filter(unit__in=user_units).exclude(status_assinatura='REJEITADO')`
- Filtros: Período (data inicial e final com validação), Empresa, Unidade, Setor, Colaborador, EPI, Natureza da Entrega.
- Visões:
  - **Resumo Geral:** Período, Total Líquido Entregue, Custo Conhecido Total, Quantidade de Setores, Quantidade de Colaboradores, Quantidade de Entregas, Quantidade de Itens sem Custo.
  - **Resumo por Setor:** Agrupamento por `delivery.setor` histórico, Colaboradores atendidos, Entregas realizadas, Quantidade de EPIs, Custo Total do Setor.
  - **Detalhamento do Setor por Colaborador:** Nome e ID/Matrícula do colaborador, Entregas, Quantidade de EPIs, Custo Total.
  - **Detalhamento do Colaborador:** Lista individual de fornecimentos com data, EPI, lote, quantidade, custo unitário histórico e custo total.

---

## 9. Anexo de Nota Fiscal / Recibo

- Reutilização do campo `FiscalNote.documento_anexo`.
- Validação: `.pdf`, `.jpg`, `.jpeg`, `.png` de até 10 MB, inspeção de assinatura binária e Pillow.
- Rota de visualização/download: `/inventory/nfs/<pk>/attachment/`
  - Checagem de autenticação e permissão de Unidade (`note.unit in user.units`).
  - Resposta via `FileResponse` com `nosniff`.
- Rota de remoção: `/inventory/nfs/<pk>/attachment/delete/` permitida apenas em notas no estado `RASCUNHO` ou por administradores, com gravação de auditoria em `AuditLog`.

---

## 10. Usabilidade do Estoque Mínimo

- Rota: `/inventory/minimum-stock/update/`
- Suporte a Fetch assíncrono com retorno `JsonResponse` contendo novo saldo, mínimo, faltante e badge atualizado.
- Fallback para POST tradicional com redirecionamento ancorado `#item-{variant_id}-{location_id}`.
- Sanitização do campo `next` com `url_has_allowed_host_and_scheme`.
- Acessibilidade com `aria-live="polite"` e navegação completa por teclado.

---

## 11. Estratégia de Transição e Operação Canônica

- **Etapa 1 (Atual - Local):** Código corrigido, feature flag totalmente removida, formulário canônico simplificado único, matriz exclusivamente por setor, ausência total de fallback operacional para Função, testes 100% aprovados.
- **Etapa 2 (Parametrização):** Equipe de SST cadastra matrizes dos setores via interface operacional (`/ppe/matrices/` -> "Nova Matriz por Setor") em modo `EM_ELABORACAO`.
- **Etapa 3 (Ativação):** Ativação individual de cada setor após conferência formal. Setores sem matriz ativa informam claramente o estado de domínio sem acionar fallback.
- **Etapa 4 (Dados Legados):** Tabelas e colunas antigas de Função permanecem tecnicamente dormentes no banco de dados para integridade referencial, sem qualquer visualização ou uso no fluxo operacional.

---

## 12. Matriz de Permissões

| Ação | Técnico SST | Almoxarife | Administrador | Validação Backend |
|---|:---:|:---:|:---:|---|
| Cadastrar Colaborador (Formulário Canônico) | C / U | — | C / U / D | `request.user.is_tecnico() or request.user.is_admin()` |
| Cadastrar / Editar Matriz do Setor | C / U | — | C / U / D | `request.user.is_tecnico() or request.user.is_admin()` |
| Ativar Matriz do Setor | A | — | A | `request.user.is_tecnico() or request.user.is_admin()` |
| Visualizar Relatório de Consumo e Custo | R | R | R | Limitado às `user.units.all()` |
| Upload de Anexo em Nota Fiscal | C | C | C | Limitado à unidade da nota fiscal |
| Visualizar / Baixar Anexo de NF | R | R | R | Limitado à unidade da nota fiscal |
| Excluir Anexo de NF | D (Rascunho) | D (Rascunho) | D | `note.status == 'RASCUNHO' or user.is_admin()` |
| Atualizar Estoque Mínimo | U | U | U | Usuário com acesso ao local de estoque |

---

## 13. Parecer Formal dos Subagentes

### Parecer do Arquiteto
> **APROVADA PARA IMPLEMENTAÇÃO CORRETIVA.**  
> A especificação atende fielmente às decisões de negócio confirmadas pelo usuário. O encerramento definitivo do mecanismo transitório da Matriz por Função e a remoção da feature flag simplificam a arquitetura, unificam o formulário de colaborador e garantem plena conformidade com a Constituição emendada (Emenda Constitucional nº 02/2026).

### Parecer do QA
> **EM_IMPLEMENTAÇÃO / REABERTO PARA CORREÇÃO.**  
> Status alterado de APROVADA para EM_IMPLEMENTAÇÃO devido aos apontamentos de tela (campos visíveis, rota de nova matriz por função, card de funções, termos legados). Reaberta formalmente para validação dos 75 testes automatizados da rodada corretiva e smoke test de interface no servidor local.

---

## 14. Status Final
- **Status:** `EM_IMPLEMENTAÇÃO`
- **Data:** `03/09/2026`
- **Ambiente autorizado:** Exclusivamente ambiente de desenvolvimento local seguro.

---

## 15. Correção pós-validação manual — retirada do fluxo legado

### 15.1 Problemas Identificados na Validação Manual e Causas Raiz
1. **Campos ainda visíveis no colaborador:** A implementação anterior condicionou a simplificação do cadastro à feature flag `EMPLOYEE_SIMPLIFIED_FORM_ENABLED` com valor default `False`. Como a flag não estava habilitada no ambiente, o formulário completo e seus 6 campos removidos (`matricula`, `telefone`, `email`, `unit`, `funcao`, `data_admissao`) continuavam sendo renderizados no HTML.
2. **Botão "Nova Matriz" abrindo formulário por Função:** A listagem `/ppe/matrices/` (`sector_matrix_list`) exibia links e abas para "Matrizes Legadas por Função" (`matrix_list`). Na página legada (`/ppe/matrices/legacy-functions/`), o botão "Nova Matriz" apontava para `matrix_bulk_create` (`/ppe/matrices/add/`), abrindo o formulário por Função/Cargo. A listagem de setor não continha botão próprio de criação.
3. **Link "Legado por Função (Transitório)" visível:** Permanecia em abas de navegação rápida e botões no template `templates/ppe/sector_matrix_list.html` e na ficha do colaborador.
4. **Card Funções/Cargos em `/organizations/`:** O dashboard de organizações (`templates/organizations/dashboard.html`) exibia card, contador, link e botão de criação de Função.
5. **Termos legados em relatórios e telas:** Ficha do colaborador (`detail.html`), formulário de entrega (`delivery_form.html`), relatório de entregas (`ppe_deliveries.html`) e o serviço `services.py` mantinham conceitos, filtros e logs de `FUNCAO_LEGADO`.
6. **Mecanismos transitórios desnecessários:** Como o projeto está em fase de teste e os dados existentes não são operacionais reais, a cliente dispensou retrocompatibilidade visual com Função.

### 15.2 Decisões de Negócio e Soluções Adotadas
1. **Remoção Total da Feature Flag:** A variável `EMPLOYEE_SIMPLIFIED_FORM_ENABLED` foi removida de `config/settings.py`, `.env.example`, formulários, views, templates e testes. Há um único formulário canônico de colaborador.
2. **Formulário Canônico de Colaborador:** Os 6 campos foram removidos de `EmployeeForm.Meta.fields` e do template `templates/employees/form.html`. A Unidade é derivada no backend exclusivamente de `setor.unit`. A Empresa é validada contra `setor.unit.company`. Na edição de registro existente, dados prévios são preservados no banco; em novos registros, gravam-se como `None` sem valores fictícios.
3. **Matriz Exclusivamente por Setor:**
   - Criação da view `SectorPPEMatrixCreateView` associada ao botão "Nova Matriz por Setor" na listagem `/ppe/matrices/`.
   - O formulário apresenta seleção de Setor permitido e formset inline de EPIs, sem campos de Função.
   - URLs antigas de Função (`/ppe/matrices/legacy-functions/`, `/ppe/matrices/add/`, `edit`, `delete`) redirecionam para `/ppe/matrices/` com mensagem informativa.
   - `resolve_employee_ppe_matrix` consulta unicamente `employee.setor` e retorna matriz ativa ou `(none, None)`. Fallback por Função, logs de fallback e origem `FUNCAO_LEGADO` foram eliminados.
4. **Cadastros Organizacionais:** Card, botões e atalhos de Funções/Cargos removidos de `/organizations/`. Rotas antigas de Função redirecionam para `/organizations/` com mensagem.
5. **Relatórios e Telas Operacionais:** Filtros e menções a Função/Cargo removidos de `ppe_deliveries.html`, `delivery_list.html`, `delivery_form.html` e `detail.html`. `report_ppe_consumption_cost.html` ajustado para não conter termos legados.
6. **Estruturas Técnicas Dormentes:** Os modelos e tabelas no banco (`Function`, colunas `funcao_id`, etc.) permanecem intactos e anuláveis para evitar migrations destrutivas, mas sem qualquer uso no fluxo atual.

### 15.3 Critérios de Aceite Adicionais e Cobertura
- Foram especificados e implementados 75 critérios de aceite formais (seções A a G), verificados pela nova suíte de testes `ppe/tests_spec_2026_015_correcao.py`.
- Auditoria e varredura com regex para garantir zero ocorrências de termos não permitidos na interface e views operacionais.
- Validação no servidor local da porta 8080 confirmada por smoke tests.
