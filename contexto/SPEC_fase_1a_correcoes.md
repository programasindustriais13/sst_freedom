# SPEC — Correções e Melhorias Fase 1A (SST Freedom)

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-002` |
| Título | Primeira Rodada de Correções e Melhorias Operacionais |
| Tipo | FIX / REFACTOR / SECURITY |
| Módulo principal | core / accounts / organizations / inventory / ppe / audit |
| Fase/Roadmap | Fase 1A (Pós-Fundação) |
| Autor da SPEC | Arquiteto (Antigravity) |
| Data de criação | 10/07/2026 |
| Última atualização | 10/07/2026 12:20 |
| Versão | 1.0.0 |
| Status | `CONCLUÍDA` |
| Prioridade | CRÍTICA |
| Risco | MÉDIO |
| Demanda de origem | Rodada 1 de Correções - Problemas de Interface, Admin, Auditoria e Cadastros |
| SPEC substituída | Não |
| SPECs relacionadas | `SPEC-2026-001` (Fase 1A) |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 10/07/2026 | Arquiteto (Antigravity) | Especificação das correções de bugs da rodada 1 | CONCLUÍDA |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 10/07/2026 | Arquitetura de banco e segurança preservada |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 10/07/2026 | Pronto para codificação |
| Implementação | Backend | `APROVADA` | 10/07/2026 | Alterações codificadas e validadas |
| QA final | QA | `APROVADA` | 10/07/2026 | Suíte de testes OK e validação visual de contraste aprovada |

---

## 1. Resumo executivo

Esta especificação define o plano de resolução de seis problemas críticos operacionais e de interface identificados no sistema **SST Freedom**:
1. Elementos textuais e links desaparecem/perdem contraste nos cards premium sob hover.
2. Os modelos operacionais do sistema estão ausentes no Django Admin.
3. Não há registros operacionais auditáveis na área administrativa.
4. Os formulários organizacionais em `/organizations/` não exibem seletores de Empresa ou Unidade.
5. O formulário de Notas Fiscais impõe obrigatoriedade fiscal rígida e não calcula divergências nem suporta C.A. e descrição nos itens (lotes).
6. O cadastro de EPIs impede seleção de Categorias de Proteção.

As correções preservam integralmente o escopo e as regras de segurança estabelecidas na Constituição do Projeto e na SPEC de Fundação (`SPEC-2026-001`).

---

## 2. Investigação e Causa Raiz de cada Problema

### 2.1 Problema 1: Cards Perdem Conteúdo no Hover
- **Causa Raiz:** O link `<a>` com `class="text-decoration-none"` que envolve o `.card-premium` em locais como `reports/list.html` faz com que, no estado `:hover`, o Bootstrap aplique a cor de link no hover (`#0a58ca` - azul escuro). Como o fundo do card sob hover muda para `#162035` (azul escuro ardósia), o contraste cai para níveis inaceitáveis, tornando o texto invisível/ilegível. Links normais contidos dentro do card sofrem do mesmo problema.
- **Impacto:** Experiência visual defeituosa e problemas graves de legibilidade.
- **Solução proposta:** Atualizar `static/css/custom.css` para redefinir o comportamento de cores de links que envolvem e estão dentro de `.card-premium`. Links externos terão `color: inherit`, e links internos terão `#38bdf8` (azul claro legível).
- **Arquivos envolvidos:** [custom.css](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/static/css/custom.css)

### 2.2 Problema 2: Django Admin sem Módulos do Sistema
- **Causa Raiz:** Os arquivos `admin.py` em todos os aplicativos (`accounts`, `organizations`, `employees`, `inventory`, `ppe`, `notifications`, `audit`) estão vazios e sem registro de seus modelos.
- **Impacto:** O administrador técnico não consegue realizar correções de retaguarda ou auditorias pelo Django Admin.
- **Solução proposta:** Registrar os modelos de domínio com classes customizadas de `admin.ModelAdmin` aplicando restrições rígidas de deleção/edição para dados históricos críticos.
- **Arquivos envolvidos:** `admin.py` em todos os aplicativos.

