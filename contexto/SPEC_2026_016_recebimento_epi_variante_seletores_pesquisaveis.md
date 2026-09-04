# SPEC_2026_016 — Recebimento de EPI por Variante Cadastrada e Seletores Pesquisáveis de EPI e Colaborador

> Esta SPEC segue estritamente o modelo de `contexto/SPEC_TEMPLATE.md` e as regras permanentes de `contexto/constitution.md`.  
> Nenhuma implementação pode ser iniciada antes da aprovação formal (`APROVADA_PARA_IMPLEMENTAÇÃO`).

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-016` |
| Título | Recebimento de EPI por variante previamente cadastrada e implantação de seletores pesquisáveis de EPI e colaborador em todo o sistema |
| Tipo | `FEATURE / FIX / REFACTOR / SECURITY` |
| Módulo principal | `inventory` e `ppe` (com impactos em `employees`, `core` e templates gerais) |
| Fase/Roadmap | `Fase 1 — Gestão de EPIs e Estoque / Fase 1b — Experiência Operacional` |
| Autor da SPEC | `Arquiteto` |
| Data de criação | `04/09/2026` |
| Última atualização | `04/09/2026 09:30` |
| Versão | `1.0.0` |
| Status | `APROVADA_PARA_IMPLEMENTAÇÃO` |
| Prioridade | `CRÍTICA` |
| Risco | `MÉDIO` |
| Demanda de origem | `Recebimento de compra criando variantes duplicadas com caixa baixa (ex: "g" para "G"), ausência de vínculo obrigatório à variante cadastrada e necessidade de seletores pesquisáveis e paginados para Colaboradores e EPIs em todo o sistema.` |
| SPEC substituída | `Não` |
| SPECs relacionadas | `contexto/SPEC_2026_009_simplificacao_estoque_grade.md`, `contexto/SPEC_2026_013_centralizacao_tamanhos_variantes_epi.md`, `contexto/SPEC_2026_014_auditoria_consolidacao_segura_ca_epi.md`, `contexto/SPEC_2026_015_ajustes_colaborador_matriz_epi_setor_consumo_custo_anexo_nf_estoque_minimo.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 04/09/2026 | Arquiteto | Investigação, causa-raiz, arquitetura de dados e componente de busca | RASCUNHO |
| 1.0.0 | 04/09/2026 | Arquiteto / QA | Definição formal de requisitos, inventário de telas, modelo TO-BE, testes e aprovação pré-implementação | APROVADA_PARA_IMPLEMENTAÇÃO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADO` | 04/09/2026 | Mapeamento completo dos models, livro-razão, causa-raiz, normalização de variantes e arquitetura de componentes de busca. |
| Revisão pré-implementação | QA | `APROVADO` | 04/09/2026 | Critérios de aceite AC01 a AC24 validados, matriz de testes e migração de limpeza planejadas. |
| Implementação | Backend | `PENDENTE` |  | Aguardando aprovação do usuário para início da execução. |
| QA final | QA | `PENDENTE` |  |  |

### 0.3 Transições de status

```text
RASCUNHO
→ EM_REVISÃO_QA
→ APROVADA_PARA_IMPLEMENTAÇÃO (Atual)
→ EM_IMPLEMENTAÇÃO
→ EM_QA_FINAL
→ APROVADA
```

---

## 1. Resumo executivo

O SESMT cadastrou um EPI (ex.: "LUVA PARA PROTEÇÃO CONTRA AGENTES TÉRMICOS E MECÂNICOS", C.A. 39670) com as variantes P, M e G. Posteriormente, o almoxarifado recebeu remessa desse EPI no tamanho G. Na tela de entrada de compra / Nota Fiscal (`/inventory/nfs/add/`), o campo "Tamanho" era um `<input type="text">` de digitação livre. O operador digitou "g" em minúsculo. Em vez de utilizar a variante canônica "G", o backend executou `ProductVariant.objects.get_or_create(...)` com base no texto digitado, criando uma variante espúria "g" e poluindo a grade técnica do EPI, que passou a exibir `P, M, G, g`.

A entrada de uma compra não pode criar variantes técnicas de EPI. O cadastro de variantes pertence exclusivamente ao catálogo mantido pelo SESMT. O recebimento deve apenas permitir a seleção de uma variante pré-existente e ativa.

Além disso, os campos de seleção de EPI e Colaborador em todo o sistema utilizam `<select>` estáticos carregados integralmente no HTML. Com o aumento da base para centenas ou milhares de colaboradores e produtos, essa abordagem torna as páginas lentas e a usabilidade inviável.

Esta SPEC resolve ambos os problemas:
1. Bloqueia a criação de variantes no fluxo de recebimento de compras, tornando o campo Tamanho um dropdown dependente do EPI selecionado, estritamente restrito às variantes cadastradas, validado no backend com rejeição transacional a POSTs adulterados.
2. Implementa uma normalização robusta e `UniqueConstraint` persistente no banco de dados para `(product, tamanho_normalizado)`, impedindo duplicidades equivalentes como "G", "g", " G ", " g ".
3. Executa migração de dados idempotente para consolidar a variante "g" na variante canônica "G", reapontando lotes e movimentações de estoque sem duplicidade de saldo, e expurgando a duplicidade.
4. Constrói uma arquitetura de seletores pesquisáveis remotos reutilizável em Vanilla JS com suporte a paginação, debounce, acessibilidade via teclado, tema escuro e compatibilidade com formsets e linhas dinâmicas, implantando a busca em todas as telas inventariadas do sistema que selecionam EPI e Colaborador.

---

## 2. Contexto da demanda e causa-raiz

### 2.1 Cenário atual

- O catálogo de EPIs é administrado pelo SESMT (`Product` e `ProductVariant`).
- A tela de recebimento (`FiscalNoteCreateView` / `templates/inventory/nfs_form.html`) renderiza dinamicamente linhas de produtos recebidos via JavaScript (`addItemRow()`).
- Cada linha continha:
  - `<select id="prod_select_${index}">` pré-carregado com todo o catálogo de produtos em JSON inline.
  - `<input type="text" id="prod_tamanho_${index}" value="U">` com digitação livre.
  - `<input type="text" id="prod_unidade_${index}">` e `<input type="text" id="prod_ca_${index}">` livres/editáveis.
- Na submissão, os dados são agrupados em um JSON string (`items_json`).
- O service `create_and_confirm_fiscal_note` (`inventory/services.py`, L.248-252) executava:
  ```python
  variant, _ = ProductVariant.objects.get_or_create(
      product=product,
      tamanho=tamanho,
      defaults={'ativo': True, 'estoque_minimo': 0}
  )
  ```
- O modelo `ProductVariant` possui apenas `unique_together = ('product', 'tamanho')`. Diferenças de caixa ("G" vs "g") ou espaços geravam registros distintos no banco de dados.

### 2.2 Evidências encontradas

| Evidência | Origem | Conclusão |
|---|---|---|
| Campo de tamanho como input texto livre | `templates/inventory/nfs_form.html#L424` | Permite digitação arbitrária ("g", " G ", "gg"). |
| Criação automática de variante no service | `inventory/services.py#L248-L252` | `get_or_create` cria variantes em tempo de recebimento. |
| Duplicidade real no banco | `db.sqlite3` (`ProductVariant` id 32="G", id 33="g") | Variante "g" (id 33) foi gerada pela NF 13 com Lot 13 e StockMovement 32. |
| Ausência de constraint de caixa no banco | `ppe/models.py#ProductVariant.Meta` | Apenas `unique_together = ('product', 'tamanho')`. |
| Selects estáticos de Colaborador e EPI | `templates/ppe/delivery_form.html`, `templates/ppe/sector_matrix_form.html`, relatórios | Renderizam querysets completos sem paginação remota. |

