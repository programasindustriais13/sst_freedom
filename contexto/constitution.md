# Constituição do Projeto SST Freedom

**Arquivo:** `contexto/constitution.md`  
**Versão:** 1.0.0  
**Data de criação:** 09/07/2026  
**Status:** Vigente  
**Projeto:** SST Freedom  
**Tecnologia principal:** Django  
**Idioma da interface:** Português do Brasil  
**Fuso horário padrão:** `America/Fortaleza`

---

## 1. Finalidade desta Constituição

Este documento estabelece as regras permanentes e não negociáveis para análise, especificação, implementação, testes, documentação e evolução do sistema SST Freedom.

Toda pessoa, agente de IA, subagente ou ferramenta que atuar no repositório deve ler este arquivo antes de propor ou executar alterações.

A Constituição existe para garantir:

- segurança dos dados;
- rastreabilidade;
- integridade dos estoques;
- proteção de informações pessoais e ocupacionais;
- facilidade de uso;
- responsividade;
- escalabilidade;
- manutenção sustentável;
- evolução orientada por especificações;
- redução de regressões e alterações improvisadas.

Nenhuma implementação pode ser considerada concluída apenas porque “funcionou na tela”. Ela deve respeitar as regras de domínio, permissões, integridade, testes e critérios de aceite definidos neste documento e na SPEC aprovada.

---

## 2. Hierarquia de autoridade

Em caso de conflito, observar a seguinte ordem:

1. requisitos legais e obrigações de segurança aplicáveis;
2. esta Constituição;
3. SPEC aprovada para a demanda atual;
4. decisões arquiteturais registradas na pasta `contexto`;
5. documentação técnica vigente;
6. padrões já consolidados no código;
7. pedido operacional atual.

Uma solicitação do usuário pode alterar a Constituição somente quando declarar expressamente que se trata de uma **emenda constitucional do projeto**.

Quando uma demanda comum contrariar esta Constituição:

- não contornar a regra;
- não implementar silenciosamente;
- registrar o conflito;
- apresentar alternativa segura;
- aguardar emenda ou ajuste da demanda, salvo quando for possível cumprir o objetivo sem violação.

---

## 3. Fluxo obrigatório SPEC-DRIVEN

Toda alteração funcional, estrutural, de banco, permissão, integração ou regra de negócio deve seguir abordagem SPEC-DRIVEN.

### 3.1 Ordem obrigatória

1. Ler `contexto/constitution.md`.
2. Ler `contexto/SPEC_TEMPLATE.md`.
3. Ler os documentos de contexto relacionados.
4. Inspecionar o código e o banco representado pelas migrations.
5. O subagente **Arquiteto** cria ou atualiza uma SPEC.
6. O subagente **QA** revisa a SPEC.
7. Somente após aprovação da SPEC o subagente **Backend** implementa.
8. O subagente **QA** revisa código, migrations, permissões, testes e regressões.
9. Emitir relatório final e parecer.

### 3.2 Estados permitidos para uma SPEC

- `RASCUNHO`
- `EM_REVISÃO_QA`
- `APROVADA_PARA_IMPLEMENTAÇÃO`
- `EM_IMPLEMENTAÇÃO`
- `EM_QA_FINAL`
- `APROVADA`
- `APROVADA_COM_RESSALVAS`
- `BLOQUEADA`
- `CANCELADA`
- `SUBSTITUÍDA`

O Backend não deve iniciar uma SPEC em estado `RASCUNHO` ou `EM_REVISÃO_QA`.

### 3.3 Demandas pequenas

Correções pequenas também exigem SPEC.

É permitido usar uma **SPEC reduzida**, mas ela deve conter no mínimo:

- problema;
- causa identificada ou hipótese;
- escopo;
- fora de escopo;
- arquivos prováveis;
- riscos;
- testes;
- critérios de aceite;
- parecer do QA.

### 3.4 Mudança de escopo durante a implementação

Se for descoberta necessidade não prevista:

- interromper apenas a parte afetada;
- registrar a descoberta na SPEC;
- revisar impacto em dados, segurança, permissões e testes;
- solicitar nova aprovação do QA da SPEC;
- somente então continuar.

Não usar “já que estamos neste arquivo” como justificativa para mudanças adicionais.

---