### 2.3 Problema 3: Logs de Acesso e Ações dos Usuários
- **Causa Raiz:** O modelo `AuditLog` e a função utilitária `log_action` existem no app `audit`, mas não são invocados em nenhuma parte da lógica do sistema nem expostos no Admin.
- **Impacto:** Sem rastreabilidade de acessos e operações críticas, violando a política de LGPD e a Constituição.
- **Solução proposta:** Conectar signals de autenticação (`user_logged_in`, `user_logged_out`, `user_login_failed`) para registrar logins e tentativas falhas de forma segura (sem armazenar senhas). Inserir chamadas a `log_action` nas views e services de operações críticas do sistema.
- **Arquivos envolvidos:** `audit/models.py`, `audit/apps.py`, `audit/admin.py`, e arquivos de views/services do projeto.

### 2.4 Problema 4: Cadastros Inviabilizados em `/organizations/`
- **Causa Raiz:** O template genérico de formulário `templates/organizations/form.html` tenta renderizar campos que não são checkbox usando um `<input type="...">` genérico. Isso renderiza `ModelChoiceField` (dropdowns/selects) como campos de texto comuns e vazios, impedindo o usuário de visualizar e selecionar as Empresas e Unidades associadas.
- **Impacto:** Bloqueia o cadastro de Unidades, Setores, CCs, Cargos e Locais de Estoque no fluxo operacional.
- **Solução proposta:** Corrigir `templates/organizations/form.html` para identificar se o campo é uma escolha/select (`field.field.choices`) ou um campo de texto longo/textarea (`field.field.widget.input_type is None`) e renderizar a tag HTML semântica correta (`<select>` ou `<textarea>`) com estilo Bootstrap Premium.
- **Arquivos envolvidos:** [form.html](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/templates/organizations/form.html)

### 2.5 Problema 5: Rigidez e Falhas no Fluxo de Notas Fiscais/Recibos
- **Causa Raiz:** 
  1. O model `FiscalNote` define `numero` e `serie` como campos de banco obrigatórios, forçando dados fiscais mesmo para simples recebimentos com recibo.
  2. O model `FiscalNote` não possui um campo para o tipo de documento de recebimento.
  3. O modelo `Lot` (item da nota) não armazena o C.A. do lote físico.
  4. Não há cálculo visual de divergência de valores na tela de detalhes nem botão de remoção de item em rascunho.
- **Impacto:** Processo de recebimento incompatível com a realidade do almoxarifado (que frequentemente recebe compras com recibos e exige especificação de C.A.s individuais).
- **Solução proposta:**
  - Adicionar o campo `tipo` (Nota Fiscal, Recibo, Sem Documento, Outro) em `FiscalNote`.
  - Tornar `numero` e `serie` nulos (`blank=True, null=True`) no banco e validar obrigatoriedade condicional no form.
  - Adicionar o campo `ca` (ForeignKey para `CertificadoAprovacao`, opcional) no modelo `Lot`.
  - Atualizar os templates de cadastro e exibição de notas fiscais, habilitando exclusão de itens de rascunho, cálculo automático de total/subtotal e exigência de justificativa de divergência.
- **Arquivos envolvidos:** `inventory/models.py`, `inventory/views.py`, `inventory/services.py`, `templates/inventory/nfs_form.html`, `templates/inventory/nfs_detail.html`

### 2.6 Problema 6: Categoria de Proteção Inválida no Cadastro de EPI
- **Causa Raiz:** Mesma causa raiz do Problema 4. O campo `categoria` no cadastro de EPI é um ChoiceField, que no formulário vira input de texto em branco. O valor digitado não bate com as chaves internas permitidas (caixa alta) e o formulário rejeita a submissão.
- **Impacto:** Bloqueia o cadastro de novos EPIs no catálogo operacional.
- **Solução proposta:** Resolvido pela mesma alteração do template `templates/organizations/form.html` descrita no item 2.4.
- **Arquivos envolvidos:** [form.html](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/templates/organizations/form.html)

---

## 3. Escopo

### 3.1 Dentro do escopo
- Melhoria e correção do CSS para cards premium.
- Registro detalhado e seguro de todos os 22 modelos operacionais no Django Admin.
- Middleware ou signal de Logs de Auditoria para eventos de login, logout e operações críticas.
- Correção do template genérico de formulário organizador para aceitar selects e textareas.
- Refatoração dos modelos e telas de Notas Fiscais para suportar Recibos, itens com C.A. e cálculos de divergência de valores.

