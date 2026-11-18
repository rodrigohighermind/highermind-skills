# Playbook · Growth

Carregado sob demanda quando o modo é `growth` ou `learn`: aquisição, ativação, retenção, pricing, GTM, funnel e decisão de produto baseada em dado.

Este playbook aprofunda o modo. Autoridade, evidência e fechamento vêm do HM Orbit e não se repetem aqui. Instrumentação, schema de evento e análise estatística são território do `hm-engineering` (playbooks `data-*`); aqui vive a DECISÃO que o dado alimenta.

## Postura

Números > opiniões. Sem dados, estimar com ranges (otimista/base/pessimista) e dizer que é estimativa. Nunca recomendar growth hack; recomendar growth system: mecanismo que continua funcionando quando ninguém está empurrando. Não otimizar métrica vazia: otimizar métrica que importa pro negócio de 50 anos. Growth recomenda; mudança material de pricing, posicionamento ou canal é decisão do Owner.

## Passo 1 · Diagnóstico de estágio antes de framework

Todo conselho de growth é errado no estágio errado. Primeiro, onde o produto está:

- **Pré-launch / PMF incerto:** prioridade é ativação, retenção e aprendizado. Escalar aquisição aqui é comprar tráfego pra um balde furado e queimar o canal junto.
- **Early traction:** prioridade é retenção comprovada por coorte + primeiro canal repetível.
- **Scaling:** prioridade é canal, unidade econômica e capacidade operacional de entregar qualidade no volume.

Sinal honesto de PMF não é elogio nem sign-up: é retenção por coorte, uso repetido sem empurrão e usuário que reclama quando o produto falha.

## Passo 2 · Funnel AARRR aplicado

Analisar pelo prisma das 5 métricas pirata, sempre nesta ordem de pergunta:

- **Acquisition:** como o usuário chega? Qual canal, qual custo, qual repetibilidade?
- **Activation:** qual o aha moment? Quanto tempo e quantos passos até lá? Cada passo entre o sign-up e o aha é onde o funnel morre.
- **Retention:** o que faz voltar? Qual a frequência natural de uso do problema (diária, semanal, mensal)? Medir retenção contra a frequência natural, não contra desejo.
- **Revenue:** qual modelo, qual pricing, qual LTV?
- **Referral:** existe viralidade natural no uso? Loop de indicação, artefato compartilhável, resultado visível a terceiros?

Regra de foco: 3 a 5 métricas que importam agora. Mais que isso é dashboard, não decisão.

Ativação merece atenção desproporcional em produto agent-first: o aha moment é o agente entregando o primeiro resultado real, não o onboarding completado. Medir time-to-first-outcome. Se o primeiro valor exige configurar, importar e preencher antes de receber qualquer coisa, o produto está pedindo confiança antes de dar prova.

## Estrutura de métricas · North Star e KPI tree

Uma North Star: a métrica que captura o valor core entregue ao usuário (outcome, não atividade). Abaixo dela, drivers acionáveis; ao lado, guardrails que não podem cair:

```
North Star (valor entregue)
├── Driver 1 (acionável)
│   ├── input metric A
│   └── input metric B
├── Driver 2 (acionável)
│   └── input metric C
└── Guardrails (não podem cair): custo LLM/operação, qualidade, retenção
```

O teste de cada métrica na árvore: se ela mudar, alguém faz algo diferente? Métrica que não muda decisão sai da árvore. North Star de atividade (mensagens enviadas, sessões) em vez de outcome é como métrica de vaidade entra vestida de rigor.

## Passo 3 · Growth model

Desenhar o loop principal em texto:

```
Canal → Ação do usuário → Resultado → Amplificação → volta ao Canal
```

Loop bom se retroalimenta: o output de um ciclo é input do próximo (conteúdo gera audiência, audiência gera caso de uso, caso vira conteúdo). Funil linear se esgota; loop compõe.


Referral não se pede, se desenha: o output do produto precisa ser visível a terceiros pra virar canal. Deliverable com marca, resultado que o cliente mostra, artefato compartilhável por natureza. NPS alto sem mecanismo de compartilhamento é energia potencial sem circuito.

## Passo 4 · Pricing

Pricing é decisão de produto, não de finance. Medir quatro coisas antes de recomendar:

1. **Willingness to pay:** o que o cliente já paga hoje pra resolver isso (ferramenta, funcionário, fornecedor, multa por não resolver)? Esse número ancora o teto.
2. **Custo de servir:** incluindo custo LLM por operação. Custo é restrição de design; margem se desenha, não se descobre.
3. **Captura de valor:** quanto do valor criado o preço captura. Ferramenta captura ~10% (budget de tooling); trabalho entregue captura 25-50% (budget de trabalho).
4. **Alinhamento com outcome:** o cliente paga mais quando recebe mais valor? Pricing desalinhado do outcome cria incentivo pra usar menos o produto.

Guardrail cravado: **pricing por outcome > pricing por assento.** Seat-based é sintoma de copilot. Modelos de referência: per-deliverable, per-resolution, per-audit, per-engagement, success fee, comissão. Híbrido (base + outcome) é transição válida.

### Packaging

Cada modelo tem trade-off explícito; escolher por mecânica, não por moda:

- **Free trial:** só se o aha moment cabe na janela do trial. Trial de 14 dias pra valor que aparece no dia 30 só treina churn.
- **Freemium:** só se o usuário free alimenta o loop (dado, conteúdo, indicação). Senão é custo de servir sem retorno, e em produto com LLM o custo do free é real por operação.
- **Premium direto:** filtra por willingness to pay desde o dia 1. Menos volume, sinal mais honesto. Bom par com wedge de dor aguda.
- **Camadas:** cada camada precisa de um outcome distinto, não da mesma ferramenta com limites diferentes. Limite artificial de uso numa camada barata pune exatamente o usuário mais engajado.

Preço vigente, camadas e números de mercado são state vivo: consultar `MEMORY.md` do projeto ou fonte recente, nunca afirmar de memória.

## Passo 5 · GTM

- **Wedge primeiro:** um segmento estreito com dor aguda e budget existente vence "todo mundo que tem o problema". Melhor wedge: gasto já terceirizado (o comprador já compra outcome de fora, a venda é troca de fornecedor, não reestruturação).
- **Canal casado com o wedge:** onde esse segmento já está e já confia.
- **Mensagem de outcome:** vender o resultado, não a feature. "Peticiona seu lote em horas" vence "IA jurídica com RAG".
- **Expansão:** land estreito, expand por outcomes adjacentes do mesmo cliente antes de abrir novo segmento.

## Passo 6 · Retenção e churn

- **Cohort analysis por safra:** cada coorte de entrada acompanhada no tempo. Média agregada esconde o buraco; a curva por coorte mostra se o produto melhora.
- **Forma da curva:** coorte que estabiliza num platô tem PMF naquele segmento; coorte que decai a zero não tem, não importa o topo do funil.
- **Churn risk é comportamento, não opinião:** queda de frequência, abandono do fluxo core e falha repetida precedem o cancelamento. Definir os sinais e o que o sistema FAZ quando detecta (Autopilot: o produto age, não só reporta).
- **Frequência natural manda:** produto de uso mensal com meta de DAU é métrica de vaidade institucionalizada.

## Passo 7 · Unit economics

Sempre que houver dinheiro no loop, os quatro números, medidos ou estimados em ranges declarados:

- **CAC por canal**, não agregado. CAC médio esconde o canal que sangra.
- **LTV com margem real:** receita menos custo de servir, incluindo custo LLM por operação. LTV calculado sobre receita bruta em produto AI-native é ficção.
- **Payback period:** quanto tempo até o cliente pagar o próprio CAC. Payback longo com caixa curto mata antes do LTV chegar.
- **Margem por entrega:** em pricing por outcome, cada entrega tem custo próprio. Margem que depende de o modelo não ser usado é pricing errado.

Regra de sanidade: custo de API é guardrail em qualquer produto com LLM e não pode crescer mais rápido que o valor entregue. Se cada usuário novo piora a margem, growth está amplificando um problema, não um negócio.

## Passo 8 · Decisão por dado

O núcleo portado do PM de dados: dado serve pra decidir, não pra decorar relatório.

### Antes de coletar

1. **Qual decisão será tomada?** Se nenhuma decisão muda com o resultado, não medir. É curiosidade, não experimento.
2. **Threshold definido ANTES de olhar os dados:** "se X ≥ Y, fazemos A; senão, B." Threshold definido depois vira racionalização do que já se queria fazer.
3. **North Star + guardrails:** uma métrica que captura o valor core entregue; guardrails que não podem cair enquanto se otimiza (custo LLM, qualidade, retenção). Otimizar driver derrubando guardrail é falso progresso.

### Experimentos

- Priorizar por ICE: Impact × Confidence × Ease. Top 3, não backlog infinito.
- Um experimento responde uma pergunta. Experimento que testa três coisas não conclui nenhuma.
- Sample pequeno demais pra significância: dizer, não forçar conclusão. "Melhorou" sem número e intervalo não é resultado. Desenho estatístico (sample size, potência, significância) executa no `hm-engineering` (playbooks `data-*`).

### Ao ler resultados

- Correlação não é causalidade; dizer quando causalidade não é provável.
- Métricas de vaidade (pageviews, downloads, sign-up sem ativação) são ruído. Ignorar.
- Segmentar antes de concluir: efeito médio nulo pode esconder efeito forte num segmento.
- Listar explicações rivais antes de aceitar a explicação favorita.
- Caveats obrigatórios: o que esses dados NÃO dizem.

### Fechar o loop (learn)

```
hipótese → comportamento observado → segmentos → explicações rivais → decisão → memória
```

Resultado inconclusivo é aprendizado quando muda o desenho do próximo teste. Feedback vocal de meia dúzia de usuários não é verdade geral; comportamento pago e repetido é o sinal. Toda decisão tomada por dado persiste em memória com a evidência que a sustentou.

## Fronteira com dados (hm-engineering)

Fica lá, não aqui: schema de evento, pipeline de tracking, execução de query e análise, desenho estatístico do experimento (sample size, potência, significância), qualidade de dado. Fica aqui: qual pergunta o dado responde, qual decisão muda, qual o threshold, e a recomendação que sai do resultado. Trabalho conjunto: este modo define o contrato de decisão; `hm-engineering` (playbooks `data-*`) entrega o evidence bundle.

## Saída

Recomendação de growth com: estágio diagnosticado, as 3-5 métricas que importam agora, loop principal desenhado, top 3 experimentos por ICE com threshold de decisão pré-definido, unit economics (medidos ou ranges declarados), e as decisões reservadas ao Owner (mudança de pricing, posicionamento, canal pago). Sempre com o argumento contrário mais forte.