## 4. Regras do repositório e da pasta de trabalho

### 4.1 Limites obrigatórios

- Trabalhar somente dentro da pasta atual do projeto.
- Não alterar, criar, mover ou excluir arquivos fora dela.
- Não criar novo ambiente virtual.
- Não copiar o projeto para outra pasta.
- Não criar projeto Django duplicado.
- Não criar aplicações duplicadas para resolver problemas já cobertos por módulos existentes.
- Não modificar arquivos de referência da pasta `fontes`.
- Não inserir segredos no repositório.
- Não executar `commit`, `push`, `merge`, deploy ou alteração em produção sem autorização expressa.
- Não apagar arquivos ou dados para “fazer os testes passarem”.
- Não usar dados reais sensíveis como fixtures de teste.

### 4.2 Regra especial da inicialização

Este repositório corresponde a um novo sistema.

Antes de existir um projeto Django válido, a SPEC inicial pode autorizar a criação de **exatamente um** projeto Django na raiz atual.

Após essa criação:

- passa a valer a proibição permanente de criar outro projeto;
- o pacote de configuração deve permanecer único;
- não criar estruturas aninhadas desnecessárias;
- não reinicializar o projeto para corrigir erros;
- futuras mudanças devem ocorrer sobre o código existente.

### 4.3 Arquivos de contexto

A pasta `contexto` é a fonte documental do projeto.

Documentos nela armazenados devem:

- refletir o estado real;
- possuir nome claro;
- evitar duplicação;
- indicar status e data quando relevante;
- ser atualizados quando uma decisão arquitetural for alterada;
- não afirmar que algo foi implementado sem confirmação no código e nos testes.

---

## 5. Princípios arquiteturais

### 5.1 Modularidade

O sistema deve ser dividido por responsabilidades de negócio, evitando aplicações genéricas gigantes.

A arquitetura deve manter limites claros entre áreas equivalentes a:

- contas e autenticação;
- organizações e unidades;
- colaboradores;
- estoque e compras;
- EPI;
- notificações;
- auditoria;
- treinamentos;
- saúde ocupacional;
- relatórios.

A divisão final deve ser confirmada por SPEC.

### 5.2 Camadas

Regras críticas não devem ficar espalhadas em templates, JavaScript ou views.

Adotar, quando aplicável:

- **models:** estrutura, constraints e invariantes locais;
- **services:** operações transacionais e mudanças de estado;
- **selectors/query services:** consultas, filtros, dashboards e relatórios;
- **forms:** validação de entrada e apresentação;
- **views:** coordenação de requisição e resposta;
- **templates:** apresentação;
- **management commands:** tarefas operacionais idempotentes;
- **tests:** prova das regras.

Views excessivamente grandes devem ser refatoradas, mas sem criar abstrações artificiais.

### 5.3 Simplicidade antes de complexidade

- Não criar SPA sem necessidade comprovada.
- Não introduzir React, Vue ou arquitetura de microsserviços por antecipação.
- Não adicionar fila, cache distribuído ou infraestrutura externa apenas por possibilidade futura.
- Preferir Django server-side, Bootstrap e JavaScript progressivo.
- Toda nova dependência deve ter justificativa, versão fixada e avaliação de manutenção.
- Preparar pontos de extensão sem implementar funcionalidades futuras pela metade.

### 5.4 Compatibilidade de banco

- Desenvolvimento pode usar SQLite.
- Produção deve ser compatível com PostgreSQL.
- Evitar SQL específico de fornecedor.
- Recursos específicos do banco exigem justificativa e fallback ou decisão arquitetural registrada.

---

## 6. Regras de código

### 6.1 Qualidade

- Não duplicar código.
- Não manter funções mortas, arquivos temporários ou comentários enganosos.
- Não esconder exceções com `except Exception: pass`.
- Não desabilitar validações para contornar erro.
- Não usar valores mágicos quando houver constante, enumeração ou configuração adequada.
- Não misturar regra de negócio com formatação visual.
- Preferir nomes técnicos claros e consistentes.
- Textos exibidos ao usuário devem estar em português do Brasil.
- Código deve ser legível antes de ser “engenhoso”.

### 6.2 Configuração

