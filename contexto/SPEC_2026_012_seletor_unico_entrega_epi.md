# SPEC — Simplificação do Seletor de Entrega de EPI no Estoque SST

---

## 0. Metadados

| Campo | Valor |
|---|---|
| Projeto | SST Freedom |
| Código da SPEC | `SPEC-2026-012` |
| Título | Simplificação do Seletor de Entrega de EPI no Estoque SST |
| Tipo | `FEATURE / REFACTOR / UX` |
| Módulo principal | `ppe` (com integração ao `inventory` e `employees`) |
| Fase/Roadmap | Fase 1A - Melhorias de Interface e Segurança Operacional |
| Autor da SPEC | Arquiteto |
| Data de criação | 21/07/2026 |
| Última atualização | 21/07/2026 18:55 |
| Versão | 1.0.0 |
| Status | `APROVADA_PARA_IMPLEMENTAÇÃO` |
| Prioridade | ALTA |
| Risco | BAIXO |
| Demanda de origem | Substituição dos seletores redundantes (EPI/Variante + Lote) por seletor único de item disponível no estoque SST |
| SPEC substituída | Não |
| SPECs relacionadas | `contexto/SPEC_fase_1a_fundacao_estoque_epi.md`, `contexto/SPEC_2026_009_simplificacao_estoque_grade.md` |

### 0.1 Histórico de versões

| Versão | Data | Autor | Alteração | Status |
|---|---|---|---|---|
| 0.1.0 | 21/07/2026 | Arquiteto | Elaboração inicial da SPEC | RASCUNHO |
| 1.0.0 | 21/07/2026 | QA | Revisão pré-implementação e aprovação arquitetural | APROVADA_PARA_IMPLEMENTAÇÃO |

### 0.2 Aprovações

| Etapa | Responsável | Parecer | Data | Observações |
|---|---|---|---|---|
| Revisão arquitetural | Arquiteto | APROVADO | 21/07/2026 | Solução sem alteração de banco/migration, mantendo integridade e rastreabilidade |
| Revisão pré-implementação | QA | APROVADO | 21/07/2026 | Critérios de aceite e plano de testes validados |
| Implementação | Backend | PENDENTE |  |  |
| QA final | QA | PENDENTE |  |  |

---

## 1. Resumo executivo

Atualmente, na tela de fornecimento individual de EPI (`/ppe/deliveries/add/`), existem dois seletores visíveis independentes:
1. `EPI / Variante de Tamanho`
2. `Lote de Origem (Saldo SST disponível)`

Essa separação cria redundância para o operador e gera o risco de desalinhamento: o operador pode selecionar a Variante X em um seletor e o Lote Y (pertencente à Variante Z) no segundo seletor.

Esta melhoria substitui os dois seletores visíveis por **apenas um seletor visível** denominado **"EPI disponível no estoque SST"** (ou "EPI / Tamanho / Lote"). A partir da escolha do lote disponível, o sistema identifica automaticamente o EPI, o tamanho/variante, o lote, a validade e o saldo disponível em estoque SST, preenchendo e persistindo os relacionamentos no backend com total segurança.

Nenhuma alteração no modelo de banco de dados ou migração será necessária, preservando entregas históricas e movimentações de estoque.

---

## 2. Contexto da demanda

### 2.1 Cenário atual

No formulário `ppe/delivery_form.html`, o operador precisa escolher o EPI/variante e, em seguida, escolher o lote. Ambos os campos são visíveis e obrigatórios.

### 2.2 Problema

- Redundância visual.
- Possibilidade de incoerência entre a variante selecionada e o lote de origem selecionado.
- Dificuldade do operador em visualizar conjuntamente EPI, Tamanho, Lote, Validade e Saldo disponível.

### 2.3 Evidências

| Evidência | Origem | Conclusão |
|---|---|---|
| Form de entrega com 2 selects | `templates/ppe/delivery_form.html` (L31-L51) | `product_variant` e `lot` exigidos separadamente na UI |
| View `PPEDeliveryCreateView` | `ppe/views.py` (L338-L430) | Permite postar `product_variant` e `lot` sem validar se pertencem ao mesmo registro |
| Modelo `Lot` | `inventory/models.py` (L80-L104) | Cada `Lot` possui a FK `product_variant`, provando a relação 1:1 entre lote e variante |

---

## 3. Objetivos

### 3.1 Objetivo principal

Simplificar a interface de entrega de EPI unificando a escolha em um único seletor visível de lote/item com saldo SST disponível.

### 3.2 Objetivos secundários

- Garantir que `product_variant` seja inferido e validado no backend a partir do `lot`.
- Ordenar as opções do seletor pelo critério FEFO (primeiro os lotes com validade física mais próxima).
- Apresentar opções legíveis no padrão:  
  `PROTETOR AUDITIVO — Tamanho P — Lote NF-IO-C39D94 — Validade 20/07/2031 — Saldo: 15`