### 2.3 Causa raiz confirmada

1. Interface permitia texto livre no recebimento de estoque onde deveria haver seleção dependente e controlada.
2. Service de estoque utilizava `get_or_create` de variante com base na entrada do usuário em vez de exigir e validar o ID de uma variante existente.
3. Ausência de normalização persistente no modelo `ProductVariant` (ex.: `tamanho_normalizado` e `UniqueConstraint`).
4. Inexistência de um componente padronizado de busca remota paginada para relacionamentos de `Employee` e `Product`.

---

## 3. Objetivos

### 3.1 Objetivo principal

Garantir que a entrada de compras referencie exclusivamente variantes cadastradas pelo SESMT, consolidar a base existente sem duplicidades de tamanho ("G" vs "g"), aplicar unicidade persistente no banco de dados e implantar seletores pesquisáveis paginados e padronizados para EPIs e Colaboradores em todas as telas do sistema.

### 3.2 Indicadores de sucesso

| Indicador | Situação atual | Meta | Como medir |
|---|---:|---:|---|
| Variantes espúrias na Luva CA 39670 | 4 (`P`, `M`, `G`, `g`) | 3 (`P`, `M`, `G`) | Consulta ao banco pós-migração |
| Criação de variante na entrada de NF | Permitida via texto | Zero (bloqueada) | Teste unitário e teste de POST |
| Constraint no banco para caixa/espaço | Inexistente | Ativa no banco | Tentativa de insert de "g" após "G" |
| Carregamento de opções de Colaborador na tela | 100% no HTML inicial | Paginado via AJAX (20/pág) | Inspeção de rede / DOM |
| Preservação de escopo por Unidade | Variável conforme template | 100% garantido no backend | Testes de acesso indevido |

