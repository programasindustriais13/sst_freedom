# SPEC_2026_013 — Centralização e Sincronização dos Tamanhos/Variantes dos EPIs

> Esta SPEC segue estritamente o modelo de `contexto/SPEC_TEMPLATE.md` e as regras de `contexto/constitution.md`.  
> Nenhuma implementação pode ser iniciada antes da aprovação do QA (`APROVADA_PARA_IMPLEMENTAÇÃO`).

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-013` |
| Título | Centralização e Sincronização dos Tamanhos/Variantes dos EPIs |
| Tipo | `FEATURE / REFACTOR / SECURITY` |
| Módulo principal | `ppe` |
| Fase/Roadmap | `Fase 1 — Gestão de EPIs e Estoque` |
| Autor da SPEC | `Arquiteto` |
| Data de criação | `23/07/2026` |
| Última atualização | `23/07/2026 15:00` |
| Versão | `1.0.0` |
| Status | `APROVADA_PARA_IMPLEMENTAÇÃO` |
| Prioridade | `ALTA` |
| Risco | `MÉDIO` |
| Demanda de origem | `Centralizar gerenciamento de variantes na tela de cadastro/edição do EPI, preencher campo de tamanhos na edição, sincronizar/normalizar variantes com segurança (impedindo exclusão com histórico) e bloquear novos EPIs duplicados pelo CA.` |
| SPEC substituída | `Não` |
| SPECs relacionadas | `contexto/SPEC_2026_008_melhoria_cadastro_epi.md`, `contexto/SPEC_2026_009_simplificacao_estoque_grade.md`, `contexto/SPEC_2026_014_auditoria_consolidacao_segura_ca_epi.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 23/07/2026 | Arquiteto | Rascunho inicial e mapeamento de componentes | RASCUNHO |
| 1.0.0 | 23/07/2026 | Arquiteto / QA | Aprovação arquitetural e validação dos critérios de aceite | APROVADA_PARA_IMPLEMENTAÇÃO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADO` | 23/07/2026 | Mapeamento completo de models, views, forms e invariantes. |
| Revisão pré-implementação | QA | `APROVADO` | 23/07/2026 | Critérios de aceite e plano de testes validados. |
| Implementação | Backend | `PENDENTE` |  | Aguardando execução do Backend. |
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

Atualmente no sistema **SST Freedom**, o gerenciamento de tamanhos/variantes de EPIs apresenta fragmentação e inconsistências operacionais:
1. Na tela de detalhes do EPI (`http://localhost:8000/ppe/<id>/`), existe um card redundante "Adicionar Tamanho/Grade" que submete para a rota `variant_create` (`/ppe/<product_pk>/variants/add/`).
2. Na tela de edição do EPI (`http://localhost:8000/ppe/<id>/edit/`), o campo "Tamanhos / Variantes Disponíveis (separados por vírgula)" aparece vazio, mesmo quando o EPI já possui tamanhos cadastrados.
3. Não há uma sincronização normalizada e segura ao salvar o cadastro/edição do EPI: se o usuário altera o texto do campo de tamanhos, variantes com histórico (estoque, lotes, movimentações, entregas, etc.) poderiam ser indevidamente removidas.
4. Não há bloqueio na aplicação contra a criação de múltiplos EPIs principais cadastrados com o mesmo número de Certificado de Aprovação (C.A.).

Esta SPEC resolve esses problemas centralizando o gerenciamento de tamanhos exclusivamente nos formulários de cadastro e edição do EPI, preenchendo o campo de edição com os tamanhos existentes, aplicando normalização idempotente de variantes, protegendo variantes com histórico e bloqueando novos EPIs duplicados pelo CA.

---

## 2. Contexto da demanda

### 2.1 Cenário atual

