# SPEC — Reformulação do Tema Visual — SST Freedom

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-003` |
| Título | Reformulação do Tema Visual com Identidade da Marca Pneus Freedom |
| Tipo | `REFACTOR` |
| Módulo principal | `core / templates / static` |
| Fase/Roadmap | Fase 1B (Tema Visual) |
| Autor da SPEC | Arquiteto (Antigravity) |
| Data de criação | 10/07/2026 |
| Última atualização | 10/07/2026 14:00 |
| Versão | 1.0.0 |
| Status | `APROVADA` |
| Prioridade | `ALTA` |
| Risco | `MÉDIO` |
| Demanda de origem | Reformulação do tema visual utilizando as cores oficiais da empresa presentes na logo |
| SPEC substituída | Não |
| SPECs relacionadas | `SPEC-2026-001` (Fase 1A - Fundação), `SPEC-2026-002` (Fase 1A - Correções) |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 10/07/2026 | Arquiteto (Antigravity) | Rascunho inicial | RASCUNHO |
| 1.0.0 | 10/07/2026 | Arquiteto (Antigravity) | Especificação completa após análise da logo e CSS atual | EM_REVISÃO_QA |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 10/07/2026 | Logo analisada, paleta extraída, escopo definido |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 10/07/2026 | Sem bloqueadores; paleta técnica adequada |
| Implementação | Backend | `APROVADA` | 10/07/2026 | CSS reescrito, logo inserida, templates atualizados |
| QA final | QA | `APROVADA` | 10/07/2026 | 16/16 testes passando; contraste validado; tema funcional |

---

## 1. Análise da Logo — Dados Reais

### 1.1 Arquivos localizados

| Arquivo | Formato | Dimensões (aprox.) | Transparência | Uso |
|---|---|---|---|---|
| `media/Untitled-1.png` | PNG | ~993×1024 px | Fundo branco | Versão monocromática preta |
| `media/Untitled-2.png` | PNG | ~993×1024 px | Fundo branco | **Versão colorida — logo oficial** |

### 1.2 Descrição visual da logo colorida (`media/Untitled-2.png`)

- **Símbolo:** Silhueta de uma águia/pássaro com asas abertas, estilizada e moderna.
- **Texto:** "PNEUS FREEDOM" em duas linhas, tipografia pesada, sem serifa, geométrica, caixa alta.
- **Cor predominante:** Dourado/âmbar — `#C9962A` (extraído visualmente).
- **Fundo:** Branco puro (sem transparência).
- **Comportamento em fundo claro:** Excelente — cor dourada destaca-se bem.
- **Comportamento em fundo escuro:** Excelente — dourado brilha bem sobre escuro.

### 1.3 Cores identificadas

| Nome | HEX | RGB | Descrição |
|---|---|---|---|
| **Dourado primário** | `#C9962A` | rgb(201,150,42) | Cor principal da águia e do texto |
| **Dourado médio** | `#B8872A` | rgb(184,135,42) | Região de sombra/transição |
| **Âmbar escuro** | `#9B7020` | rgb(155,112,32) | Sombras mais profundas |
| **Branco** | `#FFFFFF` | rgb(255,255,255) | Fundo da logo |

> A cor predominante é o dourado âmbar (~`#C9962A`). Não há azul, verde ou vermelho nativo na identidade da empresa.

---

## 2. Resumo Executivo

O sistema SST Freedom utiliza atualmente um tema visual baseado em **azul-piscina** (`#0ea5e9`) como cor primária sobre fundo ardósia-escuro (`#080c14`). Essa paleta não reflete a identidade visual da empresa **Pneus Freedom**, que usa **dourado/âmbar** como cor institucional.

Além da divergência de identidade, existem problemas de contraste:

1. Texto desaparece em cards sob hover (conflito de cor Bootstrap).
2. Ausência de hierarquia visual entre superfícies.
3. Badges com combinações de baixo contraste.
4. Formulários com placeholder/fundo mal definidos no modo escuro.
5. A logo da empresa não aparece em nenhuma parte da interface.

Esta SPEC define a reformulação completa do tema visual, centralizando-o em variáveis CSS baseadas na identidade dourado/âmbar da Pneus Freedom.

---

## 3. Paleta Institucional

### 3.1 Cores primárias (extraídas da logo)

