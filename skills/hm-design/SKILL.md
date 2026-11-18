---
name: hm-design
description: Use em qualquer trabalho de interface ou experiência, mesmo quando o pedido não diz "design" - criar ou refazer tela, página, landing, dashboard, componente, TUI, fluxo, onboarding, navegação, design system, tokens, tipografia, cor, layout, responsividade, motion, estados de loading, empty e error, texto de interface, acessibilidade, e revisar ou aprovar uma tela implementada. Aplica mesmo quando a tela vem colada como código ou o ajuste parece pequeno.
---

# HM Design

Transformar a tese do produto em experiência compreensível, distinta e implementada. Gosto sem artefato é opinião; screenshot sem fluxo é superfície.

## Contrato

**Lei de ferro: nenhum veredito sobre tela sem vê-la.** Antes de aprovar, reprovar ou dizer que está bom: renderizar (seção Render), salvar os screenshots em `.orbit/review/`, ler console e erros da página. Sem isso, o veredito é `NOT_VERIFIED`, por mais óbvio que o código pareça.

1. Se o HM Orbit não está no contexto, ler [references/orbit.md](references/orbit.md).
2. Ler o profile da casa em [references/profile.md](references/profile.md). Brief do Owner vence o profile; profile vence default de IA.
3. Ler o real antes de propor: rotas, componentes, tokens, screenshots e o design system existente. Com DS ou referência na mão, copiar o uso exato, nunca inventar wrapper.
4. Buscar em [references/incidents.md](references/incidents.md) por mídia, fluxo e falha.
5. Carregar o playbook do modo ativo, e só ele.

## Modos

| Momento | Playbook |
|---|---|
| Direção, identidade, tokens, construir interface | [direction](playbooks/direction.md) |
| Jornada, decisão, navegação, recovery, estados | [flow](playbooks/flow.md) |
| Validar experiência implementada | [review](playbooks/review.md) |

## Ciclo

1. **Assunto.** Nomear o sujeito, o usuário, a mídia e o único trabalho da tela. A identidade nasce do mundo do assunto (material, vocabulário, ofício), não de um template.
2. **Plano em duas passadas, quando a direção é nova.** Primeiro um plano compacto: 4 a 6 cores nomeadas, papéis tipográficos, layout em uma frase mais wireframe ASCII, a assinatura memorável. Depois confrontar o plano com o default de IA: se cada parte serviria a qualquer produto parecido, revisar e dizer o que mudou e por quê. Só então codar. Ajuste em tela existente parte do sistema que já existe, sem replanejar a identidade.
3. **Construir.** Conteúdo real, hierarquia intencional, ousadia gasta em um lugar só e o resto disciplinado. Responsividade, foco visível, reduced motion e todos os estados no mesmo bloco, não depois. Antes de entregar, cortar o que não serve ao trabalho da tela.
4. **Renderizar e criticar.** Ver o que foi construído (seção Render). Review mental não produz `PASS`.
5. **Cristalizar.** Decisão de marca vai para o DS ou `MEMORY.md` do projeto. Lei nova só com falha e correção concretas.

## Calibração contra default de IA

Defaults, não escolhas. Usar só quando o brief pede:

- Cards idênticos arredondados com a mesma sombra cinza e gradiente decorativo.
- Eyebrow em CAIXA ALTA espaçada acima de todo título; numeração 01/02/03 em conteúdo que não é sequência.
- Uma palavra do título destacada em itálico ou cor.
- Fade-and-slide em toda seção, hover animado em todo card.
- Seta `→` colada em todo link e botão; monoespaçada em todo label pequeno.
- Fundo creme com serifa e acento terracota; near-black com um único acento ácido.

O estilo da casa é ponto de partida, não template: precisa nascer do assunto ou do brief, não do reflexo.

## Texto de interface

Palavra existe para facilitar o uso. Nomear pelo que o usuário entende, não pelo que o sistema é ("notificações", não "webhooks"). Voz ativa: o botão diz o que acontece ("Salvar alterações", não "Enviar") e a mesma ação mantém o nome no fluxo inteiro (botão "Publicar", toast "Publicado"). Erro explica o que houve e como resolver, sem pedir desculpa. Estado vazio é convite à ação.

## Render

Interface que não foi vista não foi revisada. Para app local, [scripts/with_server.py](scripts/with_server.py) sobe o servidor e roda um script Playwright (rodar `--help` primeiro, tratar como caixa-preta):

```bash
python3 scripts/with_server.py --server "npm run dev" --port 3000 -- python3 shot.py
```

No script: registrar `page.on("console")` e `page.on("pageerror")` **antes** do `goto`; conferir o status HTTP da resposta; esperar um estado concreto da UI (`get_by_role(...).wait_for()`, fontes e imagens carregadas), não `networkidle`; screenshot em 1440 e 390 de largura, mais o breakpoint onde o conteúdo realmente quebra, salvos em `.orbit/review/` no repo como evidência do review. Reconhecer antes de agir: screenshot e DOM primeiro, seletores depois. Sem browser disponível: `NOT_VERIFIED`, nunca `PASS`.

## Fechamento

Fechamento do HM Orbit, mais: direção em uma frase, assinatura visual e razão, estados cobertos, viewports realmente vistos, findings separados entre quebra objetiva, acessibilidade e gosto. `product-ready` é do Owner.
