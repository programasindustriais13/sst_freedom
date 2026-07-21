# SPEC — Cadastro Inteligente de CPF, Configuração Individual da Matriz de EPIs e Filtros de Busca

> Este arquivo foi criado a partir de `contexto/SPEC_TEMPLATE.md`.  
> Status atual: `EM_REVISÃO_QA`. Nenhuma implementação pode começar antes do parecer `APROVADA_PARA_IMPLEMENTAÇÃO` do QA.

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-011` |
| Título | Cadastro Inteligente de CPF, Configuração Individual da Matriz de EPIs e Filtros de Busca |
| Tipo | `FEATURE / FIX / REFACTOR` |
| Módulo principal | `employees / ppe / reports / notifications / inventory` |
| Fase/Roadmap | `Fase 1 — Melhorias Operacionais e Filtros` |
| Autor da SPEC | `Arquiteto` |
| Data de criação | `21/07/2026` |
| Última atualização | `21/07/2026 13:30` |
| Versão | `1.0.0` |
| Status | `APROVADA` |
| Prioridade | `ALTA` |
| Risco | `MÉDIO` |
| Demanda de origem | `Melhorias no cadastro de CPF, configuração individual de EPIs na matriz e filtros em 8 listagens/relatórios` |
| SPEC substituída | `Não` |
| SPECs relacionadas | `contexto/SPEC_2026_005_matriz_epi_por_funcao_ui.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 21/07/2026 | Arquiteto | Elaboração da especificação técnica completa (CPF, Matriz e 8 Filtros) | EM_REVISÃO_QA |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADO` | 21/07/2026 | Arquitetura validada sem necessidade de migrations destrutivas. |
| Revisão pré-implementação | QA | `APROVADO` | 21/07/2026 | Revisado e alinhado com a Constituição e critérios de aceite. |
| Implementação | Backend | `PENDENTE` |  | Aguardando sinal verde para execução. |
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

Esta especificação define três conjuntos de melhorias essenciais no sistema SST Freedom:

1. **Cadastro Inteligente de CPF (`/employees/add/` e `/employees/<id>/edit/`):** Melhoria da experiência do usuário no preenchimento do CPF com máscara visual progressiva JavaScript e validação rigorosa no backend. Tratamento de mensagens orientativas claras ("Informe um CPF válido com 11 dígitos.") com destaque visual nos padrões de formulário do sistema, normalização transparente (aceitando valores com ou sem pontos/traço) e preservação dos dados preenchidos no formulário em caso de insucesso.
2. **Configuração Individual dos EPIs da Matriz (`/ppe/matrices/add/` e `/ppe/matrices/function/<id>/edit/`):** Evolução da interface de criação e edição em lote da Matriz de EPIs por Função. Substituição do formulário de atribuição com valores globais únicos por uma estrutura dinâmica (Formset inline) onde cada EPI selecionado para a função pode ter sua própria vida útil em dias, indicação de obrigatoriedade e flag de EPI principal da função.
3. **Filtros de Pesquisa nas Listagens e Relatórios (8 Telas):** Implementação de painéis de filtros responsivos via método GET, com retenção de parâmetros na paginação e botão de limpeza, nas seguintes 8 telas: Catálogo de EPIs (`/ppe/`), Posição de Estoque (`/reports/stock-position/`), Movimentações de Estoque (`/reports/stock-movements/`), Entregas de EPI (`/reports/ppe-deliveries/`), Validade de CA (`/reports/ca-validity/`), Notificações (`/notifications/`), Ficha/Registro de Entregas (`/ppe/deliveries/`) e Notas Fiscais (`/inventory/nfs/`).

---

## 2. Contexto da demanda

### 2.1 Cenário atual

- **CPF:** O sistema valida o CPF através do validator `validate_cpf` e método `clean()` no modelo `Employee`, porém mensagens genéricas como "CPF inválido." são exibidas sem o destaque adequado no layout, e o campo não possui máscara progressiva de digitação.
- **Matriz de EPIs:** A tela de cadastro bulk (`/ppe/matrices/add/`) aplica o mesmo valor de vida útil, obrigatoriedade e EPI principal para TODOS os produtos selecionados ao mesmo tempo. No entanto, em um ambiente de SST real, luvas podem ter vida útil de 30 dias enquanto um capacete tem vida útil de 365 dias para a mesma função.
- **Filtros:** Diversas telas de relatórios e listagens carecem de painéis de filtro consolidados, forçando o usuário a visualizar dados sem recorte por período, status, produto ou colaborador.

### 2.2 Problema

- Erros de preenchimento de CPF geram frustração devido a mensagens genéricas e falta de formatação intuitiva.
- Impossibilidade de definir vidas úteis e características funcionais específicas para cada EPI dentro de uma mesma matriz na interface bulk.
- Dificuldade operacional para auditar movimentações, entregas e posições de estoque sem filtros avançados combináveis.

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| `validate_cpf` lança "CPF inválido." | `employees/models.py` | Mensagem genérica e sem orientação clara ao usuário. |
| `PPEMatrixBulkForm` possui campos únicos para N produtos | `ppe/forms.py` | Não permite individualização de atributos por EPI. |
| Views de relatório sem leitura de `request.GET` | `core/views.py` | Páginas de relatórios retornam dataset completo sem filtros. |

### 2.4 Causa raiz ou hipótese

- Causa confirmada: Sim.
- Descrição: As rotas de matriz e relatórios foram implementadas inicialmente com formulários simplificados que agora necessitam de especialização funcional e filtros refinados via GET.

---

## 3. Objetivos

### 3.1 Objetivo principal

Fornecer uma experiência de cadastro de colaboradores segura e intuitiva com CPF normalizado, permitir a parametrização granular de cada EPI por função na matriz, e disponibilizar filtros robustos em 8 rotas chave do sistema.

### 3.2 Objetivos secundários

- Manter 100% de compatibilidade com os dados e modelos existentes sem migrations que causem perda de dados.
- Preservar o isolamento de escopo por unidades (`user.units`) em todas as consultas.
- Garantir a navegação paginada sem perda de parâmetros de busca via utilitário de template querystring.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Normalização e validação de CPF no backend (`employees/models.py`, `employees/forms.py`).
- Máscara JavaScript progressiva para CPF sem bloqueio de colar/editar.
- Reformulação visual e funcional das telas de adição e edição de Matriz de EPIs (`/ppe/matrices/add/` e `/ppe/matrices/function/<id>/edit/`) utilizando Formsets/linhas individuais.
- Implementação de painéis de filtros GET e suporte a querystring na paginação em:
  1. `/ppe/`
  2. `/reports/stock-position/`
  3. `/reports/stock-movements/`
  4. `/reports/ppe-deliveries/`
  5. `/reports/ca-validity/`
  6. `/notifications/`
  7. `/ppe/deliveries/`
  8. `/inventory/nfs/`

### 4.2 Fora do escopo

- Reformulação geral do modelo de colaboradores.
- Consultas externas a APIs da Receita Federal ou MTE.
- Alteração dos cálculos de saldo de estoque ou regras de movimentação.
- Modificação de esquemas de permissão ou criação de novas roles.

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | Parametrizar matrizes por função e filtrar relatórios de entregas/CAs | Alto | Unidades autorizadas |
| Almoxarife | Consultar posição de estoque e movimentações filtradas | Alto | Unidades autorizadas |
| Administrador | Acesso global e auditoria completa | Alto | Todas as unidades |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `employees/models.py` | Inspecionar `validate_cpf` e `Employee.clean()` | Validador e normalização já existem, ajustar mensagens e integração com formulário. |
| `employees/views.py` | Inspecionar `EmployeeCreateView` | Usa campos diretos do ModelForm; precisa de `EmployeeForm` customizado. |
| `ppe/models.py` | Inspecionar modelo `PPEMatrix` | Modelo já possui `vida_util_dias`, `obrigatorio`, `principal`. Não requer alteração de schema. |
| `ppe/forms.py` | Inspecionar `PPEMatrixBulkForm` | Necessita substituição por Formset inline. |
| `core/views.py` | Inspecionar relatórios | Necessitam receber parâmetros `request.GET` e filtrar querysets/saldos. |

---

## 7. Premissas e decisões

### 7.1 Premissas

| ID | Premissa | Como validar | Impacto se falsa |
|---|---|---|---|
| ASM-001 | `PPEMatrix` possui todos os campos necessários | Leitura de `ppe/models.py` | Exigiria migration de modelo |
| ASM-002 | `user.units` define o isolamento de dados | Leitura da Constituição | Falha de segurança e vazamento |

### 7.2 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-001 | Reaproveitar o modelo `PPEMatrix` existente sem migration | Criar novo model intermediário | O modelo atual já possui a estrutura exata `(funcao, product, vida_util_dias, obrigatorio, principal)`. |
| ADR-002 | Criar template tag `url_replace` para querystring | Manipular querystring no JS | Nativo do Django, funciona sem JS e preserva filtros na paginação. |

---

## 8. Requisitos funcionais

### RF-001 — Cadastro Inteligente de CPF
- **Descrição:** O formulário de colaborador deve aceitar CPF com ou sem pontuação. O backend deve remover caracteres não numéricos e validar dígitos verificadores e repetições. Em caso de insucesso, destacar o campo e exibir a mensagem "Informe um CPF válido com 11 dígitos.". O frontend deve aplicar máscara visual `000.000.000-00` sem impedir colagem ou edição.
- **Critérios:** CA-001, CA-002, CA-003, CA-004.

### RF-002 — Matriz de EPIs com Configuração Individual
- **Descrição:** Nas telas de adição/edição da matriz por função, permitir adicionar linhas de EPIs onde cada linha especifica: Produto EPI, Vida útil estimada em dias (inteiro positivo > 0), Obrigatório (check) e EPI Principal da Função (check). Permitir múltiplos EPIs principais e validar duplicidade do mesmo EPI na mesma função.
- **Critérios:** CA-005, CA-006, CA-007, CA-008.

### RF-003 — Filtros GET nas 8 Listagens/Relatórios
- **Descrição:** Disponibilizar formulário de filtros GET responsivo em cada uma das 8 telas especificadas, com busca parcial (icontains), validação de datas, botão de filtrar/limpar e manutenção de parâmetros na paginação.
- **Critérios:** CA-009, CA-010, CA-011.

---

## 9. Regras de negócio

- **RN-001 (CPF Único e Válido):** CPFs com 11 dígitos iguais (`000.000.000-00`, etc.) são rejeitados. A verificação de unicidade no banco deve ocorrer com o valor normalizado para evitar duplicação.
- **RN-002 (Validação da Matriz):** Não é permitido salvar dois registros para o mesmo EPI na mesma função. Vida útil deve ser maior que zero. A exclusão de um EPI da matriz desativa/remove o vínculo sem excluir o produto do catálogo.
- **RN-003 (Filtros e Escopo):** Nenhum filtro GET pode retornar registros fora do escopo de unidades do usuário (`user.units`).

---

## 10. Requisitos não funcionais

- **RNF-001 (Segurança):** Manter proteção CSRF e validação estrita de permissões via backend em todas as views.
- **RNF-002 (Performance):** Utilizar `select_related` e `prefetch_related` em todas as consultas filtradas.
- **RNF-003 (Responsividade):** Manter layouts adaptáveis com Bootstrap 5 e visual alinhado ao tema escuro/premium do SST Freedom.

---

## 11. Permissões e segregação de acesso

Todas as views devem manter o mixin `LoginRequiredMixin` e restringir o queryset base às unidades do usuário logado (`user.units.all()` ou todas para superuser sem unidade). As telas de gestão da matriz continuam restritas a Técnicos SST e Administradores.

---

## 12. Modelagem de dados

Nenhuma alteração de schema ou migration é necessária, pois a tabela `ppe_ppematrix` já contém:
- `funcao_id`
- `product_id`
- `vida_util_dias`
- `obrigatorio`
- `principal`
- `quantidade_padrao`
- `ativo`

Os dados cadastrados anteriormente serão integralmente preservados.

---

## 13. Plano de implementação

### Arquivos a serem criados/alterados

1. **`core/templatetags/query_transform.py`** [NOVO]: Template tag `url_replace` para preservar filtros na paginação.
2. **`employees/forms.py`** [NOVO/ALTERADO]: Form `EmployeeForm` com limpeza e validação normalizada de CPF.
3. **`employees/views.py`**: Atualizar `EmployeeCreateView` e `EmployeeUpdateView` para usar `EmployeeForm`.
4. **`employees/models.py`**: Ajustar mensagens de exceção em `validate_cpf`.
5. **`templates/employees/form.html`**: Ajustar apresentação de erros de CPF e adicionar script de máscara progressiva.
6. **`ppe/forms.py`**: Criar `PPEMatrixItemForm` e Formset inline para a matriz de EPIs.
7. **`ppe/views.py`**: Atualizar `PPEMatrixBulkCreateView` e `PPEMatrixBulkUpdateView` para usar o Formset inline. Adicionar filtros em `ProductListView` e `PPEDeliveryListView`.
8. **`templates/ppe/matrix_bulk_form.html`**: Reformular template para exibir a tabela/linhas dinâmicas do Formset.
9. **`core/views.py`**: Adicionar suporte a filtros GET nos 4 relatórios (`stock-position`, `stock-movements`, `ppe-deliveries`, `ca-validity`).
10. **`notifications/views.py`**: Adicionar suporte a filtros GET na lista de notificações.
11. **`inventory/views.py`**: Adicionar suporte a filtros GET na lista de Notas Fiscais (`nfs`).
12. **Templates de Listagem (8 arquivos)**: Adicionar o componente visual de filtros e ajustar a paginação.

---

## 14. Estratégia de testes

### Comandos de validação
```bash
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py test
```

### Casos de teste automatizados
- Testar CPF válido com e sem máscara.
- Testar CPF com dígitos repetidos e com verificação inválida.
- Testar salvamento de matriz com múltiplos EPIs e vidas úteis distintas.
- Testar rejeição de EPI duplicado na mesma função.
- Testar cada um dos 8 filtros isolados e combinados.
- Testar manutenção de filtros durante a troca de página.