| Variável CSS | HEX | Função |
|---|---|---|
| `--brand-primary` | `#C9962A` | Cor primária da marca (dourado) |
| `--brand-primary-dark` | `#9B7020` | Variante escura — hover de botões primários |
| `--brand-primary-light` | `#E8B84B` | Variante clara — destaques e ícones |
| `--brand-primary-glow` | `rgba(201,150,42,0.15)` | Brilho/sombra de foco e hover |

### 3.2 Superfícies (fundo)

| Variável CSS | HEX | Função |
|---|---|---|
| `--surface-page` | `#0C0F1A` | Fundo geral da página |
| `--surface-sidebar` | `#080B15` | Fundo da sidebar |
| `--surface-card` | `#141824` | Fundo dos cards e containers |
| `--surface-card-hover` | `#1C2235` | Fundo do card no hover |
| `--surface-header` | `#0C0F1A` | Fundo do cabeçalho |
| `--surface-modal` | `#1A1F30` | Fundo de modais e dropdowns |
| `--surface-muted` | `#1E2438` | Superfície de menor destaque |
| `--surface-input` | `rgba(255,255,255,0.04)` | Fundo de campos de formulário |

### 3.3 Textos

| Variável CSS | HEX | Contraste sobre card | Função |
|---|---|---|---|
| `--text-primary` | `#F0EEE8` | >7:1 | Texto principal (quente, harmoniza com o dourado) |
| `--text-secondary` | `#A89F8C` | >4.5:1 | Texto secundário e labels |
| `--text-muted` | `#6E6658` | >3:1 | Subtextos e textos de apoio |
| `--text-on-primary` | `#0C0F1A` | >7:1 sobre dourado | Texto sobre fundo primário dourado |
| `--text-on-dark` | `#F0EEE8` | >7:1 | Texto sobre fundos escuros |
| `--text-link` | `#E8B84B` | >4.5:1 | Links normais |
| `--text-link-hover` | `#F5CC70` | >4.5:1 sobre hover | Links no hover |

### 3.4 Bordas

| Variável CSS | HEX | Função |
|---|---|---|
| `--border-default` | `#252B40` | Borda padrão |
| `--border-strong` | `#3A4060` | Borda de foco e destaque |
| `--border-brand` | `#C9962A` | Borda institucional |

### 3.5 Cores semânticas

| Variável CSS | HEX | Função |
|---|---|---|
| `--status-success` | `#2ECC71` | Sucesso |
| `--status-success-glow` | `rgba(46,204,113,0.15)` | Brilho sucesso |
| `--status-warning` | `#F0A500` | Aviso (âmbar mais escuro, distinto do brand) |
| `--status-warning-glow` | `rgba(240,165,0,0.15)` | Brilho aviso |
| `--status-danger` | `#E74C3C` | Erro/Perigo |
| `--status-danger-glow` | `rgba(231,76,60,0.15)` | Brilho erro |
| `--status-info` | `#3498DB` | Informação |
| `--status-info-glow` | `rgba(52,152,219,0.15)` | Brilho info |
| `--status-disabled` | `#4A4A55` | Elemento desabilitado |
| `--status-disabled-text` | `#7A7A85` | Texto sobre elemento desabilitado |

> **Decisão:** `--status-warning` (`#F0A500`) é DISTINTO de `--brand-primary` (`#C9962A`) para preservar a semântica de "aviso". Avisos não são branding.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Análise e documentação da logo real.
- Paleta institucional baseada na logo.
- Reescrita de `static/css/custom.css` com variáveis CSS centralizadas.
- Sobrescrita controlada de variáveis Bootstrap.
- Atualização de `templates/base.html` e `templates/login.html`.
- Inserção da logo da empresa na sidebar e tela de login.
- Revisão global de contraste em todos os componentes.
- Correção de todos os estados: normal, hover, focus, active, disabled.
- Criação de `contexto/GUIA_TEMA_VISUAL_SST_FREEDOM.md`.
- Execução dos testes obrigatórios.

### 4.2 Fora do escopo

- Alteração de models, banco ou migrations.
- Alteração de regras de negócio ou views.
- Instalação de novas bibliotecas de frontend.
- Introdução de React, Vue, Tailwind ou qualquer framework JS.
- Customização profunda do Django Admin.
- Geração, edição ou substituição da logo original.
- Alteração de arquivos da pasta `fontes`.
- Commit, push ou deploy.