---

## 4. Escopo

### 4.1 Dentro do escopo

1. **Refatoração da Entrada de NF (`inventory`)**:
   - Remoção de input livre de tamanho em `templates/inventory/nfs_form.html`.
   - Transformação em select dependente carregado via endpoint `/ppe/api/variants/?product_id=<id>`.
   - Seleção automática quando houver variante única.
   - Bloqueio de submissão e mensagem orientativa quando não houver variantes cadastradas.
   - Campos Unidade e C.A. tornados somente leitura e derivados exclusivamente do EPI.
   - Refatoração de `inventory/services.py#create_and_confirm_fiscal_note` para validar `variant_id`, rejeitar POSTs adulterados com erro específico e nunca chamar `get_or_create` de variante.
   - Garantia transacional completa (`@transaction.atomic`).

2. **Normalização e Unicidade de Variantes (`ppe`)**:
   - Criação da função canônica de normalização de variantes `canonical_size_key(tamanho)` e `normalize_size_label(tamanho)`.
   - Adição do campo `tamanho_normalizado` em `ProductVariant`.
   - Adição de `UniqueConstraint(fields=['product', 'tamanho_normalizado'], name='unique_product_variant_normalized')`.
   - Atualização do método `clean()` e `save()` de `ProductVariant`.
   - Atualização do cadastro de EPI (`ProductForm` / `sync_product_variants`) para deduplicar entradas separadas por vírgula (ex: "P, M, G, g, G" -> "P, M, G").

3. **Migração de Dados e Limpeza**:
   - Migração para consolidar a variante "g" (ID 33) na variante canônica "G" (ID 32) do EPI CA 39670.
   - Reapontamento seguro de `Lot` (ID 13) e `StockMovement` (ID 32) para a variante ID 32.
   - Verificação e garantia de que o saldo em `StockMovement` não é duplicado.
   - Exclusão da variante duplicada ID 33.
   - Preenchimento de `tamanho_normalizado` para todas as variantes do banco.
   - Aplicação da `UniqueConstraint`.

4. **Componente Centralizado de Select Pesquisável**:
   - Criação de `static/js/searchable_select.js` e `static/css/searchable_select.css`.
   - Suporte a busca remota, debounce (300ms), paginação, mensagens em português, navegação por teclado, foco visível e integração ao tema escuro.
   - Suporte a formulários simples, filtros GET, inline formsets e linhas dinâmicas.
   - Endpoints seguros:
     - `/ppe/api/search/` (busca paginada de EPIs por nome, C.A., fabricante, categoria).
     - `/employees/api/search/` (busca paginada de colaboradores por nome, CPF com/sem pontuação, matrícula, setor, respeitando unidade/empresa).
     - `/ppe/api/variants/` (retorno de variantes ativas por `product_id`).

5. **Aplicação do Componente no Inventário de Telas**:
   - Todas as telas identificadas que selecionam EPI ou Colaborador.

