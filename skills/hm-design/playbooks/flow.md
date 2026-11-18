# Playbook · Fluxo Cognitivo e UX

Carregado sob demanda pelo modo `flow` (e consultado por `review` quando a validação cobre jornada, não só pixel). o que o usuário precisa pensar, em que ordem, com qual confiança.

## 1. Princípio central

Fluxo ótimo = decisões mínimas. Cada clique pergunta ao usuário: "isso é o que você quer?". Três tipos de friction matam um app, e este playbook caça os três:

1. decisão desnecessária;
2. decisão mal posicionada;
3. decisão sem informação suficiente.

Friction não é sempre ruim: friction intencional protegendo dado, dinheiro, identidade ou irreversibilidade é design. Friction acidental é bug.

Este playbook avalia DECISÃO, não visual. Pixel, tipografia e dark mode são do `review.md` e `direction.md`.

## 2. Quando rodar

- Antes de shippar feature nova com fluxo multi-step.
- Após refactor que mudou navegação.
- Quando o usuário reclama "não achei", "não entendi", "achei que ia fazer outra coisa".
- Periodicamente em onboarding, checkout e forms importantes.
- Quando conversão caiu (se medida).

## 3. Os três frictions

### 3.1 Decisão desnecessária

O usuário escolhe algo que o sistema poderia decidir por ele com confiança.

**Sinais:** default óbvio existe mas a pergunta aparece mesmo assim · opção que 95% escolhem igual (os 5% mudariam depois em configurações) · múltiplas opções equivalentes com nomes diferentes · dropdown com 1 item.

**Fix:** remover a pergunta. Se precisa de override, esconder em "configurações avançadas" ou link "outras opções". Em produto agent-first, a pergunta vira ação do agente com visibilidade + undo.

### 3.2 Decisão mal posicionada

O pedido vem antes do usuário ter contexto pra responder, ou depois de ele já ter tomado caminho difícil de desfazer.

**Sinais:** form pede dado que só faz sentido após o passo seguinte · "selecione o tipo" sem explicar o que cada tipo faz neste fluxo · modal de upgrade no meio de tarefa em progresso · onboarding que pede tudo upfront antes de provar valor.

**Fix:** mover a decisão pro ponto onde o usuário tem contexto. Lazy ask: adiar até ser necessária.

### 3.3 Decisão sem informação suficiente

O usuário encara uma escolha sem saber a consequência.

**Sinais:** botão "salvar" / "publicar" / "deletar" sem dizer o que exatamente acontece · toggle sem descrever efeito · escolha entre planos sem comparativo · "Confirmar?" sem mostrar o que será afetado.

**Fix:** preview antes de confirmar. Microcopy descrevendo consequência. Diff visual: "você está prestes a apagar 47 itens".

## 4. Arquitetura de informação e hierarquia de decisão

Ordem importa. Decisão-chave primeiro, detalhe depois. Escopo grande antes de escopo pequeno.

**Pattern funil:** topo, o que você quer fazer; meio, configurar parâmetros; base, confirmar e executar.

**Anti-pattern:** misturar níveis de detalhe na mesma tela (escolher tema do app + nome do post + autor + cores ao mesmo tempo).

A navegação reflete o modelo mental do usuário, não o schema do banco. Se explicar o fluxo exige manual, usuário comum não atravessa.

## 5. Reversibilidade

O usuário precisa saber: posso desfazer isso?

- **Ação reversível:** sem confirmação, com undo (ctrl+z, snackbar "desfazer").
- **Ação irreversível:** confirmação explícita com o nome do objeto.
- **Ação destrutiva:** type-to-confirm (digitar "delete my account") ou 2-step com botão secundário.

**Anti-pattern:** confirmação em tudo. Vira ruído, o usuário clica sem ler, e a confirmação que importava perde o efeito.

## 6. Recovery de erro

Usuário errou ou sistema errou: o que acontece?

**Fluxo bom:** form preserva dados no erro de validação (não limpa) · mensagem indica COMO consertar, não só QUE quebrou · sistema oferece alternativa quando bloqueia ("não consegui X, quer tentar Y?") · caminho de volta sempre claro (breadcrumb, X de fechar, browser back funcionando).

**Fluxo ruim:** form perde tudo no erro · "Erro" genérico sem orientação · 404 sem busca nem saída · modal sem X visível.

## 7. Friction points conhecidos

Checar cada um:

| Pattern | Friction comum |
|---|---|
| Onboarding | pergunta tudo upfront · usuário abandona |
| Form longo | sem progress indicator · usuário não sabe quanto falta |
| Multi-step | sem salvar e continuar depois |
| Choice paralysis | mais de 5 opções em paralelo sem categorização |
| Dead-end | estado sem saída óbvia |
| Primary action ambígua | 3 botões com o mesmo peso visual na tela |
| Missing affordance | clicável que parece texto, texto que parece clicável |
| Expert mode invisível | power user sem atalho de teclado |

## 8. Estados

### Empty

Toda lista, dashboard e área: o que aparece antes do usuário popular? Empty state vazio é bug de UX, não "melhora depois".

**Bom:** explica o que a área mostra + CTA pra criar/popular + preview do output esperado.
**Ruim:** "Nenhum item encontrado." (e agora?)

### Loading

Toda transição assíncrona: o que aparece enquanto carrega?

**Bom:** shimmer/skeleton com o shape do conteúdo final · spinner tolerável só em operação <2s dentro de contexto (botão, inline) · estimativa de tempo se >5s ("destilando seu mapa... ~15s") · cancelável quando aplicável.
**Ruim:** spinner genérico girando indefinidamente, freeze sem feedback, "Carregando..." em texto plano. Spinner genérico isolado como único loading state reprova.

### Error e success

Erro diz o que houve, o que fazer e preserva o trabalho. Success confirma com feedback proporcional: mudança pequena, feedback discreto; conclusão de fluxo, fechamento claro.

## 9. Responsividade de fluxo: desktop vs mobile

O fluxo funciona nos dois, mas o ótimo difere:

| Desktop | Mobile |
|---|---|
| hover states ricos | touch targets >= 44px |
| multi-column | single column |
| keyboard shortcuts | gestures (swipe, pull-to-refresh) |
| modal grande OK | bottom sheet > modal |
| form longo tolerável | form quebra em steps |

## 10. Acessibilidade de fluxo

Mínimo pra qualquer fluxo crítico:

- Percorrível inteiro por teclado, com ordem de foco lógica e foco visível.
- Ação primária alcançável sem mouse; Escape fecha o que abriu.
- Contraste de texto e de estado (erro, disabled) legível, não só distinguível por cor.
- Touch targets >= 44px em mobile.
- `prefers-reduced-motion` não quebra transição de passo (o fluxo avança sem a animação).
- Mensagens de erro associadas ao campo (não só um toast que some).

## 11. Como executar o audit

Pra cada fluxo crítico:

1. **Mapear:** quantos passos, onde estão as decisões, onde estão as transições async.
2. **Walkthrough como usuário novo:** anotar cada momento de dúvida.
3. **Walkthrough como power user:** quem usa toda semana, anotar friction repetida.
4. **Edge cases:** rede ruim, clique duplo, back button, duas abas abertas.
5. **Priorizar os 3 maiores frictions** com fix concreto cada.

Walkthrough apenas mental não sustenta `PASS`: percorrer o fluxo renderizado quando ele existe.

## 12. Formato do audit

```text
UX FLOW AUDIT
Projeto: [nome]
Fluxos analisados: [lista]

FLUXO: [nome]
Passos: [N] · Decisões do usuário: [N]

DECISÕES DESNECESSÁRIAS
- [step X]: [decisão] · fix: [remover/default]

DECISÕES MAL POSICIONADAS
- [step Y]: [decisão] vem antes de [contexto necessário] · fix: [mover pra step Z]

DECISÕES SEM INFORMAÇÃO
- [step]: [decisão] sem [contexto] · fix: [microcopy/preview]

FRICTION POINTS
- [descrição]: [impacto] · fix: [como corrigir]

RECOVERY DE ERRO
- [cenário]: [tratado/quebrado] · fix se quebrado

EMPTY STATES
- [área]: [tem/falta]

LOADING STATES
- [área]: [shimmer/spinner/quebrado]

CLASSIFICAÇÃO POR FLUXO
[fluxo]: PASS / OPTIMIZE / REDESIGN
```

A classificação por fluxo alimenta o fechamento do HM Orbit; ela não o substitui.

## 13. Regras

- Avaliar decisão, não visual. Visual é `review.md`.
- Empty state vazio e spinner genérico reprovam, sem exceção de "MVP".
- Se o fluxo exige manual pra ser percorrido, está reprovado pra usuário comum.
- Owner pode ter razão pra friction extra (ex: type-to-confirm em delete grande). Reportar a friction; Owner confirma se é intencional.