- Segredos e parâmetros de ambiente devem vir de variáveis de ambiente.
- Fornecer `.env.example` sem valores reais.
- Não usar caminhos absolutos ligados ao computador do desenvolvedor.
- Configurações de desenvolvimento e produção devem ser distinguíveis.
- `DEBUG` nunca deve ser presumido como ativo em produção.

### 6.3 Datas, horas e valores

- Utilizar datas e horas conscientes de fuso.
- Fuso padrão: `America/Fortaleza`.
- Armazenar valores monetários com `Decimal`, nunca `float`.
- Moeda padrão: Real brasileiro.
- Exibir datas, CPF, CNPJ, valores e quantidades no padrão brasileiro, sem prejudicar o armazenamento normalizado.

---

## 7. Modelo de usuário, autenticação e autorização

### 7.1 Usuário customizado

O projeto deve usar modelo de usuário customizado desde o início.

Depois das migrations iniciais compartilhadas, a troca do modelo de usuário exige SPEC específica de alto risco.

### 7.2 Menor privilégio

- Todo acesso deve seguir o princípio do menor privilégio.
- Permissões devem ser verificadas no backend.
- Ocultar botão não é autorização.
- Querysets devem ser filtrados pelo escopo permitido.
- Acesso por URL direta deve ser testado.
- Usuários não podem acessar unidades, empresas ou dados fora de seu escopo.
- Superuser não deve ser usado como solução operacional comum.

### 7.3 Perfis iniciais

Perfis de negócio previstos:

- Técnico de Segurança do Trabalho;
- Almoxarife;
- Administrador técnico.

Novos perfis exigem matriz de permissões na SPEC.

### 7.4 Separação de dados ocupacionais

O Almoxarife não pode acessar:

- ASO;
- exames;
- diagnósticos;
- resultados clínicos;
- restrições médicas detalhadas;
- documentos de saúde ocupacional.

Quando o estoque precisar identificar um colaborador, mostrar somente os dados operacionais mínimos necessários.

---

## 8. LGPD, privacidade e segurança

### 8.1 Minimização

Coletar somente dados necessários para a finalidade definida.

Toda SPEC que criar novo dado pessoal deve informar:

- finalidade;
- quem acessa;
- período de retenção;
- uso em relatórios;
- possibilidade de anonimização;
- riscos de exposição.

### 8.2 Dados sensíveis

Dados de saúde ocupacional devem possuir:

- módulo e permissões próprios;
- auditoria de acesso e alteração quando aplicável;
- proteção contra exposição em URLs, logs e mensagens;
- exportações restritas;
- testes de autorização específicos.

### 8.3 Logs

Não registrar em logs:

- senhas;
- tokens;
- documentos completos sem necessidade;
- resultados médicos;
- arquivos;
- dados pessoais em excesso.

### 8.4 Uploads

Uploads devem possuir:

- tipos permitidos;
- limite de tamanho;
- nomes internos seguros e não previsíveis;
- validação no servidor;
- armazenamento configurável;
- controle de acesso;
- prevenção de execução de arquivo;
- política de substituição e exclusão auditável.

### 8.5 Segurança web

Manter:

- CSRF;
- escape de templates;
- validação no servidor;
- cookies seguros em produção;
- cabeçalhos adequados;
- tratamento seguro de redirecionamentos;
- proteção contra acesso indevido a objetos;
- mensagens de erro que não exponham internals.

---

## 9. Regras permanentes do domínio de estoque

### 9.1 Fonte da verdade

O estoque deve ser derivado de um **livro-razão de movimentações**.

É proibido tratar um campo de quantidade editável como única fonte da verdade.

Se existir cache de saldo:

- ele é derivado;
- deve poder ser reconciliado;
- não substitui as movimentações;
- divergências devem gerar alerta.

### 9.2 Imutabilidade

Movimentações concluídas:

- não podem ser apagadas;
- não podem ter quantidade, lote, origem, destino ou custo silenciosamente alterados;
- devem ser corrigidas por estorno ou movimento compensatório;
- devem preservar usuário, data, justificativa e correlação.

### 9.3 Saldo

- Estoque negativo é proibido.
- Toda saída deve validar saldo disponível.
- Operações concorrentes devem usar transação e bloqueio apropriado.
- Confirmações devem ser idempotentes.
- Repetir uma requisição não pode duplicar entrada, transferência ou entrega.