- Exibir apenas lotes com saldo SST `> 0`.

---

## 4. Escopo

### 4.1 Dentro do escopo

- Criação/Atualização do formulário de entrega (`PPEDeliveryForm`) em `ppe/forms.py`.
- Atualização da view `PPEDeliveryCreateView` em `ppe/views.py`.
- Atualização do template `templates/ppe/delivery_form.html`.
- Validação estrita no backend em `ppe/forms.py` / `ppe/services.py`.
- Atualização e criação de testes automatizados unitários e de integração em `ppe/test_improvements.py` e `ppe/tests.py`.

### 4.2 Fora do escopo

- Alteração de tabelas no banco de dados.
- Alteração da lógica de devolução ou baixa de estoque por avaria.
- Alteração de cadastros de produtos ou de lotes.

---

## 5. Estado atual do código

### 5.1 Arquivos afetados

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `ppe/forms.py` | Modificar | Adicionar `PPEDeliveryForm` com validação de `lot` e inferência de `product_variant` |
| `ppe/views.py` | Modificar | Usar `PPEDeliveryForm` em `PPEDeliveryCreateView` |
| `templates/ppe/delivery_form.html` | Modificar | Exibir apenas um campo seletor visível para o item/lote |
| `ppe/services.py` | Modificar | Reforçar validação de coerência entre `lot.product_variant` e `product_variant` |
| `ppe/test_improvements.py` | Modificar/Criar | Atualizar testes existentes e incluir testes da nova SPEC |

---

## 6. Premissas e decisões

### 6.1 Premissas

- `Lot.product_variant` é a fonte da verdade para determinar o EPI e Tamanho de um lote.
- O saldo disponível de um lote no estoque SST é calculado por `inventory.services.get_stock_balance(loc_sst, product_variant, lot)`.

### 6.2 Decisões arquiteturais

| ID | Decisão | Justificativa |
|---|---|---|
| ADR-001 | Manter campo `product_variant` no formulário como `HiddenInput` / preenchido no `clean()` | Garante compatibilidade técnica com `PPEDelivery` sem necessitar de migrations ou alterar a assinatura de `deliver_ppe`. |
| ADR-002 | Ordenação FEFO no queryset de Lotes | Atende à boa prática de almoxarifado (lotes com validade mais próxima são apresentados primeiro). |
| ADR-003 | Constatação sobre Lote Vencido (Regra 11) | Atualmente o sistema não bloqueia entregas de lotes vencidos no service `deliver_ppe`. Conforme a Regra 11 da demanda, esta constatação está documentada aqui sem introduzir regra oculta, para decisão do negócio em SPEC futura. |

---

## 7. Requisitos funcionais

### RF-001 — Seletor Único de Item/Lote SST

- O formulário de entrega deve apresentar apenas **um seletor visível** para a escolha do EPI.
- Rótulo: `EPI disponível no estoque SST`
- Opção inicial: `Selecione o EPI disponível no estoque SST...`
- Cada opção do seletor deve formatar legivelmente:  
  `[Nome do EPI] — Tamanho [Tam] — Lote [Identificador/NF] — Validade [DD/MM/AAAA] — Saldo: [Saldo]`

### RF-002 — Validação e Associação Automática no Backend

- Ao selecionar o lote, o backend deve atribuir e validar automaticamente `product_variant = lot.product_variant`.
- Se o frontend enviar uma variante divergente da variante real do lote, a validação do backend deve rejeitar com erro claro:  
  `O lote selecionado não pertence ao EPI ou tamanho informado.`

### RF-003 — Filtragem de Saldo e FEFO

- O seletor deve exibir exclusivamente lotes com saldo SST `> 0` para a unidade do colaborador/operador.
- A lista de opções deve estar ordenada por `data_validade` ascendente (FEFO), seguida de nome do produto e identificador.

---

## 8. Regras de negócio

- **RN-001:** O seletor mostra apenas lotes com saldo positivo no estoque SST.
- **RN-002:** Não é possível associar um lote a uma variante diferente de `lot.product_variant`.
- **RN-003:** Não é possível realizar entrega em quantidade superior ao saldo SST do lote.
- **RN-004:** Toda entrega realizada debita atomicamente o saldo do lote no estoque SST.
- **RN-005:** Usuários com perfil restrito apenas conseguem visualizar e entregar lotes de sua unidade.

---

## 9. Critérios de aceite

1. Existe apenas um seletor visível na interface de entrega de EPI.
2. O seletor identifica conjuntamente EPI, Tamanho, Lote, Validade e Saldo.
3. A variante correta é vinculada automaticamente no backend a partir do lote.
4. Lotes sem saldo não aparecem na lista de seleção.
5. Tentativa de entregar quantidade superior ao saldo exibe mensagem de erro e bloqueia a operação.
6. Entregas históricas permanecem inalteradas.
7. Todos os testes automatizados da aplicação passam com 100% de sucesso.
