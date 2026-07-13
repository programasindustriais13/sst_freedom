# SPEC — Consulta Individual Automática no ConsultaCA

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-007` |
| Título | Consulta Individual Automática no ConsultaCA |
| Tipo | FEATURE |
| Módulo principal | `ppe` |
| Fase/Roadmap | Fase 1b / Expansão |
| Autor da SPEC | Arquiteto / Antigravity |
| Data de criação | 13/07/2026 |
| Última atualização | 13/07/2026 12:00 |
| Versão | 1.0.0 |
| Status | `EM_REVISÃO_QA` |
| Prioridade | ALTA |
| Risco | BAIXO |
| Demanda de origem | Consulta automática on-demand no portal ConsultaCA durante o cadastro/edição de EPI |
| SPEC substituída | Parcialmente a `SPEC-2026-006` (desativa download da base completa) |
| SPECs relacionadas | `SPEC-2026-006` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 13/07/2026 | Arquiteto / Antigravity | Especificação inicial | `EM_REVISÃO_QA` |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 13/07/2026 | Arquitetura aderente com uso de cache local e tratamento de falha não-bloqueante. |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 13/07/2026 | Plano de testes robusto e cobertura de segurança XSS/SSRF completa. |
| Implementação | Backend | `PENDENTE` |  |  |
| QA final | QA | `PENDENTE` |  |  |

---

## 1. Resumo executivo

Esta especificação define o desenvolvimento da integração em tempo real com o portal ConsultaCA para preenchimento e validação automática de dados dos Certificados de Aprovação (CA) de Equipamentos de Proteção Individual (EPI). 

Sempre que o usuário digitar um CA válido no cadastro ou edição de EPI, o sistema disparará uma requisição AJAX para um endpoint Django local. O backend fará o papel de proxy resiliente: consultará a página correspondente no portal ConsultaCA (`https://consultaca.com/NUMERO_DO_CA`), interpretará as informações técnicas por meio de um parser HTML semântico com BeautifulSoup e retornará os dados normalizados para a interface. O resultado será exibido imediatamente abaixo do campo do CA na tela de cadastro de produto, sem a necessidade de recarregar a página e sem bloquear a digitação.

Caso o portal de terceiros esteja indisponível, o sistema emitirá uma notificação amigável instruindo o usuário a prosseguir com o cadastro manual. Os resultados bem-sucedidos e os registros de CAs inexistentes serão cacheados na base local por períodos definidos (24 horas e 1 hora, respectivamente) para reduzir chamadas desnecessárias à rede externa.

---

## 2. Contexto da demanda

### 2.1 Cenário atual

No cenário atual, o sistema possui a tabela de `CertificadoAprovacao`, porém a tentativa anterior de baixar periodicamente a base inteira via FTP do MTE falhou devido ao tamanho dos arquivos e à instabilidade constante do servidor do Ministério. Além disso, existe um trecho de JavaScript provisório no template genérico `organizations/form.html` que consulta uma rota local de AJAX (`/ppe/ca/consultar_ajax/`), a qual apenas busca o CA na tabela local. Se o CA não estiver cadastrado no banco local (o que é o caso comum, já que a sincronização da base inteira falhou), o sistema apenas exibe um aviso de "CA não encontrado na base local" e o usuário é obrigado a digitar todos os dados manualmente.

### 2.2 Problema

O Técnico de SST e o Almoxarife precisam que as informações oficiais do fabricante, descrição oficial, validade e situação (válido, vencido, suspenso) sejam preenchidas de forma automática ao informar o número do CA, para evitar digitação manual demorada e mitigar riscos legais relacionados a CAs vencidos ou suspensos.

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| `templates/organizations/form.html` | `/templates/organizations/form.html:L68-185` | O Javascript de produto está mesclado em um template genérico de formulário e a consulta AJAX apenas retorna registros já inseridos na tabela `CertificadoAprovacao` local. |
| `caepi_sync.py` | `ppe/caepi_sync.py` | Implementação de download de base inteira inoperante devido à instabilidade do link FTP original. |

### 2.4 Causa raiz ou hipótese

A base oficial de CAEPI do MTE não é confiável para download completo via FTP/ZIP. No entanto, o portal público de consulta individual `consultaca.com` está funcional e responde rapidamente a requisições HTTP normais de páginas individuais.

---

## 3. Objetivos

### 3.1 Objetivo principal