### 9.4 Lotes e custos

Toda movimentação relevante deve preservar:

- produto e variante;
- lote;
- C.A. aplicável;
- validade física;
- quantidade;
- local;
- custo histórico;
- documento ou operação de origem.

O custo histórico de uma entrega não deve mudar porque o preço atual do produto mudou.

### 9.5 Locais

Almoxarifado e SST são locais de estoque distintos.

Transferência deve ter, no mínimo:

- origem;
- destino;
- itens;
- expedição;
- recebimento;
- estados controlados;
- tratamento de divergência;
- trilha de auditoria.

Não gerar entrada no destino antes da etapa definida pelo fluxo aprovado.

---

## 10. Regras permanentes do domínio de EPI

### 10.1 Conceitos que nunca devem ser confundidos

Manter separados:

1. validade do Certificado de Aprovação — C.A.;
2. validade física do produto ou lote;
3. vida útil estimada após entrega;
4. data prevista de troca;
5. situação real do item entregue.

### 10.2 C.A.

- Número deve ser normalizado para busca.
- Dados oficiais e dados manuais devem ser distinguíveis.
- Importações devem ser idempotentes.
- Não apagar histórico porque o registro deixou de aparecer na fonte.
- Não fazer scraping frágil.
- Não burlar CAPTCHA ou proteção de portal.
- C.A. não encontrado ou desatualizado deve gerar estado visível.
- Correção manual exige justificativa e auditoria.

### 10.3 Matriz por função

A matriz de EPI por função representa a necessidade principal da atividade.

Ela:

- não comprova entrega;
- não movimenta estoque automaticamente;
- não apaga histórico quando alterada;
- deve possuir vigência quando necessário;
- deve permitir vida útil e quantidade padrão configuráveis.

### 10.4 EPI extraordinário

EPI extraordinário:

- pertence a uma necessidade específica do colaborador;
- exige motivo;
- não altera a matriz da função;
- não aparece como EPI principal;
- permanece no histórico e nos custos;
- deve ser filtrável separadamente.

### 10.5 Entrega

Entrega individual deve registrar o contexto no momento da operação:

- colaborador;
- função;
- setor;
- centro de custo;
- unidade;
- produto e variante;
- lote;
- C.A.;
- validade;
- quantidade;
- custo;
- data;
- responsável;
- origem da necessidade;
- vida útil aplicada;
- próxima troca;
- ciência ou pendência de ciência.

A alteração posterior do cadastro do colaborador não pode reescrever a entrega histórica.

### 10.6 Substituição e devolução

- Substituição deve referenciar a entrega anterior.
- Entrega antiga não pode ser sobrescrita.
- Troca antecipada exige motivo.
- Devolução deve registrar condição.
- Retorno ao estoque exige regra explícita de reutilização.
- Dano, perda, extravio e vencimento devem produzir baixa rastreável.

---

## 11. Treinamentos e saúde ocupacional

### 11.1 Separação modular

Treinamentos e saúde ocupacional devem ser módulos distintos do estoque, embora compartilhem colaborador, função, unidade e alertas.

### 11.2 Periodicidades

É proibido hardcodar uma periodicidade universal para:

- ASO;
- audiometria;
- exames;
- treinamentos;
- reciclagens;
- troca de EPI.

Periodicidades devem ser configuráveis conforme:

- função;
- risco;
- programa ocupacional;
- norma aplicável;
- orientação técnica ou médica;
- regra específica da empresa.

### 11.3 Saúde ocupacional

- Resultados médicos exigem acesso restrito.
- Almoxarifado não acessa dados clínicos.
- Alertas podem informar necessidade de ação sem expor diagnóstico.
- Retenção e exportação devem ser definidas em SPEC específica.
- O sistema não deve tomar decisão médica automática.

---

## 12. Auditoria

Operações críticas devem gerar auditoria.

Eventos mínimos:

- criação, alteração e inativação de colaborador;
- mudança de função, setor, unidade ou centro de custo;
- confirmação e cancelamento de nota;
- ajustes de estoque;
- expedição e recebimento;
- divergência;
- entrega, substituição, devolução e baixa;
- alteração manual de C.A.;
- importações;
- alteração de permissões;
- acesso ou exportação de informações sensíveis, quando aplicável.

A auditoria deve indicar:

- ator;
- data e hora;
- ação;
- entidade;
- identificador;
- antes e depois, quando seguro e necessário;
- justificativa;
- origem técnica.

Auditoria não substitui histórico de domínio.

---

## 13. Migrations e integridade de banco

### 13.1 Regras de migrations

- Toda alteração de modelo exige migration.
- Não alterar migration já aplicada ou compartilhada.
- Correções devem ocorrer em nova migration.
- Migrations de dados devem ser idempotentes ou possuir proteção clara.
- Não misturar transformação destrutiva sem plano de recuperação.
- Não apagar coluna com dados sem inventário, migração e rollback definidos.
- Medir impacto de migrations potencialmente pesadas.
- Usar nomes descritivos.

### 13.2 Constraints

Sempre avaliar:

- `UniqueConstraint`;
- `CheckConstraint`;
- integridade referencial;
- índices;
- estados válidos;
- quantidades positivas;
- unicidade por empresa/unidade;
- proteção contra duplicidade de confirmação.

Validação apenas no formulário é insuficiente quando o banco pode garantir a regra.

### 13.3 Exclusão

Regra padrão:

- cadastros usados historicamente devem ser inativados;
- documentos e movimentos críticos não devem ser excluídos;
- `CASCADE` deve ser analisado com cautela;
- `PROTECT` ou preservação histórica deve ser usada quando a exclusão destruir rastreabilidade.

---

## 14. Performance e escalabilidade

Toda lista potencialmente grande deve considerar:

- paginação;
- filtros;
- índices;
- `select_related`;
- `prefetch_related`;
- agregações no banco;
- ausência de consultas por item;
- exportação eficiente;
- limites de período;
- resposta adequada em smartphone.

Dashboards não devem carregar todos os registros para calcular métricas em Python quando o banco puder agregar.

Novas consultas críticas devem ser avaliadas com volume realista, não apenas com três registros de teste.

Processos longos devem ser preparados para execução por comando ou fila futura, mas sem adicionar infraestrutura desnecessária antecipadamente.

---

## 15. Interface e experiência do usuário

### 15.1 Mobile-first

Toda tela operacional deve funcionar em smartphone.

Obrigatório:

- layout responsivo;
- navegação adaptável;
- alvos de toque adequados;
- labels visíveis;
- erros próximos aos campos;
- formulários divididos logicamente;
- filtros recolhíveis;
- tabelas com alternativa móvel;
- ausência de rolagem horizontal como fluxo principal;
- botões principais facilmente identificáveis;
- confirmações para ações críticas.

### 15.2 Acessibilidade

Manter:

- HTML semântico;
- associação entre label e campo;
- navegação por teclado;
- foco visível;
- contraste;
- textos alternativos;
- ícone acompanhado de texto quando a ação não for óbvia;
- mensagens que não dependam apenas de cor.

### 15.3 Consistência

- Usar componentes compartilhados.
- Não criar estilo isolado para cada tela.
- Datas, valores, badges e estados devem seguir padrão.
- Django Admin não é a interface operacional principal.
- JavaScript melhora a experiência, mas não pode ser a única proteção de regra crítica.

---

## 16. Integrações e importações

Toda integração deve possuir:

- finalidade;
- origem;
- contrato;
- autenticação;
- timeout;
- tratamento de indisponibilidade;
- idempotência;
- logs seguros;
- estratégia de atualização;
- fallback;
- testes;
- forma de desativação.

Importações devem oferecer, quando aplicável:

- `--dry-run`;
- validação de cabeçalhos;
- relatório de erros;
- controle de duplicidade;
- transação;
- resumo final;
- preservação do arquivo original;
- identificação da execução;
- possibilidade de reprocessamento seguro.

Planilhas legadas não definem diretamente o modelo do banco. Elas devem ser normalizadas.

---

## 17. Alertas e tarefas programadas

Alertas devem ser:

- derivados de condições verificáveis;
- idempotentes;
- deduplicados;
- resolvidos quando a condição deixa de existir;
- filtrados pelo escopo do usuário;
- associados à entidade e à ação relevante.

Nesta fase arquitetural, tarefas recorrentes podem ser comandos Django executados por agendador.

Não adicionar Celery ou Redis sem SPEC que demonstre necessidade.

---

