# SPEC_2026_017 — Correções de Homologação dos Seletores Pesquisáveis, Formsets Dinâmicos, Estrutura Organizacional, Menu Lateral, Ativação da Matriz e Reformulação de Variantes do EPI

> Esta SPEC segue estritamente o modelo de `contexto/SPEC_TEMPLATE.md` e as regras permanentes de `contexto/constitution.md`.  
> Status atual: `APROVADA_PARA_IMPLEMENTAÇÃO` (Subagentes Arquiteto e QA — Rodada 2).  
> Referência explícita às SPECs originais: `contexto/SPEC_2026_015_ajustes_colaborador_matriz_epi_setor_consumo_custo_anexo_nf_estoque_minimo.md` e `contexto/SPEC_2026_016_recebimento_epi_variante_seletores_pesquisaveis.md`.

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-017` |
| Título | Correções de homologação dos seletores pesquisáveis, formsets dinâmicos, estrutura organizacional, menu lateral, ativação da matriz e reformulação de variantes do EPI |
| Tipo | `FIX / REFACTOR / UX / SECURITY / DATA_MIGRATION` |
| Módulo principal | `ppe`, `core`, `inventory`, `organizations`, `notifications`, `reports` |
| Fase/Roadmap | `Fase 1 — Gestão de EPIs, Cadastros Operacionais e Estoque / Fase 1b — Homologação Operacional` |
| Autor da SPEC | `Arquiteto` |
| Data de criação | `04/09/2026` |
| Última atualização | `04/09/2026 14:00` |
| Versão | `1.1.0` |
| Status | `APROVADA_PARA_IMPLEMENTAÇÃO` |
| Prioridade | `CRÍTICA` |
| Risco | `MÉDIO` (controlado por migrations aditivas e preservação de dados históricos) |
| Demanda de origem | `Correções pós-homologação manual (Rodada 1 e Rodada 2): seletores pesquisáveis, matriz de EPI por setor, menu lateral, ativação da matriz, unidade de medida, seletor visual de variantes, unicidade de C.A. e proteção de Enter.` |
| SPEC substituída | `Não` |
| SPECs relacionadas | `contexto/SPEC_2026_015_ajustes_colaborador_matriz_epi_setor_consumo_custo_anexo_nf_estoque_minimo.md`, `contexto/SPEC_2026_016_recebimento_epi_variante_seletores_pesquisaveis.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 04/09/2026 | Arquiteto / QA | Elaboração da especificação técnica com diagnóstico de causa-raiz e plano corretivo da Rodada 1 | APROVADA_PARA_IMPLEMENTAÇÃO |
| 1.1.0 | 04/09/2026 | Arquiteto / QA | Acréscimo da seção "Achados da homologação manual — rodada 2" com diagnóstico de menu lateral, ativação de matriz, unidade de medida canônica, novo seletor visual de tamanhos, unicidade de C.A. e prevenção de Enter | APROVADA_PARA_IMPLEMENTAÇÃO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADO` | 04/09/2026 | Investigação completa das 34 questões da Rodada 2; causas-raízes identificadas; catálogo canônico de tamanhos definido; template tag centralizada de menu modelada. |
| Revisão pré-implementação | QA | `APROVADO` | 04/09/2026 | Critérios AC01 a AC32 da Rodada 2 formalizados; 48 cenários de testes automatizados e 11 cenários manuais definidos. |
| Implementação | Backend | `PENDENTE` |  | Aguardando conclusão da revisão de planejamento para iniciar código. |
| QA final | QA | `PENDENTE` |  |  |

---

## 1. Resumo executivo

Durante a homologação manual das entregas das SPECs 015 e 016, foram observadas 6 divergências operacionais:
1. Em `/ppe/matrices/add/`, o botão "Adicionar EPI" clonava uma linha já inicializada por JavaScript (`rows[0]`), duplicando instâncias quebradas e valores da linha anterior.
2. Em `/ppe/matrices/add/` e `/reports/ppe-consumption-cost/`, os dropdowns de opções abriam cortados pelos containers ancestrais (`.card-premium` com `overflow: hidden;` e `.table-responsive` com `overflow-x: auto;`), exigindo rolagem interna do card para ver as opções.
3. Em `/organizations/unit/add/`, a abertura da tela falhava com `FieldError: Unknown field(s) (cnpj) specified for Unit`, pois `UnitCreateView.fields` declarava `cnpj`, atributo inexistente no model `Unit`.
4. Em `/organizations/`, as empresas cadastradas não eram apresentadas em nenhum card do painel.
5. Em `/organizations/`, os cards de Setores e Locais de Estoque exibiam a chave estrangeira bruta ou código numérico (ex: "1") em vez do nome legível da Unidade (ex: "FREEDOM").
6. Em `/reports/ppe-consumption-cost/`, o filtro de colaborador era um input de texto simples e os filtros ficavam limitados pelo container do card.

Esta SPEC estabelece a solução arquitetural definitiva e compartilhada para sanar todas essas falhas sem recorrer a soluções pontuais ou bibliotecas externas pesadas.

---

## 2. Achados da Homologação Manual e Causa-Raiz

### Achado 1: Matriz de EPI por Setor — Novas Linhas Não Funcionam
- **Evidência**: Em `/ppe/matrices/add/`, clicar em "Adicionar EPI" cria uma linha com dropdown inoperante e que visualmente herda valores e rótulo da primeira linha.
- **Causa-Raiz**: O script em `sector_matrix_create.html` executava `rows[0].cloneNode(true)` sobre uma linha cujo select original já estava oculto (`style="display: none;"`) e acompanhado do wrapper gerado pelo `SearchableSelect`. A clonagem duplicava o wrapper estático sem listeners e não invocava `initSearchableSelects` nem limpava os campos de forma limpa a partir de `empty_form`.

### Achado 2: Dropdowns Escondidos / Cortados Dentro dos Cards
- **Evidência**: Nos cards de filtros e na tabela da matriz, a lista de opções do seletor ficava oculta ou forçava barras de rolagem internas no card/tabela.
- **Causa-Raiz**: A classe `.card-premium` possui `overflow: hidden;` e `.table-responsive` possui `overflow-x: auto;`. Como `.searchable-select-dropdown` possuía `position: absolute;` ancorado relativamente ao `.searchable-select-wrapper` interno, o navegador estritamente recortava qualquer elemento que ultrapassasse as dimensões do card ou criava scroll vertical dentro da tabela.

### Achado 3: FieldError (cnpj) em UnitCreateView
- **Evidência**: `/organizations/unit/add/` gerava `FieldError: Unknown field(s) (cnpj) specified for Unit`.
- **Causa-Raiz**: O model `Unit` (`organizations/models.py`) possui os campos `['company', 'codigo', 'nome', 'cidade', 'estado', 'ativo']`. O atributo `cnpj` pertence exclusivamente ao model `Company`. No entanto, `UnitCreateView.fields` em `organizations/views.py` listava indevidamente `'cnpj'`.

### Achado 4: Ausência de Listagem de Empresas em /organizations/
- **Evidência**: `/organizations/` possuía cards para Unidades, Setores, Centros de Custo e Locais de Estoque, mas nenhum card para Empresas.
- **Causa-Raiz**: `OrganizationDashboardView` injetava `companies` no contexto, mas o template `templates/organizations/dashboard.html` não continha o bloco de marcação para renderizar a tabela de empresas.

### Achado 5: Exibição de ID/Código Bruto no Lugar do Nome da Unidade
- **Evidência**: Nos cards de Setores e Locais de Estoque de `/organizations/`, a coluna "Unidade" exibia `{{ sector.unit.codigo }}` e `{{ loc.unit.codigo }}` (ex: "1" ou "UN-01").
- **Causa-Raiz**: O template renderizava a propriedade `.codigo` em vez de `.nome` da Unidade, e a view não fazia `select_related('unit')`, gerando consultas adicionais.

### Achado 6: Filtros de Relatório Pouco Intuitivos em /reports/ppe-consumption-cost/
- **Evidência**: O campo colaborador era texto livre, o EPI sofria corte de overflow, e os filtros de Empresa/Unidade/Setor não utilizavam a interface pesquisável padronizada.
- **Causa-Raiz**: O formulário utilizava campos heterogêneos sem vinculação ao componente central `SearchableSelect` e sem pré-seleção dos dados de colaboradores.

---

## 3. Arquitetura da Solução TO-BE

### 3.1 Portal Flutuante do SearchableSelect (Sem Recorte de Overflow)
- **Mecanismo Portal**: Ao ser aberto (`open()`), o elemento `.searchable-select-dropdown` é anexado diretamente ao `document.body` (ou reposicionado em camada global).
- **Posicionamento**: Utiliza `position: fixed;` calculando as coordenadas precisas através de `control.getBoundingClientRect()`:
  - `top = rect.bottom + 4px;`
  - `left = rect.left;`
  - `width = rect.width;`
  - `z-index = 99999;`
- **Inversão Vertical Inteligente**: Se o espaço inferior na janela (`window.innerHeight - rect.bottom`) for menor que 260px e houver mais espaço superior, o dropdown abre para cima (`bottom = window.innerHeight - rect.top + 4px;`).
- **Comportamento em Scroll/Resize**: Reposiciona o dropdown ao rolar a página ou redimensionar a janela; fecha ao clicar fora.
- **Destruição Limpa**: Ao fechar ou destruir o componente, o dropdown é removido do `document.body`.

### 3.2 Formsets Dinâmicos com `empty_form` e `<template>`
- Em `sector_matrix_create.html` e `sector_matrix_form.html`:
  - Declarado bloco `<template id="empty-form-template">` contendo `{{ formset.empty_form }}`.
  - Ao clicar em "Adicionar EPI", clona o conteúdo limpo do template substituindo `__prefix__` pelo índice corrente (`TOTAL_FORMS`).
  - Cada nova linha inicia 100% limpa, sem EPI selecionado, com defaults de formulário (`quantidade_padrao=1`, `vida_util_dias=365`, `obrigatorio=True`, `principal=True`).
  - Executa `window.initSearchableSelects(newRow)` garantindo uma instância nova e independente.
  - Preserva a regra de negócio existente em `BasePPEMatrixSectorFormSet.clean()`, que impede o mesmo EPI de ser adicionado duas vezes no mesmo setor.

### 3.3 Correção da Estrutura Organizacional
- **`UnitCreateView` e `UnitUpdateView`**:
  - `fields = ['company', 'codigo', 'nome', 'cidade', 'estado', 'ativo']`.
  - Remoção total da referência a `'cnpj'`.
  - Adição de `UnitUpdateView` mapeada em `/organizations/unit/<int:pk>/edit/`.
- **Card de Empresas em `/organizations/`**:
  - Card visualmente idêntico aos demais, com listagem de `companies` acessíveis (filtradas por permissão/unidades para não-superusuários).
  - Colunas: Nome Fantasia / Razão Social, CNPJ formatado, Status (Badge Ativo/Inativo).
  - Estado vazio amigável: "Nenhuma empresa cadastrada."
- **Exibição Legível de Unidades**:
  - Em Setores e Locais de Estoque, exibe `{{ sector.unit.nome }}` e `{{ loc.unit.nome }}`.
  - Otimização do queryset com `select_related('unit', 'unit__company')`.

### 3.4 Filtros de Consumo e Custo (`/reports/ppe-consumption-cost/`)
- Colaborador passa a ser um `<select>` com `class="form-select form-control-premium searchable-select" data-search-url="/employees/api/search/" data-placeholder="Todos os Colaboradores">`.
- Suporte duplo no backend: se receber ID numérico, filtra por `employee_id`; se receber texto, preserva busca por nome/CPF (compatibilidade total).
- Preservação da opção pré-selecionada no HTML ao aplicar filtros.
- Selects de Empresa, Unidade e Setor com `searchable-select` para busca rápida, mantendo a opção inicial "Todas/Todos".

---

## 4. Critérios de Aceite

- **AC01**: Em `/ppe/matrices/add/`, o primeiro seletor de EPI funciona normalmente.
- **AC02**: Cada nova linha adicionada pelo botão "Adicionar EPI" possui um seletor pesquisável ativo e independente.
- **AC03**: A nova linha criada não herda o EPI nem valores modificados da linha anterior.
- **AC04**: A nova linha não clona wrappers HTML da biblioteca de select nem IDs duplicados.
- **AC05**: `TOTAL_FORMS` e nomes de campos dos formsets mantêm indexação consistente.
- **AC06**: É possível remover linhas intermediárias e adicionar novas sem quebrar os seletores restantes.
- **AC07**: Em `/ppe/matrices/add/`, o menu suspenso abre sobre o card sem ser cortado pelas bordas.
- **AC08**: A abertura do menu suspenso não gera barra de rolagem vertical interna no card.
- **AC09**: O menu suspenso possui rolagem própria quando a lista de resultados excede a altura máxima.
- **AC10**: `/organizations/unit/add/` abre em GET com código HTTP 200 sem `FieldError`.
- **AC11**: O formulário de Unidade solicita exclusivamente os campos reais do model `Unit`.
- **AC12**: É possível cadastrar e editar uma Unidade com sucesso.
- **AC13**: `/organizations/` apresenta o card "Empresas" listando as empresas acessíveis.
- **AC14**: Usuário restrito não visualiza empresas fora de suas unidades autorizadas.
- **AC15**: Os cards de Setores e Locais de Estoque exibem o nome legível da Unidade (ex.: FREEDOM).
- **AC16**: Em `/reports/ppe-consumption-cost/`, o campo Colaborador é um seletor pesquisável com busca remota e debounce.
- **AC17**: Em `/reports/ppe-consumption-cost/`, o campo EPI é pesquisável por nome e C.A.
- **AC18**: Filtros de Empresa, Unidade e Setor permitem filtragem ágil preservando a opção "Todos".
- **AC19**: Os filtros preenchidos permanecem selecionados após clicar em "Filtrar" e ao recarregar a página.
- **AC20**: O botão "Limpar" restaura todos os filtros do relatório para o estado vazio.
- **AC21**: Nenhum dropdown do relatório fica escondido dentro do card de filtros.
- **AC22**: O componente `SearchableSelect` é único, centralizado e reutilizável.
- **AC23**: Não são criadas migrations indevidas de `cnpj` em `Unit`.
- **AC24**: Permissões de acesso aos endpoints respeitam autenticação e escopo por Unidade.
- **AC25**: `manage.py check` passa com 0 erros.
- **AC26**: `manage.py makemigrations --check` aponta que não há alterações pendentes.
- **AC27**: Todos os testes automatizados existentes e os novos testes de homologação passam com sucesso.
- **AC28**: O salvamento da matriz com tentativa de EPI duplicado é bloqueado com mensagem amigável no backend.

---

## 5. Plano de Testes

1. **Testes Automatizados**:
   - `ppe.tests_spec_2026_017`:
     - Teste de renderização GET de `/ppe/matrices/add/` contendo `<template id="empty-form-template">`.
     - Teste de submissão do formset com múltiplas linhas válidas.
     - Teste de rejeição de EPI duplicado na mesma matriz.
     - Teste de GET em `/organizations/unit/add/` (HTTP 200, sem campo `cnpj`).
     - Teste de POST válido criando `Unit` e edição em `UnitUpdateView`.
     - Teste de GET em `/organizations/` confirmando card de Empresas e nomes legíveis das unidades.
     - Teste de filtros em `/reports/ppe-consumption-cost/` por ID de colaborador e por texto.
2. **Testes Manuais do QA**:
   - Cenário A: Matriz com 3 linhas adicionadas dinamicamente, remoção da 2ª linha, adição da 4ª e salvamento.
   - Cenário B: Visibilidade dos dropdowns flutuantes sobre cards com `overflow: hidden;`.
   - Cenário C: Criação e edição de Unidade em `/organizations/unit/add/`.
   - Cenário D: Painel organizacional com card de Empresas e nomes das unidades.
   - Cenário E: Filtros do Relatório de Consumo e Custo.

---

## 6. Achados da Homologação Manual — Rodada 2

### 6.1 Investigação Arquitetural e Diagnóstico de Causa-Raiz

#### MENU LATERAL (Itens 1 a 5 da Investigação)
- **Questão 1 — Template responsável:** `templates/base.html` (linhas 20 a 99) renderiza a barra de navegação lateral (`.sidebar-wrapper`).
- **Questão 2 — Decisão do estado ativo:** Atualmente decidido por testes ad-hoc de substring em `request.path` (ex: `'ppe' in request.path`, `'reports' in request.path`, `'alerts' in request.path`), exceto o Início que compara `request.resolver_match.url_name == 'dashboard'`.
- **Questão 3 — Condições amplas / colidências:** 
  - `'ppe' in request.path and 'deliver' not in request.path and 'matrices' not in request.path and 'matrix' not in request.path` ativava indevidamente o item "EPIs / Catálogo" em `/reports/ppe-consumption-cost/` e `/reports/ppe-deliveries/`.
  - Na rota `/reports/ppe-deliveries/`, TRÊS itens ficavam ativos simultaneamente: "EPIs / Catálogo", "Entregas / Ficha EPI" (por conter `deliver`) e "Relatórios" (por conter `reports`).
  - Na rota `/notifications/`, o menu procurava `'alerts' in request.path`, deixando Alertas completamente inativo.
- **Questão 4 — Mapeamento das 11 rotas principais:**
  1. Início: `dashboard` (`/`)
  2. Colaboradores: `employee_list`, `employee_create`, `employee_detail`, `employee_update` (prefixo `/employees/`)
  3. EPIs / Catálogo: `product_list`, `product_create`, `product_detail`, `product_update` (prefixo `/ppe/`, exceto `/ppe/matrices/` e `/ppe/deliveries/`)
  4. Matriz de EPI por Setor: `sector_matrix_list`, `sector_matrix_create`, `sector_matrix_edit`, `sector_matrix_activate`, `sector_matrix_deactivate` (prefixo `/ppe/matrices/`)
  5. Almoxarifado / Compras: `fiscal_note_list`, `fiscal_note_create`, `fiscal_note_detail`, `supplier_list` (prefixos `/inventory/nfs/` e `/inventory/suppliers/`)
  6. Transferências: `transfer_list`, `transfer_create`, `transfer_detail` (prefixo `/inventory/transfers/`)
  7. Estoque Mínimo: `minimum_stock_list` (prefixo `/inventory/minimum-stock/`)
  8. Entregas / Ficha EPI: `delivery_list`, `delivery_create`, `delivery_detail` (prefixo `/ppe/deliveries/`)
  9. Alertas: `alert_list` (prefixo `/notifications/`)
  10. Relatórios: `report_list`, `report_stock_position`, `report_stock_movements`, `report_ppe_deliveries`, `report_ca_validity`, `report_ppe_consumption_cost` (prefixo `/reports/`)
  11. Cadastros / Unidades: `organization_dashboard`, `unit_create`, `unit_update`, `sector_create`, etc. (prefixo `/organizations/`)
- **Questão 5 — Outros caminhos com falha:** Identificado que `/reports/ca-validity/` funcionava por sorte pois não continha `ppe`, mas qualquer outro relatório associado a EPI falhava com destaque duplo ou triplo.

#### MATRIZ DE EPI (Itens 6 a 16 da Investigação)
- **Questão 6 — Model da matriz:** `SectorPPEMatrix` armazena a configuração/status do setor, e `PPEMatrix` armazena as recomendações por setor (`setor = models.ForeignKey(Sector, ...)`).
- **Questão 7 — Campo de status:** `SectorPPEMatrix.status`.
- **Questão 8 — Valores reais:** `STATUS_CHOICES = (('EM_ELABORACAO', 'Em Elaboração'), ('ATIVA', 'Ativa'))`.
- **Questão 9 — Onde é feita a ativação:** `SectorPPEMatrixActivateView` em `ppe/views.py#L878`.
- **Questão 10 — Botão "Ativar" existente na listagem:** Já utiliza método HTTP `POST` com proteção `{% csrf_token %}`, checagem de permissão (`is_tecnico` ou `is_admin`), valida se a matriz possui itens ativos (`count() > 0`), log de auditoria e mensagem amigável com redirecionamento para a listagem. O botão funciona perfeitamente quando a matriz possui itens.
- **Questão 11 & 12 — Causa de manter "Em Elaboração":** Em `SectorPPEMatrixCreateView` (`/ppe/matrices/add/`) e `SectorPPEMatrixEditView` (`/ppe/matrices/sector/<id>/edit/`), existia apenas um botão "Salvar Matriz do Setor". As views executavam `SectorPPEMatrix.objects.get_or_create(..., defaults={'status': 'EM_ELABORACAO'})` e salvavam o formset sem transicionar o status nem dar a opção ao operador de "Salvar e Ativar".
- **Questão 13 — Versionamento:** Não há versionamento de matrizes. `SectorPPEMatrix.sector` é `OneToOneField(Sector)`, garantindo exatamente uma matriz por setor operacional.
- **Questão 14 — Edição de matriz ativa:** A view salvava os itens da matriz sem alterar o status. Se a matriz já estava `ATIVA`, permanecia `ATIVA`. A falha residia no fato de matrizes em elaboração não oferecerem ação de ativação no formulário.
- **Questão 15 — Ativação sem EPIs:** O sistema bloqueia a ativação de matriz sem EPI ativo (`active_items_count == 0`), exibindo mensagem de erro.
- **Questão 16 — Unicidade de matriz ativa por setor:** Garantida pelo `OneToOneField` entre `Sector` e `SectorPPEMatrix`.

