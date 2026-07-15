# SPEC — Exclusão Administrativa em Cascata no Django Admin

Este documento especifica o design técnico e plano de implementação da exclusão em cascata controlada e segura no Django Admin para o projeto SST Freedom.

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-010` |
| Título | Exclusão Administrativa em Cascata Controlada e Segura no Django Admin |
| Tipo | FEATURE / SECURITY |
| Módulo principal | core / organizations |
| Fase/Roadmap | Fase 1B (Evolução / Segurança) |
| Autor da SPEC | Arquiteto (Antigravity) |
| Data de criação | 14/07/2026 |
| Última atualização | 14/07/2026 16:15 |
| Versão | 0.1.0 |
| Status | `EM_REVISÃO_QA` |
| Prioridade | CRÍTICA |
| Risco | ALTO |
| Demanda de origem | Exclusão administrativa em cascata no Django Admin (Solicitação do Cliente) |
| SPEC substituída | Não |
| SPECs relacionadas | Não se aplica |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 14/07/2026 | Arquiteto | Criação da especificação inicial | EM_REVISÃO_QA |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 14/07/2026 | Arquitetura segura via Django ORM e transações |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 14/07/2026 | Testes e validações bem mapeados |
| Implementação | Backend | `PENDENTE` |  |  |
| QA final | QA | `PENDENTE` |  |  |

---

## 1. Resumo executivo

Atualmente, no Django Admin, ao tentar excluir uma `Company` (Empresa), a operação é bloqueada devido a relacionamentos protegidos por `on_delete=models.PROTECT`. O cliente deseja que administradores autorizados ou superusuários possam forçar a exclusão em cascata de um registro principal de forma controlada através do Django Admin, respeitando as restrições transacionais e gerando um registro completo de auditoria.

Esta especificação apresenta:
- Um serviço reutilizável no app `core` para coletar recursivamente todas as dependências (incluindo relações genéricas) e ordená-las de forma que as folhas (filhos mais distantes) sejam apagadas primeiro, contornando a proteção do banco sem alterar os metadados `on_delete=models.PROTECT` globais.
- A integração visual no Django Admin com aviso de perigo destacado, contagem de registros por modelo e um campo de confirmação adicional que exige a palavra `EXCLUIR` digitada.
- Validação rígida no backend e registro completo em `AuditLog` das informações textualizadas que foram deletadas.

---

## 2. Contexto da demanda

### 2.1 Cenário atual
Os relacionamentos críticos do projeto usam `on_delete=models.PROTECT` para evitar perda inadvertida de dados por usuários comuns. No Django Admin, ao tentar remover um objeto com dependências, o Django mostra a tela padrão bloqueando a operação e listando apenas os objetos afetados.

### 2.2 Problema
Não há como o administrador do sistema executar limpezas de dados de teste ou reestruturar as organizações do banco deletando uma Empresa legada/antiga diretamente no Admin, a menos que ele delete manualmente cada registro de cada tabela relacionada em ordem reversa, o que é inviável operacionalmente.

---

## 3. Objetivos

### 3.1 Objetivo principal
Permitir que superusuários ou usuários com permissão especial excluam uma `Company` (ou outro modelo cadastrado) com todos os seus objetos vinculados diretamente pelo Django Admin.

### 3.2 Objetivos secundários
- Rastrear toda a operação no `AuditLog` com um snapshot textual do que foi apagado.
- Garantir segurança transacional (rollback completo se qualquer item falhar).
- Validar a confirmação no backend.
- Tornar o mecanismo extensível a outros ModelAdmin.

---

## 4. Escopo

### 4.1 Dentro do escopo
- Serviço de coleta e ordenação topológica de dependências.
- Criação da permissão customizada `can_force_cascade_delete` associada a `Company`.
- Criação do template e fluxo de confirmação reforçada individual e em massa (bulk actions) no admin.
- Registro em auditoria e rollback em transações atômicas.

### 4.2 Fora do escopo
- Alteração das views normais do sistema (a exclusão normal de colaboradores, EPIs, etc., continuará respeitando `models.PROTECT`).

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Administrador Técnico / Superuser | Excluir dados organizacionais sem erros de chave estrangeira. | Permite saneamento e manutenção do banco. | Acesso total com confirmação. |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `organizations/models.py` | Identificar relacionamentos das empresas e unidades. | Relações com `Company` e `Unit` usam `PROTECT`. |
| `employees/models.py` | Mapear dependências de colaboradores e histórico. | `EmployeeHistory` usa `CASCADE` para `Employee`, mas outros são `PROTECT`. |
| `inventory/models.py` | Mapear lotes, notas fiscais, movimentos e transferências. | Relações usam `PROTECT`. |
| `ppe/models.py` | Mapear entregas e matrizes de EPI. | Relações usam `PROTECT`. |
| `audit/models.py` | Verificar estrutura de auditoria existente. | `AuditLog` está disponível e possui o método utilitário `log_audit`. |

---

## 7. Premissas e decisões

### 7.1 Premissas
- A ordenação topológica impede violação das restrições de chave estrangeira nas exclusões individuais.

### 7.2 Decisões arquiteturais
- **ADR-001:** Usar ordenação topológica de modelos para deletar recursivamente as folhas antes do tronco.
- **ADR-002:** Não desativar constraints no banco. Toda integridade referencial do banco de dados é mantida e as constraints são satisfeitas excluindo na ordem correta.

---

## 8. Requisitos funcionais

### RF-001 — Serviço de Coleta e Ordenação de Dependências
- **Descrição:** Coleta recursivamente todas as instâncias de todos os modelos que apontam para os objetos de origem direta ou indiretamente, incluindo instâncias de relações genéricas (`Alert`). Classifica os modelos usando ordenação topológica (Kahn's algorithm).

### RF-002 — Tela de Confirmação Reforçada no Admin
- **Descrição:** Exibe aviso visual destacado em vermelho na tela de exclusão individual ou em massa indicando o perigo da exclusão e listando em tabela os objetos a serem removidos agrupados por tipo, com suas respectivas contagens.
- **Ações:** Exige digitação da palavra exata `EXCLUIR` no campo de texto para habilitar/processar a exclusão.

### RF-003 — Validação no Backend e Execução Transacional
- **Descrição:** O POST valida novamente as permissões do usuário, recalcula e coleta as dependências para evitar concorrência/inconsistência e verifica se a confirmação `EXCLUIR` foi submetida corretamente. A exclusão roda dentro de `transaction.atomic()`.

### RF-004 — Permissão de Acesso
- **Descrição:** A funcionalidade de exclusão forçada em cascata está restrita a superusuários ou usuários que possuam a permissão `organizations.can_force_cascade_delete`. Usuários sem privilégio veem a interface de bloqueio padrão.

### RF-005 — Registro detalhado na Auditoria
- **Descrição:** A operação gera um log no `AuditLog` com a ação `"Exclusão em Cascata Administrativa"`, o ID da entidade principal, o nome do responsável e, em `changes_before`, um sumário em formato texto/JSON com todos os registros excluídos (modelo, ID, representação textual).

---

## 9. Regras de negócio

### RN-001 — Confirmação Correta do Backend
- **Regra:** Se o valor enviado no POST para a palavra de confirmação for diferente de `"EXCLUIR"` (sensível a maiúsculas), a transação sofre rollback, a exclusão é abortada e uma mensagem de erro é exibida.
- **Aplicação:** View administrativa.

### RN-002 — Ordem Topológica de Deleção
- **Regra:** Os registros filhos (como entregas, movimentações, históricos) devem ser deletados obrigatoriamente antes de seus pais para que nenhuma constraint de chave estrangeira seja violada no banco de dados.

---

## 10. Requisitos não funcionais

### RNF-001 — Transações
- Toda a exclusão deve rodar de forma atômica no banco de dados. Qualquer falha técnica em um trigger ou constraint deve reverter todo o estado do banco.

---

## 11. Plano de implementação

### 11.1 Arquivos previstos

| Arquivo | Ação | Motivo |
|---|---|---|
| `organizations/models.py` | Alterar | Adicionar permissão customizada `can_force_cascade_delete` no Meta de `Company`. |
| `core/services.py` | Criar | Contém a classe `CascadeDeleteService` com os métodos de coleta, ordenação topológica e execução. |
| `core/admin.py` | Alterar | Criar e exportar o `CascadeDeleteAdminMixin`. |
| `templates/admin/cascade_delete_confirmation.html` | Criar | Template customizado para confirmação individual e em massa (bulk). |
| `organizations/admin.py` | Alterar | Aplicar o `CascadeDeleteAdminMixin` no `CompanyAdmin`. |
| `core/tests.py` | Alterar | Adicionar suíte de testes de regressão, segurança e concorrência para a funcionalidade. |

---

## 12. Estratégia de testes

### 12.1 Matriz de testes

- **Caso 1:** Superusuário ou usuário autorizado consegue excluir uma `Company` com todas as suas dependências (Unidades, Colaboradores, Entregas, Lotes, Movimentos) digitando `EXCLUIR` corretamente.
- **Caso 2:** Usuário sem a permissão `organizations.can_force_cascade_delete` recebe erro 403 ou visualiza o bloqueio padrão de exclusão do Django Admin.
- **Caso 3:** Entrada incorreta da palavra de confirmação impede a exclusão tanto no frontend quanto no backend.
- **Caso 4:** Ocorrência de erro técnico simulado durante a exclusão causa rollback completo (nada é deletado).
- **Caso 5:** Verificação de que o log de auditoria é preenchido com a contagem de registros apagados e detalhes JSON das entidades destruídas.
