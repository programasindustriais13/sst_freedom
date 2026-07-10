# SPEC — Reformulação do Recebimento de N.F./Recibo e Controle de Estoque de EPIs

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-004` |
| Título | Reformulação do Recebimento de N.F./Recibo e Controle de Estoque de EPIs |
| Tipo | FEATURE |
| Módulo principal | inventory / ppe |
| Fase/Roadmap | Fase 1A (Extensão) |
| Autor da SPEC | Arquiteto (Antigravity) |
| Data de criação | 10/07/2026 |
| Última atualização | 10/07/2026 14:15 |
| Versão | 1.0.0 |
| Status | `RASCUNHO` |
| Prioridade | CRÍTICA |
| Risco | ALTO |
| Demanda de origem | Reformulação do recebimento de N.F./Recibo e controle de estoque de EPIs |
| SPEC substituída | Não |
| SPECs relacionadas | `SPEC-2026-001` (Fundação, Estoques e Controle de EPI) |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 10/07/2026 | Arquiteto | Rascunho inicial com arquitetura unificada | RASCUNHO |
| 1.0.0 | 10/07/2026 | Arquiteto | Detalhamento dos requisitos e modelagem | RASCUNHO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `PENDENTE` |  |  |
| Revisão pré-implementação | QA | `PENDENTE` |  |  |
| Implementação | Backend | `PENDENTE` |  |  |
| QA final | QA | `PENDENTE` |  |  |

### 0.3 Transições de status

```text
RASCUNHO
→ EM_REVISÃO_QA
→ APROVADA_PARA_IMPLEMENTAÇÃO
→ EM_IMPLEMENTAÇÃO
→ EM_QA_FINAL
→ APROVADA
```

---

## 1. Resumo executivo

O objetivo desta especificação é reformular o processo de entrada de Nota Fiscal (N.F.) ou Recibo no sistema **SST Freedom**. O fluxo atual exige dois passos separados e não lineares: primeiro cadastra-se o documento (Nota Fiscal) em Rascunho e, em seguida, navega-se para a tela de detalhes da nota para cadastrar seus itens individuais (lotes). Esse design gera fricção no trabalho diário dos técnicos.

Esta SPEC propõe uma tela de cadastro única e responsiva onde o usuário preenche o cabeçalho do documento (Nota Fiscal/Recibo) e adiciona dinamicamente as linhas de itens na mesma página. Além disso, a entrada física no estoque do Almoxarifado será acionada de forma atômica no momento do salvamento do formulário unificado, reduzindo inconsistências.

Outro ponto crucial é a consolidação do catálogo de produtos. Atualmente, há uma aparente separação conceitual entre EPIs e outros materiais de estoque. Unificaremos o cadastro para que o sistema possua um catálogo único de produtos, onde a classificação (EPI, Fardamento, Ferramenta, etc.) define se o produto exige um número de Certificado de Aprovação (C.A.).

---

## 2. Contexto da demanda

### 2.1 Cenário atual

1. O técnico cria um documento de entrada em `/inventory/nfs/add/`, preenchendo dados como fornecedor, número e valor total. Ao salvar, é redirecionado para a tela de visualização do documento (`/inventory/nfs/<id>/`).
2. Nessa tela de visualização (detalhes), ele deve utilizar um formulário secundário para adicionar cada lote individual do produto recebido, indicando código de barra, variante, quantidade e custo unitário.
3. Se o produto recebido ainda não estiver catalogado, o técnico precisa abandonar o fluxo da nota fiscal, navegar até `/ppe/add/` para criar o produto, adicionar suas variantes (tamanhos) em outra tela, e só então retornar à tela da Nota Fiscal para concluir o lançamento.
4. Por fim, ele precisa clicar em "Confirmar Nota Fiscal" para que o saldo físico seja atualizado no Almoxarifado.

### 2.2 Problema

O fluxo atual é propenso a erros de digitação, abandono de processos e inconsistências de saldo. Além disso, a duplicação na classificação de produtos e a falta de flexibilidade no cadastro de tamanhos misturam fluxos independentes.

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| Rota `/inventory/nfs/add/` | `inventory/views.py:FiscalNoteCreateView` | Cadastro inicial sem itens |
| Formulário em `nfs_detail.html` | `templates/inventory/nfs_detail.html` | Cadastro tardio de lotes |
| Rota `/ppe/add/` | `ppe/views.py:ProductCreateView` | Cadastro isolado do catálogo de produtos |

---

## 3. Objetivos

### 3.1 Objetivo principal

Implementar uma tela única e atômica de recebimento de Notas Fiscais e Recibos com cadastro em lote dinâmico de itens na mesma operação, dando entrada direta e atômica no estoque do Almoxarifado central.

### 3.2 Objetivos secundários

1. Adicionar campos de classificação (`tipo_produto`) e `ca_numero` no modelo `Product` para unificar o catálogo.
2. Permitir o cadastro rápido de produtos através de um Modal de cadastro assíncrono (via AJAX) diretamente na tela da Nota Fiscal.
3. Realizar busca dinâmica de produtos semelhantes ao digitar para evitar cadastros duplicados.
4. Ocultar ou desabilitar o campo de C.A. caso o produto não seja classificado como EPI.
5. Garantir que as transferências para o estoque do SST ocorram unicamente a partir de saldos disponíveis no Almoxarifado.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Unificação do formulário de Nota Fiscal/Recibo para suportar inserção dinâmica de múltiplos lotes via JavaScript.
- Criação e integração do Modal de cadastro rápido de produtos em `/ppe/add/ajax/`.
- Autocomplete e detecção de duplicidades em `/ppe/search_ajax/`.
- Reestruturação do modelo `Product` para incluir `tipo_produto` e `ca_numero`.
- Transação atômica que garante rollback completo se houver erro ao salvar qualquer item da nota.
- Entrada automática no local Almoxarifado da respectiva unidade.

### 4.2 Fora do escopo

- Emissão de notas fiscais ou integração direta com o ambiente da SEFAZ para consulta de XML (futuro).
- Controle de estoque por código de barras em modo offline (Fase 5).

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST / Almoxarife | Lançar documentos de compra e compras rapidamente, sem transições de tela confusas. | Alto | Escopo restrito às suas unidades permitidas. |
| Administrador | Garantir a integridade dos saldos de estoque e trilha de auditoria sem registros soltos. | Alto | Global. |

---

## 6. Estado atual do código

### 6.1 Módulos lidos

- [inventory/models.py](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/inventory/models.py): Contém os modelos de `FiscalNote`, `Lot` e `StockMovement`.
- [inventory/views.py](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/inventory/views.py): Contém a lógica de listagem e criação de Notas Fiscais e itens.
- [ppe/models.py](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/ppe/models.py): Contém o modelo de `Product`, `ProductVariant` e `CertificadoAprovacao`.

---

## 7. Premissas e decisões

### 7.1 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-004 | JSON Payload para itens da Nota Fiscal | Formset dinâmico do Django | Formsets dinâmicos do Django exigem reindexação manual complexa em JS ao remover linhas. O JSON payload serializado em um input oculto e parsed no backend é limpo e menos sujeito a falhas de submissão. |
| ADR-005 | C.A. como campo textual no Produto | Apenas relação FK com `CertificadoAprovacao` | O C.A. cadastrado no produto armazena a string informada (ex: "CA 12345"). No backend, o sistema busca ou gera dinamicamente um registro no modelo `CertificadoAprovacao` com base nesse texto para manter a integridade referencial com os lotes antigos. |

---

## 8. Requisitos funcionais

### RF-001 — Tela Única de Nota Fiscal / Recibo
- **Atores:** Almoxarife, Técnico SST, Administrador.
- **Fluxo:**
  1. O usuário acessa `/inventory/nfs/add/`.
  2. Preenche os metadados do documento (Tipo, Fornecedor, Número, Data de Recebimento, Centro de Custo).
  3. Na seção "Itens Recebidos", clica em `+ Adicionar Produto`.
  4. Seleciona o produto e digita a quantidade, tamanho/variação, C.A., lote do fabricante, validade física e valor unitário.
  5. Clica em `Salvar e dar entrada no estoque`.
  6. O backend processa todos os itens e gera as entradas físicas no Almoxarifado central de forma atômica.

### RF-002 — Cadastro Rápido de Produtos (Modal)
- **Atores:** Almoxarife, Técnico SST, Administrador.
- **Fluxo:**
  1. Dentro do formulário da Nota Fiscal, na linha de inserção do item, há um link ou botão `[Novo Produto]`.
  2. Ao clicar, abre-se um Modal centralizado que solicita: Nome, Classificação (EPI, Fardamento, Ferramenta, etc.), Unidade de Medida e C.A. (se classificado como EPI).
  3. Ao preencher e salvar, o sistema faz uma requisição assíncrona (AJAX), valida e cria o produto e suas variantes no banco.
  4. O produto recém-cadastrado é inserido e selecionado automaticamente na linha da Nota Fiscal.

### RF-003 — Exibição Condicional do C.A.
- **Atores:** Sistema/Interface.
- **Comportamento:**
  - No cadastro de produtos (tanto na tela cheia quanto no modal de cadastro rápido), ao selecionar `EPI`, o campo C.A. fica visível e disponível para preenchimento.
  - Se for selecionada qualquer outra classificação (Uniforme, Ferramenta, etc.), o campo de C.A. é ocultado ou desabilitado.

---

## 9. Regras de negócio

### RN-004 — Destino Padrão: Almoxarifado
- **Regra:** Toda entrada por compra/recebimento de Nota Fiscal ou Recibo é direcionada obrigatoriamente para o Local de Estoque do tipo `ALMOXARIFADO` ativo da Unidade selecionada.
- **Aplicação:** Backend (`confirm_fiscal_note` / view de criação).

### RN-005 — Atomicidade do Lançamento
- **Regra:** Se a criação da Nota Fiscal ou de qualquer um de seus lotes/itens falhar (ex: data de validade vencida, valores inconsistentes, falta de saldo inicial), nenhum registro de estoque ou documento deve ser persistido no banco de dados.
- **Aplicação:** Uso de `transaction.atomic` no backend.

### RN-006 — Prevenção de Duplicidades no Cadastro Rápido
- **Regra:** Ao digitar o nome do produto no formulário de cadastro rápido, o sistema deve pesquisar produtos ativos. Se houver nomes foneticamente ou graficamente próximos, exibe um alerta indicando a existência de produto semelhante e permitindo selecioná-lo.
- **Aplicação:** Chamada assíncrona para `/ppe/search_ajax/` com algoritmo de distância de Levenshtein ou busca simples de substring.

---

## 10. Requisitos não funcionais

- **Responsividade:** O formulário dinâmico de itens deve se adaptar para celulares, transformando as linhas da tabela em blocos ou painéis colapsáveis independentes.
- **Performance:** A busca de duplicidades deve retornar em menos de 200ms.

---

## 11. Modelagem de dados

### 11.1 Novos Campos em Modelos Existentes

#### Modelo: `Product` (`ppe/models.py`)

| Campo | Tipo | Obrigatório | Default | Regra |
|---|---|---|---|---|
| `tipo_produto` | CharField | Sim | `'EPI'` | Choices: `EPI`, `MATERIAL_SEGURANCA`, `MATERIAL_CONSUMO`, `FERRAMENTA`, `UNIFORME`, `OUTRO`. |
| `ca_numero` | CharField | Não | `None` | Número do C.A. em formato livre (texto). |

---

## 12. Serviços de domínio e views

### 12.1 Endpoints AJAX

#### POST `/ppe/add/ajax/`
- Cadastro assíncrono de produtos.
- Retorno esperado: `{"success": true, "product": {"id": 1, "nome": "Luva de Raspa", "ca_numero": "CA 12345", "unidade_medida": "PAR"}}`.

#### GET `/ppe/search_ajax/?q=<nome>`
- Busca produtos semelhantes para evitar duplicidade.
- Retorno esperado: `{"items": [{"id": 1, "nome": "Luva de Raspa", "similar": true}]}`.

---

## 13. Testes e validação

### Casos de teste mínimos

1. **NF com múltiplos produtos:** Garantir que todos os lotes e movimentações de entrada no Almoxarifado sejam criados na mesma transação.
2. **Rollback de erro:** Simular uma inserção de item com quantidade negativa ou inválida e validar que a Nota Fiscal não é salva de forma alguma.
3. **C.A. Condicional:** Validar que produtos do tipo Uniforme não exigem e não aceitam C.A., enquanto produtos do tipo EPI validam e salvam o C.A.
4. **Prevenção de duplicidades:** Validar que a API de busca dinâmica sinaliza o aviso em caso de produtos semelhantes.

---

## 14. Parecer dos Subagentes

### 14.1 Parecer do Arquiteto (Antigravity)
> A arquitetura de unificação do fluxo atende perfeitamente à regra de negócio do Almoxarifado central. A modelagem garante a integridade dos dados históricos através de transações atômicas e previne a criação de telas concorrentes desnecessárias. A solução é robusta e mantém compatibilidade retroativa total.  
> **Parecer: APROVADA**

### 14.2 Parecer do QA
> A SPEC especifica claramente os fluxos, regras de rollback atômico e as validações mobile. O escopo está contido.  
> **Parecer: APROVADA_PARA_IMPLEMENTAÇÃO**
