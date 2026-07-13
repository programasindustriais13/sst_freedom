# SPEC — Módulo e Telas de Gestão da Matriz de EPIs por Função

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-005` |
| Título | Módulo e Telas de Gestão da Matriz de EPIs por Função |
| Tipo | FEATURE |
| Módulo principal | ppe |
| Fase/Roadmap | Fase 1A (Extensão) |
| Autor da SPEC | Arquiteto (Antigravity) |
| Data de criação | 10/07/2026 |
| Última atualização | 10/07/2026 15:20 |
| Versão | 1.0.0 |
| Status | `APROVADA_PARA_IMPLEMENTAÇÃO` |
| Prioridade | ALTA |
| Risco | MÉDIO |
| Demanda de origem | Criar interface própria para consultar e gerenciar a Matriz de EPIs por Função |
| SPEC substituída | Não |
| SPECs relacionadas | `SPEC-2026-001` (Fundação, Estoques e Controle de EPI) |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 10/07/2026 | Arquiteto | Rascunho inicial | RASCUNHO |
| 1.0.0 | 10/07/2026 | Arquiteto | Revisão e aprovação do QA | APROVADA_PARA_IMPLEMENTAÇÃO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 10/07/2026 | Desenho e modelagem adequados às regras do domínio e à Constituição. |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 10/07/2026 | Requisitos cobertos, testes especificados e verificações de backend previstas. |
| Implementação | Backend | `PENDENTE` |  |  |
| QA final | QA | `PENDENTE` |  |  |

### 0.3 Transições de status

```text
RASCUNHO
→ EM_REVISÃO_QA (Revisado pelo Arquiteto/QA)
→ APROVADA_PARA_IMPLEMENTAÇÃO (Aprovado para início do desenvolvimento)
```

---

## 1. Resumo executivo

O objetivo desta especificação é prover uma interface própria na área operacional do **SST Freedom** para que usuários autorizados possam gerenciar a **Matriz de EPIs por Função** sem a necessidade de acessar o painel administrativo do Django (`/admin`).

A matriz de EPIs por função representa a necessidade regulamentar de Equipamentos de Proteção Individual para cada atividade profissional na empresa. Atualmente, a modelagem existe e funciona no Django Admin, mas os usuários operacionais necessitam de uma tela integrada ao visual escuro institucional, com busca, filtros, paginação e suporte a cadastros em lote (seleção de múltiplos EPIs para uma função de forma atômica).

Esta SPEC detalha as rotas, views, templates, formulários e o plano de testes automatizados necessários para implementar essa funcionalidade com segurança, garantindo o princípio do privilégio mínimo e integridade de dados.

---

## 2. Contexto da demanda

### 2.1 Cenário atual

1. O modelo `PPEMatrix` existe no app `ppe` e faz o relacionamento N-para-1 entre `Function` (Função/Cargo) e `Product` (EPI) com metadados como vida útil e quantidade.
2. A gestão completa hoje ocorre em `/admin/ppe/ppematrix/`. No sistema principal, há apenas a visualização da matriz na ficha do colaborador em `/employees/<id>/` e a tela de detalhes de uma função isolada em `/organizations/function/<id>/` (que permite adicionar/editar um EPI por vez).
3. Não há uma tela que agrupe todas as funções e liste de forma consolidada e paginada quais EPIs estão recomendados para cada uma.

### 2.2 Problema

O técnico de SST precisa gerenciar as matrizes operacionais no dia a dia, mas o Django Admin expõe configurações técnicas do banco de dados e não é amigável a dispositivos móveis, além de não permitir a associação em lote de múltiplos EPIs a uma função de uma só vez (experiência lenta).

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| Rota `/admin/ppe/ppematrix/` | `ppe/admin.py` | Cadastro restrito ao Django Admin |
| Modelo `PPEMatrix` | `ppe/models.py` | Relacionamento individual entre função e produto |
| Regra de Negócio §10.3 | `contexto/constitution.md` | Matriz de EPI por função deve permitir vida útil e quantidade configuráveis |

---

## 3. Objetivos

### 3.1 Objetivo principal

Implementar as telas de listagem, cadastro em lote, edição, detalhe e exclusão da Matriz de EPI por Função integrada à interface principal do sistema.

### 3.2 Objetivos secundários

1. Garantir que as permissões de acesso sejam verificadas no backend (apenas Técnicos SST e Administradores).
2. Fornecer busca por nome de função e filtros por status e empresa.
3. Criar uma experiência de cadastro simplificada onde o usuário seleciona uma função e marca múltiplos EPIs.
4. Manter compatibilidade bidirecional total com o Django Admin.
5. Preservar a auditoria detalhada via logs para todas as ações do módulo.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Rota de listagem consolidada de matrizes por função (agrupadas para melhor visualização).
- Rota e tela de cadastro bulk (selecionar 1 função e N EPIs).
- Rota e tela de edição (modificar múltiplos EPIs da função).
- Integração da exclusão (física com tratamento de erros de integridade, ou lógica conforme padrão do projeto).
- Verificação de autorização (Técnico e Admin autorizados; Almoxarife e não-autenticados negados).
- Logs de auditoria para criação, modificação e deleção.
- Link no menu lateral do sistema.

### 4.2 Fora do escopo

- Alteração da modelagem do banco (o modelo `PPEMatrix` e tabelas existentes devem ser mantidos sem alterações de migração).
- Automatização de movimentações de estoque baseada na matriz de EPIs (matriz representa apenas a recomendação teórica).

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | Consultar e ajustar a matriz rapidamente de acordo com os riscos. | Alta produtividade no cadastro e manutenção de normas. | Acesso completo (C, R, U, D) |
| Almoxarife | Consultar quais EPIs são recomendados para um colaborador. | Consulta rápida sem permissão de alteração. | Acesso apenas leitura (R) |
| Administrador | Gerenciar parâmetros globais e monitorar alterações. | Auditoria e controle total das matrizes de todas as unidades. | Acesso completo (C, R, U, D) |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `ppe/models.py` | Compreender campos do modelo `PPEMatrix`. | Possui `funcao`, `product`, `variant`, `quantidade_padrao`, `vida_util_dias`, `ativo`. |
| `ppe/forms.py` | Verificar formulários existentes. | Possui `ProductForm` e o formulário `PPEMatrixForm` criado para edição unitária. |
| `ppe/urls.py` | Analisar rotas do módulo de EPIs. | Necessita de novas rotas de listagem geral, bulk create, bulk update e delete. |
| `organizations/views.py` | Analisar as views de estrutura corporativa. | Possui `FunctionDetailView` que exibe a matriz unitária por função. |
| `audit/models.py` | Verificar ferramenta de logs. | A função `log_audit(request, ...)` está disponível para registrar as ações. |

---

## 7. Requisitos funcionais

### RF-001 — Listagem Geral de Matrizes por Função

**Descrição:**  
Apresentar uma tela contendo todas as funções cadastradas no sistema que possuem ao menos uma recomendação de EPI, exibindo o nome do cargo, a empresa associada, o resumo em formato de badges dos EPIs ativos vinculados, e a contagem total de EPIs.

**Atores:** Técnico de SST, Almoxarife, Administrador.

**Pré-condições:** Usuário logado.

**Fluxo principal:**
1. O usuário acessa a rota `/ppe/matrices/`.
2. O sistema recupera as funções agrupadas com suas respectivas relações de `PPEMatrix`.
3. Renderiza a tabela paginada e com suporte a buscas por texto (no nome da função) e filtros (por empresa).
4. O usuário visualiza as ações: Visualizar Detalhes, Editar Matriz e Excluir.

---

### RF-002 — Cadastro em Lote (Bulk Create)

**Descrição:**  
Permitir a criação da matriz para uma função que ainda não tenha EPIs recomendados, selecionando a função e múltiplos EPIs.

**Atores:** Técnico de SST, Administrador.

**Fluxo principal:**
1. O usuário acessa `/ppe/matrices/add/`.
2. Seleciona a função desejada em um dropdown.
3. Seleciona múltiplos EPIs a partir de um campo de seleção múltipla (ou checkboxes organizadas).
4. Define a quantidade padrão padrão (ex: 1) e vida útil padrão em dias (ex: 365) que serão aplicadas para os EPIs recém-associados.
5. Salva a requisição.
6. O backend cria os registros de `PPEMatrix` individuais e redireciona para os detalhes da função.

---

### RF-003 — Edição em Lote (Bulk Update)

**Descrição:**  
Permitir alterar a lista de EPIs vinculados a uma função. EPIs desmarcados serão inativados (`ativo=False`) e EPIs novos serão criados.

**Atores:** Técnico de SST, Administrador.

**Fluxo principal:**
1. O usuário clica em "Editar" na listagem ou na tela de detalhes da função.
2. Abre a tela de edição em lote na rota `/ppe/matrices/function/<id>/edit/`.
3. O nome da função aparece de forma fixa (bloqueado para edição).
4. A lista de seleção múltipla exibe os EPIs já marcados.
5. O usuário marca novos ou desmarca existentes e clica em Salvar.
6. O backend realiza a reconciliação (cria novos, inativa desmarcados) e atualiza o histórico.

---

### RF-004 — Visualização de Detalhes

**Descrição:**  
Exibir a ficha completa da função contendo descrição, empresa, status da função e a lista detalhada de cada EPI recomendado (com variante, C.A., fabricante, validade do C.A., periodicidade/vida útil e observações).

**Atores:** Técnico de SST, Almoxarife, Administrador.

**Nota:** Reutilizaremos e aprimoraremos a rota `/organizations/function/<id>/` criada anteriormente, garantindo que contenha todas as informações úteis exigidas no escopo de visualização.

---

### RF-005 — Exclusão Física / Lógica

**Descrição:**  
Permitir a exclusão completa das recomendações de EPI para uma função com confirmação prévia e tratamento de integridade.

**Atores:** Técnico de SST, Administrador.

**Fluxo principal:**
1. O usuário clica em "Excluir" em uma função na rota `/ppe/matrices/<id>/delete/`.
2. O sistema exibe tela de confirmação avisando que todas as recomendações de EPI para a função serão removidas.
3. Ao confirmar, o sistema remove fisicamente os registros de `PPEMatrix` associados a ela, tratando exceções de `ProtectedError` caso existam FKs impedindo (e exibindo mensagem de erro amigável ao usuário).

---

## 8. Regras de negócio

### RN-001 — Controle de Permissões
- **Regra:** Apenas usuários com `profile_type` igual a `TECNICO_SST` ou `ADMIN` (ou superusuário) podem realizar operações de escrita (criar, editar, excluir, toggle de ativação). Usuários com perfil `ALMOXARIFE` possuem apenas permissão de consulta (GET na listagem e nos detalhes).
- **Aplicação:** Views backend (verificação no `dispatch` ou `UserPassesTestMixin`).

### RN-002 — Reconciliação em Lote na Edição
- **Regra:** Ao atualizar a lista de EPIs recomendados de uma função:
  - Novos EPIs marcados geram novas instâncias de `PPEMatrix`.
  - EPIs previamente associados que foram desmarcados na seleção bulk devem ser definidos como inativos (`ativo=False`) para preservar o histórico regulamentar de recomendações, em conformidade com o princípio de integridade histórica da Constituição.

---

## 9. Requisitos não funcionais

### RNF-001 — Responsividade e Visual
Toda a interface deve seguir rigorosamente as diretrizes contidas em `GUIA_TEMA_VISUAL_SST_FREEDOM.md` (superfície `--surface-page` escura, cards com `--surface-card`, botões com hover dourado `--brand-primary`, formulários estilizados com `.form-control-premium`).

### RNF-002 — Otimização de Consultas
Evitar o problema de consultas N+1 utilizando `select_related('funcao', 'company')` e `prefetch_related('ppe_matrix_entries__product')` na listagem de funções.

---

## 10. Permissões e segregação de acesso

| Recurso/Ação | Técnico SST | Almoxarife | Administrador | Observação |
|---|---:|---:|---:|---|
| Listar Matrizes | R | R | R | Consulta geral permitida a todos. |
| Detalhar Matriz | R | R | R | Visualização detalhada permitida a todos. |
| Criar/Editar Bulk | C / U | — | C / U | Apenas TST ou Admin. |
| Excluir Recomendações | D | — | D | Apenas TST ou Admin. |

---

## 11. Testes automatizados propostos

Serão criados testes no arquivo `ppe/tests_matrix_bulk.py` cobrindo:
1. Acesso à listagem geral por usuário logado (TST e Almoxarife).
2. Bloqueio de rotas de alteração (Nova/Editar/Excluir) para Almoxarifes (retornando status 403).
3. Criação de matriz bulk com múltiplos EPIs associados com sucesso.
4. Edição de matriz bulk realizando a desmarcação de EPI (que deve ser definida como `ativo=False`) e marcação de novos.
5. Exclusão física com redirecionamento correto e segurança contra perda de integridade.
6. Acesso anônimo sendo redirecionado para a tela de login.