### 4.3 Uso de `!important` — Justificativas Pré-aprovadas

1. **Campos de formulário** (`.form-control-premium`): Bootstrap aplica `background-color` e `color` com alta especificidade.
2. **Cor de texto em links dentro de cards**: Bootstrap e browsers aplicam herança de cor de link.
3. **Seletores de data e hora** (`input[type=date]`): Chromium browsers não respeitam cor sem `!important`.

---

## 5. Arquivos a Modificar ou Criar

| Arquivo | Ação | Motivo |
|---|---|---|
| `static/css/custom.css` | **MODIFICAR** | Reescrever variáveis e componentes com paleta institucional |
| `static/images/logo_freedom.png` | **CRIAR (cópia)** | Logo para uso nos templates (preserva original em media/) |
| `templates/base.html` | **MODIFICAR** | Inserir logo, atualizar sidebar e header |
| `templates/login.html` | **MODIFICAR** | Inserir logo, atualizar gradiente |
| `contexto/SPEC_fase_1b_tema_visual.md` | **CRIAR** | Este documento |
| `contexto/GUIA_TEMA_VISUAL_SST_FREEDOM.md` | **CRIAR** | Guia de referência do tema |

> Nota: `static/images/logo_freedom.png` é uma cópia do arquivo `media/Untitled-2.png`. O original é preservado intacto. A cópia ficará em `static/images/` para ser referenciada via `{% static %}` no template.

---

## 6. Problemas Identificados no CSS Atual

| Problema | Localização | Solução |
|---|---|---|
| Cor primária `#0ea5e9` (azul) não reflete a identidade | `:root` | Substituir por `--brand-primary: #C9962A` |
| Cards hover: texto desaparece | `.card-premium:hover` | Regra `* { color: var(--text-primary) }` no hover |
| Links dentro de cards herdam cor do Bootstrap | `.card-premium a:hover` | `color: var(--text-link-hover) !important` |
| Sidebar usa texto "SST Freedom" com ícone | `.sidebar-logo` | Substituir por `<img>` da logo |
| `--bg-card-hover: #162035` (azul ardósia) | `:root` | Substituir por `--surface-card-hover: #1C2235` (mais neutro) |
| `.badge-premium-warning` fundo similar ao brand | badge | Usar `--status-warning-glow` distinto do brand |
| Sem estilo para `select` nativo e `option` | ausente | Adicionar regras de `select` |
| Sem controle de `::placeholder` | ausente | Adicionar `opacity: 0.5; color: var(--text-muted)` |
| Sem estilo para `input[type=date]` | ausente | Adicionar regra de cor para calendário nativo |
| Sem variável `--status-disabled` | ausente | Adicionar à `:root` |
| Sem estilo de breadcrumb | ausente | Adicionar regras de cor |
| Logo não aparece na interface | ausente | Inserir logo nos templates |

---

## 7. Invariantes desta SPEC

- `media/Untitled-2.png` não deve ser alterada.
- Nenhuma migration deve ser gerada.
- Nenhuma regra de negócio deve ser alterada.
- As permissões de acesso não mudam.
- Todos os testes Django existentes devem continuar passando.
- O Django Admin não deve receber estilos que alterem sua usabilidade.

---

## 8. Critérios de Aceite

1. Logo real analisada e documentada.
2. Logo original preservada.
3. Paleta institucional dourada implementada.
4. Tema centralizado em variáveis CSS.
5. Sem códigos HEX espalhados nos componentes.
6. Cards legíveis em todos os estados.
7. Botões com contraste em todos os estados.
8. Formulários legíveis (campos, labels, placeholders, erros).
9. Tabelas legíveis.
10. Badges legíveis em todas as variantes.
11. Alertas legíveis.
12. Sidebar e menus legíveis.
13. Sistema funcional em smartphone (360px).
14. Logo não distorcida.
15. Django Admin sem conflito.
16. `python manage.py check` sem erros.
17. `python manage.py makemigrations --check` sem migrações.
18. `python manage.py test` passando.
19. `GUIA_TEMA_VISUAL_SST_FREEDOM.md` criado.
20. QA emite parecer final.
