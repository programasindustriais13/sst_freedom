# Guia do Tema Visual — SST Freedom

**Arquivo:** `contexto/GUIA_TEMA_VISUAL_SST_FREEDOM.md`
**Versão:** 1.0.0
**Data:** 10/07/2026
**SPEC:** `SPEC-2026-003`
**Status:** Vigente

---

## 1. Logo da Empresa

### 1.1 Arquivo original (não alterar)

```
media/Untitled-2.png
```

- **Empresa:** Pneus Freedom
- **Formato:** PNG
- **Dimensões:** ~993 × 1024 px
- **Transparência:** Não (fundo branco)
- **Versão colorida:** Águia estilizada + texto "PNEUS FREEDOM" em dourado/âmbar
- **Versão monocromática:** `media/Untitled-1.png` (preto e branco)

### 1.2 Cópia para uso nos templates

```
static/images/logo_freedom.png
```

- Cópia idêntica da logo colorida.
- Referenciada nos templates via `{% static 'images/logo_freedom.png' %}`.
- Não duplicar. Usar SEMPRE este caminho nas novas telas.

### 1.3 Uso correto da logo nos templates

```html
{% load static %}
<!-- Sidebar -->
<img src="{% static 'images/logo_freedom.png' %}"
     alt="Logo Pneus Freedom"
     class="sidebar-logo-img">

<!-- Login (maior) -->
<img src="{% static 'images/logo_freedom.png' %}"
     alt="Logo Pneus Freedom"
     class="login-logo-img">
```

### 1.4 Regras da logo

- `max-height: 52px` na sidebar, `80px` no login.
- `object-fit: contain` — nunca distorcer.
- Sempre incluir `alt="Logo Pneus Freedom"`.
- Não usar caminho absoluto do sistema operacional.
- Não editar, recortar ou adicionar filtros CSS na logo.

---

## 2. Paleta Institucional

### 2.1 Cores primárias

| Variável | HEX | Uso |
|---|---|---|
| `--brand-primary` | `#C9962A` | Botão principal, item ativo, acento de card, ícone principal |
| `--brand-primary-dark` | `#9B7020` | Hover de botão primário |
| `--brand-primary-light` | `#E8B84B` | Ícones secundários, links, destaque |
| `--brand-primary-glow` | `rgba(201,150,42,0.15)` | Sombra de foco, hover sutil |

### 2.2 Superfícies

| Variável | HEX | Camada |
|---|---|---|
| `--surface-page` | `#0C0F1A` | Fundo geral da página (mais externa) |
| `--surface-sidebar` | `#080B15` | Sidebar |
| `--surface-card` | `#141824` | Cards, containers, tabelas |
| `--surface-card-hover` | `#1C2235` | Card sob hover |
| `--surface-modal` | `#1A1F30` | Modais, dropdowns, popovers |
| `--surface-muted` | `#1E2438` | Superfície de menor destaque |
| `--surface-input` | `rgba(255,255,255,0.04)` | Campos de formulário |

### 2.3 Textos

| Variável | HEX | Contraste mínimo | Uso |
|---|---|---|---|
| `--text-primary` | `#F0EEE8` | 7:1 sobre card | Texto principal, títulos |
| `--text-secondary` | `#A89F8C` | 4.5:1 sobre card | Labels, subtítulos, texto de apoio |
| `--text-muted` | `#6E6658` | 3:1 sobre card | Placeholders, texto mínimo |
| `--text-on-primary` | `#0C0F1A` | 7:1 sobre dourado | Texto em botão primário |
| `--text-link` | `#E8B84B` | 4.5:1 sobre card | Links |
| `--text-link-hover` | `#F5CC70` | 4.5:1 sobre hover | Links no hover |

### 2.4 Bordas

| Variável | HEX | Uso |
|---|---|---|
| `--border-default` | `#252B40` | Borda padrão de cards e inputs |
| `--border-strong` | `#3A4060` | Borda de foco, destaque |
| `--border-brand` | `#C9962A` | Borda institucional dourada |

### 2.5 Status semânticos

| Variável | HEX | Significado |
|---|---|---|
| `--status-success` | `#2ECC71` | Sucesso, ativo, válido |
| `--status-warning` | `#F0A500` | Aviso, atenção |
| `--status-danger` | `#E74C3C` | Erro, perigo, crítico |
| `--status-info` | `#3498DB` | Informação, neutro |
| `--status-disabled` | `#4A4A55` | Elemento desabilitado |
| `--status-disabled-text` | `#7A7A85` | Texto desabilitado |