#### CADASTRO DO EPI (Itens 17 a 34 da Investigação)
- **Questão 17 — Models relacionados:**
  - `Product`: cadastro principal do EPI.
  - `CertificadoAprovacao`: base técnica do C.A.
  - `ProductVariant`: variantes/tamanhos (FK para `Product`).
  - `unidade_medida`: campo no `Product`.
  - `Lot`: lotes vinculados à variante.
  - `StockMovement`: livro-razão de estoque.
  - `PPEDelivery`: entregas aos colaboradores.
  - `FiscalNote`: notas fiscais de compra.
  - `LocationStockMinimo`: estoque mínimo por local.
- **Questão 18 & 19 — Unicidade do C.A. e cadastro duplicado:** `Product.ca_numero` não possuía `unique=True` nem `UniqueConstraint` no banco. A validação existia apenas em `ProductForm.clean()`, mas era reativa (somente após submeter todo o form).
- **Questão 20 — Normalização do C.A.:** String numérica sem caracteres não dígitos (`"".join([c for c in str(ca) if c.isdigit()])`).
- **Questão 21 & 22 — Diagnóstico no Banco Real:**
  - Total de produtos no banco: 4 produtos (IDs 18, 19, 21 e 25).
  - C.As existentes: 43010, 35719, 17137 e 39670.
  - Duplicidades de C.A. encontradas: **0 (nenhuma duplicidade presente no banco atual)**.
  - Vínculos existentes: Todos os 4 produtos possuem variantes ativas e movimentos/matrizes consistentes.
