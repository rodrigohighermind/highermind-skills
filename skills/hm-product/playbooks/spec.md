# Playbook · Spec

Carregado sob demanda quando o modo é `spec`: transformar decisão de produto em contrato executável pelo Dev Team.

Este playbook aprofunda o modo. Autoridade, evidência e fechamento vêm do HM Orbit e não se repetem aqui.

## O que uma spec é

Contrato entre PM e Dev Team. Não é wireframe, não é documento de arquitetura, não é wishlist. Uma spec boa deixa o Dev Team implementar sem voltar com pergunta de produto, e deixa qualquer um verificar depois se o que foi entregue é o que foi pedido. Ambiguidade na spec vira pergunta no meio da sprint; pergunta no meio da sprint vira pausa; pausa custa dias.

Spec só nasce de decisão tomada. Se a direção ainda está em aberto, voltar para `direction`. Se o problema ainda não tem evidência, voltar para `discover`.

## Formato cravado

Ordem obrigatória. Seção não aplicável é declarada não aplicável, não omitida em silêncio.

### 1. Problema e hipótese (topo)

- **Problema:** quem sofre, quando, com que frequência, qual o custo de não resolver. Comportamento observado, não opinião.
- **Hipótese:** falsificável. "Se entregarmos X, o usuário fará Y, medido por Z." Hipótese que não pode falhar não é hipótese, é fé.

### 2. Outcome e non-goals

- **Outcome:** o resultado no mundo que esta entrega protege ou cria. Em comportamento, tempo, dinheiro, risco ou capacidade.
- **Non-goals:** o que explicitamente NÃO entra. Non-goals matam scope creep antes de nascer. Spec sem non-goals convida escopo escondido.

### 3. Acceptance criteria · Given/When/Then

Cada critério: um comportamento observável, verificável por qualquer pessoa, sem interpretação. Critério que precisa de reunião pra entender está mal escrito.

Exemplo real (padrão a seguir):

```gherkin
# Feature: agente financeiro concilia comprovante de pagamento

Given uma bill em aberto no mês corrente com valor e beneficiário conhecidos
When o Owner cola um comprovante de pagamento no chat
Then o agente extrai valor, data e beneficiário do comprovante
  And casa com a bill correspondente por valor e beneficiário
  And marca a bill como paga com referência ao comprovante
  And responde com o match em uma linha, sem pedir confirmação

Given um comprovante cujo valor diverge da bill candidata em mais de 1%
When o agente tenta conciliar
Then o agente NÃO marca a bill como paga
  And apresenta a divergência (valor esperado vs valor pago) e pede decisão do Owner

Given um comprovante que não casa com nenhuma bill em aberto
When o agente tenta conciliar
Then o agente lista as 3 bills mais próximas por valor e pergunta se é alguma delas
  And oferece registrar como pagamento avulso
```

Regras do bloco:

- Cobrir o caminho feliz E os caminhos de falha. Spec que só descreve sucesso está pela metade.
- Um critério por comportamento. Critério com "e também" escondendo três comportamentos vira três critérios.
- Nada de "deve ser rápido", "deve ser intuitivo". Quantificar ou cortar.

### 4. Estados obrigatórios

Mapear todos os aplicáveis. Estado não mapeado na spec é gap que o Dev Team vai reportar:

- loading, empty, error, success;
- permissions (quem pode ver/fazer o quê);
- concurrency (dois atores mexendo no mesmo dado);
- recovery (o que acontece depois da falha: retry, resume, estado parcial).

Agent-first se aplica aqui: antes de especificar tela para um estado, perguntar se o agente resolve via conversa. UI é visibilidade e override, não o caminho primário.

### 5. Constraints

Produto, dados, segurança e custo. Exemplos do tipo de constraint que pertence à spec:

- custo por operação (chamadas LLM, API externa) com teto;
- dados sensíveis envolvidos e o que nunca sai do dispositivo/projeto;
- compatibilidade obrigatória com fluxo ou contrato existente;
- performance percebida quando ela é requisito de produto (com número).

Constraint técnica sem motivo de produto não entra: vira decisão delegada.

### 6. Decisões delegadas vs reservadas