- O modelo `Product` possui relacionamento 1-N com `ProductVariant` via `related_name='variants'`.
- O formulário de detalhes `ProductDetailView` exibe o card "Adicionar Tamanho/Grade" via `templates/ppe/product_detail.html`.
- O formulário de edição `ProductUpdateView` não popula `tamanhos_str` no contexto ou no formulário `ProductForm`, forçando o usuário a re-digitar tamanhos ou deixando o campo vazio.
- O método `form_valid` de `ProductUpdateView` executa `ProductVariant.objects.get_or_create(...)` mas não lida com a remoção/desativação de tamanhos excluídos do texto, nem impede exclusão de variantes que possuem saldos ou histórico em `inventory` ou `ppe`.
- O formulário `ProductForm` aceita salvar produtos com `ca_numero` duplicado sem avisar se já existe outro produto principal registrado para aquele CA.

### 2.2 Problema

- Risco de criação de variantes duplicadas ou despadronizadas (ex: `P`, `p`, ` P `).
- Interface confusa com dois locais diferentes para cadastrar tamanhos.
- Risco de perda de vínculo ou erro ao desativar/excluir variantes com movimentações ou saldo.
- Permissão de duplicidades de EPIs principais pelo CA na criação manual.

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| Card "Adicionar Tamanho/Grade" | `templates/ppe/product_detail.html#L125` | Formulário isolado via POST para `variant_create`. |
| Rota de adição de variante | `ppe/urls.py#L16` | Endpoint `<int:product_pk>/variants/add/` ativo. |
| Campo vazio na edição | `ppe/views.py#ProductUpdateView` | `tamanhos_str` não é preenchido no `get_context_data` nem no `initial`. |
| Normalização sem tratamento de remoção | `ppe/views.py#L136` | Apenas cria variantes novas sem validar as removidas. |

### 2.4 Causa raiz ou hipótese

- Causa confirmada: Sim. O fluxo de variantes foi parcialmente implementado em iterações anteriores (SPEC-2026-008 e SPEC-2026-009) mantendo o formulário legado de adição individual de tamanhos na tela de detalhes, e a rotina de sincronização na edição não foi totalmente integrada.

---

## 3. Objetivos

### 3.1 Objetivo principal

Centralizar a gestão de variantes/tamanhos no formulário de cadastro e edição de EPIs com normalização idempotente, preenchimento automático na edição, proteção contra exclusão de variantes com histórico/estoque e bloqueio de novos EPIs duplicados pelo número do CA.

### 3.2 Objetivos secundários

1. Remover o card "Adicionar Tamanho/Grade" da tela de detalhes (`/ppe/<id>/`).
2. Bloquear o uso da rota legada `/ppe/<product_pk>/variants/add/` redirecionando para a edição do EPI com mensagem explicativa.
3. Garantir preenchimento ordenado e consistente dos tamanhos existentes no campo `tamanhos_str` na edição (`/ppe/<id>/edit/`).
4. Implementar serviço único de normalização e sincronização de variantes (`sync_product_variants`).
5. Exibir mensagem amigável e bloquear remoção quando o usuário tentar retirar uma variante que possui histórico ou estoque.
6. Bloquear o cadastro de novos EPIs com o mesmo CA normalizado.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Alteração em `templates/ppe/product_detail.html` (remoção do card "Adicionar Tamanho/Grade").
- Atualização em `ppe/views.py` (`ProductDetailView`, `ProductUpdateView`, `ProductCreateView`, `ProductVariantCreateView`).
- Atualização em `ppe/forms.py` (`ProductForm` para validação de CA duplicado e tratamento de `tamanhos_str`).
- Criação de helper/serviço de sincronização e validação de variantes em `ppe/services.py`.
- Criação de testes unitários e de integração em `ppe/tests.py` ou `ppe/test_simplification.py` para validar todos os 19 cenários obrigatórios da SPEC 1.

### 4.2 Fora do escopo

- Exclusão física de modelos ou tabelas no banco de dados.
- Consolidação automática de EPIs existentes em lote (escopo exclusivo da SPEC 2).
- Adição de constraint `UNIQUE` no banco de dados nesta etapa (deve ocorrer apenas após limpeza total dos dados legados).

