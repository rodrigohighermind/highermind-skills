# Playbook · Plan

Carregado sob demanda quando o modo é `plan`: sequenciar trabalho, montar sprint, mapear dependências e riscos, gerir pausa e estouro de estimativa.

Este playbook aprofunda o modo. Autoridade, evidência e fechamento vêm do HM Orbit e não se repetem aqui.

## Princípios de execução

- Shipping > planning. Plano perfeito que não shipa vale zero.
- Task vaga é task que não acontece. Especificidade é respeito pelo executor.
- Se o escopo não cabe no tempo, corta escopo. Nunca corta qualidade.
- Velocidade e qualidade não são trade-off: são ambos obrigatórios. O que se negocia é escopo.
- Processo existe pra remover fricção, não pra adicionar. Não criar cerimônia por criar.
- O Owner opera múltiplos projetos em paralelo: cada projeto precisa de próximo passo claro a qualquer momento. Nada parado sem motivo nomeado.

## Sequenciamento

Quebrar por **outcomes verificáveis**, não por camadas técnicas. "Backend pronto" não é outcome; "Owner consegue conciliar um comprovante de ponta a ponta" é.

Ordem de decisão do sequenciamento:

1. **Dependência dura:** o que precisa existir antes (dado, contrato, decisão do Owner, serviço externo).
2. **Risco na frente:** o bloco mais incerto vai primeiro. Descobrir que a peça central não funciona no dia 8 de 10 é falha de sequenciamento, não azar.
3. **Aprendizado:** o que responde a pergunta mais cara mais cedo.
4. **Custo de atraso:** o que perde valor esperando.

Priorização entre iniciativas: valor × aprendizado × custo de atraso, descontado por esforço e dependência. Volume de ideias não é critério. Entre projetos, vale last-touch wins: a sessão atual é prioridade total até o Owner cravar outra coisa.

## Estrutura de sprint

```
Sprint N · [nome do outcome] (estimativa em dias)
├── [P0] blocker: sem isso nada funciona
├── [P0] blocker
├── [P1] importante, não bloqueia o outcome
├── [P2] cortável se apertar
└── [DoD] critérios de fechamento (referência à spec)
```

Exemplo com conteúdo real, no nível de especificidade esperado:

```
Sprint 3 · Owner concilia comprovante pelo chat, ponta a ponta (4 dias)
├── [P0] parser de comprovante extrai valor/data/beneficiário (formatos: PDF do banco, print, texto colado)
├── [P0] matcher casa comprovante com bill aberta por valor+beneficiário, tolerância 1%
├── [P0] estados de divergência e não-match respondem conforme spec §3
├── [P1] registro de pagamento avulso quando não há bill
├── [P2] histórico de conciliações no comando de status
└── [DoD] todos os Given/When/Then da spec verificados + evidence bundle + baseline-ready
```

"Melhorar a conciliação" não é task. "Matcher casa por valor+beneficiário com tolerância 1%" é.

- P0 = sem isso o outcome não existe. P1 = importante, entra se couber. P2 = primeiro a cair.
- Quando a timeline aperta, o corte é sempre de baixo pra cima: P2, depois P1. P0 não se corta; se P0 não cabe, a sprint está mal desenhada e volta pro planejamento.
- Toda entrega tem DoD claro. "Feito" não é DoD. O DoD da sprint referencia a spec; baseline-ready é o gate do Dev Team, product-ready é a avaliação do Owner, nesta ordem.
- Sprint fecha com auto-checkpoint: lição, gotcha e decisão persistidas em `MEMORY.md` ou topic file. Histórico de sessão não sobrevive; memória escrita sobrevive.

## Dependências e critical path

Para cada bloco, nomear o que precisa existir antes de começar: decisão, dado, acesso, artefato de outro modo (spec aprovada, design direction, schema do `hm-engineering` (playbooks `data-*`)).

- Critical path explícito: a corrente de blocos que define a duração total. Todo o resto tem folga; o critical path não.
- Dependência externa (serviço de terceiro, aprovação, credencial) é risco por definição: identificar cedo, pedir cedo, nunca deixar para o dia em que bloqueia.
- Handoff entre skills é dependência também: spec → dev, design direction → implementação, migration → feature. Handoff sem artefato pronto é bloqueio disfarçado de "em paralelo".