### 4.2 Fora do escopo

- Redesenho do módulo contábil de estoque ou alteração na fórmula de cálculo de saldo (livro-razão em `StockMovement` permanece intocado).
- Alteração das regras de preços, frete ou descontos na NF.
- Permitir ao operador de almoxarifado cadastrar variantes durante a Nota Fiscal.
- Transformar todos os ForeignKeys do sistema em autocomplete (somente EPIs e Colaboradores).
- Reset do banco de dados.

---

## 5. Inventário Completo de Telas e Campos (EPI e Colaborador)

| Rota / Tela | View / Form Responsável | Campo / Elemento | Entidade / Queryset | Regra de Escopo / Permissão | Tipo de Uso | Como recebe a busca |
|---|---|---|---|---|---|---|
| `/inventory/nfs/add/` (Entrada de NF) | `FiscalNoteCreateView` / `nfs_form.html` | `prod_select_${index}` (EPI) | `Product` (ativos) | Almoxarife / Admin | Tabela dinâmica | Searchable Select remoto com debounce |
| `/inventory/nfs/add/` (Entrada de NF) | `FiscalNoteCreateView` / `nfs_form.html` | `prod_tamanho_${index}` (Tamanho) | `ProductVariant` do EPI selecionado | Almoxarife / Admin | Dropdown dependente | `<select>` dependente via `/ppe/api/variants/` |
| `/inventory/nfs/<pk>/lots/add/` (Adicionar Lote) | `LotCreateView` / `nfs_detail.html` | `product_variant` | `ProductVariant` ativos | Almoxarife / Admin | Modal / Form simples | Searchable Select com busca de EPI/variante |
| `/ppe/deliveries/add/` (Entrega de EPI) | `PPEDeliveryCreateView` / `PPEDeliveryForm` | `employee` | `Employee` (ativos, da unidade) | Técnico SST / Admin | Form padrão | Searchable Select remoto (`/employees/api/search/`) |
| `/ppe/deliveries/add/` (Entrega de EPI) | `PPEDeliveryCreateView` / `PPEDeliveryForm` | `lot` (EPI disponível no estoque SST) | `Lot` com saldo > 0 no SST da unidade | Técnico SST / Admin | Form padrão | Searchable Select com texto descritivo e saldo |
| `/ppe/matrices/add/` e `/edit/` (Matriz Individual) | `PPEMatrixCreateView` / `PPEMatrixForm` | `product` e `variant` | `Product` (EPIs ativos) e `ProductVariant` | Técnico SST / Admin | Form padrão | Searchable Select de EPI + Select dependente de Variante |
| `/ppe/sectors/<id>/matrix/edit/` (Matriz Setor) | `sector_matrix_edit_view` / `PPEMatrixSectorFormSet` | `form-*-product` | `Product` (tipo EPI, ativos) | Técnico SST / Admin | Inline Formset dinâmico | Searchable Select inicializado por linha com deleção segura |
| `/ppe/deliveries/` (Listagem de Entregas) | `DeliveryListView` | `product` (filtro GET) | `Product` (ativos) | Técnico SST / Admin | Filtro GET | Searchable Select de EPI com envio no form GET |
| `/ppe/deliveries/` (Listagem de Entregas) | `DeliveryListView` | `q` (filtro colaborador) | Texto livre (nome, CPF, matrícula) | Técnico SST / Admin | Filtro GET | Mantido input ou enriquecido com Searchable Select |
| `/reports/ppe-deliveries/` (Relatório de Entregas) | `ReportPPEDeliveriesView` | `product` (filtro GET) | `Product` (ativos) | Todos autenticados | Filtro GET | Searchable Select de EPI |
| `/reports/ppe-consumption-cost/` (Consumo e Custo) | `ReportPPEConsumptionCostView` | `product` (filtro GET) | `Product` (ativos) | Todos autenticados | Filtro GET | Searchable Select de EPI |
| `/reports/stock-position/` (Posição de Estoque) | `ReportStockPositionView` | `product` (filtro GET) | `Product` (ativos) | Todos autenticados | Filtro GET | Searchable Select de EPI |
| `/reports/stock-movements/` (Movimentações) | `ReportStockMovementsView` | `product` (filtro GET) | `Product` (ativos) | Todos autenticados | Filtro GET | Searchable Select de EPI |

