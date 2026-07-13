# SPEC — Simplificação do Recebimento de NF e Ajuste da Grade de Tamanhos de EPI

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-009` |
| Título | Simplificação do Recebimento de NF e Ajuste da Grade de Tamanhos de EPI |
| Tipo | FIX |
| Módulo principal | `inventory` / `ppe` |
| Fase/Roadmap | Fase 1a / Correções |
| Autor da SPEC | Arquiteto / Antigravity |
| Data de criação | 13/07/2026 |
| Última atualização | 13/07/2026 14:05 |
| Versão | 1.0.0 |
| Status | `APROVADA_PARA_IMPLEMENTAÇÃO` |
| Prioridade | ALTA |
| Risco | BAIXO |
| Demanda de origem | Simplificar o cadastro de entrada de material/NF (remover botão Novo, Lote e Validade do form) e remover a coluna "Inativo" da grade de tamanhos do EPI |
| SPEC substituída | Não |
| SPECs relacionadas | Não se aplica |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 13/07/2026 | Arquiteto / Antigravity | Especificação inicial | `APROVADA_PARA_IMPLEMENTAÇÃO` |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 13/07/2026 | Desenho de menor impacto sem migrations aprovado. |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 13/07/2026 | Testes e critérios de aceitação validados. |
| Implementação | Backend | `PENDENTE` |  |  |
| QA final | QA | `PENDENTE` |  |  |

---

## 1. Resumo executivo

Esta especificação aborda duas melhorias pontuais solicitadas para os módulos de estoque e EPIs:

1. **Simplificação da tela de entrada de material/NF (`/inventory/nfs/add/`):**
   Remoção da opção de cadastrar novos produtos a partir do form (botão `+ Novo`) e dos campos `Lote` e `Validade` nas linhas de produtos recebidos. O objetivo é tornar o processo simples e focado no almoxarife, deixando a parte técnica (como validade do CA e cadastro de EPI) para o Técnico de Segurança do Trabalho (SST).
   Para manter a integridade física do estoque e o livro-razão de movimentações, o backend gerará valores padrão/automáticos para os campos `Lote` e `Validade Física` no momento de salvar a NF.

2. **Remoção da coluna "Inativo" da grade de tamanhos de EPI (`/ppe/<id>/`):**
   Remover a coluna "Status" (Ativo/Inativo) da tabela de grade de tamanhos cadastrados para evitar confusão dos operadores, já que o estado inativo estava sendo mostrado de forma confusa. O valor padrão no banco não será modificado.

---

## 2. Contexto da demanda

### 2.1 Cenário atual

1. Na tela de adição de NF (`/inventory/nfs/add/`), o usuário pode adicionar itens em um formset dinâmico que exige Produto, Quantidade, Tamanho, Lote, CA, Validade e Custo Unitário. Existe também um botão `+ Novo` que permite ao Almoxarife cadastrar novos produtos via modal AJAX.
2. Na tela de detalhes de um EPI (`/ppe/<id>/`), o card "Grade de Tamanhos Cadastrados" exibe uma tabela contendo as colunas: Tamanho, SKU / Código, Estoque Mínimo e Status (Ativo/Inativo).

### 2.2 Problema

1. O cadastro técnico e detalhado de EPIs cabe ao Técnico SST (por CA e cadastro próprio). Exigir que o Almoxarife cadastre novos produtos e informe Lote e Validade física na entrada dificulta e atrasa o processo de recebimento.
2. A coluna de status/inativo na grade de tamanhos está confundindo os operadores, exibindo "Inativo" para itens que eles esperam estar ativos ou cuja informação é irrelevante naquela grade específica.

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| Botão "+ Novo" e inputs de Lote/Validade | `templates/inventory/nfs_form.html` | Exibição em tela dos inputs obrigatórios de lote e validade e botão AJAX |
| Coluna "Status" com badges | `templates/ppe/product_detail.html` | Coluna exibindo status do tamanho cadastrado |

### 2.4 Causa raiz ou hipótese

- Causa confirmada: Sim
- Descrição: As telas contêm elementos visuais e obrigatoriedades de entrada (no JS e Backend) que precisam ser removidos ou automatizados.

---

## 3. Objetivos

### 3.1 Objetivo principal

- Simplificar a interface do Almoxarife para lançamento de NF, removendo os campos e o botão solicitados sem quebrar a integridade do banco de dados e as regras de estoque.
- Limpar a exibição da grade de tamanhos de EPI na tela de detalhes.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Remoção visual do botão `+ Novo` na linha de produtos da tela `/inventory/nfs/add/`.
- Remoção visual dos campos `Lote` e `Validade` de cada item na tela `/inventory/nfs/add/`.
- Ajuste no JavaScript de validação de envio e formset em `/inventory/nfs/add/`.
- Ajuste no backend (`inventory/services.py`) para gerar valores padrão/automáticos de `identificador` e `data_validade` se não forem informados.
- Remoção da coluna de Status na grade de tamanhos da tela `/ppe/<id>/`.
- Ajuste de `colspan` de 4 para 3 na linha de estado vazio da grade de tamanhos.

### 4.2 Fora do escopo

- Remoção física dos campos de lote/validade do banco de dados (sem migrations).
- Alterações no cadastro de EPI pelo CA ou na tela de cadastro de EPI.
- Alterações de regras de permissão ou de movimentações físicas de estoque.
- Modificação de outras listagens ou do Django Admin.

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Almoxarife | Recebimento rápido de materiais sem atrito técnico | Interface simplificada e automática | Sem acesso a dados de saúde |
| Técnico SST | Cadastro de EPI controlado e centralizado | Garantia de que Almoxarife não criará produtos sem validação de CA | Acesso completo |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| [views.py](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/inventory/views.py) | Investigar o fluxo do post e form_valid da NF | Recebe JSON de itens e delega ao service para salvar |
| [services.py](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/inventory/services.py) | Entender a criação de lotes e estoque físico | Exige validade e identificador do lote, gerando ValidationError se ausentes |
| [nfs_form.html](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/templates/inventory/nfs_form.html) | Localizar botão "+ Novo" e inputs de lote/validade | Contém HTML de formset dinâmico e JS de serialização |
| [product_detail.html](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/templates/ppe/product_detail.html) | Localizar coluna de status na grade de tamanhos | Exibe th e td da coluna Status (var.ativo) e colspan="4" |

---

## 7. Premissas e decisões

### 7.1 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-001 | Geração de Lote automático no Backend | Exigir no backend / Enviar valores estáticos no JS | Evita expor no JS dados desnecessários e garante unicidade via uuid + prefixo NF. |
| ADR-002 | Validade padrão no backend | Enviar data no JS | Se o Almoxarife não fornece a validade, a mesma é estimada como Data de Recebimento + 5 anos. |

---

## 8. Requisitos funcionais

### RF-001 — Simplificação de Lançamento de NF
- **Atores:** Almoxarife, Superuser
- **Pré-condições:** Acesso à página `/inventory/nfs/add/`
- **Fluxo principal:**
  1. Acessa a página.
  2. Adiciona itens através de "Adicionar Produto" (botão preservado).
  3. Preenche apenas Produto, Qtd, Unidade, Tamanho, CA (opcional), Custo Unitário.
  4. Salva a NF com sucesso.
- **Resultado esperado:** NF salva e estoque incrementado no Almoxarifado com lote gerado no formato `NF-<número_nf_ou_id>-<uuid>` e validade padrão de 5 anos a partir do recebimento.

### RF-002 — Ocultação da Situação de Tamanhos do EPI
- **Atores:** Técnico SST, Superuser
- **Pré-condições:** Acesso à página `/ppe/<id>/`
- **Fluxo principal:**
  1. Abre a página de detalhes de um EPI.
  2. Observa a tabela de "Grade de Tamanhos Cadastrados".
- **Resultado esperado:** A tabela não possui a coluna de Status/Inativo, mostrando apenas Tamanho, SKU/Código e Estoque Mínimo.

---

## 9. Regras de negócio

### RN-001 — Unicidade de Lotes Gerados automaticamente
- **Regra:** O lote autogerado deve ser único para evitar conflitos na restrição `unique_together` de `product_variant` e `identificador`.
- **Aplicação:** `inventory/services.py`
- **Mensagem esperada:** Nenhuma (deve salvar com sucesso).

---

## 10. Requisitos não funcionais

- **Segurança:** O almoxarife continua com perfil restrito e sem permissão para cadastrar EPIs na tela própria.
- **Responsividade:** As tabelas devem continuar responsivas e sem quebras de layout.

---

## 11. Permissões e segregação de acesso

Não há alteração na matriz de permissões.

---

## 12. Modelagem de dados

Nenhuma alteração de modelo ou nova tabela/campo.

---

## 13. Plano de implementação

### 13.1 Arquivos previstos

| Arquivo | Ação | Motivo |
|---|---|---|
| [services.py](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/inventory/services.py) | MODIFICAR | Alterar `create_and_confirm_fiscal_note` para autogerar lote e validade se vazios. |
| [nfs_form.html](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/templates/inventory/nfs_form.html) | MODIFICAR | Remover botão `+ Novo` e os inputs de `Lote` e `Validade`. Ajustar validação de JS. |
| [product_detail.html](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/templates/ppe/product_detail.html) | MODIFICAR | Remover a coluna Status da grade de tamanhos cadastrados. |
| [views.py](file:///C:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/ppe/views.py) | MODIFICAR | Alterar `ProductVariantCreateView` para validar duplicidade de tamanho antes de salvar e evitar IntegrityError. |

---

## 14. Estratégia de testes

### 14.1 Casos de teste

1. **Testes do Backend (NF):**
   - Garantir que `create_and_confirm_fiscal_note` aceita `identificador` e `data_validade` vazios/nulos no payload e gera os valores corretos.
   - Verificar que a movimentação de estoque correspondente é criada.
2. **Testes do Frontend (Visual):**
   - Verificar no HTML retornado por `/inventory/nfs/add/` a ausência do botão `+ Novo` e dos campos lote/validade dos itens.
   - Verificar no HTML de `/ppe/<id>/` a ausência da coluna `Status` e se o `colspan` da linha vazia é 3.
3. **Testes de Duplicidade de Grade:**
   - Garantir que a tentativa de adicionar uma variante com tamanho duplicado falha graciosamente informando erro via messages framework sem causar IntegrityError.

---
