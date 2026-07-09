# Arquitetura do Sistema SST Freedom

**Arquivo:** `contexto/ARQUITETURA_sst_freedom.md`  
**Versão:** 1.0.0  
**Data:** 09/07/2026  
**Status:** Vigente  

Este documento descreve os padrões arquiteturais, a divisão modular, o modelo de segurança e a estratégia de armazenamento de dados e controle de estoques adotados no **SST Freedom**.

---

## 1. Visão Geral da Arquitetura

O sistema é construído sobre o framework **Django** em sua versão LTS, utilizando uma arquitetura baseada em serviços de domínio (Service Layer) e seletores para desacoplar a lógica de negócio das Views e dos Templates.

```text
+-------------------------------------------------------+
|                      User / UI                        |
|               (Bootstrap 5 + HTML/JS)                 |
+--------------------------+----------------------------+
                           |
                           v
+-------------------------------------------------------+
|                    Views & Forms                      |
|                  (Django MVC Layer)                   |
+---------------+----------------------+----------------+
                |                      |
                v                      v
+-----------------------+      +------------------------+
|    Services (Write)   |      |   Selectors (Read)     |
|   (Domain Operations) |      | (Aggregations/Queries) |
+---------------+-------+      +-----------+------------+
                |                          |
                v                          v
+-------------------------------------------------------+
|                       Models                          |
|             (Django ORM + Database Constraints)       |
+--------------------------+----------------------------+
                           |
                           v
+-------------------------------------------------------+
|                  Database (SQLite)                    |
|             (Immutable Ledger + Indices)              |
+-------------------------------------------------------+
```

---

## 2. Divisão de Módulos (Apps Django)

O projeto é estruturado de forma modular nas seguintes aplicações:

1. **`core`:** Contém o painel principal (Dashboard), middleware global, classes base, mixins comuns e funções utilitárias gerais.
2. **`accounts`:** Responsável pela autenticação, modelo de usuário customizado (`CustomUser`) e perfis de permissões (Administrador, Técnico SST e Almoxarife).
3. **`organizations`:** Gerencia a hierarquia da empresa: Empresa, Unidade (Filiais), Setores, Centros de Custo, Funções/Cargos e Locais de Estoque.
4. **`employees`:** Controla o cadastro de colaboradores, históricos de alterações cadastrais/funcionais e numerações de tamanho (camisa, calça, calçado, luva).
5. **`inventory`:** Gerencia fornecedores, notas fiscais de compra, lotes físicos, controle de saldo e o fluxo de transferências de estoque (Almoxarifado ➔ SST).
6. **`ppe` (Equipamentos de Proteção Individual):** Catálogo de EPIs, variantes de tamanho, Certificados de Aprovação (C.A.) com integração do CAEPI/MTE, Matriz de EPI por função, EPIs Extraordinários, entregas físicas individuais, devoluções, trocas e baixas.
7. **`notifications`:** Motor interno de geração de alertas (estoque mínimo, validade física de lote, validade de C.A., vencimento de trocas).
8. **`audit`:** Registrador imutável de eventos críticos (trilha de auditoria).

---

## 3. Livro-Razão de Estoque (Ledger)

Para garantir a integridade absoluta dos estoques, o sistema utiliza o padrão de **Livro-Razão imutável**. A quantidade atual de qualquer item nunca é armazenada apenas em uma coluna editável. O saldo disponível é derivado da soma histórica de lançamentos na tabela `StockMovement`.

### 3.1 Modelo `StockMovement`
Cada linha representa um fato físico irreversível no estoque:
- `unit`: Unidade operacional.
- `location`: Almoxarifado, SST ou outro local físico na unidade.
- `variant`: Variante de produto (ex: Bota nº 40).
- `lot`: Lote do fabricante (contendo validade e custo).
- `quantity`: Quantidade movimentada (positiva para entradas, negativa para saídas).
- `movement_type`: Enum de controle (`ENTRADA_COMPRA`, `TRANSFERENCIA_SAIDA`, `TRANSFERENCIA_ENTRADA`, `ENTREGA_COLABORADOR`, `DEVOLUCAO_COLABORADOR`, `AJUSTE_POSITIVO`, `AJUSTE_NEGATIVO`, `BAIXA_DANO`, `BAIXA_PERDA`, `BAIXA_VENCIMENTO`, `ESTORNO`).
- `cost_unit`: Custo unitário histórico de aquisição do lote.
- `user`: Usuário que registrou a movimentação.
- `created_at`: Data e hora do lançamento.