- **Questão 23, 24 & 25 — Unidades de medida no banco:**
  - Todos os 4 produtos utilizam `'UND'`.
  - O campo era `CharField` livre no HTML.
  - Sinônimos mapeados para canonização: `UND`, `und`, `Unid`, `UNID`, `unidade`, `UN` -> `UND`; `PAR`, `par`, `pares` -> `PAR`; `CX`, `cx`, `caixa` -> `CX`; `PCT`, `pct` -> `PCT`; `KIT`, `kit` -> `KIT`; `CJ`, `cj` -> `CJ`; `M`, `m` -> `M`.
- **Questão 26 & 27 — Variantes por vírgula e normalização:** `ProductForm` usava `tamanhos_str`, que era processado por `sync_product_variants` e `normalize_size_string`. Os usuários se confundiam e criavam um EPI novo para cada tamanho.
- **Questão 28 — Constraints de variantes:** `ProductVariant` possui `unique_together = ('product', 'tamanho')` e `UniqueConstraint(fields=['product', 'tamanho_normalizado'], name='unique_product_variant_normalized')`.
- **Questão 29 — Remoção de variantes na edição:** `sync_product_variants` já verifica `variant_has_history_or_stock(variant)`. Se houver estoque, lotes, entregas ou transferências, a exclusão é bloqueada com mensagem de aviso e a variante é preservada ativa.
- **Questão 30 & 31 — Catálogo central de tamanhos:** Não existia catálogo fixo; a solução ideal e menos invasiva é um catálogo canônico em `ppe/constants.py` com ordenação por grupos (Letras, Luvas, Calçados).
- **Questão 32, 33 & 34 — Submissão por Enter:**
  - O navegador dispara o `submit` do primeiro botão `type="submit"` do formulário quando o usuário pressiona Enter em qualquer `<input type="text">`.
  - O formulário possuía botão "Salvar" com `type="submit"` e campos de texto sem bloqueio de Enter.
  - Enter no campo C.A. submetia o formulário inteiro antes mesmo da consulta ser concluída.