## Estimativa honesta

- Estimar por bloco de outcome, não por total chutado. O total é a soma dos blocos mais a incerteza nomeada.
- Separar o conhecido do desconhecido: bloco já feito antes estima justo; bloco com incógnita (API nova, formato de dado desconhecido, integração nunca testada) carrega buffer explícito e vai pra frente da sprint, onde a incerteza custa menos.
- Estimativa sem os pressupostos escritos não é estimativa, é palpite. "4 dias assumindo que o formato do PDF é estável" deixa o estouro diagnosticável.
- Otimismo crônico não se corrige com mais otimismo: comparar estimado × realizado nas últimas sprints do projeto (`MEMORY.md`, git log) e calibrar.

## Riscos

| Risco | Probabilidade | Impacto | Mitigação | Dono |
|---|---|---|---|---|
| | | | | |

Regras: risco sem mitigação nomeada é só ansiedade documentada. Risco de alta probabilidade × alto impacto muda o sequenciamento (vai pra frente da sprint). Flagar blocker cedo é trabalho do plano; blocker descoberto tarde quase sempre era visível antes.

## Cadência

- **Checkpoints:** pontos nomeados onde progresso é comparado ao plano. Em sprint curta de solo, o checkpoint natural é o fechamento de cada P0.
- **Ship date:** data alvo declarada. Sem data, "quase pronto" dura semanas.
- **Rollback plan:** antes de shipar, saber como voltar. Entrega sem caminho de volta em operação que toca dados reais viola dados sagrados.

## Pausa de sprint

Regras cravadas de quem pode pausar o quê:

- **PM pausa o Dev Team** por até ~2h sem confirmar com o Owner, para resolver pergunta de produto que precisa dele. Acima de 2h: Owner é pingado.
- **Blocker externo** (serviço fora do ar, dependência indisponível, infra quebrada) é ping imediato ao Owner. Não se espera 2h por algo que ninguém no fluxo controla.
- **Dev Team pausa a si mesmo** sem pedir permissão quando a exploração revela escopo diferente do mapeado: branch suja com untracked, schema diferente do esperado, dependência não documentada. Reporta o achado e espera decisão. Seguir implementando sobre terreno não mapeado é como escopo escondido entra.

Pausa não é falha do plano. Pausa não reportada é.

## Estado entre sessões

O plano precisa sobreviver à sessão que o criou. Convenções de estado:

- PR aberta = "em revisão". Branch local = "trabalho em progresso, segue cravado".
- Stash não guarda estado que precisa viver mais que algumas horas. Stash some.
- Sessão longa pode compactar: o que sobrevive é `MEMORY.md` + topic files + commits, nunca o histórico do chat. Decisão de plano tomada em conversa e não persistida não existe na próxima sessão.
- Ao retomar: ler `MEMORY.md` do repo, depois git log recente da branch ativa, depois o último pedido do Owner. Nessa ordem.

## Estouro de estimativa: a regra dos 20%

Quando a estimativa da sprint vai estourar em mais de 20%, o Dev Team escala. Não silenciosamente absorve, não corta qualidade pra caber. A escalation traz:

1. o que causou o estouro (descoberta, dependência, subestimativa);
2. estimativa revisada com o que já se sabe agora;
3. opções: cortar P1/P2, dividir a sprint, replanejar.

O PM decide o ajuste de escopo dentro da spec; se o corte muda UX final ou valor pro usuário, sobe pro Owner. Estouro reportado no dia 3 é gestão; no dia 9 é surpresa.

## Escopo novo no meio da sprint

Escopo novo volta para decisão. Não entra escondido na sprint.

- Ideia nova durante a execução vai pra fila de `direction`/`discover`, não pro sprint corrente.
- A exceção é correção que bloqueia o outcome da própria sprint: isso não é escopo novo, é P0 descoberto.
- "Já que estou mexendo aqui..." é a origem da maioria dos estouros. Nomear e devolver pra fila.

## Saída

Plano com: outcome da sprint, breakdown P0/P1/P2 com DoD, dependências e critical path, tabela de riscos com donos, cadência (checkpoints, ship date, rollback), e as decisões reservadas ao Owner pendentes que podem bloquear o caminho. Próxima ação única e verificável.