> ⚠️ **REGRA:** `--status-warning` é DIFERENTE de `--brand-primary`. Não usar o dourado da marca para avisos — isso confunde identidade com semântica de risco.

---

## 3. Componentes — Padrões de Uso

### 3.1 Cards

```html
<!-- Card simples -->
<div class="card-premium">...</div>

<!-- Card com acento colorido lateral -->
<div class="card-premium card-primary">...</div>   <!-- dourado -->
<div class="card-premium card-success">...</div>   <!-- verde -->
<div class="card-premium card-warning">...</div>   <!-- âmbar -->
<div class="card-premium card-danger">...</div>    <!-- vermelho -->

<!-- Card clicável (envolto em âncora) -->
<a href="..." class="text-decoration-none">
    <div class="card-premium card-primary h-100">
        <h5>Título</h5>
        <p class="text-secondary small">Descrição</p>
    </div>
</a>
```

**Regras de card:**
- Sempre usar `class="card-premium"` — não criar cards com fundo/borda inline.
- Em cards clicáveis, a âncora envolve o card inteiro.
- Não usar `color` global em `.card:hover` sem garantir contraste dos filhos.
- Verificar texto em: normal, hover, focus, active, disabled.

### 3.2 Botões

```html
<!-- Primário (identidade da empresa) -->
<button class="btn btn-premium btn-premium-primary">
    <i class="bi bi-check-lg me-2"></i> Salvar
</button>

<!-- Perigo -->
<button class="btn btn-premium btn-premium-danger">
    <i class="bi bi-trash3-fill me-2"></i> Excluir
</button>

<!-- Outline primário -->
<a href="..." class="btn btn-outline-primary btn-premium">Ver Todos</a>

<!-- Outline secundário (voltar, cancelar) -->
<a href="..." class="btn btn-outline-secondary btn-premium">Voltar</a>
```

**Regras de botão:**
- Ações primárias: `btn-premium-primary` (dourado).
- Ações destrutivas: `btn-premium-danger` (vermelho).
- Ações secundárias: `btn-outline-secondary`.
- Navegação/filtro: `btn-outline-primary`.
- Nunca usar apenas cor para diferenciar ação crítica de ação normal.

### 3.3 Badges

```html
<!-- Semânticos (legíveis em modo escuro) -->
<span class="badge-premium badge-premium-success">Ativo</span>
<span class="badge-premium badge-premium-warning">Pendente</span>
<span class="badge-premium badge-premium-danger">Vencido</span>
<span class="badge-premium badge-premium-info">C.A. Vigente</span>
<span class="badge-premium badge-premium-brand">Novidade</span>

<!-- Bootstrap native (funcionam com o tema) -->
<span class="badge bg-success">Conferido</span>
<span class="badge bg-danger">Cancelado</span>
<span class="badge bg-warning">Rascunho</span>
```

**Combinações PROIBIDAS:**
- ❌ Texto amarelo/dourado sobre fundo branco (sem borda).
- ❌ Texto verde claro sobre fundo branco (sem borda).
- ❌ Vermelho escuro sobre fundo preto sem contraste.
- ✅ Sempre usar o par `badge-premium-*` com fundo escuro semitransparente e borda.

### 3.4 Formulários

```html
<!-- Label + Input padrão -->
<div class="mb-3">
    <label for="id_campo" class="form-label fw-semibold">Nome do Campo</label>
    <input type="text" id="id_campo" class="form-control" required>
    <div class="form-text">Texto de ajuda opcional.</div>
</div>

<!-- Select -->
<select id="id_select" class="form-select">
    <option value="">Selecione...</option>
</select>

<!-- Campo inválido -->
<input type="text" class="form-control is-invalid">
<div class="invalid-feedback">Mensagem de erro clara.</div>
```

**Regras de formulário:**
- Sempre associar `<label>` ao campo (`for` + `id`).
- Nunca usar placeholder como substituto de label.
- Campo desabilitado: `disabled` — visível, mas não interativo.
- Não colocar fundo escuro institucional em inputs — usar `--surface-input`.

### 3.5 Tabelas

```html
<!-- Tabela premium -->
<table class="table table-premium">
    <thead>
        <tr>
            <th class="border-0">Coluna</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="text-light fw-semibold">Dado principal</td>
        </tr>
    </tbody>
</table>

<!-- Tabela Bootstrap dark (alternativa) -->
<table class="table table-dark table-hover mb-0"
       style="--bs-table-bg: transparent; --bs-table-border-color: var(--border-default);">
    ...
</table>
```