---

### 6.2 Arquitetura da Solução TO-BE (Rodada 2)

#### 1. Menu Lateral Centralizado e Acessível (`core/templatetags/nav_tags.py`)
- Criação da template tag `active_nav(request, item_name)` que retorna `active aria-current="page"` se o item corresponder à rota atual.
- Algoritmo de mapeamento estrito e mutuamente exclusivo:
  - `dashboard`: `/`
  - `employees`: `/employees/`
  - `ppe`: rota inicia com `/ppe/` E NÃO inicia com `/ppe/matrices/` E NÃO inicia com `/ppe/deliveries/`
  - `matrices`: rota inicia com `/ppe/matrices/`
  - `nfs`: `/inventory/nfs/` ou `/inventory/suppliers/`
  - `transfers`: `/inventory/transfers/`
  - `minimum_stock`: `/inventory/minimum-stock/`
  - `deliveries`: `/ppe/deliveries/`
  - `notifications`: `/notifications/`
  - `reports`: rota inicia com `/reports/`
  - `organizations`: rota inicia com `/organizations/`
- Impossibilidade matemática de mais de um item ficar ativo.

#### 2. Fluxo Intuitivo de Ativação da Matriz de EPI
- Em `SectorPPEMatrixCreateView` e `SectorPPEMatrixEditView`:
  - Se a matriz estiver em `EM_ELABORACAO`, apresentar dois botões com `name="action"`:
    - `save_draft` ("Salvar como elaboração"): valida, persiste os itens do formset e mantém `status='EM_ELABORACAO'`. Mensagem: *"Matriz salva como elaboração. Ela ainda não está sendo utilizada nas recomendações de EPI."*
    - `save_and_activate` ("Salvar e ativar"): valida itens, exige no mínimo 1 EPI válido, e dentro de transação atômica (`transaction.atomic`) persiste os itens e ativa a matriz (`status='ATIVA'`, `ativado_por=request.user`, `ativado_em=timezone.now()`). Mensagem: *"Matriz do setor ativada com sucesso."*
  - Se a matriz já estiver `ATIVA`:
    - Exibe badge verde "Ativa".
    - Botão principal: "Salvar alterações" (`action=save_changes`), que mantém o status `ATIVA`.
    - Botão secundário: "Retornar para Elaboração" via POST com confirmação e CSRF.
  - Manutenção do botão verde "Ativar" na listagem (`/ppe/matrices/`) com POST e validações completas.

