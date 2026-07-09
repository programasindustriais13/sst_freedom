# SPEC — [TÍTULO DA DEMANDA]

> Este arquivo deve ser criado a partir de `contexto/SPEC_TEMPLATE.md`.  
> Remova as instruções entre colchetes somente depois de preencher a seção correspondente.  
> Nenhuma implementação pode começar antes do parecer `APROVADA_PARA_IMPLEMENTAÇÃO` do QA.

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `[SPEC-AAAA-NNN]` |
| Título | `[Título objetivo]` |
| Tipo | `[FEATURE / FIX / REFACTOR / MIGRATION / SECURITY / PERFORMANCE / DOCUMENTATION]` |
| Módulo principal | `[accounts / organizations / employees / inventory / ppe / training / occupational_health / reports / outro]` |
| Fase/Roadmap | `[Fase e subdivisão]` |
| Autor da SPEC | `[Arquiteto]` |
| Data de criação | `[DD/MM/AAAA]` |
| Última atualização | `[DD/MM/AAAA HH:MM]` |
| Versão | `[1.0.0]` |
| Status | `RASCUNHO` |
| Prioridade | `[CRÍTICA / ALTA / MÉDIA / BAIXA]` |
| Risco | `[CRÍTICO / ALTO / MÉDIO / BAIXO]` |
| Demanda de origem | `[Resumo ou referência ao pedido]` |
| SPEC substituída | `[Não / caminho]` |
| SPECs relacionadas | `[Caminhos ou Não se aplica]` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | `[data]` | `[autor]` | Rascunho inicial | RASCUNHO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `[PENDENTE]` |  |  |
| Revisão pré-implementação | QA | `[PENDENTE]` |  |  |
| Implementação | Backend | `[PENDENTE]` |  |  |
| QA final | QA | `[PENDENTE]` |  |  |

### 0.3 Transições de status

Fluxo normal:

```text
RASCUNHO
→ EM_REVISÃO_QA
→ APROVADA_PARA_IMPLEMENTAÇÃO
→ EM_IMPLEMENTAÇÃO
→ EM_QA_FINAL
→ APROVADA | APROVADA_COM_RESSALVAS | BLOQUEADA
```

---

## 1. Resumo executivo

[Explique em até cinco parágrafos:

- qual problema será resolvido;
- quem é afetado;
- qual resultado será entregue;
- por que a mudança é necessária;
- quais são os principais riscos.]

---

## 2. Contexto da demanda

### 2.1 Cenário atual

[Descreva como o processo funciona hoje, no sistema, planilha ou operação manual.]

### 2.2 Problema

[Descreva o problema observável, sem antecipar uma solução.]

### 2.3 Evidências

[Liste evidências: telas, logs, planilhas, arquivos, rotas, consultas, comportamento reproduzível ou relato validado.]

| Evidência | Origem | Conclusão |
|---|---|---|
| `[exemplo]` | `[arquivo/rota/log]` | `[o que comprova]` |

### 2.4 Causa raiz ou hipótese

- Causa confirmada: `[Sim/Não]`
- Descrição: `[causa ou hipótese]`
- Como foi validada: `[método]`

Para correções, não implementar solução permanente com base apenas em hipótese não investigada.

---

## 3. Objetivos

### 3.1 Objetivo principal

[Resultado central mensurável.]

### 3.2 Objetivos secundários

- `[objetivo]`
- `[objetivo]`

### 3.3 Indicadores de sucesso

| Indicador | Situação atual | Meta | Como medir |
|---|---:|---:|---|
| `[indicador]` | `[valor]` | `[valor]` | `[consulta/teste/relatório]` |

---

## 4. Escopo

### 4.1 Dentro do escopo

- `[entrega objetiva]`
- `[entrega objetiva]`

### 4.2 Fora do escopo

- `[item explicitamente não implementado]`
- `[fase futura]`

### 4.3 Restrições

- respeitar `contexto/constitution.md`;
- trabalhar somente dentro da pasta atual;
- não criar novo ambiente virtual;
- não duplicar projeto ou código;
- não alterar arquivos da pasta `fontes`;
- não fazer commit, push ou deploy;
- `[outras restrições]`.