---

## 6. Fluxos AS-IS e TO-BE

### 6.1 Fluxo de Recebimento de Estoque (NF)

#### AS-IS (Incorreto):
```text
Almoxarife abre /inventory/nfs/add/
→ Clica em "Adicionar Produto"
→ Seleciona EPI em select estático
→ Digita "g" manualmente no campo Tamanho
→ Informa Quantidade e Valor
→ Submete o formulário
→ Backend executa ProductVariant.objects.get_or_create(product=EPI, tamanho="g")
→ Nova variante "g" é criada no banco (ID 33) duplicando a variante "G" (ID 32)
→ Grade do EPI no SESMT é conspurcada com "P, M, G, g"
```

#### TO-BE (Correto e Seguro):
```text
Almoxarife abre /inventory/nfs/add/
→ Clica em "Adicionar Produto"
→ Digita nome ou CA no Seletor Pesquisável de EPI
→ Seletor busca assincronamente com debounce (/ppe/api/search/?q=...)
→ Almoxarife seleciona o EPI desejado
→ Campo Unidade e C.A. são preenchidos automaticamente como readonly
→ Campo Tamanho/Variante é habilitado e dispara AJAX para /ppe/api/variants/?product_id=<id>
→ Carrega exclusivamente as variantes cadastradas (ex: P, M, G)
→ Se houver apenas 1 variante (ex: "U"), seleciona automaticamente
→ Almoxarife seleciona "G" (armazenando variant_id = 32)
→ Informa Quantidade e Valor
→ Ao trocar o EPI, a variante anterior é limpa imediatamente
→ Submissão envia variant_id
→ Backend valida: variant existe, pertence ao EPI informado e está ativa
→ Se adulterado, aborta transação com mensagem "O tamanho selecionado não pertence ao EPI informado."
→ Lote e StockMovement vinculados ao ID 32 (variante "G")
→ NENHUMA variante nova é criada
→ Grade do EPI permanece rigorosamente P, M, G
```

---

## 7. Modelagem de Dados e Regras de Normalização

### 7.1 Regras de Normalização Canônica de Variantes

Função centralizada em `ppe/services.py`:
```python
import re
import unicodedata

def canonical_size_key(tamanho: str) -> str:
    """
    Gera a chave normalizada persistente da variante:
    - Normalização Unicode NFKC
    - Remoção de espaços iniciais, finais e repetidos
    - Conversão para maiúsculo
    - 'ÚNICO', 'UNICO', 'U' mapeados para 'U'
    """
    if not tamanho:
        return 'U'
    norm = unicodedata.normalize('NFKC', str(tamanho)).strip().upper()
    norm = re.sub(r'\s+', ' ', norm)
    if norm in ('UNICO', 'ÚNICO', 'U'):
        return 'U'
    return norm

def normalize_size_label(tamanho: str) -> str:
    """
    Retorna o rótulo canônico amigável de exibição:
    - Siglas usuais padronizadas: PP, P, M, G, GG, XG, XXG, U
    - Numéricos preservados: 38, 39, 40
    - Textos livres limpos de espaços extras
    """
    key = canonical_size_key(tamanho)
    standard_labels = {
        'U': 'U',
        'PP': 'PP',
        'P': 'P',
        'M': 'M',
        'G': 'G',
        'GG': 'GG',
        'XG': 'XG',
        'XXG': 'XXG'
    }
    return standard_labels.get(key, key)
```

### 7.2 Alterações no Modelo `ProductVariant` (`ppe/models.py`)

- **Novo campo**: `tamanho_normalizado = models.CharField(max_length=20, db_index=True, verbose_name="Chave Normalizada do Tamanho")`
- **Constraint**:
  ```python
  models.UniqueConstraint(
      fields=['product', 'tamanho_normalizado'],
      name='unique_product_variant_normalized'
  )
  ```