#### 3. Catálogo Canônico de Unidades de Medida
- No model `Product`:
  - `UNIDADE_MEDIDA_CHOICES = (('UND', 'UND — Unidade'), ('PAR', 'PAR — Par'), ('CX', 'CX — Caixa'), ('PCT', 'PCT — Pacote'), ('KIT', 'KIT — Kit'), ('CJ', 'CJ — Conjunto'), ('M', 'M — Metro'))`
  - Substituição do `<input type="text">` por `<select class="form-select form-control-premium">`.
  - Normalização no `clean()` para mapear sinônimos automaticamente e rejeitar entradas adulteradas.

#### 4. Reformulação Visual de Tamanhos e Variantes do EPI
- No `templates/ppe/product_form.html`:
  - Decisão obrigatória em botões: *"Este EPI possui variação de tamanho?"*
    - Opção 1: `Não — Tamanho único` (cria variante canônica `'U'`).
    - Opção 2: `Sim — Possui tamanhos` (revela interface de múltipla seleção).
  - Seleção por chips/botões organizados em grupos do catálogo canônico:
    - Letras: `PP, P, M, G, GG, XG, XXG`
    - Luvas: `6, 7, 8, 9, 10, 11, 12`
    - Calçados: `34 a 46`
  - Orientação visual clara: *"Cadastre o EPI uma única vez e selecione aqui todos os tamanhos comercializados para este mesmo C.A."*
  - Resumo em tempo real: *"Tamanhos selecionados: P, M e G"*, com chips removíveis individualmente e ordenação lógica.
  - Backend valida que "Único" não pode coexistir com outros tamanhos e exige pelo menos um tamanho quando marcado "Possui tamanhos".

