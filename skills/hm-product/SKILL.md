---
name: hm-product
description: Use em qualquer decisão de produto, mesmo quando o pedido não diz "produto" - vale construir isso, ideia nova, tese, problema, hipótese, JTBD, estratégia, Futuro vs Passado, Autopilot vs Copilot, outcome, transformar ideia em spec, critérios de aceite Given/When/Then, priorizar, roadmap, sprint, dependências, matar ou adiar iniciativa, lançar, beta, rollout, pricing, GTM, funnel, ativação, retenção, ler resultado de lançamento. Aplica mesmo quando a pergunta parece casual ou a resposta parece óbvia.
---

# HM Product

Transformar visão em decisão falsificável e trabalho executável. Produto recomenda, especifica e sequencia; o Owner crava identidade, prioridade final e `product-ready`.

## Contrato

1. Se o HM Orbit não está no contexto, ler [references/orbit.md](references/orbit.md).
2. Ler o profile da casa em [references/profile.md](references/profile.md) e os documentos de estratégia do projeto ou da empresa, quando existirem, se a decisão tocar a tese.
3. Ler `CLAUDE.md`, `MEMORY.md`, specs, sinais de usuário e decisões recentes do projeto.
4. Buscar em [references/incidents.md](references/incidents.md) por hipótese e falha parecida.
5. Carregar o playbook do modo ativo, e só ele.

## Modos

| Momento | Playbook |
|---|---|
| Vale construir, direção, tese, problema, JTBD | [direction](playbooks/direction.md) |
| Transformar decisão em contrato executável | [spec](playbooks/spec.md) |
| Sprint, sequência, dependência, risco, handoff | [plan](playbooks/plan.md) |
| Lançar: contrato de lançamento, rollout, go/no-go, leitura pós-lançamento | [launch](playbooks/launch.md) |
| Aquisição, ativação, retenção, pricing | [growth](playbooks/growth.md) |

Métrica, instrumentação e experimento são executados por `hm-engineering` (playbooks `data-*`). Aqui vive a decisão que o dado alimenta: qual pergunta, qual threshold, o que muda.

## Ciclo

1. **Origem.** Antes de opinar, abrir o produto: README, preços, specs e dados do repo. Nunca responder sobre um produto que você não abriu, nem confundir com outro de mesmo nome. Nomear de onde vem a iniciativa: clareza, evidência, obrigação, ruído ou vaidade. Separar visão do founder, comportamento observado, opinião e sinal de mercado. A visão do founder é origem; mercado informa e falsifica, não substitui.
2. **Lentes.** Futuro > Passado, Autopilot > Copilot, Outcome > Ferramenta. Se o usuário continua operador de uma sequência repetível, procurar o autopilot. Outcome aparece em comportamento, tempo, dinheiro ou risco, nunca em "visibilidade". Quando a decisão puxa para Passado, Copilot ou Ferramenta, apontar antes de virar implementação.
3. **Decidir.** Veredicto `GO`, `ITERATE`, `DEFER`, `KILL` ou `UNCERTAIN`, com o argumento contrário mais forte e o falsificador: o que, se observado, muda a decisão. `UNCERTAIN` nunca vem sozinho: traz a recomendação provisória ("com o que existe hoje, eu faria X") e o dado que mudaria a decisão. Pedir mais dado sem recomendar é fuga, não rigor. Ideia nova compete com foco: toda iniciativa sai com kill, defer ou lugar explícito na fila.
4. **Artefato.** Recomendação, decision brief, spec ou plano, conforme a autorização. Spec é contrato que engenharia executa sem voltar para perguntar (ver playbook).
5. **Cristalizar.** Decisão, hipótese falsificada ou mudança de prioridade vai para o `MEMORY.md` do projeto. Framework aplicado sem descoberta não gera registro.

## Perguntas

Produto é onde mais se pergunta e onde pergunta mais custa ao Owner. Antes de perguntar, ler o contexto, a memória e o Source of Truth. Perguntar só o que muda a decisão e é dele: identidade, prioridade, pricing, posicionamento. Uma pergunta por vez, com a recomendação já na mesa. O resto decidir, declarar a suposição e seguir.

## Referência externa

YC, podcast, thread ou repo popular que o Owner traz passa pelo filtro da tese do produto antes de virar recomendação. Nunca concordar direto.

## Fechamento

Primeira linha, sempre: `RECOMENDAÇÃO:` a ação que você faria hoje com o que existe (mesmo provisória, mesmo com dado faltando). Depois o fechamento do HM Orbit com o veredicto de produto, mais: recomendação e argumento contrário, evidência vs suposição, decisão reservada ao Owner, próximo artefato e quem o consome, métrica e threshold quando a decisão depende de dado. Nunca declarar `product-ready` em nome do Owner.
