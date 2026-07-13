# SPEC — Melhoria no Fluxo de Cadastro e Edição de EPI (ConsultaCA)

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-008` |
| Título | Melhoria no Fluxo de Cadastro e Edição de EPI (ConsultaCA) |
| Tipo | FEATURE |
| Módulo principal | `ppe` |
| Fase/Roadmap | Fase 1b / Expansão |
| Autor da SPEC | Arquiteto / Antigravity |
| Data de criação | 13/07/2026 |
| Última atualização | 13/07/2026 13:40 |
| Versão | 1.0.0 |
| Status | `RASCUNHO` |
| Prioridade | ALTA |
| Risco | BAIXO |
| Demanda de origem | Organização do formulário de EPI, consulta automática guiada pelo número do CA e preenchimento dos dados oficiais com bloqueio de edição. |
| SPEC substituída | Não |
| SPECs relacionadas | `SPEC-2026-007` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 13/07/2026 | Arquiteto / Antigravity | Especificação inicial para melhoria de formulários e mapeamentos | `RASCUNHO` |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 13/07/2026 | Arquitetura de dados oficiais separada dos complementares aprovada. |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 13/07/2026 | Plano de testes e fluxo semelhante a busca de CEP confirmados. |
| Implementação | Backend | `PENDENTE` |  |  |
| QA final | QA | `PENDENTE` |  |  |

---

## 1. Resumo executivo

Esta especificação define a melhoria no fluxo de cadastro e edição de Equipamentos de Proteção Individual (EPI). Atualmente, o usuário preenche a ficha de EPI de forma dispersa e informa o número do CA no meio do processo. 

A partir desta melhoria, o preenchimento será guiado pelo número do CA, de maneira semelhante a uma busca de CEP:
1. O usuário informa primeiramente o número do CA.
2. O sistema executa automaticamente a consulta AJAX ao backend (ConsultaCA).
3. Os dados oficiais obtidos são preenchidos automaticamente na seção correspondente ("Dados oficiais do CA") e travados (somente leitura) contra modificação incorreta.
4. O usuário complementa os dados exclusivamente internos e operacionais do EPI no card correspondente ("Dados complementares do EPI").
5. Caso o número do CA seja alterado após uma consulta, os dados oficiais anteriores são completamente limpos e uma nova consulta é iniciada, preservando os dados complementares não dependentes do CA.

Para que as informações consultadas não sejam perdidas nas consultas locais (cache hits), estenderemos o modelo `CertificadoAprovacao` adicionando campos técnicos que atualmente são parseados do ConsultaCA mas não são persistidos.

---

## 2. Contexto da demanda

### 2.1 Cenário atual

No cenário atual, o formulário de cadastro de EPI renderiza todos os campos de forma genérica (loop `for field in form` no template `organizations/form.html`). O usuário informa o número do CA e o JS dispara uma requisição AJAX que retorna informações básicas e preenche apenas o fabricante (se estiver em branco) e sugere a categoria de proteção.
No entanto, dados oficiais importantes (como descrição detalhada, situação do CA, validade, CNPJ, nome fantasia do fabricante, cidade, UF, processo e natureza de proteção) não são persistidos individualmente e de forma estruturada no cache ou na tabela do banco, sendo mesclados ou ignorados durante consultas subsequentes (cache hits).

### 2.2 Problema

O Técnico de SST e o Almoxarife precisam visualizar claramente quais dados são oficiais do CA e quais são operacionais. Além disso, as informações oficiais não devem ser editáveis na tela do produto para evitar preenchimento incorreto de dados legais (ex: data de validade falsa ou situação de validade adulterada).

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| `ppe/models.py:L69-98` | `CertificadoAprovacao` | Falta de campos como `processo`, `natureza`, `grupo_protecao`, `nome_fantasia`, `cidade`, `uf` e `aprovado_para` na tabela do banco. |
| `ppe/ca_services.py:L330-345` | `_to_dict` | Dados retornados em cache hits não contêm os campos acima, perdendo detalhes úteis parseados da web. |
| `templates/ppe/product_form.html` | `product_form.html` | HTML herdado renderiza os campos em loop genérico sem estrutura de cartões e fluxo direcionado pelo CA. |

---

## 3. Objetivos

### 3.1 Objetivo principal

- Reorganizar a interface de cadastro e edição de EPI com três cartões estruturados, bloqueando a edição de campos oficiais e garantindo que o fluxo comece obrigatoriamente pela validação do CA.

### 3.2 Objetivos secundários

- Estender o modelo `CertificadoAprovacao` para persistir todos os campos extraídos pelo parser.
- Garantir que a alteração do CA limpe o card oficial e dispare nova consulta.
- Validar no backend (ProductForm) os dados oficiais a partir do cache seguro para impedir envio de valores adulterados via POST do navegador.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Alteração no model `CertificadoAprovacao` para incluir campos adicionais oficiais.
- Geração e aplicação de nova migration (não destrutiva).
- Atualização do parser e do serviço de cache no backend para gravar e ler os novos campos.
- Reestruturação do template `templates/ppe/product_form.html` com layout de 3 cards:
  1. Card de Consulta do CA (Início).
  2. Card de Dados oficiais do CA (Somente Leitura).
  3. Card de Dados complementares (Nome do produto, unidade, categoria interna, etc. - Editáveis).
- JavaScript para conduzir o fluxo AJAX de consulta, tratamento de erro, limpeza em caso de alteração e travas.
- Testes automatizados cobrindo os 32 cenários descritos nos requisitos.

### 4.2 Fora do escopo

- Alterações em fluxos de estoque, notas fiscais, entregas de EPI e relatórios.

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | Cadastrar EPIs garantindo integridade das informações legais vinculadas ao CA. | Previne o cadastro de EPIs com informações falsificadas de CA. | Gravação |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `ppe/models.py` | Identificar onde os dados do CA são guardados. | `CertificadoAprovacao` precisa ser expandido com campos oficiais adicionais. |
| `ppe/ca_services.py` | Entender o fluxo de scraping e cache. | Precisa salvar os novos campos no banco e ler no `_to_dict`. |
| `ppe/forms.py` | Entender a validação backend do produto. | `ProductForm` deve obter os dados oficiais do cache e ignorar dados manipulados no frontend. |
| `templates/ppe/product_form.html` | Entender a estrutura da tela atual. | Deve ser completamente reestruturada para suportar o fluxo em 3 cards. |

---

## 7. Premissas e decisões

### 7.1 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-008-1 | Armazenar dados adicionais na tabela `CertificadoAprovacao` | Manter no `Product` ou na sessão do usuário. | Evita duplicação desnecessária em múltiplos produtos que usam o mesmo CA, mantendo o cache normalizado. |
| ADR-008-2 | Renderizar campos oficiais como texto informativo e inputs readonly | Usar campos desabilitados (`disabled`). | `disabled` impede que o Django processe os dados nos formulários padrão, enquanto `readonly` e tags HTML textuais mantêm visualização sem riscos. |

---

## 8. Requisitos funcionais

### RF-001 — Fluxo de Cadastro Iniciado pelo CA

- **Descrição:** O formulário de EPI deve exibir o card "Consultar Certificado de Aprovação" no topo. O usuário deve informar o número do CA antes de prosseguir.
- **Validações:** Se o CA estiver vazio, o card oficial e os dados complementares devem estar sob o estado inicial.
- **Resultado esperado:** Interface focada na consulta inicial.

### RF-002 — Preenchimento Automático sem Recarregamento

- **Descrição:** Após consulta bem-sucedida, os dados oficiais devem ser preenchidos dinamicamente nos respectivos campos do card de Dados Oficiais.
- **Campos Oficiais:** Número do CA, descrição oficial, grupo de proteção, situação, validade, número do processo, natureza, razão social do fabricante, CNPJ, nome fantasia, cidade, UF, aprovado para, fonte da consulta e data/hora da consulta.

### RF-003 — Proteção de Dados Oficiais contra Edição

- **Descrição:** Os campos oficiais carregados não devem permitir alteração manual comum pelo usuário (uso de `readonly` e elementos estáticos).

### RF-004 — Alteração do CA com Limpeza e Reconsulta

- **Descrição:** Se o usuário alterar o número do CA, o sistema limpa os dados oficiais anteriores e dispara nova consulta, mantendo intactos os campos complementares (ex: nome interno, observações).

### RF-005 — Tratamento de Erros e Indisponibilidade

- **Descrição:** Identificar e tratar estados como "Não encontrado", "Vencido" e "Indisponível", exibindo as mensagens corretas sem travar ou quebrar o formulário.

---

## 9. Regras de negócio

### RN-001 — Mapeamento Centralizado dos Campos do CA
- **Regra:** O mapeamento entre a resposta do ConsultaCA e a interface deve ser centralizado e explícito na camada de serviços ou no model.
- **Aplicação:** `ConsultaCAService` e template JS.

### RN-002 — Validação no Servidor
- **Regra:** O backend não deve aceitar nem confiar nos campos oficiais enviados no formulário POST. Ele deve buscar do cache local `CertificadoAprovacao` usando o número do CA e salvar as informações com base nessa fonte oficial.
- **Aplicação:** `ProductForm.clean()`

---

## 10. Modelagem de dados

### 10.1 Alterações no Modelo `CertificadoAprovacao`

Adicionar os campos:
- `grupo_protecao`: CharField(max_length=255, blank=True, null=True)
- `processo`: CharField(max_length=100, blank=True, null=True)
- `natureza`: CharField(max_length=100, blank=True, null=True)
- `nome_fantasia`: CharField(max_length=255, blank=True, null=True)
- `cidade`: CharField(max_length=100, blank=True, null=True)
- `uf`: CharField(max_length=10, blank=True, null=True)
- `aprovado_para`: TextField(blank=True, null=True)

---

## 11. Plano de implementação

### 11.1 Arquivos a alterar/criar

1. `ppe/models.py`: expandir `CertificadoAprovacao`.
2. Criar migration: `.venv/Scripts/python.exe manage.py makemigrations ppe`.
3. `ppe/ca_services.py`: extrair, persistir e retornar os novos campos na view AJAX.
4. `ppe/forms.py`: adequar `ProductForm` para ignorar valores adulterados e validar do banco.
5. `templates/ppe/product_form.html`: reestruturar visualmente em 3 cartões e refatorar JavaScript de controle.
6. `ppe/tests_consultaca.py`: adicionar novos testes cobrindo preenchimentos, limpezas, proteção de campos e validações de backend.

---

## 12. Estratégia de testes

Executar testes locais sem necessidade de internet usando mocks.

```bash
.venv/Scripts/python.exe manage.py test ppe.tests_consultaca
```

---