#### 5. Impedimento de Duplicação de EPI por C.A.
- Na consulta AJAX do C.A. (`/ppe/ca/consultar_ajax/`):
  - Verifica se já existe um `Product` cadastrado com o C.A. informado (excluindo a própria instância na edição).
  - Se já existir, interrompe o formulário com feedback visual destacado:
    *"Este C.A. já está cadastrado no sistema. EPI: [Nome]. Tamanhos atuais: [P, M, G]. Para incluir outro tamanho, edite o cadastro existente. Não crie um novo EPI para cada tamanho."*
  - Fornece botão direto *"Abrir cadastro existente"* (`/ppe/<id>/edit/`) e oculta campos de criação duplicada.
- No Backend:
  - Normalização no `clean()` e `save()` de `Product`.
  - Adição de `UniqueConstraint(fields=['ca_numero'], condition=models.Q(ca_numero__isnull=False) & ~models.Q(ca_numero=''), name='unique_product_ca_numero_not_empty')`.

#### 6. Proteção Acessível contra Envio Acidental por Enter
- Listener de teclado no formulário de EPI:
  - Enter em campos de texto comuns tem o evento cancelado (`e.preventDefault()`).
  - Enter no campo `id_ca_numero` dispara a consulta do C.A. sem submeter.
  - Enter em `textarea` insere quebra de linha.
  - Enter dentro dos seletores pesquisáveis seleciona a opção.
  - Enter ou Espaço com o foco no botão "Salvar" submete o formulário com total acessibilidade para teclado e leitores de tela.