- **Métodos `clean()` e `save()`**:
  ```python
  def clean(self):
      super().clean()
      self.tamanho = normalize_size_label(self.tamanho)
      self.tamanho_normalizado = canonical_size_key(self.tamanho)

  def save(self, *args, **kwargs):
      self.tamanho = normalize_size_label(self.tamanho)
      self.tamanho_normalizado = canonical_size_key(self.tamanho)
      super().save(*args, **kwargs)
  ```

---

## 8. Estratégia de Migração de Dados e Limpeza (Regra de Negócio 4)

A migração de dados deve ser determinística, segura e idempotente:
1. Adicionar coluna `tamanho_normalizado` em `ProductVariant` permitindo temporariamente null (`null=True`).
2. Executar migração de dados (`RunPython`):
   - Percorrer todos os `Product` existentes.
   - Agrupar as variantes do produto por `canonical_size_key(v.tamanho)`.
   - Para cada grupo com mais de 1 variante:
     - Identificar a variante canônica (aquela com rótulo padrão ou menor ID se idênticos). No caso da Luva CA 39670, ID 32 ("G") é canônica; ID 33 ("g") é duplicada.
     - Reapontar todas as referências da variante duplicada para a canônica:
       - `Lot.objects.filter(product_variant=dup).update(product_variant=canonical)`
       - `StockMovement.objects.filter(product_variant=dup).update(product_variant=canonical)`
       - `PPEDelivery.objects.filter(product_variant=dup).update(product_variant=canonical)`
       - `StockTransferItem.objects.filter(product_variant=dup).update(product_variant=canonical)`
       - `LocationStockMinimo.objects.filter(product_variant=dup).update(product_variant=canonical)`
       - `PPEMatrix.objects.filter(variant=dup).update(variant=canonical)`
       - `ExtraordinaryPPE.objects.filter(variant=dup).update(variant=canonical)`
     - Excluir a variante duplicada (`dup.delete()`).
   - Para todas as variantes restantes, gravar `tamanho_normalizado = canonical_size_key(v.tamanho)` e `tamanho = normalize_size_label(v.tamanho)`.
3. Aplicar migração de schema final tornando `tamanho_normalizado` não nulo (`null=False`) e inserindo a `UniqueConstraint`.

---

## 9. Arquitetura do Componente de Busca Reutilizável

### 9.1 Princípios de Design

- **Tecnologia**: Vanilla JavaScript modular (`static/js/searchable_select.js`) sem dependências pesadas, estilizado com classes do tema do sistema (`static/css/searchable_select.css`).
- **Comportamento**:
  - Transforma qualquer `<select class="searchable-select">` ou `<input type="hidden" class="searchable-select">` em uma caixa de pesquisa com dropdown flutuante estilizado.
  - Parâmetros configuráveis via `data-*` attributes:
    - `data-search-url`: URL do endpoint AJAX.
    - `data-placeholder`: Mensagem padrão.
    - `data-min-chars`: Mínimo de caracteres para buscar (default: 0).
    - `data-dependent-target`: Seletor do elemento dependente (ex.: select de variantes).
    - `data-dependent-url`: URL do endpoint que alimenta o elemento dependente.
  - Suporte a debouncing nativo (300ms).
  - Paginação remota transparente: botão "Carregar mais..." ou scroll com indicador "Carregando...".
  - Acessibilidade: navegação completa por teclado (ArrowUp, ArrowDown, Enter para selecionar, Escape para fechar, Tab para perder foco).
  - Formsets dinâmicos: expõe função global `window.initSearchableSelects(container)` para inicializar novas linhas adicionadas no formset de matriz ou na tabela da NF.
  - Preservação de valores selecionados pós-POST inválido (`data-initial-id`, `data-initial-text` ou `<option selected>`).

### 9.2 Endpoints Necessários

1. **`GET /ppe/api/search/`**:
   - Autenticado (`LoginRequiredMixin`).
   - Parâmetros: `q` (texto), `page` (default 1), `page_size` (default 20), `tipo_produto` (opcional: 'EPI').
   - Filtra produtos ativos por `nome__icontains` ou `ca_numero__icontains`.
   - Retorna lista com `id`, `text`, `nome`, `ca_numero`, `unidade_medida`, `fabricante`, `tipo_produto`.

