# Mapeamento de Planilhas Legadas

**Arquivo:** `contexto/MAPEAMENTO_planilhas_legadas.md`  
**Versão:** 1.0.0  
**Data:** 09/07/2026  
**Status:** Vigente  

Este documento detalha a estrutura de colunas e o mapeamento dos dados legados contidos nas planilhas de referência localizadas na pasta `fontes`.

---

## 1. Planilha `EPIs ESTOQ.xlsx`

Esta planilha é utilizada para o levantamento inicial de produtos, Certificados de Aprovação (C.A.), custos unitários e estoque atual.

### 1.1 Aba `ESTOQ`

Contém a listagem física de estoques e fornecedores. Possui uma estrutura de dados particular para produtos com grade de tamanho (botas, luvas, vestimentas).

#### Estrutura de Colunas:
- **Coluna 1 (FORNECEDOR):** Nome do fornecedor principal (ex: `LOJÃO PB`).
- **Coluna 2 (PRODUTO):** Nome do produto/EPI.
- **Coluna 3 (ESTOQ):** Quantidade em estoque para itens sem grade. Para itens com grade, exibe `-` indicando que o saldo está detalhado por tamanho na linha subsequente.
- **Coluna 4 (C.A.):** Número do Certificado de Aprovação (ex: `CA 18731` ou `CA 36099 `).
- **Coluna 5 (PREÇO/UND):** Preço unitário em Real (ex: `20` ou `78.3`).
- **Colunas 6 a 15 (Grade de Tamanhos):**
  - Para botas/calçados: Numeração de `35` a `44`.
  - Para luvas/vestimentas: Tamanhos `P`, `M`, `G`, `GG`, `XG`.

#### Padrão de Representação de Grades (Linha Dupla):
1. **Linha de Definição (Linha N):** Define o produto, C.A., preço unitário e lista os tamanhos disponíveis nas colunas 6 a 15.
2. **Linha de Saldo (Linha N+1):** Deixa os campos de metadados em branco (nulo) e lista a quantidade física disponível em estoque correspondente a cada tamanho nas colunas 6 a 15.

*Exemplo Bota (Linhas 9 e 10 da planilha):*
- Row N: `['LOJÃO PB', 'BOTA ', '-', 'CA 43377', 63.4, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]`
- Row N+1: `['LOJÃO PB', None, None, None, None, 12, 14, 2, 0, 9, 2, 4, 3, 14, None]`
*(Interpretação: 12 unidades de tamanho 35, 14 unidades de tamanho 36, etc.)*

---

## 2. Planilha `PLANILHA DE ATUALIZAÇÃO ASO...xlsx`

Esta planilha define a estrutura organizacional de unidades, colaboradores e as pendências/situação de ASO e exames.

### 2.1 Aba `SUPORTE`

Lista as unidades operacionais da empresa sob a coluna `EMPRESA`.
- **Valores identificados:**
  - `RDC - 01`
  - `RDC - 02`
  - `RDC - 03`
  - `RDC - 04`
  - `BQS - 02`
  - `BQS - 03`
  - `GALPÃO`
  - `CAMPINA ATACADO`

### 2.2 Aba `EXAMES ASO`

Possui cabeçalho localizado na **linha 8** da planilha (1-indexed). As linhas abaixo contêm a estrutura a ser mapeada para colaboradores.

#### Mapeamento de Campos de Cadastro de Colaborador:
- **Col 0 (NOME):** Nome completo do colaborador.
- **Col 1 (UNID.):** Unidade (referenciada a partir da aba SUPORTE).
- **Col 2 (FUNÇÃO):** Cargo ou Função do colaborador.
- **Col 3 (SETOR):** Setor operacional.
- **Col 4 (CPF):** CPF (necessita validação e normalização de formato).
- **Col 11 (TELEFONE):** Telefone de contato.
- **Col 34 (Sexo):** Sexo do colaborador (`M` / `F`).
- **Col 35 (Farda Modelo):** Modelo da farda de trabalho.

#### Mapeamento de Tamanhos Corporativos:
- **Col 20 (Nº):** Numeração de calçado/bota.
- **Col 23 (Tamnho):** Tamanho da farda (camisa/calça).

#### Mapeamento de EPIs Individuais / Vida Útil:
- **Col 12/13 (Protetor Plug / Validade):** Indica recebimento e data de validade.
- **Col 14/15 (Protetor Concha / Validade):** Indica recebimento e data de validade.
- **Col 16/17 (Filtro Químico / Validade4):** Indica recebimento e data de validade.
- **Col 18/19 (BOTAS / Validade5):** Indica recebimento e data de validade.
- **Col 21/22 (FARDAS / Validade 6):** Indica recebimento e data de validade.

#### Mapeamento de Treinamentos (Fases Futuras):
- **Col 24 (TREINAMENTO BRIGADISTA):** Data de conclusão.
- **Col 26 (TREINENTO ELÉTRICA):** Data de conclusão.
- **Col 28 (TREINAMENTO EMPILHADEIRA):** Data de conclusão.
- **Col 30 (TREIN. TRAB. ALTURA):** Data de conclusão.
- **Col 32 (TREINAMENTO CALDEIRA):** Data de conclusão.

#### Mapeamento de Saúde / ASO (Fases Futuras):
- **Col 5 (TIPO de ASO):** Tipo do último ASO.
- **Col 6 (DATA):** Data do último ASO.
- **Col 7 (SITUAÇÃO):** Situação de aptidão.
- **Col 8 (AUDIO):** Exame de audiometria.
- **Col 9 (TOXICOLOGICO):** Exame toxicológico.
- **Col 10 (2240):** Código do evento eSocial 2240 (Condições Ambientais do Trabalho).
- **Col 36 (o.s):** Ordem de Serviço de SST emitida.

---

## 3. Inconsistências e Desafios de Normalização

1. **Nomes de Colunas Imprecisos:** Colunas como `Validade4`, `Validade5`, `Validade 6`, `Tamnho` possuem grafias inconsistentes que devem ser tratadas de forma normalizada nos modelos do banco.
2. **Representação Dupla de Itens com Grade:** A aba de estoque utiliza duas linhas para representar um único produto (uma com a grade de tamanhos, outra com as quantidades). O banco de dados deve normalizar isso em tabelas de `Product` e `ProductVariant` (uma linha por variante).
3. **Ausência de Identificadores Únicos:** Não há IDs numéricos para colaboradores além do CPF e matrícula (que devem ser validados e tornados únicos).
4. **Acoplamento de Domínios na Planilha Legada:** A planilha de exames mistura cadastro de pessoal, tamanhos, entregas físicas de EPI, datas de treinamentos e dados médicos de ASO. O sistema deve separar rigorosamente estes dados em seus respectivos módulos (`employees`, `ppe`, `inventory`, `training`, `occupational_health`).