### 4.4 Dependências

| Dependência | Tipo | Situação | Ação |
|---|---|---|---|
| `[serviço, módulo ou dado]` | `[interna/externa]` | `[disponível/pendente]` | `[ação]` |

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | `[necessidade]` | `[impacto]` | `[escopo]` |
| Almoxarife | `[necessidade]` | `[impacto]` | `[escopo]` |
| Administrador | `[necessidade]` | `[impacto]` | `[escopo]` |

Adicionar outros perfis quando necessário.

---

## 6. Estado atual do código

### 6.1 Arquivos e módulos lidos

| Arquivo/Módulo | Motivo da leitura | Conclusão |
|---|---|---|
| `[caminho]` | `[motivo]` | `[conclusão]` |

### 6.2 Fluxo atual

[Descrever o fluxo existente do início ao fim.]

### 6.3 Modelos existentes relacionados

| Modelo | App | Responsabilidade | Pode ser reutilizado? |
|---|---|---|---|
| `[modelo]` | `[app]` | `[função]` | `[Sim/Não/Parcial]` |

### 6.4 Dívidas ou riscos encontrados

- `[dívida]`
- `[risco]`

Não incluir correções fora do escopo sem registrá-las como dependência ou SPEC separada.

---

## 7. Premissas e decisões

### 7.1 Premissas

| ID | Premissa | Como validar | Impacto se falsa |
|---|---|---|---|
| ASM-001 | `[premissa]` | `[validação]` | `[impacto]` |

### 7.2 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-001 | `[decisão]` | `[alternativas]` | `[motivo]` |

### 7.3 Questões resolvidas

| Questão | Resposta adotada | Evidência |
|---|---|---|
| `[questão]` | `[resposta]` | `[origem]` |

### 7.4 Questões em aberto

| Questão | Bloqueia? | Responsável | Prazo/ação |
|---|---|---|---|
| `[questão]` | `[Sim/Não]` | `[responsável]` | `[ação]` |

Uma questão que afete integridade, permissão, migração ou segurança deve bloquear a implementação.

---

## 8. Requisitos funcionais

Use identificadores estáveis.

### RF-001 — [Nome do requisito]

**Descrição:**  
[Comportamento esperado.]

**Atores:**  
[Perfis autorizados.]

**Pré-condições:**

- `[condição]`

**Fluxo principal:**

1. `[passo]`
2. `[passo]`

**Fluxos alternativos:**

- `[alternativa]`

**Validações:**

- `[validação]`

**Resultado esperado:**

- `[resultado]`

**Auditoria necessária:**

- `[evento ou Não se aplica]`

**Permissões:**

- `[regra backend]`

**Critérios relacionados:**

- `[CA-001]`

---

[Duplicar a seção RF para cada requisito.]

### 8.x Matriz resumida de requisitos

| ID | Requisito | Prioridade | Perfil | Critério de aceite |
|---|---|---|---|---|
| RF-001 | `[resumo]` | `[Must/Should/Could]` | `[perfil]` | CA-001 |

---

## 9. Regras de negócio

### RN-001 — [Nome da regra]

- **Regra:** `[descrição inequívoca]`
- **Motivo:** `[razão de negócio]`
- **Aplicação:** `[model/service/form/view]`
- **Exceções:** `[exceções ou nenhuma]`
- **Falha esperada:** `[mensagem/comportamento]`
- **Teste:** `[teste que comprova]`

[Duplicar para cada regra.]

### 9.1 Invariantes

Listar regras que nunca podem ser quebradas, por exemplo:

- saldo não pode ficar negativo;
- movimento concluído não pode ser apagado;
- usuário não acessa unidade não autorizada;
- custo histórico não muda após confirmação;
- EPI extraordinário não altera a matriz da função.

Invariantes desta SPEC:

- `[invariante]`
- `[invariante]`

---

## 10. Requisitos não funcionais

### RNF-001 — Segurança

[Requisitos de autenticação, autorização, CSRF, upload, logs, dados sensíveis.]

### RNF-002 — Performance

[Volume esperado, paginação, índices, quantidade máxima, tempo aceitável.]

