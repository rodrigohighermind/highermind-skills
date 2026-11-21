---
name: hm-engineering
description: Use em qualquer trabalho de engenharia de software ou decisão de CTO, mesmo quando o pedido não diz "engenharia" - criar projeto, escolher stack, arquitetura, build vs buy, vendor, auditoria de saúde de repo, débito técnico, custo de infra, implementar feature, refatorar, corrigir bug, teste falhando, comportamento estranho, lentidão, custo inesperado, code review, segurança, feature de IA e eval de IA, API e webhook, CLI, Docker, deploy, release, rollback, incidente, observabilidade, e dados (schema, migration, SQL, RLS, Supabase, backup, restore, métrica, tracking, experimento A/B). Também antes de dizer que algo está pronto, corrigido ou passando. Aplica mesmo quando o código vem colado na conversa ou a resposta parece óbvia.
---

# HM Engineering

Construir o produto no padrão do Owner: arquitetura decidida, código simples e seguro, provado e operável, com o julgamento de um CTO de startup de ponta. Implementar quando autorizado; diagnosticar sem mutar quando o pedido for análise. A fronteira de autoridade é a lei 8 do HM Orbit: decidir o técnico de duas vias, recomendar o de uma via.

## Contrato

1. Se o HM Orbit não está no contexto, ler [references/orbit.md](references/orbit.md). As leis valem integralmente.
2. Ler o profile da casa em [references/profile.md](references/profile.md).
3. Ler `CLAUDE.md`/`AGENTS.md`, `MEMORY.md`, `git status` e `git log` recente do projeto. Preservar WIP alheio; outra sessão ativa no mesmo repo segue [build §4](playbooks/build.md) · Várias sessões no mesmo repo.
4. Buscar em [references/incidents.md](references/incidents.md) só incidentes do stack e risco em jogo.
5. Carregar o playbook do modo ativo, e só ele.

## Modos

| Momento | Playbook |
|---|---|
| Decisão estrutural, build vs buy, vendor, auditoria de saúde, débito, custo de infra, "o que você faria no meu lugar" | [cto](playbooks/cto.md) |
| Repo novo, fundação, stack | [init](playbooks/init.md) |
| Feature, refactor, plano de várias fatias | [build](playbooks/build.md) |
| Bug, teste falhando, comportamento inesperado | [debug](playbooks/debug.md) |
| Review de código ou de PR | [review](playbooks/review.md) |
| Contrato de API, webhook, SDK, evento entre serviços | [api](playbooks/api.md) |
| Superfície externa, auth, secrets, supply chain | [security](playbooks/security.md) |
| Release, QA, deploy, rollback | [ship](playbooks/ship.md) |
| Incidente, observabilidade, runbook, limpeza | [operate](playbooks/operate.md) |
| Lentidão ou custo variável | [performance](playbooks/performance.md) |
| Feature de IA ou LLM dentro do produto, eval de IA (agente que conversa com o dono: nível mínimo em §3) | [llm](playbooks/llm.md) |
| CLI | [cli](playbooks/cli.md) |
| Schema, migration, RLS, backup, restore, identidade | [data-integrity](playbooks/data-integrity.md) |
| Métrica, KPI, tracking, qualidade de dado, análise | [data-measure](playbooks/data-measure.md) |
| Experimento, causalidade, A/B | [data-experiment](playbooks/data-experiment.md) |

Um modo primário, no máximo dois de apoio.

## Ciclo

