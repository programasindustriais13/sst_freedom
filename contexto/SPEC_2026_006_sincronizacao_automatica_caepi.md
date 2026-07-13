# SPEC — Sincronização Automática da Base CAEPI (MTE)

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-006` |
| Título | Sincronização Automática da Base CAEPI (MTE) e Consulta Local |
| Tipo | FEATURE |
| Módulo principal | `ppe` |
| Fase/Roadmap | Fase 1b / Expansão |
| Autor da SPEC | Arquiteto / Antigravity |
| Data de criação | 13/07/2026 |
| Última atualização | 13/07/2026 09:30 |
| Versão | 1.0.0 |
| Status | `EM_REVISÃO_QA` |
| Prioridade | ALTA |
| Risco | MÉDIO |
| Demanda de origem | Sincronização automática e periódica da base oficial de Certificados de Aprovação (CA) |
| SPEC substituída | Não |
| SPECs relacionadas | Não se aplica |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 13/07/2026 | Arquiteto / Antigravity | Especificação inicial | `EM_REVISÃO_QA` |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 13/07/2026 | Arquitetura aderente e em conformidade com as diretrizes do projeto. |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 13/07/2026 | Cobertura completa de cenários de erro e testes de idempotência definidos. |
| Implementação | Backend | `PENDENTE` |  |  |
| QA final | QA | `PENDENTE` |  |  |

---

## 1. Resumo executivo

Esta especificação define o desenvolvimento de um sistema de sincronização automática e manual para a base oficial de Certificados de Aprovação (CA) de Equipamentos de Proteção Individual (EPI), mantida pelo Ministério do Trabalho e Emprego (MTE). 

O sistema importará os dados a partir da fonte oficial (FTP do MTE) no formato `tgg_export_caepi.zip` contendo o arquivo `tgg_export_caepi.txt`, executará a normalização dos dados e atualizará a tabela local no banco de dados. Isso garantirá que o sistema possa consultar e preencher os dados de CA de forma autônoma e em tempo real, sem depender da estabilidade do servidor externo durante o uso normal do sistema pelos usuários nas telas de cadastro e movimentação de EPI.

Os principais riscos abordados incluem o tempo de travamento das tabelas durante o processamento de 125 mil registros (mitigado por processamento em lote/bulk operations), instabilidade ou timeouts na rede pública, arquivos corrompidos ou incompletos (resolvidos com regras rígidas de validação pré-importação e rollback automático) e garantia de que os registros antigos não sejam apagados indevidamente (resolvido com exclusão lógica e flag de presença na fonte).

---

## 2. Contexto da demanda

### 2.1 Cenário atual

Atualmente, o sistema possui o modelo `CertificadoAprovacao`, mas a base de dados oficial do CAEPI não é carregada de forma automática e integrada. Existe apenas um comando manual simples (`sync_caepi.py`) que importa a partir de um arquivo local, sem tratar downloads da rede pública, detecção automatizada de codificação ou exclusão lógica de registros removidos na fonte oficial. Além disso, as telas de cadastro e nota fiscal criam registros "manuais" sem validação automática em relação à base oficial completa.

### 2.2 Problema

O Técnico de SST e o Almoxarife precisam que as telas de cadastro de produto e recebimento de Notas Fiscais identifiquem de imediato se o número do CA fornecido é válido, quem é o fabricante oficial, qual a validade física/legal e qual a descrição oficial do equipamento. Sem uma base local de CAs sincronizada e atualizada periodicamente, o sistema fica vulnerável a erros humanos de digitação e inconsistências que invalidam a segurança jurídica dos EPIs distribuídos.

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| `sync_caepi.py` | `ppe/management/commands/sync_caepi.py` | Existe comando inicial rudimentar, mas que exige intervenção manual e download prévio pelo operador, não tratando compactação ZIP nem resiliência de rede. |
| `CertificadoAprovacao` | `ppe/models.py` | Modelo atual não possui CNPJ, observações de restrições ou identificadores de versão de importação para auditoria de remoção na fonte. |

### 2.4 Causa raiz ou hipótese

- Causa confirmada: Sim
- Descrição: A ausência de um client FTP/HTTP automatizado com suporte a extração de ZIP na memória, validação de integridade estrutural e bulk updates gera retrabalho e dependência de planilhas locais externas.

---

## 3. Objetivos

### 3.1 Objetivo principal

Implementar um serviço de sincronização da base CAEPI resiliente, automático (semanal) e manual que atualize a base de dados local de CAs de forma idempotente e segura, reduzindo a zero a necessidade de downloads manuais de arquivos pelo administrador.

### 3.2 Objetivos secundários

- Otimizar o processamento para tratar 125 mil linhas em menos de 30 segundos no banco local.
- Adicionar visualizações intuitivas de verificação de CA em tempo real no cadastro de EPIs e lançamento de NFs por meio de AJAX local.
- Proteger o banco local de dados incompletos ou corrompidos em caso de falha a qualquer momento da importação.

### 3.3 Indicadores de sucesso

| Indicador | Situação atual | Meta | Como medir |
|---|---|---|---|
| Tempo de carga inicial | N/A (Manual) | < 30 seg | Logs de execução da sincronização |
| Independência de rede | Baixa (Manual) | 100% local no uso | Teste simulando rede externa offline |

---

## 4. Escopo

### 4.1 Dentro do escopo

- Criação do serviço `caepi_sync.py` no app `ppe` contendo o client, parser, validador e serviço principal.
- Atualização do modelo `CertificadoAprovacao` com novos campos: `cnpj`, `observacoes_laudo`, `presente_na_fonte` e `versao_importacao`.
- Criação do modelo `CAEPISyncLog` para auditoria e histórico de execuções.
- Reescrita do comando `python manage.py sincronizar_caepi` para suportar execução manual, download automático, `--dry-run`, `--arquivo` local e `--forcar`.
- Implementação de um mecanismo de concorrência por lock no banco de dados baseado em status ativo no `CAEPISyncLog`.
- Criação de views AJAX para consulta rápida e autocompletar de CAs no formulário de produtos e notas fiscais.
- Criação de testes unitários e de integração locais simulados (mocks) para cobrir 100% das regras de negócio.
- Documentação de implantação detalhada.

### 4.2 Fora do escopo

- Scraping da tela pública de consulta do MTE ou contorno de CAPTCHAs.
- Agendador de filas de segundo plano complexo (Celery) caso não esteja previamente instalado no projeto (usar-se-á comandos de gerenciamento com suporte para agendador Cron ou Windows Task Scheduler).

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | Validar e selecionar CAs corretos no cadastro e entrega de EPIs de forma rápida | Garante a legalidade e proteção jurídica das fichas de EPI | Escopo geral de SST |
| Almoxarife | Receber Notas Fiscais e cadastrar novos lotes verificar os CAs instantaneamente | Previne o recebimento de lotes com CAs vencidos ou suspensos | Escopo operacional de estoque |

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `ppe/models.py` | Analisar campos do CertificadoAprovacao | O modelo armazena os campos básicos, mas carece de controle de versão/presença e campos estendidos como CNPJ. |
| `ppe/management/commands/sync_caepi.py` | Analisar comando existente | O comando atual lê apenas arquivos CSV/Excel locais passados por argumento de forma básica e ineficiente. |
| `templates/organizations/form.html` | Verificar renderização de formulários | Usa Django Forms padrão, necessita de JS progressivo para feedback do CA. |
| `templates/inventory/nfs_form.html` | Verificar cadastro rápido no modal | Usa requisição AJAX própria, necessita de validação de CA integrada. |

---

## 7. Premissas e decisões

### 7.1 Premissas

| ID | Premissa | Como validar | Impacto se falsa |
|---|---|---|---|
| ASM-001 | O servidor FTP do MTE é instável ou lento. | Download via socket com timeout e retentativas | Execuções paradas por tempo indeterminado |
| ASM-002 | A base oficial de CAs pode ter campos nulos ou corrompidos. | Validação estrita por linha com descarte seguro | Inconsistência de integridade no banco |

### 7.2 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-001 | Usar lock baseado no banco (`CAEPISyncLog`) | Lock em arquivo / Redis | Compatibilidade multiplataforma nativa (Windows e Linux) sem dependência externa. |
| ADR-002 | Processar dados em blocos (`bulk_create` e `bulk_update` em lotes de 2000) dentro de transação atômica única | Exclusão total e recriação / Lote individual | Evita locks prolongados no banco e previne a indisponibilidade de consulta pelos usuários durante a atualização. |
| ADR-003 | Flag `presente_na_fonte` para desativados | Deletar fisicamente registros ausentes | Preserva o histórico legal de CAs que já foram entregues aos trabalhadores. |

---

## 8. Requisitos funcionais

### RF-001 — Sincronização Automática e Manual (Comando Django)

**Descrição:**  
O sistema deve expor o comando `python manage.py sincronizar_caepi` para sincronizar os CAs a partir do servidor FTP oficial. O comando deve aceitar `--dry-run`, `--arquivo` local (para testes off-line), `--forcar` (ignora o hash anterior do arquivo) e `--verbose`.

**Atores:**  
Administrador do Sistema / Cron semanal.

**Pré-condições:**
- Conexão de rede ativa (salvo com a opção `--arquivo`).
- Nenhuma outra sincronização em andamento.

**Fluxo principal:**
1. O comando é disparado.
2. É criado um registro `CAEPISyncLog` com status `INICIADO`.
3. O client baixa o ZIP temporariamente da fonte configurada (FTP).
4. O parser extrai o arquivo e valida a assinatura, tamanho e integridade.
5. Se for idêntico ao anterior (SHA-256 coincide) e não houver flag `--forcar`, o processo é encerrado com status `IGNORADO`.
6. Caso contrário, lê as linhas e valida cada registro em lote (CNPJ válido, CA numérico, etc.).
7. Em lote, grava no banco de dados.
8. Atualiza CAs ausentes na nova base com `presente_na_fonte = False`.
9. Salva log com status `CONCLUIDO`.

**Fluxos alternativos:**
- Se o download falhar: tenta novamente até `CAEPI_SYNC_MAX_RETRIES` vezes. Se persistir, atualiza o log para `FALHOU` com a mensagem de erro e libera o lock. Os dados anteriores permanecem inalterados.
- Se o percentual de registros válidos cair de maneira anormal (ex: queda > 20% do volume total ou arquivo vazio), bloqueia o processamento por segurança e salva log como `FALHOU`.

---

### RF-002 — Consulta Local Inteligente de CA (AJAX)

**Descrição:**  
Ao digitar o número do CA nas telas de cadastro de produto (EPI) ou recebimento de Nota Fiscal, o sistema realiza uma consulta AJAX ao banco de dados local.

**Atores:**  
Técnico SST / Almoxarife.

**Validações:**
- Busca pelo número normalizado (dígitos).
- Retorna JSON contendo a situação oficial (VÁLIDO, VENCIDO, etc.), fabricante, equipamento e validade.

**Resultado esperado:**
- Exibe de forma visível ao lado do campo do formulário o status do CA encontrado na base local e preenche automaticamente o fabricante.

---

## 9. Regras de negócio

### RN-001 — Unicidade e Normalização de CAs
- **Regra:** O número do CA gravado no banco de dados deve ser normalizado (somente dígitos numéricos). O campo `numero` é único na tabela.
- **Motivo:** Evita cadastros redundantes baseados em variações de digitação (ex: "CA-12345", "12.345", "12345").
- **Aplicação:** No parser e validador antes de salvar.

### RN-002 — Limite Seguro de Falha Estrutural
- **Regra:** A importação deve ser abortada imediatamente e nenhum dado persistido se a base lida for menor do que `CAEPI_SYNC_MIN_RECORD_RATIO` (padrão: 80%) em relação ao total de registros já salvos atualmente no sistema.
- **Motivo:** Evita corrupção silenciosa ou perda da base de dados caso a fonte oficial envie um arquivo incompleto ou corrompido.
- **Aplicação:** No validador antes da escrita no banco.

---

## 10. Requisitos não funcionais

### RNF-001 — Performance
- O processamento de 125 mil registros deve ocorrer utilizando bulk updates em lotes configuráveis (ex: `CAEPI_SYNC_BATCH_SIZE=2000`) para minimizar a alocação de memória e tempo de CPU.

### RNF-002 — Compatibilidade e Resiliência
- O download deve utilizar tratamento de Socket timeouts configurável e fechamento correto de sockets de rede para evitar vazamento de portas de rede.

---

## 11. Permissões e segregação de acesso

### 11.1 Matriz de permissões

| Recurso/Ação | Técnico SST | Almoxarife | Administrador | Observação |
|---|---:|---:|---:|---|
| Sincronização Manual | — | — | Sim (via terminal/admin) | Comando técnico restrito |
| Consulta de CA | R | R | R | Uso geral nas telas operacionais |
| Edição Manual de CA | — | — | Sim (com justificativa) | Admin Django somente |

---

## 12. Fluxos e máquinas de estado

### 12.1 Estados de Sincronização

```text
[INICIADO]
→ [BAIXANDO]
→ [PROCESSANDO]
→ [CONCLUIDO] ou [CONCLUIDO_ALERTAS] ou [FALHOU] ou [IGNORADO]
```

---

## 13. Modelagem de dados

### 13.1 Novos modelos

#### Modelo: `CAEPISyncLog`
**Responsabilidade:** Registrar o histórico de cada execução e atuar como lock distribuído.

| Campo | Tipo | Obrigatório | Default | Índice |
|---|---|---:|---|---:|
| `start_time` | DateTimeField | Sim | auto_now_add | Sim |
| `end_time` | DateTimeField | Não | None | Não |
| `status` | CharField | Sim | 'INICIADO' | Sim |
| `tipo_execucao` | CharField | Sim | 'MANUAL' | Não |
| `usuario` | ForeignKey | Não | None | Não |
| `fonte` | CharField | Sim | — | Não |
| `arquivo_nome` | CharField | Não | None | Não |
| `arquivo_tamanho`| BigIntegerField | Não | None | Não |
| `arquivo_hash` | CharField | Não | None | Não |
| `total_lido` | IntegerField | Sim | 0 | Não |
| `total_valido` | IntegerField | Sim | 0 | Não |
| `total_invalido` | IntegerField | Sim | 0 | Não |
| `total_criados` | IntegerField | Sim | 0 | Não |
| `total_atualizados`| IntegerField | Sim | 0 | Não |
| `total_inalterados`| IntegerField | Sim | 0 | Não |
| `total_desativados`| IntegerField | Sim | 0 | Não |
| `erro_mensagem` | TextField | Não | None | Não |
| `traceback` | TextField | Não | None | Não |
| `duracao_segundos`| FloatField | Não | None | Não |

### 13.2 Alterações em modelos existentes

#### Modelo: `CertificadoAprovacao`

| Campo | Alteração | Tipo | Default |
|---|---|---|---|
| `cnpj` | Novo campo | CharField(max_length=20, null=True, blank=True) | None |
| `observacoes` | Novo campo | TextField(null=True, blank=True) | None |
| `presente_na_fonte`| Novo campo | BooleanField | True |
| `versao_importacao`| Novo campo | BigIntegerField | 0 |

---

## 14. Serviços de domínio e consultas

### 14.1 Services

#### `caepi_sync_service`
- **Responsabilidade:** Coordenação completa da sincronização (Download, Validação, Processamento em lote, Rollback e logs).
- **Entrada:** `tipo_execucao` (MANUAL/AUTOMATICA), `usuario` (opcional), `arquivo_local_path` (opcional), `forcar` (bool), `verbose` (bool).
- **Transação atômica:** Sim.
- **Lock concorrente:** Sim, bloqueia se outro log ativo estiver rodando há menos de 2 horas.

---

## 15. Interface, rotas e experiência móvel

### 15.1 Novas Rotas

| Método | Rota | View | Perfil | Finalidade |
|---|---|---|---|---|
| GET | `/ppe/ca/consultar_ajax/` | `ca_consultar_ajax` | Autenticado | Consultar dados locais de um CA em tempo real |

---

## 16. Plano de migration e dados

### 16.1 Migrations previstas

| Ordem | Migration | Tipo | Risco | Reversível? |
|---:|---|---|---|---|
| 1 | `0002_add_caepi_fields_and_synclog` | Schema | Baixo | Sim |

---

## 17. Estratégia de testes

### 17.1 Casos mínimos a testar

1. **Download bem-sucedido:** Simulação com arquivo mock local.
2. **Timeout / Indisponibilidade:** Simulação de erro de conexão capturado com retentativas.
3. **Arquivo corrompido / Vazio / Layout inválido:** Lançamento correto de erro e rollback.
4. **Proteção contra redução da base:** Interrupção se dados caírem abaixo do ratio mínimo.
5. **Lock ativo:** Erro ao disparar nova sincronização concorrente.
6. **Idempotência:** Duas execuções no mesmo arquivo não alteram dados já inseridos.
7. **Dry Run:** Execução sem persistência no banco de dados.
8. **Consulta AJAX:** Retorno dos dados do CA localmente via API AJAX.

---

## 18. Critérios de aceite

### CA-001 — Sincronização via terminal
**Dado que** o comando `sincronizar_caepi` é executado com a opção `--arquivo` passando um arquivo válido  
**Quando** o processamento é concluído com sucesso  
**Then** os dados são carregados no banco, a versão de importação é definida e o status do log é gravado como `CONCLUIDO`.

### CA-002 — Rollback em caso de falha
**Dado que** o comando está importando e ocorre uma falha estrutural no meio do processamento  
**Quando** a transação atômica é abortada  
**Then** a base anterior permanece exatamente intacta e o status do log é salvo como `FALHOU`.

---

## 19. Implantação e operação

### 19.1 Configurações de Ambiente (.env)
```env
CAEPI_SYNC_ENABLED=true
CAEPI_SOURCE_URL=ftp://ftp.mtps.gov.br/portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/tgg_export_caepi.zip
CAEPI_SYNC_TIMEOUT=60
CAEPI_SYNC_MAX_RETRIES=3
CAEPI_SYNC_BATCH_SIZE=2000
CAEPI_SYNC_MAX_INVALID_PERCENT=10.0
CAEPI_SYNC_MIN_RECORD_RATIO=0.8
```

---

## 20. Parecer dos Subagentes

### 20.1 Revisão do Arquiteto
- **Parecer:** APROVADA
- **Observações:** A especificação garante modularidade isolando o client FTP, parser ZIP e a escrita bulk na transação Django, mantendo as views e comandos livres de regras de negócio.

### 20.2 Revisão pré-implementação do QA
- **Parecer:** APROVADA_PARA_IMPLEMENTAÇÃO
- **Observações:** Plano de testes mapeia cenários de teste reais de rede e integridade de arquivos em lotes sem dependência de internet.