2. **`GET /employees/api/search/`**:
   - Autenticado (`LoginRequiredMixin`).
   - Parâmetros: `q` (texto), `page` (default 1), `page_size` (default 20), `setor_id` (opcional).
   - Escopo estrito: somente colaboradores da unidade permitida ao usuário autenticado (`unit__in=user.units.all()`).
   - Busca por nome, CPF (dígitos normalizados), matrícula ou setor.
   - Retorna `id`, `text` formatado (`NOME — Setor`), `cpf_mascarado`, `matricula`. Nunca expõe CPF completo.

3. **`GET /ppe/api/variants/`**:
   - Autenticado.
   - Parâmetro: `product_id` (inteiro).
   - Valida existência do produto.
   - Retorna lista ordenada de variantes ativas: `[{"id": 30, "tamanho": "P"}, {"id": 31, "tamanho": "M"}, {"id": 32, "tamanho": "G"}]`.
   - Ordenação inteligente de tamanhos: siglas padrão primeiro ('PP', 'P', 'M', 'G', 'GG', 'XG', 'U'), seguidas de tamanhos numéricos.

---

## 10. Critérios de Aceite

| ID | Critério de Aceite |
|---|---|
| **AC01** | A tela de recebimento não possui campo de texto livre para tamanho. |
| **AC02** | Antes de escolher o EPI, o campo de variante permanece desabilitado com mensagem orientativa. |
| **AC03** | Ao escolher um EPI, aparecem somente as variantes cadastradas e ativas para ele. |
| **AC04** | Quando o EPI possui uma única variante (ex.: "U"), ela é selecionada automaticamente. |
| **AC05** | Ao trocar o EPI, a variante anteriormente selecionada é apagada imediatamente. |
| **AC06** | Uma variante pertencente a outro EPI não pode ser enviada por POST adulterado (rejeição com erro descritivo). |
| **AC07** | A entrada de compra nunca cria uma nova variante em nenhuma circunstância. |
| **AC08** | O backend não utiliza texto digitado para localizar ou criar o estoque de uma variante. |
| **AC09** | Unidade de medida e C.A. são derivados do EPI e não são confiados ao navegador. |
| **AC10** | Receber quantidade para a variante G incrementa o mesmo estoque da variante G já existente. |
| **AC11** | Depois da entrada da luva CA 39670, a grade continua contendo exclusivamente P, M e G, sem criar g. |
| **AC12** | A restrição do banco (`UniqueConstraint`) impede G e g no mesmo EPI. |
| **AC13** | O cadastro de EPI com "P, M, G, g, G" cria somente P, M e G. |
| **AC14** | EPIs podem ser pesquisados assincronamente por nome e por C.A. |
| **AC15** | Colaboradores podem ser pesquisados assincronamente por nome, matrícula, setor e CPF com/sem pontuação. |
| **AC16** | A busca é aplicada a todas as telas do inventário que selecionam EPI ou colaborador. |
| **AC17** | Os seletores continuam respeitando rigorosamente as regras de permissão e escopo de cada tela. |
| **AC18** | O componente de busca funciona perfeitamente em linhas adicionadas dinamicamente via formsets ou JS. |
| **AC19** | Valores selecionados continuam visíveis e selecionados em edição e após erros de validação. |
| **AC20** | Usuários não autenticados ou sem permissão recebem 401/403 nos endpoints de busca e variantes. |
| **AC21** | A busca não mistura nem expõe dados entre empresas ou unidades organizacionais não autorizadas. |
| **AC22** | A implementação centraliza o código JavaScript e CSS sem duplicações em templates. |
| **AC23** | O tema escuro, a navegação por teclado e as mensagens em português do Brasil funcionam em desktop e smartphone. |
| **AC24** | Nenhuma Nota Fiscal ou movimentação parcial é gravada quando uma linha de produto for inválida (transacionalidade atômica). |

---

## 11. Plano de Testes Obrigatórios

1. **Testes de Normalização e Model**:
   - `test_canonical_size_key_upper_and_spaces`: normalização de "G", "g", " G ", "  g  ".
   - `test_canonical_size_key_unique`: "U", "UNICO", "ÚNICO" resultam em "U".
   - `test_unique_constraint_variant_duplicate`: tentativa de criar "g" para EPI que já tem "G" lança `IntegrityError`.