## 18. Testes obrigatórios

### 18.1 Princípio

Código sem teste adequado não está concluído.

Toda SPEC deve definir os testes necessários.

### 18.2 Categorias

Conforme o impacto, testar:

- modelos e constraints;
- services;
- transições de estado;
- permissões;
- escopo por empresa/unidade;
- formulários;
- views e URLs;
- comandos;
- importações;
- idempotência;
- concorrência lógica;
- relatórios;
- exportações;
- alertas;
- regressões;
- interface principal.

### 18.3 Comandos mínimos

Ao final de uma implementação Django:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
```

Quando houver banco ou ambiente que não permita `migrate`, documentar exatamente o motivo e executar validação equivalente segura.

### 18.4 Proibições

- Não remover teste válido porque passou a falhar.
- Não reduzir uma asserção apenas para obter verde.
- Não ignorar falha sem justificativa.
- Não afirmar “testado” sem registrar comando e resultado.
- Não declarar conclusão com testes obrigatórios falhando.

---

## 19. QA e critérios de aprovação

O QA deve revisar:

- aderência à SPEC;
- aderência à Constituição;
- escopo;
- migrations;
- integridade;
- permissões;
- segurança;
- LGPD;
- performance;
- responsividade;
- testes;
- documentação;
- regressões;
- arquivos fora do escopo;
- alteração indevida das fontes.

Pareceres permitidos:

### APROVADA

Todos os critérios obrigatórios foram atendidos.

### APROVADA COM RESSALVAS

A entrega pode avançar, mas existem pendências não críticas claramente registradas, com impacto e ação recomendada.

### BLOQUEADA

Existe falha crítica, risco de dados, violação de permissão, migration insegura, teste obrigatório falhando ou divergência material da SPEC.

QA não deve aprovar “por aparência”.

---

## 20. Documentação

Toda funcionalidade relevante deve atualizar:

- SPEC correspondente;
- README, quando alterar instalação ou operação;
- `.env.example`, quando criar variável;
- arquitetura, quando criar decisão estrutural;
- manual operacional, quando alterar fluxo;
- roadmap, quando mudar fase;
- mapeamento legado, quando alterar importação.

Documentação deve descrever o que realmente existe.

---

## 21. Git e entrega

### 21.1 Antes de encerrar

Informar:

- arquivos lidos;
- arquivos criados;
- arquivos alterados;
- migrations;
- testes e resultados;
- limitações;
- riscos;
- parecer do QA;
- sugestão de commit.

### 21.2 Commits

O agente pode sugerir um commit no padrão:

```text
tipo(escopo): descrição objetiva
```

Exemplos de tipo:

- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `chore`
- `perf`
- `security`

Não executar commit sem autorização.

---

## 22. Definition of Done

Uma demanda somente está concluída quando:

- existe SPEC aprovada;
- implementação respeita o escopo;
- regras de negócio estão no backend;
- permissions e querysets foram verificados;
- migrations são seguras;
- testes obrigatórios passam;
- responsividade foi validada;
- documentação foi atualizada;
- não há alteração indevida fora do escopo;
- não há dados ou segredos expostos;
- QA emitiu parecer compatível;
- relatório final foi entregue.

“Funciona no meu computador” não constitui Definition of Done.

---

## 23. Emendas a esta Constituição

Uma emenda deve:

1. ser solicitada expressamente;
2. explicar o motivo;
3. indicar se a mudança é compatível ou incompatível com versões anteriores;
4. atualizar o número da versão;
5. registrar data e responsável;
6. apontar documentos e código afetados;
7. receber revisão do QA;
8. não apagar o histórico da regra anterior.

Versionamento sugerido:

- **PATCH:** esclarecimento sem alterar obrigação;
- **MINOR:** nova regra compatível;
- **MAJOR:** mudança incompatível ou retirada de proteção.

---

## 24. Declaração final

O SST Freedom deve priorizar integridade, segurança, rastreabilidade e facilidade de operação.

Nenhuma conveniência de implementação justifica:

- perda de histórico;
- saldo incorreto;
- acesso indevido;
- exposição de saúde ocupacional;
- alteração silenciosa de custo;
- duplicação de operação;
- quebra da experiência móvel;
- ausência de testes;
- desrespeito à SPEC aprovada.