| Delegado ao Dev Team (não especificar) | Reservado ao Owner (não delegar) |
|---|---|
| Arquitetura, stack, libs, schema interno | Identidade do produto, nome, narrativa |
| Estrutura de código, patterns, refactors | O que é valor pro usuário final |
| Estratégia de teste e tooling | Escopo da sprint (o que entra e sai) |
| Sequência interna de implementação | Trade-off que muda a UX final |
| Escolha de infra dentro das constraints | Custo financeiro relevante (plano, serviço pago) |
| | Declarar product-ready |

Escrever arquitetura como requisito de produto exige necessidade externa demonstrada (compliance, contrato, integração). Sem isso, é invasão do território do Dev Team e a spec deve ser corrigida.

Listar explicitamente na spec as decisões delegadas relevantes ("Dev Team decide: estratégia de cache, formato de persistência, biblioteca de parsing"). Delegação explícita evita escalation desnecessária.

### 7. Analytics e threshold de aprendizado

- Quais eventos/medidas provam ou falsificam a hipótese do topo.
- Threshold definido ANTES do lançamento: "se X ≥ Y em N dias, hipótese confirmada; abaixo, iteramos ou matamos."
- Instrumentação (schema de evento, pipeline) é território do `hm-engineering` (playbooks `data-*`); a spec declara O QUE medir e o threshold de decisão, não o COMO.

### 8. Definition of Done e evidence bundle

DoD da entrega = baseline-ready do HM Orbit + o específico desta spec:

- todos os acceptance criteria verificados, com evidência por critério;
- todos os estados da seção 4 implementados e demonstrados;
- analytics da seção 7 emitindo;
- evidence bundle esperado: o que o Dev Team apresenta como prova (comando rodado, screenshot, gravação de fluxo, query). "Funciona na minha máquina" não é evidência.

Projeto pode endurecer o DoD; nunca afrouxar. Depois do baseline-ready vem a validação do Owner. São dois estados distintos e em sequência; confundir os dois gera atrito.

### 9. Escalate path (base)

Para cada tipo de bloqueio, o destino:

- **Ambiguidade de produto** (dois entendimentos válidos do critério): PM decide. Dev Team não escolhe interpretação de produto sozinho.
- **Gap técnico que muda custo/prazo material:** Dev Team propõe opções com trade-offs; PM atualiza a spec; Owner decide se o trade-off toca UX ou escopo.
- **Decisão reservada ao Owner emergindo no meio da sprint:** parar aquele fio, seguir no que não depende, escalar.

## Gaps que o Dev Team reporta

A spec deve antecipá-los; quando ainda assim aparecem, são escalation legítima e obrigam atualização da spec, não gambiarra local:

1. Acceptance criterion tecnicamente inviável como escrito.
2. Decisão técnica não cravada que muda significativamente custo ou tempo.
3. Estado ou contexto não mapeado pelo PM (branch suja, untracked files, dependência inesperada, schema diferente do esperado).
4. Estimativa da sprint estourando mais de 20%.
5. Padrão arquitetural existente no projeto colidindo com o que a spec pede.

Gap reportado é sinal de contrato funcionando. A resposta do PM é sempre atualizar a spec: a spec é o contrato vivo, não o chat.

## Anti-padrões de spec

- **Spec-romance:** páginas de contexto, zero critério verificável.
- **Spec-arquitetura:** decide schema, lib e pattern e chama de requisito.
- **Spec-caminho-feliz:** nenhum estado de erro, permissão ou concorrência.
- **Spec-formulário:** descreve telas e campos antes de descrever o trabalho que o agente entrega.
- **Critério de gosto:** "deve parecer premium". Gosto é direção de design (`hm-design`), não acceptance criterion.
- **Hipótese blindada:** sem métrica nem threshold, impossível de falsificar.
- **Delegação vazia:** "Dev Team decide o resto" sem listar o que é "o resto".

## Saída

A spec completa no formato acima, mais:

- suposições assumidas que o Owner deve confirmar antes da sprint;
- decisões reservadas ao Owner pendentes, se houver;
- consumidor do artefato (Dev Team, sprint alvo) e próxima ação.