### RNF-003 — Responsividade

[Comportamento em smartphone, tablet e desktop.]

### RNF-004 — Acessibilidade

[Labels, teclado, foco, contraste, mensagens.]

### RNF-005 — Escalabilidade e manutenção

[Modularidade, services, selectors, extensão futura.]

### RNF-006 — Compatibilidade

[Bancos, navegadores, Python/Django, formatos.]

### RNF-007 — Auditoria e observabilidade

[Eventos, logs seguros, métricas.]

### RNF-008 — Privacidade e LGPD

[Finalidade, minimização, acesso, retenção e exportação.]

---

## 11. Permissões e segregação de acesso

### 11.1 Matriz de permissões

Legenda:

- `C`: criar
- `R`: consultar
- `U`: editar
- `D`: excluir/inativar
- `A`: ação especial
- `—`: não permitido

| Recurso/Ação | Técnico SST | Almoxarife | Administrador | Observação |
|---|---:|---:|---:|---|
| `[recurso]` | `[C/R/U/A]` | `[R]` | `[todos]` | `[regra]` |

### 11.2 Escopo de dados

- Empresa: `[regra]`
- Unidade: `[regra]`
- Setor: `[regra]`
- Dados pessoais: `[regra]`
- Dados de saúde: `[regra]`
- Custos: `[regra]`

### 11.3 Testes de acesso indevido

| Cenário | Resultado esperado |
|---|---|
| URL direta sem login | Redirecionar ou negar |
| Objeto de outra unidade | 404 ou 403 conforme padrão definido |
| Perfil sem permissão | 403 |
| ID manipulado | Sem exposição de dados |

---

## 12. Fluxos e máquinas de estado

### 12.1 Fluxo principal

```text
[ESTADO_INICIAL]
→ [AÇÃO]
→ [ESTADO_INTERMEDIÁRIO]
→ [AÇÃO]
→ [ESTADO_FINAL]
```

### 12.2 Tabela de transições

| Estado atual | Ação | Novo estado | Perfil | Pré-condições | Efeito |
|---|---|---|---|---|---|
| `[estado]` | `[ação]` | `[novo]` | `[perfil]` | `[condição]` | `[efeito]` |

### 12.3 Transições proibidas

- `[estado A → estado B]`
- `[ação repetida]`

### 12.4 Idempotência

- Chave ou proteção: `[estratégia]`
- Operações protegidas: `[lista]`
- Resultado de repetição: `[sem duplicar/retornar existente/etc.]`

---

## 13. Modelagem de dados

### 13.1 Diagrama textual

```text
Empresa 1 ── N Unidade
Unidade 1 ── N Setor
[completar relações]
```

### 13.2 Novos modelos

#### Modelo: `[Nome]`

**Responsabilidade:**  
[Descrição.]

| Campo | Tipo | Obrigatório | Default | Índice | Regra |
|---|---|---:|---|---:|---|
| `[campo]` | `[tipo]` | `[Sim/Não]` | `[valor]` | `[Sim/Não]` | `[regra]` |

**Constraints:**

- `[constraint]`

**Métodos/propriedades:**

- `[método]`

**Estratégia de exclusão:**

- `[PROTECT / inativação / SET_NULL / outra]`

**Auditoria:**

- `[eventos]`

### 13.3 Alterações em modelos existentes

| Modelo | Alteração | Compatibilidade | Migração necessária |
|---|---|---|---|
| `[modelo]` | `[alteração]` | `[impacto]` | `[Sim/Não]` |

### 13.4 Índices

| Modelo | Campos | Motivo |
|---|---|---|
| `[modelo]` | `[campos]` | `[consulta]` |

### 13.5 Constraints e integridade

| ID | Constraint | Camada | Mensagem |
|---|---|---|---|
| DB-001 | `[regra]` | Banco/model | `[mensagem]` |

### 13.6 Retenção e histórico

[Descrever o que pode ser excluído, inativado ou deve ser preservado.]

---

## 14. Serviços de domínio e consultas

### 14.1 Services

#### `[nome_do_service]`