### 4.3 Restrições

- Respeitar `contexto/constitution.md`.
- Trabalhar somente na pasta do projeto.
- Preservar permissões e regras de acesso existentes.
- Não alterar schema de banco de forma destrutiva.

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | Cadastrar e editar EPIs com variantes de forma intuitiva e sem duplicar CAs. | Interface simplificada e segura. | Acesso completo a EPIs e Matrizes. |
| Almoxarife | Garantir que tamanhos com estoque não sumam do sistema. | Prevenção de divergências de saldo. | Leitura de EPIs e movimentações. |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `ppe/models.py` | Mapeamento dos modelos `Product` e `ProductVariant`. | `ProductVariant` possui `unique_together=('product', 'tamanho')` e campo `ativo`. |
| `ppe/forms.py` | Análise do `ProductForm`. | Valida CA no `clean()`, mas não verifica duplicidades entre produtos. |
| `ppe/views.py` | Análise de `ProductCreateView`, `ProductUpdateView`, `ProductVariantCreateView`. | Processamento disperso de `tamanhos_str`. |
| `templates/ppe/product_detail.html` | Identificação do card a ser removido. | Linhas 120-140 contêm a estrutura HTML do card. |

---

## 7. Premissas e decisões

### 7.1 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-013-1 | Centralizar sincronização de variantes em `ppe/services.py` | Manter lógica no `form_valid` da view | Evita duplicar código entre formulários/views e facilita testes unitários isolados. |
| ADR-013-2 | Bloquear desativação/remoção de variantes com estoque ou histórico | Desativar silenciosamente | Garante a integridade de livros-razão e impede inconsistências no almoxarifado. |
| ADR-013-3 | Redirecionar acessos diretos à rota `variant_create` para a edição do EPI | Retornar erro 404/403 | Melhora a UX guiando o usuário para o fluxo correto centralizado. |
| ADR-013-4 | Validação de CA duplicado em nível de formulário/aplicação | Aplicar `UniqueConstraint` no banco | O banco de dados de produção possui duplicidades legadas. Adicionar a constraint no banco agora falharia nas migrations. |

---

## 8. Requisitos funcionais

### RF-001 — Remoção do Card da Tela de Detalhes
**Descrição:** O card "Adicionar Tamanho/Grade" deve ser completamente removido da template `ppe/product_detail.html`. Não pode restar formulário oculto ou via CSS.

### RF-002 — Bloqueio da Rota Legada de Adição de Variante
**Descrição:** Requisições GET ou POST para `/ppe/<product_pk>/variants/add/` (`ProductVariantCreateView`) não devem criar variantes. A view deve redirecionar o usuário para `ProductUpdateView` (`/ppe/<product_pk>/edit/`) exibindo mensagem informativa.

### RF-003 — Preenchimento dos Tamanhos na Edição
**Descrição:** Ao abrir a página de edição do EPI (`/ppe/<id>/edit/`), o campo `tamanhos_str` deve vir preenchido com a lista de tamanhos das variantes ativas do EPI, separados por vírgula e ordenados (ex: `P, M, G, GG`).

### RF-004 — Normalização e Sincronização Idempotente de Variantes
**Descrição:** O serviço de sincronização deve:
- Separar valores por vírgula.
- Strip de espaços extras.
- Ignorar itens vazios.
- Deduplicar case-insensitivamente (ex: `P, M, G, m, GG, , P` -> `P, M, G, GG`).
- Manter variantes existentes preservando seus atributos (`sku`, `estoque_minimo`, `codigo_barras`, etc.).
- Criar apenas variantes novas.

### RF-005 — Proteção de Variantes com Estoque ou Histórico
**Descrição:** Quando uma variante deixa de ser informada no campo `tamanhos_str`:
- Verificar se possui saldo de estoque > 0, lotes (`Lot`), movimentações (`StockMovement`), entregas (`PPEDelivery`), devoluções, itens de transferência ou matriz (`PPEMatrix`).
- Se possuir estoque ou histórico, a operação de salvamento do EPI deve ser bloqueada ou a variante mantida com mensagem amigável: `"A variante G não pode ser removida porque possui estoque ou histórico de movimentações."`
- Se não possuir qualquer dependência/histórico/estoque, a variante deve ter `ativo = False`.