---

### 6.3 Critérios de Aceite — Rodada 2

- **AC01**: O relatório de consumo `/reports/ppe-consumption-cost/` ativa somente "Relatórios" no menu lateral.
- **AC02**: A tela de notificações `/notifications/` ativa somente "Alertas" no menu lateral.
- **AC03**: Nenhuma rota do sistema deixa dois itens principais do menu ativos simultaneamente.
- **AC04**: Rotas filhas (ex: `/ppe/add/`, `/employees/add/`, `/reports/stock-position/`) ativam corretamente o item principal correspondente.
- **AC05**: A matriz de EPI possui ação clara e explícita para "Salvar como elaboração".
- **AC06**: A matriz de EPI possui ação clara e explícita para "Salvar e ativar".
- **AC07**: O botão "Ativar" na listagem de matrizes executa a transição para Ativa.
- **AC08**: A ativação da matriz é realizada exclusivamente por POST e possui proteção CSRF.
- **AC09**: Matriz inválida ou sem EPIs não pode ser ativada, exibindo erro específico.
- **AC10**: Matriz ativada exibe visualmente o badge "Ativa" e mensagem de sucesso.
- **AC11**: A edição de matriz ativa salva alterações mantendo o status ativa, sem voltar para elaboração.
- **AC12**: O campo Unidade de Medida no cadastro de EPI não é mais texto livre.
- **AC13**: Somente unidades canônicas pré-definidas podem ser salvas no cadastro de EPI.
- **AC14**: Entradas de sinônimos como `UND`, `und`, `unid`, `UN` resultam no valor canônico `UND`.
- **AC15**: O campo de texto livre separado por vírgulas foi completamente removido da interface.
- **AC16**: O usuário é obrigado a escolher entre "Tamanho único" e "Possui tamanhos".
- **AC17**: Os tamanhos são selecionados visualmente através de botões/chips organizados.
- **AC18**: O tamanho único não pode coexistir com outros tamanhos no mesmo EPI.
- **AC19**: Variantes equivalentes em caixa (ex: `G` e `g`) não podem coexistir.
- **AC20**: Ao digitar um C.A. já existente em novo cadastro, o formulário bloqueia a criação de um segundo EPI.
- **AC21**: O sistema direciona o usuário ao cadastro existente do C.A. para inclusão de novos tamanhos.
- **AC22**: Um único EPI pode possuir os tamanhos P, M e G simultaneamente.
- **AC23**: O usuário não precisa memorizar ou ler instruções sobre sintaxe de vírgulas.
- **AC24**: Pressionar Enter em campos comuns do formulário de EPI não salva o cadastro.
- **AC25**: A tecla Enter continua funcional em textareas e em seletores pesquisáveis.
- **AC26**: O salvamento através do botão Salvar continua 100% funcional e acessível via teclado.
- **AC27**: Variantes com histórico de movimentação ou estoque não podem ser excluídas indevidamente.
- **AC28**: A entrada de compra (`/inventory/nfs/add/`) continua restrita a variantes cadastradas.
- **AC29**: Todos os novos elementos e botões respeitam o design system em tema escuro.
- **AC30**: O card de dados complementares e a seleção de tamanhos são totalmente responsivos em mobile.
- **AC31**: `manage.py check` finaliza com 0 erros.
- **AC32**: `manage.py makemigrations --check` confirma ausência de migrações não documentadas.

---

### 6.4 Plano de Testes — Rodada 2

1. **Testes Automatizados (`ppe/tests_spec_2026_017_round2.py`)**:
   - Menu lateral: asserções de que `/reports/ppe-consumption-cost/`, `/reports/ppe-deliveries/`, `/notifications/`, `/ppe/add/`, `/ppe/matrices/` ativam exatamente um item com `aria-current="page"`.
   - Matriz: teste de salvar rascunho (`status='EM_ELABORACAO'`), salvar e ativar (`status='ATIVA'`), ativação vazia bloqueada, ativação via listagem com POST.
   - Unidade de Medida: validação de choices, rejeição de texto arbitrário, normalização de sinônimos.
   - Variantes: tamanho único cria `'U'`, proibição de `'U'` com outros tamanhos, seleção múltipla (P, M, G), catálogo canônico, ordenação.
   - C.A.: rejeição de C.A. duplicado no model e form, comparação normalizada por dígitos, ajax retornando `already_registered`.
   - Regressão: recebimento de NF em `/inventory/nfs/add/` e filtros de matriz.

2. **Testes Manuais do QA**:
   - Cenários A a K conforme descritos no roteiro de testes operacionais da demanda.
