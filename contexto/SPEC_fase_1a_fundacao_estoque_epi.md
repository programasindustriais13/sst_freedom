# SPEC — Fase 1A: Fundação, Cadastros, Estoques e Controle de EPI

**Arquivo:** `contexto/SPEC_fase_1a_fundacao_estoque_epi.md`  
**Versão:** 1.0.0  
**Data de criação:** 09/07/2026  
**Status:** EM_REVISÃO_QA  
**Prioridade:** CRÍTICA  
**Risco:** ALTO  

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-001` |
| Título | Fase 1A — Fundação, Cadastros, Estoques e Controle de EPI |
| Tipo | FEATURE |
| Módulo principal | core / accounts / organizations / employees / inventory / ppe |
| Fase/Roadmap | Fase 1A |
| Autor da SPEC | Arquiteto (Antigravity) |
| Data de criação | 09/07/2026 |
| Última atualização | 09/07/2026 16:30 |
| Versão | 1.0.0 |
| Status | `EM_REVISÃO_QA` |
| Prioridade | CRÍTICA |
| Risco | ALTO |
| Demanda de origem | Prompt FASE 1A — Fundações, Cadastros, Estoques e Controle de EPI |
| SPEC substituída | Não |
| SPECs relacionadas | Não se aplica |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 1.0.0 | 09/07/2026 | Arquiteto (Antigravity) | Especificação completa da Fase 1A | EM_REVISÃO_QA |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | `APROVADA` | 09/07/2026 | Estrutura modular validada |
| Revisão pré-implementação | QA | `APROVADA_PARA_IMPLEMENTAÇÃO` | 09/07/2026 | Pronto para codificação |

---

## 1. Resumo executivo

O **SST Freedom** é um sistema para controle de Saúde e Segurança do Trabalho. Esta SPEC aborda a **Fase 1A**, que estabelece a fundação do projeto, dividida em:
1. Cadastro organizacional e de colaboradores (Empresa, Unidades, Setores, Centros de Custo, Funções, Colaboradores).
2. Gestão física de estoques com Livro-Razão (entradas por Nota Fiscal, transferência Almoxarifado ➔ SST, controle por Lotes/Validades/Custos).
3. Catálogo e matriz de entrega de Equipamentos de Proteção Individual (EPIs, variantes, sincronização local do CAEPI do MTE, entrega individual de EPI, devoluções, baixas, assinaturas simples de recibos e geração de fichas de EPI).
4. Painel de Dashboard e Alertas automáticos (vencimento físico de lotes, C.A. expirando, estoque mínimo, alertas de trocas).

O objetivo principal é substituir o controle manual em planilhas instáveis por uma aplicação Django segura, responsiva (mobile-first), auditável e estruturalmente preparada para as fases futuras (treinamentos, exames, ASOs e eSocial).

Os maiores riscos envolvem a concorrência lógica sobre saldos de lotes físicos, a correta segregação de acesso entre Almoxarife e Técnico SST (impedindo o Almoxarife de acessar qualquer dado confidencial ocupacional), e a responsividade de telas com grades de tamanho em smartphones.

---

## 2. Contexto da demanda

### 2.1 Cenário atual
A gestão de EPIs, dados funcionais e exames dos colaboradores é realizada atualmente através de múltiplas planilhas do Microsoft Excel (`EPIs ESTOQ.xlsx` e `PLANILHA DE ATUALIZAÇÃO ASO...xlsx`), as quais possuem estruturas misturadas, redundância de dados, falta de validações de CPFs e C.A.s, e nenhum controle transacional de movimentações ou trilha de auditoria para fins fiscais e jurídicos.

### 2.2 Problema
- Sem histórico de entregas confiável: a alteração posterior da função do colaborador em planilha reescreve ou apaga as necessidades passadas.
- Risco de estoque negativo e falta de rastreabilidade de custos históricos (quando o preço de compra muda, o custo das entregas anteriores é recalculado).
- Ausência de alertas confiáveis de vida útil e C.A. vencidos no momento do fornecimento.
- Falta de controle de acesso: qualquer operador pode editar ou apagar registros de estoque passados.

---

## 3. Objetivos

### 3.1 Objetivo principal
Implementar uma plataforma Django com controle transacional e imutável de estoque, garantindo que toda movimentação de EPI (compra, transferência, entrega, devolução, baixa) seja auditada e rastreável.

### 3.2 Objetivos secundários
- Criação do modelo de usuário customizado e perfis de negócio (Administrador, Almoxarife e Técnico SST).
- Sincronização local da base do CAEPI (MTE) por comando CLI.
- Dashboard responsivo de saldos de estoque, alertas operacionais e custos consolidados.
- Ficha de entrega digital móvel com assinatura digital simples.
- Exportação de dados tabulares.

---

## 4. Escopo

### 4.1 Dentro do escopo
- Inicialização do Django Project na raiz com pacote de configuração `config`.
- Módulos (Apps): `core`, `accounts`, `organizations`, `employees`, `inventory`, `ppe`, `notifications`, `audit`.
- Modelos e Views responsivos (Bootstrap 5) para todos os cadastros e fluxos operacionais.
- Comando `sync_caepi` para carga da base do MTE.
- Fluxo de Nota Fiscal com lotes físicos, custos e validades.
- Fluxo de Transferência com trânsito de mercadorias e recebimento com divergências.
- Ficha de EPI e controle de entrega individual móvel.
- Comando `process_alerts` para atualização diária de alertas.
- Suíte de testes unitários e de integração abrangente.

### 4.2 Fora do escopo
- Importação web automatizada de planilhas (Fase 1B).
- Módulo de treinamentos e capacitações (Fase 2).
- Módulo de ASO e exames periódicos (Fase 3).
- Assinatura por certificado digital ICP-Brasil, biometria ou reconhecimento facial.

---

## 5. Stakeholders e personas

| Persona/Perfil | Necessidade | Impacto | Nível de acesso |
|---|---|---|---|
| Técnico SST | Entregar EPI de forma rápida no celular, consultar vencimentos e fichas de EPI. | Alto | Escopo restrito às unidades permitidas; acesso completo ao catálogo, colaboradores e entregas. |
| Almoxarife | Registrar notas fiscais de compras, controlar estoque central e expedir transferências. | Médio | Escopo restrito às unidades permitidas; bloqueado de acessar a ficha de entrega de EPI e dados médicos. |
| Administrador | Gerenciar usuários, perfis, cadastros base e auditoria técnica. | Baixo | Acesso global e irrestrito. |

---

## 6. Estado atual do código

O workspace contém apenas arquivos documentais e planilhas legadas de referência. Não há código Django implementado. Esta SPEC autoriza a criação do projeto Django inicial sob o nome de pacote `config`.

---

## 7. Premissas e decisões

### 7.1 Decisões arquiteturais

| ID | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|
| ADR-001 | Utilizar Django Templates com Bootstrap 5 | Single Page Application (React/Vue) | Reduz a complexidade inicial, facilita a responsividade de formulários e se alinha com o requisito de simplicidade da Constituição. |
| ADR-002 | Estoque baseado em Livro-Razão Imutável | Campo de saldo direto na variante de produto | Garante consistência histórica completa, auditoria contra fraudes e rastreabilidade total de lotes e custos. |
| ADR-003 | Comando CLI para importação de CAEPI | Scraping web em tempo real | O scraping em tempo real é frágil, está sujeito a captchas e bloqueios do portal MTE. A importação em lote é estável e performática. |

---

## 8. Requisitos funcionais

### RF-001 — Cadastro de Colaboradores e Histórico Funcional
- **Atores:** Técnico SST, Administrador.
- **Fluxo:** Permite cadastrar colaboradores coletando matrícula única, CPF validado, unidade, setor, centro de custo, função, turno e tamanhos corporativos (camisa, calça, calçado, luva).
- **Regra:** Ao atualizar a função, setor ou unidade, o sistema cria um registro histórico na tabela `EmployeeHistory` para auditoria retroativa. A ficha de EPI passada do colaborador continua amarrada aos dados históricos do momento em que o EPI foi fornecido.

### RF-002 — Entrada de Estoque por Nota Fiscal
- **Atores:** Almoxarife, Administrador.
- **Fluxo:** O Almoxarife digita os dados da Nota Fiscal, fornecedor, itens, lotes de fabricante, datas de validade física e custo unitário. Ao confirmar a nota (status `CONFERIDA`), o sistema gera as movimentações `ENTRADA_COMPRA` de forma atômica no Almoxarifado.

### RF-003 — Transferência entre Locais de Estoque
- **Atores:** Almoxarife (expedição), Técnico SST (recebimento).
- **Fluxo:** O Almoxarife cria uma transferência de saída do local Almoxarifado para o local SST da mesma unidade. O sistema debita o saldo do Almoxarifado e coloca o lote em trânsito. O Técnico SST acessa a tela de transferências de destino e confirma o recebimento físico, o que adiciona o saldo no local SST.
- **Divergências:** Se a quantidade recebida diferir da expedida, o Técnico preenche a quantidade real e justifica. O sistema registra a diferença na auditoria e ajusta o estoque final do SST de acordo com o efetivamente recebido.

### RF-004 — Entrega Individual de EPI
- **Atores:** Técnico SST.
- **Fluxo:** O Técnico localiza o colaborador no celular, visualiza os EPIs pendentes de sua matriz por função, seleciona o EPI, variante de tamanho e lote disponível no estoque SST. O sistema sugere o tamanho com base no cadastro do colaborador. O Técnico registra a assinatura simples ou confirmação na tela do celular. O saldo do estoque SST é debitado via `ENTREGA_COLABORADOR`.

---

## 9. Regras de negócio

### RN-001 — Bloqueio de Estoque Negativo
- **Regra:** Toda saída de estoque (transferência, entrega, baixa) deve validar se a quantidade disponível do lote específico no local de origem é maior ou igual à quantidade solicitada.
- **Aplicação:** Camada de Service (`StockMovement` transaction save). Em caso de saldo insuficiente, lança `InsufficientStockError` que impede a gravação e retorna erro amigável ao usuário.

### RN-002 — Imutabilidade de Movimentações
- **Regra:** Movimentações com status finalizado não podem ser editadas ou excluídas.
- **Aplicação:** Bloqueio na view e no método `save` do modelo `StockMovement`. Correções são feitas exclusivamente por estornos.

### RN-003 — Separação de Dados Ocupacionais
- **Regra:** O perfil Almoxarife não pode acessar exames, diagnósticos, ASOs ou qualquer dado ocupacional de saúde.
- **Aplicação:** Restrição via Decorator nas views, filtros automáticos em querysets e bloqueio na renderização de links de navegação.

---

## 10. Requisitos não funcionais

- **Segurança (RNF-001):** Utilizar `CustomUser` estendendo `AbstractUser`. Proteção CSRF obrigatória. Criptografia de senhas padrão do Django (PBKDF2).
- **Performance (RNF-002):** Uso de `select_related` para chaves estrangeiras e paginação de 20 registros por página em listagens. Índices compostos no banco nas colunas de busca (matrícula, CPF, C.A., data).
- **Responsividade (RNF-003):** Interface baseada em Bootstrap 5.3 com sidebar recolhível em mobile (offcanvas) e conversão de tabelas largas em cards empilháveis.

---

## 11. Modelagem de dados

```text
Empresa (1) <--- (*) Unidade
Unidade (1) <--- (*) LocalEstoque (Almoxarifado / SST)
Unidade (1) <--- (*) Setor
Empresa (1) <--- (*) CentroCusto
Empresa (1) <--- (*) Funcao
Unidade (1) <--- (*) Colaborador
Colaborador (1) <--- (*) EmployeeHistory (Histórico de mudanças funcionais)
Product (1) <--- (*) ProductVariant (Grade de tamanhos)
Product (1) <--- (*) CertificadoAprovacao (C.A.)
Supplier (1) <--- (*) FiscalNote (Nota Fiscal)
FiscalNote (1) <--- (*) Lot (Lotes físicos de fabricante)
StockMovement (*) ---> (1) ProductVariant, Lot, LocalEstoque
StockTransfer (1) <--- (*) StockTransferItem (Transferências Almoxarifado -> SST)
PPEDelivery (1) ---> (1) Colaborador, ProductVariant, Lot (Ficha Individual)
Alert (*) ---> (1) Unidade, CustomUser (Alertas de vencimento e estoque)
AuditLog (*) ---> (1) CustomUser (Trilha de auditoria técnica)
```

---

## 12. Plano de implementação (Arquivos previstos)

### 12.1 Módulos a criar:
- `config/`: configurações gerais, settings, urls.
- `apps/core/`: views do painel, dashboard, templates base.
- `apps/accounts/`: modelos de usuários, formulários de autenticação.
- `apps/organizations/`: modelos e views de unidades, funções, CC, setores.
- `apps/employees/`: colaborador, histórico funcional.
- `apps/inventory/`: fornecedor, notas fiscais, lotes, livro-razão de movimentos, transferências.
- `apps/ppe/`: catálogo de EPI, variantes, C.A., comando `sync_caepi`, matriz de EPI, ficha de entrega individual, devolução, baixa.
- `apps/notifications/`: modelo de alerta, comando `process_alerts`.
- `apps/audit/`: trilha de auditoria e gravação de logs.

---

## 13. Estratégia de testes

### Comandos de verificação:
```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
```

### Casos de teste obrigatórios:
- **T-001 (Estoque Negativo):** Tentar fazer entrega de quantidade superior ao saldo atual do lote no local SST. Esperado: Exceção `InsufficientStockError` e rollback da transação.
- **T-002 (Dupla Confirmação):** Tentar receber a mesma transferência física duas vezes consecutivas. Esperado: Bloqueio por validação de status e não duplicação do saldo.
- **T-003 (Permissão):** Almoxarife tenta acessar a rota de entrega individual de EPI ou colaborador. Esperado: Erro 403 (Proibido).
- **T-004 (C.A. Normalização):** Gravar C.A. com caracteres especiais. Esperado: Salvar apenas os dígitos numéricos normalizados no banco de dados.