### RF-006 — Bloqueio de EPIs Duplicados pelo CA
**Descrição:** No formulário `ProductForm`, quando `tipo_produto == 'EPI'` e um `ca_numero` for informado:
- Normalizar o CA (apenas dígitos).
- Buscar outro `Product` ativo/existente com o mesmo CA normalizado (ignorando o próprio registro na edição).
- Se encontrado outro EPI, adicionar erro no campo `ca_numero`: `"Já existe um EPI cadastrado com o CA 12345. Abra o cadastro existente para adicionar ou editar os tamanhos disponíveis."`

---

## 9. Regras de negócio

### RN-001 — Unicidade de CA por EPI Principal
- **Regra:** Um número de CA normalizado só pode estar associado a um único `Product` (EPI principal).
- **Aplicação:** `ProductForm.clean()`.

### RN-002 — Invariante de Preservação de Histórico de Variantes
- **Regra:** Nenhuma variante vinculada a histórico ou saldo em estoque pode ser excluída ou inativada indevidamente.
- **Aplicação:** `ppe/services.py#sync_product_variants`.

---

## 10. Requisitos não funcionais

- **Segurança:** Manter controle de permissões (somente usuários autenticados e autorizados).
- **Interface:** Layout responsivo compatível com o tema visual do SST Freedom.
- **Auditoria:** Gravar logs de auditoria via `audit.models.log_audit` na atualização do EPI.

---

## 11. Plano de implementação

1. Atualizar `ppe/services.py` criando as funções:
   - `normalize_size_string(tamanhos_str)`
   - `variant_has_history_or_stock(variant)`
   - `sync_product_variants(product, tamanhos_str)`
2. Atualizar `ppe/forms.py` (`ProductForm`):
   - Adicionar campo `tamanhos_str = forms.CharField(required=False)`.
   - Adicionar validação de CA duplicado em `clean()`.
3. Atualizar `ppe/views.py`:
   - `ProductCreateView` e `ProductUpdateView`: integrar chamada a `sync_product_variants` e preencher `initial['tamanhos_str']`.
   - `ProductVariantCreateView`: alterar para redirecionar com mensagem de aviso para `product_update`.
4. Atualizar `templates/ppe/product_detail.html`:
   - Remover a seção do card "Adicionar Tamanho/Grade".
5. Executar os 19 testes obrigatórios da SPEC 1.

---

## 12. Estratégia de testes da SPEC 1

Criar/atualizar suíte de testes cobrindo os 19 cenários obrigatórios:
1. O card "Adicionar Tamanho/Grade" não aparece no detalhe.
2. O formulário antigo não permanece escondido no HTML.
3. A rota antiga (`variant_create`) redireciona e impede novo cadastro pelo fluxo removido.
4. O formulário de edição apresenta os tamanhos existentes.
5. O formulário apresenta apenas os tamanhos do EPI atual.
6. Salvar sem modificar o campo não cria duplicidades.
7. Adicionar uma nova variante preserva as existentes.
8. Espaços e valores vazios são ignorados.
9. Valores repetidos são deduplicados.
10. A comparação de tamanhos não diferencia maiúsculas/minúsculas.
11. SKU e estoque mínimo existentes são preservados.
12. Variante com estoque não é excluída/desativada.
13. Variante com histórico não é excluída/desativada.
14. Mensagem de bloqueio de remoção é apresentada.
15. CA já existente bloqueia criação de novo EPI principal.
16. Edição do próprio EPI com o mesmo CA continua permitida.
17. CA vazio não agrupa registros indevidamente.
18. Consulta automática de CA respeita validação de duplicidade.
19. Permissões atuais continuam funcionando normalmente.