**Regras de tabela:**
- Cabeçalho: `text-muted` com `font-size: 0.72rem`.
- Célula principal: `text-light` (alias de `--text-primary`).
- Célula secundária: herda `--text-secondary` da tabela.
- Hover: sempre legível — não usar fundo que anule o texto.

### 3.6 Alertas Django

Os alertas são renderizados automaticamente em `base.html`. Classes CSS do tema garantem contraste.

Mapeamento de `message.tags`:
- `success` → `alert-success` (fundo verde semitransparente, texto `#5EE890`)
- `warning` → `alert-warning` (fundo âmbar semitransparente, texto `#F5C23E`)
- `error` → `alert-danger` (fundo vermelho semitransparente, texto `#F08080`)
- `info` / padrão → `alert-info` (fundo azul semitransparente, texto `#74B9E8`)

---

## 4. Regras de Contraste

| Texto | Fundo | Relação mínima | Status |
|---|---|---|---|
| `--text-primary` (`#F0EEE8`) | `--surface-card` (`#141824`) | >7:1 | ✅ |
| `--text-secondary` (`#A89F8C`) | `--surface-card` (`#141824`) | >4.5:1 | ✅ |
| `--text-muted` (`#6E6658`) | `--surface-card` (`#141824`) | >3:1 | ✅ |
| `--text-on-primary` (`#0C0F1A`) | `--brand-primary` (`#C9962A`) | >7:1 | ✅ |
| `--text-link` (`#E8B84B`) | `--surface-card` (`#141824`) | >4.5:1 | ✅ |
| `--status-success` (`#2ECC71`) | `--surface-card` (`#141824`) | >4.5:1 | ✅ |
| `--status-danger` (`#E74C3C`) | `--surface-card` (`#141824`) | >4.5:1 | ✅ |
| `--status-warning` (`#F0A500`) | `--surface-card` (`#141824`) | >4.5:1 | ✅ |
| `--status-info` (`#3498DB`) | `--surface-card` (`#141824`) | >3:1 | ✅ |

---

## 5. Combinações Proibidas

| ❌ Combinação | Motivo |
|---|---|
| Texto `--text-muted` sobre fundo branco | Contraste insuficiente |
| Texto `--brand-primary` como cor de aviso | Confunde identidade com semântica |
| Card hover com `color: var(--brand-primary)` sem verificar filhos | Filhos ficam dourados sobre fundo quase-dourado |
| `color: inherit` em link dentro de card escuro | Herda cor de link azul do Bootstrap |
| Badge sem fundo sobre superfície clara | Texto some |
| `!important` para resolver problema de especificidade sem documentar | Cria cascata imprevisível |

---

## 6. Orientações para Futuras Telas

1. **Sempre usar variáveis CSS** — nunca hardcodar HEX diretamente em templates ou componentes.
2. **Testar o hover** de todos os cards clicáveis antes de marcar como concluído.
3. **Usar `.card-premium`** para todos os containers de conteúdo, sem exceção.
4. **Verificar em 360px** — toda nova tela deve ser revisada no menor breakpoint.
5. **Incluir `alt` na logo** — `alt="Logo Pneus Freedom"` sempre.
6. **Não criar CSS isolado por tela** — se um estilo se repetir, ele vai para `custom.css`.
7. **Respeitar a hierarquia de superfícies:**
   - Página (`--surface-page`) → Card (`--surface-card`) → Modal (`--surface-modal`)
   - Não usar a mesma cor em dois níveis adjacentes.
8. **Botão primário = cor da empresa** — ações secundárias usam outline ou cores semânticas.
9. **Placeholders não substituem labels** — ambos devem coexistir.
10. **`!important` com justificativa** — documentar no SPEC antes de usar.

---

## 7. Arquivo CSS de Referência

```
static/css/custom.css
```

Este é o ÚNICO arquivo de tema do sistema. Não criar `custom2.css`, `fixes.css`, `overrides.css` etc.

Estrutura do arquivo:
1. Import Google Fonts
2. Variáveis `:root` — paleta institucional
3. Sobrescrita Bootstrap
4. Reset e estilos globais
5. Logo
6. Sidebar
7. Main Content e Header
8. Cards
9. Botões
10. Formulários
11. Tabelas
12. Badges
13. Alertas
14. List Group
15. Modais e Dropdowns
16. Paginação
17. Offcanvas
18. Responsividade
19. Animações
20. Isolamento Django Admin
21. Utilitários