### 3.2 Fora do escopo
- Alterações estruturais nos fontes de referência de `fontes/`.
- Mudança de tecnologia do frontend (continua utilizando Bootstrap e server-side render).

---

## 4. Regras de Negócio e Segurança de Dados

### RN-001 — Imutabilidade no Django Admin
- Registros de logs de auditoria (`AuditLog`) são **somente leitura** para todos os usuários, incluindo administradores técnicos. Não é permitida adição, alteração ou exclusão direta.
- Movimentações de estoque concluídas (`StockMovement`) e entregas finalizadas (`PPEDelivery`) não permitem alteração ou exclusão.

### RN-002 — Validação Condicional do Documento de Entrada
- Se o tipo do documento for `NOTA_FISCAL`, os campos `numero` e `serie` tornam-se **obrigatórios** no formulário e no backend.
- Se o tipo do documento for `RECIBO`, `SEM_DOCUMENTO` ou `OUTRO`, os campos `numero` e `serie` são opcionais.

### RN-003 — Justificativa de Divergência
- Ao tentar confirmar um documento de entrada (status `CONFERIDA`), se a soma do valor dos lotes inseridos (`valor_total_calculado`) divergir do valor total informado no cabeçalho do documento (`valor_total_informado`), o sistema **exige** que o campo `observacoes` do documento esteja preenchido com a justificativa técnica. Do contrário, a confirmação é bloqueada.

---

## 5. Modelagem de Dados (Alterações)

### 5.1 Modelo `inventory.FiscalNote`
- **Novo campo:**
  - `tipo`: CharField, max_length=20, choices=TIPO_CHOICES, default='NOTA_FISCAL'
- **Campos alterados:**
  - `numero`: models.CharField(max_length=50, blank=True, null=True)
  - `serie`: models.CharField(max_length=10, blank=True, null=True)

### 5.2 Modelo `inventory.Lot`
- **Novo campo:**
  - `ca`: models.ForeignKey('ppe.CertificadoAprovacao', on_delete=models.PROTECT, blank=True, null=True)

---

## 6. Plano de Implementação (Arquivos a Alterar)

1. **`static/css/custom.css`:** Ajustar estilo dos cards e links.
2. **`templates/organizations/form.html`:** Adicionar suporte a select e textarea genéricos.
3. **`accounts/admin.py`:** Registrar `CustomUser`.
4. **`organizations/admin.py`:** Registrar modelos organizacionais.
5. **`employees/admin.py`:** Registrar colaborador e históricos com proteção.
6. **`inventory/admin.py`:** Registrar nota fiscal, lote, livro-razão e transferências com restrições.
7. **`ppe/admin.py`:** Registrar EPI, matriz e entregas com proteção de imutabilidade.
8. **`notifications/admin.py`:** Registrar alertas.
9. **`audit/admin.py`:** Registrar logs de auditoria como somente leitura.
10. **`audit/apps.py` e `audit/signals.py` [Novo]:** Conectar signals de login e registrar logs correspondentes.
11. **`inventory/models.py`:** Adicionar campos `tipo` na Nota Fiscal e `ca` no Lote.
12. **`inventory/views.py`:**
    - Adicionar `tipo` na `FiscalNoteCreateView`.
    - Adicionar `LotDeleteView` para exclusão de itens de rascunhos.
13. **`templates/inventory/nfs_form.html`:** Adicionar seletor de tipo de documento e JS para comportamento condicional.
14. **`templates/inventory/nfs_detail.html`:** Exibir totais calculados, divergências, seletor de C.A. na inserção do lote e botão de exclusão de lote.

---

## 7. Estratégia de Testes

### Testes Automatizados
Adicionar os seguintes testes unitários em `inventory/tests.py` e `ppe/tests.py`:
- Testar criação de Nota Fiscal com `numero` e `serie` nulos (quando tipo = `RECIBO`).
- Testar rejeição de Nota Fiscal com `numero` nulo (quando tipo = `NOTA_FISCAL`).
- Testar bloqueio de confirmação de nota fiscal com divergência de valor sem observações preenchidas.
- Testar a gravação automatizada dos Logs de Auditoria no login e logout.
- Testar imutabilidade e proteção de deleção dos modelos históricos no admin.

### Comandos de Verificação
```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
```