- Responsabilidade: `[operação]`
- Entrada: `[dados]`
- Saída: `[resultado]`
- Transação atômica: `[Sim/Não]`
- Bloqueio concorrente: `[estratégia]`
- Idempotência: `[estratégia]`
- Exceções de domínio: `[lista]`
- Auditoria: `[evento]`

### 14.2 Selectors / Query services

| Selector | Finalidade | Otimizações |
|---|---|---|
| `[selector]` | `[consulta]` | `[select_related, índices, agregação]` |

### 14.3 Sinais

Evitar signals para regras críticas.

Caso um signal seja realmente necessário:

- motivo: `[justificativa]`;
- evento: `[pre/post save etc.]`;
- risco: `[risco]`;
- alternativa descartada: `[alternativa]`;
- testes: `[testes]`.

---

## 15. Interface, rotas e experiência móvel

### 15.1 Rotas

| Método | Rota | View | Perfil | Finalidade |
|---|---|---|---|---|
| GET | `/exemplo/` | `[view]` | `[perfil]` | `[finalidade]` |

### 15.2 Telas

#### Tela: `[nome]`

- Rota: `[rota]`
- Perfis: `[perfis]`
- Objetivo: `[objetivo]`
- Componentes: `[cards, filtros, tabela etc.]`
- Estado vazio: `[mensagem/ação]`
- Erros: `[tratamento]`
- Ações críticas: `[confirmações]`

### 15.3 Comportamento responsivo

| Largura | Comportamento |
|---|---|
| Smartphone | `[cards, offcanvas, botões]` |
| Tablet | `[layout]` |
| Desktop | `[layout]` |

### 15.4 Acessibilidade

- labels: `[regra]`
- foco: `[regra]`
- contraste: `[regra]`
- teclado: `[regra]`
- leitores de tela: `[regra]`

### 15.5 JavaScript

- Necessidade: `[Sim/Não]`
- Função: `[melhoria progressiva]`
- Fallback sem JavaScript: `[comportamento]`

---

## 16. Integrações, arquivos e importações

### 16.1 Integração externa

| Item | Definição |
|---|---|
| Provedor | `[nome]` |
| Finalidade | `[finalidade]` |
| Autenticação | `[tipo]` |
| Timeout | `[valor]` |
| Retentativas | `[regra]` |
| Fallback | `[regra]` |
| Dados armazenados | `[dados]` |
| LGPD | `[impacto]` |

### 16.2 Importação

- Formato: `[XLSX/CSV/JSON/etc.]`
- Origem: `[fonte]`
- Identificador de duplicidade: `[campo]`
- `--dry-run`: `[Sim/Não]`
- Transação: `[estratégia]`
- Relatório de erros: `[formato]`
- Reprocessamento: `[regra]`
- Encoding/data: `[tratamento]`

### 16.3 Uploads

- Tipos permitidos: `[lista]`
- Limite: `[tamanho]`
- Armazenamento: `[local/R2/etc.]`
- Permissão: `[regra]`
- Retenção: `[regra]`

---

## 17. Plano de migration e dados

### 17.1 Migrations previstas

| Ordem | Migration | Tipo | Risco | Reversível? |
|---:|---|---|---|---|
| 1 | `[nome]` | `[schema/data]` | `[nível]` | `[Sim/Não]` |

### 17.2 Dados existentes

- Volume estimado: `[quantidade]`
- Campos afetados: `[lista]`
- Nulos existentes: `[situação]`
- Duplicidades: `[situação]`
- Dados inválidos: `[situação]`

### 17.3 Estratégia de backfill

1. `[passo]`
2. `[passo]`

### 17.4 Compatibilidade durante deploy

[Descrever se código antigo e novo podem coexistir durante a migration.]

### 17.5 Rollback

- Código: `[estratégia]`
- Banco: `[estratégia]`
- Dados: `[estratégia]`
- Limitações: `[limitações]`

### 17.6 Validação pós-migration

```bash
[comandos e consultas]
```

---

## 18. Segurança, privacidade e auditoria

### 18.1 Ameaças analisadas