- Implementar a consulta automática individual ao ConsultaCA sob demanda a partir do formulário de cadastro/edição de EPI, mantendo o fluxo do formulário não-bloqueante em caso de instabilidade.

### 3.2 Objetivos secundários

- Criar um parser semântico robusto para extrair as variáveis do HTML de resposta.
- Implementar cache local das consultas para otimizar tempo de resposta e evitar bloqueios de rede.
- Separar o JavaScript de produto de dentro do template global `organizations/form.html` para um template herdado específico `ppe/product_form.html`.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Cliente HTTP no backend (`ConsultaCAClient`) com tratamento rígido de timeouts e verificação SSL.
- Parser de HTML (`ConsultaCAParser`) com detecção de rótulos semânticos para os campos descritos na demanda.
- Serviço de orquestração (`ConsultaCAService`) com cache e normalizações.
- Endpoint Django com autenticação e validação segura do parâmetro.
- Interface visual aprimorada baseada em cards na tela de cadastro/edição de produto.

### 4.2 Fora do escopo

- Sincronização periódica ou download em lote de arquivos zipados (estratégia anterior abandonada).
- Automações para contornar CAPTCHA ou login em ConsultaCA (proibido).
- Alteração em telas de Almoxarifado, Nota Fiscal ou entregas.

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | Cadastro ágil e seguro de EPIs com CAs verificados. | Reduz retrabalho de digitação manual e evita cadastro de CAs inválidos. | Gravação (EPI e CA) |
| Almoxarife | Cadastro rápido de itens do almoxarifado. | Autocompleta fabricante e descrição básica de forma segura. | Gravação (EPI) |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `ppe/caepi_sync.py` | Compreender a estratégia anterior. | Deve ser preservada sem uso, ou desativada, não devendo ser executada. O comando `sync_caepi` não será usado pelo usuário. |
| `ppe/views.py` | Inspecionar a view AJAX atual `ca_consultar_ajax`. | O endpoint atual faz busca puramente local. Deve ser modificado para integrar a nova camada de serviço. |
| `templates/organizations/form.html` | Verificar como o formulário e o JS atual funcionam. | Contém Javascript misturado que deve ser movido para um template próprio de EPI. |

### 6.2 Modelos existentes relacionados

| Modelo | App | Responsabilidade | Pode ser reutilizado? |
|---|---|---|---|
| `CertificadoAprovacao` | `ppe` | Armazena dados de CAs verificados e manuais. | Sim, atuará como tabela de persistência definitiva e cache local. |

---

## 7. Premissas e decisões

### 7.1 Premissas

| ID | Premissa | Como validar | Impacto se falsa |
|---|---|---|---|
| PRE-01 | O portal ConsultaCA mantém o padrão de URL `https://consultaca.com/NUMERO_DO_CA`. | Testado via requisição. | A URL precisará ser configurável via settings. |
| PRE-02 | Usuário pode cadastrar manualmente caso a consulta falhe. | O formulário deve permitir submissão mesmo se o card de CA indicar indisponibilidade. | O sistema impedirá o cadastro se o ConsultaCA cair, violando o critério de aceitação de resiliência. |

### 7.2 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-01 | Criar `ppe/ca_services.py` | Colocar tudo em `views.py` ou `models.py`. | Separação de conceitos (Clean Architecture), facilitando a testabilidade unitária sem banco de dados ou requisições de rede reais. |
| ADR-02 | Uso do BeautifulSoup | Regex no HTML bruto ou HTMLParser embutido. | BeautifulSoup permite busca semântica por labels de forma muito mais estável diante de pequenas variações de layout. |

---

## 8. Requisitos funcionais

### RF-001 — Consulta automática por AJAX na digitação do CA

**Descrição:**  
Quando o usuário digita o número do CA nas telas de cadastro ou edição de EPI, o sistema deve aguardar o término da digitação (debounce de 600ms a 1000ms) ou a perda do foco do campo e disparar a consulta em segundo plano.

**Atores:**  
Qualquer usuário autenticado com acesso à tela de cadastro de produto.

**Fluxo principal:**
1. O usuário digita o CA.
2. O Javascript dispara a requisição AJAX para o endpoint local.
3. Exibe indicador discreto: "Consultando CA...".
4. Apresenta os dados retornados em um card visual abaixo do campo.
5. Auto-preenche o campo fabricante (se vazio).

---

## 9. Regras de negócio

### RN-001 — Cache Local e Timeout