### 3.2 Invariantes de Estoque
- **Saldo Não-Negativo:** O banco de dados deve possuir `CheckConstraint` para garantir que o saldo projetado no local não resulte em valor negativo.
- **Imutabilidade:** Movimentações passadas não podem ser alteradas ou excluídas. Ajustes devem ser feitos via movimentação de estorno ou ajuste com justificativa explícita.
- **Bloqueio Concorrente:** Lógica de saída de estoque utiliza `select_for_update` para evitar concorrência desordenada sobre o mesmo saldo do lote.

---

## 4. Segurança e Segregação de Perfis

O sistema aplica rigorosamente o princípio do menor privilégio no backend.

### 4.1 Perfis de Acesso
- **Administrador:** Acesso irrestrito a configurações de sistema, gerenciamento de usuários e controle de unidades permitidas.
- **Técnico de Segurança (SST):**
  - Gerencia colaboradores, funções e a matriz de EPIs.
  - Recebe transferências destinadas ao estoque SST.
  - Efetua entregas individuais de EPI, substituições e devoluções.
  - Acessa painéis de custos de EPI e relatórios de validade.
- **Almoxarife:**
  - Gerencia fornecedores, notas fiscais e compras.
  - Registra a entrada física no Almoxarifado.
  - Executa a transferência de mercadorias para o local SST.
  - *Não pode:* Acessar fichas médicas, exames, ASOs ou entregar EPIs diretamente ao trabalhador.

### 4.2 Escopo de Dados por Unidade
O usuário (Técnico SST ou Almoxarife) é associado a um conjunto de unidades autorizadas. A filtragem de dados ocorre no nível do banco através de Querysets customizados (`get_queryset`), impedindo o acesso ou visualização de dados de outras filiais, mesmo que as rotas URLs sejam digitadas manualmente.

---

## 5. Estratégia de Certificados de Aprovação (C.A.)

A gestão de C.A. assegura a legalidade do fornecimento de proteção individual.

- **Importação CAEPI (MTE):** Sincronização por meio da carga em lote da planilha oficial do MTE (MTE CAEPI). Um comando customizado Django (`sync_caepi`) executa o processamento do arquivo no servidor utilizando transações e dry-run opcional.
- **Provedor de C.A.:** Abstração de interface que permite consultar a base local. O cadastro de EPI no frontend consulta dinamicamente esta base para autocompletar fabricante e tipo de proteção.
- **Controle Manual:** Se um C.A. for novo e ainda não constar na base oficial importada, o Técnico de Segurança pode cadastrá-lo manualmente, sendo obrigatório registrar a justificativa no sistema e na auditoria.

---

## 6. Pontos de Extensão para Fases Futuras

- **Módulo de Treinamentos (Fase 2):** Projetado para compartilhar os modelos de `Employee` e `Function` sem acoplamento direto com o controle físico do almoxarifado.
- **Módulo de ASO e Saúde Ocupacional (Fase 3):** Isolação lógica total. Os dados clínicos ficarão em um banco ou aplicação separada. O painel operacional de estoques e colaboradores apenas lerá um indicador de status de aptidão ocupacional (Apto/Inapto/Vencido), sem expor exames ou históricos médicos confidenciais.
- **Fila de Alertas e E-mail (Fase 4):** A arquitetura utiliza um comando de alertas modular. O agendamento futuro poderá substituir a execução cron por uma fila de tarefas (como Celery ou Django-Q) sem alterar a regra de geração de alertas.