| Ameaça | Risco | Mitigação | Teste |
|---|---|---|---|
| IDOR/acesso por ID | Alto | Filtrar queryset e permissão | `[teste]` |
| `[ameaça]` | `[nível]` | `[mitigação]` | `[teste]` |

### 18.2 Dados pessoais

| Dado | Finalidade | Perfis | Retenção | Exportável? |
|---|---|---|---|---|
| `[dado]` | `[finalidade]` | `[perfis]` | `[prazo/regra]` | `[Sim/Não]` |

### 18.3 Eventos de auditoria

| Evento | Quando | Dados registrados | Dados proibidos |
|---|---|---|---|
| `[evento]` | `[condição]` | `[dados]` | `[dados sensíveis]` |

---

## 19. Performance e capacidade

### 19.1 Volume esperado

| Entidade | Atual | 1 ano | 5 anos |
|---|---:|---:|---:|
| `[entidade]` | `[qtd]` | `[qtd]` | `[qtd]` |

### 19.2 Consultas críticas

| Consulta | Risco | Estratégia |
|---|---|---|
| `[consulta]` | `[N+1/agregação]` | `[índice/selector]` |

### 19.3 Paginação e limites

- Tamanho padrão: `[n]`
- Máximo: `[n]`
- Exportação: `[limite/assíncrono futuro]`

### 19.4 Metas

- Tela principal: `[meta]`
- Ação transacional: `[meta]`
- Relatório: `[meta]`

Metas devem ser realistas para o ambiente conhecido.

---

## 20. Alertas e agendamentos

### 20.1 Condições

| Alerta | Condição | Faixas | Resolução |
|---|---|---|---|
| `[alerta]` | `[regra]` | `[90/60/30/etc.]` | `[automática/manual]` |

### 20.2 Idempotência

[Como evitar alertas duplicados.]

### 20.3 Execução

```bash
python manage.py [comando]
```

- Frequência sugerida: `[frequência]`
- Sem Celery nesta fase: `[Sim/Não e justificativa]`

---

## 21. Relatórios e exportações

| Relatório | Filtros | Colunas | Formato | Permissão |
|---|---|---|---|---|
| `[nome]` | `[filtros]` | `[colunas]` | `[CSV/XLSX/PDF]` | `[perfil]` |

Regras:

- respeitar escopo;
- registrar filtros;
- formatar datas e valores;
- evitar exposição indevida;
- preservar origem dos cálculos;
- testar volume.

---

## 22. Plano de implementação

### 22.1 Arquivos previstos

| Arquivo | Ação | Motivo |
|---|---|---|
| `[caminho]` | `[criar/alterar]` | `[motivo]` |

A lista é previsão, não autorização para alterar arquivos adicionais sem registrar a mudança.

### 22.2 Ordem de implementação

1. `[passo]`
2. `[passo]`
3. `[passo]`

### 22.3 Compatibilidade

- Dados legados: `[regra]`
- URLs existentes: `[regra]`
- Templates existentes: `[regra]`
- APIs existentes: `[regra]`

### 22.4 Itens que exigem cuidado manual

- `[item]`

---

## 23. Estratégia de testes

### 23.1 Matriz de testes

| ID | Tipo | Cenário | Resultado esperado | Requisito |
|---|---|---|---|---|
| T-001 | Unitário | `[cenário]` | `[resultado]` | RN-001 |
| T-002 | Permissão | `[cenário]` | `[resultado]` | RF-001 |

### 23.2 Casos mínimos

#### Caminho feliz

- `[caso]`

#### Validações

- `[caso]`

#### Permissões

- `[caso]`

#### Idempotência

- `[caso]`

#### Concorrência

- `[caso]`

#### Regressão

- `[caso]`

#### Responsividade

- `[caso]`

#### Migration

- `[caso]`