- **Regra:** CAs válidos/vencidos/cancelados retornados com sucesso do ConsultaCA devem ser cacheados localmente na tabela `CertificadoAprovacao` por 24 horas (`CONSULTACA_CACHE_TIMEOUT`). CAs consultados mas que retornaram como "Não encontrado" devem ser cacheados por 1 hora (`CONSULTACA_NOT_FOUND_CACHE_TIMEOUT`) para evitar requisições repetitivas maliciosas ao site parceiro. Em caso de falha de conexão (Timeout, Erro HTTP, DNS), nada é salvo no cache local (não salvar falhas como CAs inexistentes).
- **Aplicação:** `ConsultaCAService`
- **Falha esperada:** Nenhuma (devolve dados mock ou passa para o fluxo manual).

### RN-002 — Normalização e Snapshot do CA ao Salvar o EPI

- **Regra:** O número do CA informado no form deve ser normalizado para conter apenas dígitos no backend. No momento em que o EPI (Product) é salvo no banco, o backend deve certificar-se de que existe ou é criada uma instância correspondente em `CertificadoAprovacao` representando o snapshot da data de validade e situação obtidas na consulta recente (seja vinda do cache ou de uma consulta online). Os dados vindos do navegador no POST final não são confiáveis: o backend deve recarregar a partir do banco/cache local para persistir.
- **Aplicação:** `ProductForm.clean` e views de salvamento.

---

## 10. Requisitos não funcionais

### RNF-001 — Segurança (SSRF e XSS)

- O endpoint Django aceitará apenas parâmetros numéricos (dígitos) e limitará o tamanho a 20 caracteres para evitar SSRF ou injeções de parâmetros arbitrários.
- O HTML retornado pelo ConsultaCA nunca deve ser renderizado diretamente ou repassado como HTML bruto no JSON. Apenas os campos JSON com strings sanitizadas serão devolvidos, e o template Django/Javascript usará inserções de texto seguras (`innerText` ou variáveis de template escapadas) para evitar XSS.
- Autenticação obrigatória para acessar o endpoint AJAX.

### RNF-002 — Resiliência

- O timeout de conexão do client HTTP externo será curto (3 segundos de conexão, 5 segundos de leitura) para não travar o processo do servidor web Django em caso de lentidão externa.
- Mensagens de erro amigáveis para o usuário sem traceback técnico.

---

## 11. Plano de implementação

### 11.1 Arquivos previstos

| Arquivo | Ação | Motivo |
|---|---|---|
| `config/settings.py` | MODIFICAR | Registrar variáveis `CONSULTACA_*`. |
| `ppe/ca_services.py` | NOVO | Criar `ConsultaCAClient`, `ConsultaCAParser` e `ConsultaCAService`. |
| `templates/ppe/product_form.html` | NOVO | Template específico para o form de EPI estendendo o template de base. |
| `templates/organizations/form.html` | MODIFICAR | Remover script provisório/ad-hoc anterior. |
| `ppe/views.py` | MODIFICAR | Atualizar views de produto e a view `ca_consultar_ajax`. |
| `ppe/forms.py` | MODIFICAR | Tratar limpeza e normalização do CA no `ProductForm`. |
| `ppe/tests_consultaca.py` | NOVO | Suíte de testes unitários e de integração mockados. |

---

## 12. Estratégia de testes

### 12.1 Matriz de testes

| ID | Tipo | Cenário | Resultado esperado |
|---|---|---|---|
| T-001 | Unitário | Testar parsing de fixture HTML de CA 11223 | Dados extraídos perfeitamente (Fabricante, CNPJ, Situação, Validade). |
| T-002 | Unitário | Testar parsing com contador de dias | Extrai apenas a data sem o contador de dias dinâmico. |
| T-003 | Unitário | Testar cache local recente | Retorna do banco de dados local sem disparar requisição HTTP. |
| T-004 | Unitário | Testar expiração de cache | Dispara requisição HTTP mockada após expiração de 24h. |
| T-005 | Integração | Testar erro DNS/Timeout externo | Retorna resposta JSON com `found: false` e `indisponivel: true` sem quebrar o servidor. |
| T-006 | Segurança | Acessar endpoint AJAX sem autenticação | Retorna status 403 / 401. |
| T-007 | Segurança | Enviar CA com caracteres alfabéticos ou URLs maliciosas | Endpoint sanitiza/rejeita e impede SSRF. |