2. **Testes de Cadastro de EPI**:
   - `test_create_product_deduplicate_comma_sizes`: input "P, M, G, g, G" cria apenas 3 variantes (P, M, G).
   - `test_create_product_empty_sizes_defaults_to_u`: cadastro sem tamanhos cria variante canônica "U".

3. **Testes dos Endpoints**:
   - `test_product_search_endpoint`: busca por nome e por C.A. com paginação.
   - `test_employee_search_endpoint`: busca por nome, CPF e matrícula, restrita à unidade do usuário.
   - `test_variants_endpoint`: retorna apenas variantes do EPI solicitado ordenadas; não cria dados; rejeita sem autenticação.

4. **Testes de Recebimento de NF e Estoque**:
   - `test_fiscal_note_valid_variant_increments_existing_stock`: entrada com variante "G" existente incrementa estoque em 1 sem criar variante nova.
   - `test_fiscal_note_rejects_foreign_variant`: tentativa de enviar variant_id de outro EPI rejeita a NF com erro específico e não cria movimentação.
   - `test_fiscal_note_rejects_missing_variant`: rejeita item sem variante.
   - `test_fiscal_note_atomic_rollback`: se uma linha falhar, nenhum lote e nenhum movimento é salvo.

5. **Testes da Migração de Dados**:
   - `test_migration_consolidates_g_into_g`: confirma que após a migração a Luva CA 39670 possui apenas P, M, G (sem "g"), o Lote 13 e o StockMovement 32 apontam para o ID 32 ("G"), e o saldo de "G" é 1.

---

## 12. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Quebra de referências de integridade ao apagar variante duplicada | Alto | A migração de dados reaponta explicitamente todas as FKs (`Lot`, `StockMovement`, `PPEDelivery`, etc.) antes da exclusão. |
| Incompatibilidade do JavaScript com formsets dinâmicos | Médio | Criar funções idempotentes de inicialização (`initSearchableSelects`) que removem clones sujos e reconectam os listeners. |
| Lentidão em querysets de busca | Médio | Usar paginação com `LIMIT 20`, índices em `nome` e `cpf` e busca por campos normalizados. |

---

## 13. Arquivos Previstos

| Arquivo | Ação | Motivo |
|---|---|---|
| `ppe/models.py` | Alterar | Adicionar `tamanho_normalizado` e `UniqueConstraint` |
| `ppe/services.py` | Alterar | Adicionar `canonical_size_key`, `normalize_size_label` e atualizar `sync_product_variants` |
| `ppe/migrations/XXXX_...` | Criar | Schema e migração de dados de consolidação |
| `inventory/services.py` | Alterar | Remover `get_or_create` de variante em `create_and_confirm_fiscal_note`, validar `variant_id` e transação |
| `inventory/views.py` | Alterar | Validar dados de entrada de itens da NF |
| `templates/inventory/nfs_form.html` | Alterar | Remover input livre de tamanho, implantar seletor pesquisável e dropdown dependente |
| `static/js/searchable_select.js` | Criar | Componente reutilizável de select pesquisável |
| `static/css/searchable_select.css` | Criar | Estilização acessível integrada ao tema escuro |
| `ppe/views.py` e `ppe/urls.py` | Alterar | Endpoints `/ppe/api/search/` e `/ppe/api/variants/` |
| `employees/views.py` e `employees/urls.py` | Alterar | Endpoint `/employees/api/search/` |
| `templates/base.html` | Alterar | Incluir assets do componente de select pesquisável |
| `templates/ppe/delivery_form.html` | Alterar | Aplicar searchable select para colaborador e lote |
| `templates/ppe/sector_matrix_form.html` | Alterar | Integrar searchable select no formset de matriz |
| `templates/reports/ppe_deliveries.html` | Alterar | Aplicar searchable select nos filtros |
| `templates/reports/ppe_consumption_cost.html` | Alterar | Aplicar searchable select nos filtros |
| `ppe/tests_spec_2026_016.py` | Criar | Suíte completa de testes automatizados da demanda |
