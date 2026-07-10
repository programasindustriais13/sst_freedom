# SPEC — Infraestrutura Inicial de Versionamento e Dependências

**Arquivo:** `contexto/SPEC_fase_0_infraestrutura_inicial.md`  
**Versão:** 1.0.0  
**Data de criação:** 09/07/2026  
**Status:** APROVADA  
**Prioridade:** ALTA  
**Risco:** BAIXO  

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-000` |
| Título | Infraestrutura Inicial de Versionamento e Dependências |
| Tipo | DOCUMENTATION |
| Módulo principal | infraestrutura |
| Fase/Roadmap | Fase 0 |
| Autor da SPEC | Arquiteto (Antigravity) |
| Data de criação | 09/07/2026 |
| Última atualização | 09/07/2026 20:10 |
| Versão | 1.0.0 |
| Status | `APROVADA` |
| Prioridade | ALTA |
| Risco | BAIXO |
| Demanda de origem | Criação de .gitignore e requirements.txt do projeto SST Freedom |
| SPEC substituída | Não |
| SPECs relacionadas | `SPEC_fase_1a_fundacao_estoque_epi.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 09/07/2026 | Arquiteto (Antigravity) | Rascunho inicial com requisitos e dependências | RASCUNHO |
| 1.0.0 | 09/07/2026 | QA (Antigravity) | Revisão, aprovação da SPEC e validação da entrega | APROVADA |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 09/07/2026 | Arquivos de infraestrutura mapeados de acordo com a Constituição |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 09/07/2026 | Padrões de segurança e versões coerentes |
| Implementação | Backend | `APROVADA` | 09/07/2026 | .gitignore e requirements.txt criados com sucesso |
| QA final | QA | `APROVADA` | 09/07/2026 | Arquivos validados, sem conflitos ou duplicidades |

---

## 1. Resumo executivo

Esta especificação define a criação da infraestrutura básica de versionamento e dependências do projeto **SST Freedom**. O objetivo é criar os arquivos `.gitignore` e `requirements.txt` na raiz da pasta do projeto. 

O `.gitignore` será configurado para evitar o envio de arquivos de ambiente local, temporários, cache, bancos de dados locais e chaves privadas, sem interferir com os arquivos vitais do Django e da pasta `contexto`.

O `requirements.txt` definirá as dependências necessárias para a Fase 1A do projeto, garantindo que as versões dos pacotes sejam compatíveis com o **Django 5.2 LTS** e entre si. Pacotes desnecessários ou que não serão usados de imediato (como Celery, Redis e Channels) foram explicitamente removidos do escopo.

---

## 2. Contexto da demanda

### 2.1 Cenário atual
O repositório do projeto **SST Freedom** possui a estrutura inicial de pastas e código Django, porém não possui os arquivos `.gitignore` e `requirements.txt`. O ambiente virtual local foi inicializado pelo usuário, mas a instalação de dependências falhou por falta do arquivo `requirements.txt`.

### 2.2 Problema
A ausência do `.gitignore` expõe o repositório ao risco de inclusão acidental de arquivos locais (como a pasta `.venv`, bancos de dados de teste `db.sqlite3` e arquivos de configuração `.env` contendo segredos). A ausência do `requirements.txt` impede a padronização e instalação correta do ambiente de desenvolvimento.

---

## 3. Objetivos

### 3.1 Objetivo principal
Criar os arquivos de infraestrutura `.gitignore` e `requirements.txt` na raiz do workspace, totalmente aderentes aos padrões de qualidade da Constituição do projeto.

---

## 4. Escopo

### 4.1 Dentro do escopo
- Criação do arquivo `.gitignore` com exclusão de arquivos de SO, IDEs, caches, Logs, banco de dados local SQLite, arquivos de build e pastas de ambiente virtual.
- Inclusão explícita/preservação de arquivos de controle do projeto (ex: `manage.py`, `requirements.txt`, `.env.example`, migrações, templates, static, pasta `contexto`).
- Criação do arquivo `requirements.txt` contendo as dependências básicas para rodar o Django 5.2 LTS, psycopg, Pillow, openpyxl, reportlab, django-crispy-forms, crispy-bootstrap5, django-cleanup, django-storages, boto3, whitenoise, gunicorn, pytest, pytest-django, ruff, black, isort, mypy e ipython.

### 4.2 Fora do escopo
- Criação de novo projeto Django.
- Instalação automática ou manual de dependências no virtual environment.
- Modificação de arquivos nas subpastas existentes (como `accounts`, `core`, etc.).
- Modificação de arquivos de referência na pasta `fontes`.
- Execução de comandos git (commit/push).

---

## 5. Estado atual do código