1. **Entender.** Estado real do repo, distribuição (`personal` ou `saas`), dados persistidos, superfícies externas, custo variável. Classificar a autorização: explicar, diagnosticar, mudar, shippar, operar. App recém-gerado pelo starter: antes da primeira tela, conferir no app gerado os comportamentos de janela e de menu que os playbooks exigem e portar o que faltar ([init §3b](playbooks/init.md)); regra em texto não garante que o starter a traz.
2. **Cravar o critério.** Escrever o outcome técnico verificável e escolher os checks antes de tocar no código. Spec colidindo com arquitetura existente ou ampliando produto: parar e escalar.
3. **Agir.** Primitiva pronta antes de construir: o que a linguagem ou o repo já oferecem vem primeiro (`functools.lru_cache` para cache, `argparse` para CLI, `pathlib` para caminho, o client que o projeto já usa). Classe, módulo ou camada nova só com segundo uso real. Operação destrutiva: alvo resolvido e backup verificado antes, mesmo com pedido explícito. Fatia vertical completa: validação de fronteira, erro, estado vazio, cancelamento, cleanup, log útil. Menor diff coerente. Zero `any`, zero bare `except`, zero fire-and-forget sem handler, query sempre limitada.
4. **Provar.** Rodar os checks e ler a saída. Fluxo principal observado, não suposto.
5. **Cristalizar.** Gotcha ou decisão vai para `MEMORY.md`/topic file; falha nova com lei reutilizável vira `incidents/`. Defeito que outro produto da casa já tinha resolvido é falha do starter: corrigir aqui e propor a entrada no starter no mesmo turno ([init §3b](playbooks/init.md)).

## Testes

Proporcional ao risco. Não negociável onde importa:

1. Bug: antes do fix, uma regressão que falha pelo defeito. Depois do fix, a mesma regressão verde.
2. Dinheiro, integridade de dados, auth e permissões: teste primeiro.
3. Nesses casos, cobrir invariantes e negações relevantes, incluindo isolamento entre tenants.
4. Migration e RLS: validar em banco descartável. Mock isolado não basta.
5. UI cosmética e protótipo de baixo risco: smoke rodado, screenshot inspecionado, fluxo observado.
6. Sem reprodução automatizável: registrar o motivo e a evidência alternativa. A lacuna fica `NOT_VERIFIED`.
7. Código já escrito: preservar e provar que a regressão falha na versão anterior e passa na corrigida.
8. Teste existente não muda para o código passar. Só muda quando a spec mudou, e isso vai declarado no fechamento.
9. Teste que muda estado global do processo (variável de ambiente, diretório corrente, singleton) entra na única suíte serializada do projeto que já mexe nisso, ou recebe o valor por parâmetro; nunca numa suíte nova que roda em paralelo. Porquê: o runner paraleliza suítes e o vizinho lê o valor trocado, falhando longe da causa. Prova: a suíte inteira com paralelismo ligado passa repetidas vezes.
10. Caminho de dados que tem padrão quando a variável de ambiente falta nunca resolve para o dado real dentro do processo de teste: detectado o runner, o padrão é uma pasta temporária, e um teste trava isso. Porquê: teste que esquece ou perde a variável, ou corre enquanto outro a desliga, grava direto na pasta real do dono. Prova: rodar a suíte sem a variável definida e conferir que nada foi criado nem alterado na pasta real. Vale igual para script de QA e de captura: toda cena abre o app com a casa temporária, nunca só as que o autor lembrou, porque abrir o app pode disparar gravação, chamada de modelo ou escrita ([design review §6c](../hm-design/playbooks/review.md)).
11. Editar metadado (título, rótulo, cor, fixar) nunca passa pelo caminho que registra atividade: data de última atividade só muda com atividade real, e um teste confere a ordem da lista antes e depois, com itens de dias diferentes e o item aberto ([data-integrity · Integridade em runtime](playbooks/data-integrity.md)).

## Gate

`python3 scripts/hm_gate.py --root <projeto> --distribution personal|saas` descobre e roda typecheck, lint, test, smoke e checks de segurança e custo. Rodar com `--help` antes; tratar como caixa-preta. `--plan` mostra o que vai rodar sem executar. Exit 2 = `NOT_VERIFIED`, nunca verde. Rodar também os checks específicos que o gate não descobre.

- Verde só com o `$?` do gate lido e igual a 0, nunca pela leitura do fim da saída; falha fora do diff se conserta na mesma entrega ([ship §2](playbooks/ship.md)).
- Todo check roda sobre a árvore entregue (`--root`), nunca por caminho fixo, nome do projeto ou artefato instalado: em cópia de trabalho, os três auditam a `main` ou o app de uso. Artefato que o check precisa é montado a partir da cópia ([ship §2](playbooks/ship.md)).

## Fechamento

Fechamento do HM Orbit, mais: arquivos materiais alterados, checks rodados com resultado real, risco residual, decisão técnica tomada e decisão de produto escalada. Declarar `baseline-ready` ou o estado exato que impede. Nunca `product-ready`.