### 23.3 Comandos obrigatórios

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
```

Comandos adicionais:

```bash
[lint, cobertura, testes específicos]
```

### 23.4 Dados de teste

[Descrever factories/fixtures. Não usar dados pessoais reais.]

---

## 24. Critérios de aceite

Use critérios objetivos, testáveis e numerados.

### CA-001 — [Nome]

**Dado que** `[contexto]`  
**Quando** `[ação]`  
**Então** `[resultado observável]`

### CA-002 — [Nome]

**Dado que** `[contexto]`  
**Quando** `[ação]`  
**Então** `[resultado]`

### 24.1 Checklist de aceite

- [ ] Todos os requisitos `Must` foram implementados.
- [ ] Permissões foram testadas no backend.
- [ ] Não há acesso entre unidades indevido.
- [ ] Migrations foram revisadas.
- [ ] Testes obrigatórios passam.
- [ ] Interface móvel foi validada.
- [ ] Auditoria foi validada.
- [ ] Documentação foi atualizada.
- [ ] Nenhum arquivo de `fontes` foi alterado.
- [ ] Nenhuma alteração fora do escopo foi incluída.

---

## 25. Riscos

| ID | Risco | Probabilidade | Impacto | Mitigação | Responsável |
|---|---|---|---|---|---|
| R-001 | `[risco]` | `[B/M/A]` | `[B/M/A]` | `[ação]` | `[responsável]` |

### 25.1 Riscos que bloqueiam

- `[risco ou Nenhum]`

### 25.2 Dívida aceita

- `[dívida]`
- motivo: `[justificativa]`
- prazo/roadmap: `[destino]`

---

## 26. Implantação e operação

### 26.1 Preparação

- `[backup]`
- `[variáveis]`
- `[migrations]`
- `[comandos]`

### 26.2 Sequência de implantação

1. `[passo]`
2. `[passo]`

### 26.3 Validação pós-implantação

- `[smoke test]`
- `[consulta]`
- `[saldo/contagem]`

### 26.4 Rollback operacional

- Gatilho: `[condição]`
- Passos: `[passos]`
- Dados que não podem ser revertidos: `[lista]`

A execução de deploy depende de autorização expressa e não faz parte da implementação local, salvo pedido específico.

---

## 27. Observabilidade e suporte

- Logs necessários: `[lista]`
- Logs proibidos: `[lista]`
- Métricas: `[lista]`
- Alertas operacionais: `[lista]`
- Como diagnosticar: `[passos]`
- Comando de reconciliação: `[se aplicável]`

---

## 28. Documentação a atualizar

- [ ] `README.md`
- [ ] `.env.example`
- [ ] `contexto/ARQUITETURA_sst_freedom.md`
- [ ] `contexto/ROADMAP_sst_freedom.md`
- [ ] `contexto/OPERACAO_inicial.md`
- [ ] `contexto/MAPEAMENTO_planilhas_legadas.md`
- [ ] outra: `[arquivo]`

---

## 29. Revisão do Arquiteto

### 29.1 Parecer

`[APROVADA PARA QA / DEVOLVIDA PARA AJUSTES / BLOQUEADA]`

### 29.2 Verificações

- [ ] A solução reutiliza o código existente.
- [ ] Não cria projeto ou app duplicado.
- [ ] Regras críticas estão em services/models.
- [ ] O modelo suporta evolução futura sem superengenharia.
- [ ] Permissões foram definidas.
- [ ] Migrations e rollback foram planejados.
- [ ] Testes e critérios de aceite são suficientes.
- [ ] Escopo e fora de escopo estão claros.
- [ ] Constituição foi respeitada.

### 29.3 Observações

[Observações.]

---

## 30. Revisão pré-implementação do QA

### 30.1 Parecer

`[APROVADA_PARA_IMPLEMENTAÇÃO / APROVADA_COM_RESSALVAS / BLOQUEADA]`

### 30.2 Checklist

- [ ] Requisitos são testáveis.
- [ ] Não há ambiguidade crítica.
- [ ] Invariantes estão explícitas.
- [ ] Matriz de permissões está completa.
- [ ] Casos negativos foram previstos.
- [ ] Idempotência foi analisada.
- [ ] Concorrência foi analisada.
- [ ] Dados legados foram analisados.
- [ ] Segurança e LGPD foram analisadas.
- [ ] Responsividade está especificada.
- [ ] Riscos e rollback estão definidos.
- [ ] Não há implementação fora da fase atual.

### 30.3 Ressalvas ou bloqueios

[Descrever.]

### 30.4 Autorização

A implementação somente está autorizada quando o parecer acima for `APROVADA_PARA_IMPLEMENTAÇÃO`.

---

# REGISTRO DE IMPLEMENTAÇÃO

> Esta parte deve ser preenchida durante e depois da implementação.  
> Divergências materiais exigem atualização e nova revisão da SPEC.

---

## 31. Implementação realizada

### 31.1 Resumo

[O que foi implementado.]

### 31.2 Divergências da proposta

| Item | Previsto | Implementado | Justificativa | QA aprovou? |
|---|---|---|---|---|
| `[item]` | `[previsto]` | `[real]` | `[motivo]` | `[Sim/Não]` |

### 31.3 Arquivos lidos

| Arquivo | Finalidade |
|---|---|
| `[caminho]` | `[finalidade]` |

### 31.4 Arquivos criados

| Arquivo | Finalidade |
|---|---|
| `[caminho]` | `[finalidade]` |

### 31.5 Arquivos alterados

| Arquivo | Alteração |
|---|---|
| `[caminho]` | `[resumo]` |

### 31.6 Migrations criadas

| Migration | Operações | Risco |
|---|---|---|
| `[caminho]` | `[operações]` | `[nível]` |

### 31.7 Services e selectors

| Componente | Responsabilidade |
|---|---|
| `[componente]` | `[responsabilidade]` |

### 31.8 Rotas e telas

| Rota | Tela/Ação | Perfil |
|---|---|---|
| `[rota]` | `[finalidade]` | `[perfil]` |

---

## 32. Testes executados

| Comando/Teste | Resultado | Evidência/Resumo |
|---|---|---|
| `python manage.py check` | `[PASS/FAIL]` | `[resultado]` |
| `python manage.py makemigrations --check` | `[PASS/FAIL]` | `[resultado]` |
| `python manage.py migrate` | `[PASS/FAIL/N/A]` | `[resultado]` |
| `python manage.py test` | `[PASS/FAIL]` | `[quantidade/resultado]` |

### 32.1 Testes manuais

| Cenário | Dispositivo/Largura | Resultado |
|---|---|---|
| `[cenário]` | `[mobile/desktop]` | `[resultado]` |

### 32.2 Falhas ou testes não executados

[Descrever com transparência. Nunca omitir.]

---

## 33. Validação dos critérios de aceite

| Critério | Status | Evidência |
|---|---|---|
| CA-001 | `[ATENDIDO/NÃO ATENDIDO]` | `[teste/tela]` |

---

## 34. QA final

### 34.1 Parecer final

`[APROVADA / APROVADA_COM_RESSALVAS / BLOQUEADA]`

### 34.2 Revisão

- [ ] Implementação corresponde à SPEC.
- [ ] Constituição foi respeitada.
- [ ] Permissões foram verificadas.
- [ ] Integridade de dados foi preservada.
- [ ] Migrations são seguras.
- [ ] Testes obrigatórios passam.
- [ ] Não há regressão conhecida crítica.
- [ ] Interface móvel foi validada.
- [ ] Auditoria funciona.
- [ ] Documentação foi atualizada.
- [ ] Arquivos de `fontes` permanecem intactos.
- [ ] Não houve alteração fora da pasta atual.
- [ ] Não houve commit, push ou deploy.

### 34.3 Ressalvas

| ID | Ressalva | Impacto | Ação recomendada | Bloqueia? |
|---|---|---|---|---|
| `[id]` | `[descrição]` | `[impacto]` | `[ação]` | `[Sim/Não]` |

### 34.4 Evidências

[Resultados, arquivos, testes e observações.]

---

## 35. Pendências e próximos passos

- `[pendência]`
- `[SPEC futura]`

Itens fora de escopo não devem ser apresentados como erro desta entrega quando foram explicitamente adiados.

---

## 36. Sugestão de commit

```text
[tipo]([escopo]): [descrição objetiva]
```

Não executar commit sem autorização expressa.

---

## 37. Encerramento

- Status final da SPEC: `[status]`
- Data: `[data]`
- Responsável pelo encerramento: `[responsável]`
- Observação final: `[observação]`