### 5.1 Arquivos lidos
- [contexto/constitution.md](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/contexto/constitution.md): para conformidade com as regras do projeto.
- [contexto/SPEC_TEMPLATE.md](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/contexto/SPEC_TEMPLATE.md): para uso como base de estrutura da SPEC.
- [Instrucoes_dev.txt](file:///c:/Users/Unicompo/Documents/03_PYTHON1/09%20-%20SST_EPI/Instrucoes_dev.txt): para validar comandos locais de instalação de dependências.

---

## 6. Premissas e decisões

### 6.1 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-001 | Locking de versões relaxado/compatível | Fixar versões absolutas (ex: `Django==5.2.0`) | O uso de faixas compatíveis (ex: `Django>=5.2,<5.3` ou `Django~=5.2.0`) garante que correções de segurança (patches) do Django 5.2 LTS sejam baixadas automaticamente sem quebrar o projeto. |
| ADR-002 | Estrutura organizada e comentada | Arquivo de requisitos flat e sem comentários | Agrupar as dependências por funcionalidade (Framework, Banco, Produção, etc.) facilita a manutenção e auditoria do projeto. |

### 6.2 Premissas

| ID | Premissa | Como validar | Impacto se falsa |
|---|---|---|---|
| PRE-001 | A versão do Python no host e no `.venv` deve ser >= 3.10 (recomendado 3.12 ou 3.13). | Executar `python --version` com o ambiente virtual ativo. | O `pip` falhará ao instalar dependências, visto que o Django 5.2 requer no mínimo Python 3.10. |

---

## 7. Requisitos

### 7.1 Requisitos do `.gitignore`
Deve ignorar, no mínimo:
- Python: `__pycache__/`, `*.py[cod]`, `*$py.class`
- Virtual Environment: `.venv/`, `venv/`, `env/`, `ENV/`
- Build: `build/`, `dist/`, `*.egg-info/`
- Logs: `*.log`, `logs/`
- SQLite: `db.sqlite3`, `db.sqlite3-journal`
- Environment: `.env`, `.env.*` (exceto `.env.example`, que deve ser rastreado)
- VSCode: `.vscode/`
- JetBrains: `.idea/`
- Windows/macOS: `Thumbs.db`, `Desktop.ini`, `.DS_Store`
- Cache: `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.cache/`
- Coverage: `.coverage`, `htmlcov/`
- Static Coletado / Media: `staticfiles/`, `media/`
- Node: `node_modules/`

Não deve ignorar:
- `manage.py`, `README.md`, `requirements.txt`, `pyproject.toml`, `.env.example`, migrations, templates, static do projeto e pasta `contexto`.

### 7.2 Requisitos do `requirements.txt`
- Django: compatível com **Django 5.2 LTS**.
- Banco: `psycopg[binary]`
- Configurações: `python-decouple` e `python-dotenv` (justificada pelo uso de `import dotenv` em `config/settings.py` pré-existente, respeitando a regra de não alterar código).
- Imagens: `Pillow`
- Excel: `openpyxl`
- PDF: `reportlab`
- Componentes Bootstrap: `django-crispy-forms`, `crispy-bootstrap5`
- Uploads: `django-cleanup`
- Armazenamento futuro: `django-storages`, `boto3`
- Produção: `whitenoise`, `gunicorn`
- Desenvolvimento: `ipython`
- Testes: `pytest`, `pytest-django`
- Qualidade/Formatação/Ordenação/Tipagem: `ruff`, `black`, `isort`, `mypy`
- Sem dependências não utilizadas (ex: Celery, Redis, Channels, DRF, HTMX, Pandas, Numpy).

---

## 8. Plano de implementação

### 8.1 Arquivos previstos

| Arquivo | Ação | Motivo |
|---|---|---|
| `.gitignore` | `NEW` | Criação do arquivo de exclusão de versionamento. |
| `requirements.txt` | `NEW` | Criação do arquivo de definição de dependências. |

### 8.2 Passos
1. O Arquiteto submete a SPEC como `RASCUNHO` (completo nesta etapa).
2. O QA revisa a SPEC, verifica se atende às regras constitucionais e atualiza para `APROVADA_PARA_IMPLEMENTAÇÃO`.
3. O Backend escreve `.gitignore` e `requirements.txt` seguindo a especificação.
4. O QA valida os arquivos criados e emite parecer final.

---

## 9. Estratégia de testes

### 9.1 Validação do `.gitignore`
- Executar `git status --ignored` para checar se arquivos indesejados são ignorados e arquivos cruciais não são ignorados.

### 9.2 Validação do `requirements.txt`
- Verificar se não há pacotes duplicados.
- Verificar se todos os pacotes possuem suporte ao Django 5.2.
