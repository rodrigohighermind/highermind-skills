---
name: hm-design
description: Use em qualquer trabalho de interface ou experiência, mesmo quando o pedido não diz "design" - criar ou refazer tela, página, landing, dashboard, componente, TUI, fluxo, onboarding, navegação, design system, tokens, tipografia, cor, layout, responsividade, motion, estados de loading, empty e error, texto de interface, acessibilidade, e revisar ou aprovar uma tela implementada. Aplica mesmo quando a tela vem colada como código ou o ajuste parece pequeno.
---

# HM Design

Transformar a tese do produto em experiência compreensível, distinta e implementada. Gosto sem artefato é opinião; screenshot sem fluxo é superfície.

## Contrato

**Lei de ferro: nenhum veredito sobre tela sem vê-la.** Antes de aprovar, reprovar ou dizer que está bom: renderizar (seção Render), salvar os screenshots em `.orbit/review/`, ler console e erros da página. Sem isso, o veredito é `NOT_VERIFIED`, por mais óbvio que o código pareça.

**Lei de acabamento: a barra é um app nativo da Apple.** Se a Apple não deixaria passar, reprova. Defeito de acabamento é uma classe, não um caso: transição seca ou com emenda, camada por cima mal composta, salto de layout, flicker, animação sem curva ou longa demais, estado sem desenho, foco ou hover inconsistente, elemento cortado ou desalinhado em qualquer tamanho. Movimento se prova quadro a quadro e estado se prova forçado e visto; sem isso, `NOT_VERIFIED`. Achou um defeito da classe: varrer o produto inteiro atrás dos irmãos dele antes de corrigir só o reportado.

**Lei de processo: defeito que o dono do produto acha é falha do processo.** Corrigir e, no mesmo trabalho, adicionar a checagem que o teria pegado. Clone ou referência se mede antes de construir (geometria em pt, peso, cor, a partir de captura em 2x) e se prova com régua de paridade automática e depois lado a lado no olho ([review §2b](playbooks/review.md)). Número de olho não existe. Feature de paridade atualiza o estado da linha dela na matriz no mesmo commit: a matriz responde sozinha o que falta.

**Lei da honestidade: a interface nunca afirma mais do que o dado sabe.** Valor estimado ou desconhecido tem estado próprio no modelo e aparência própria na tela, nunca um default plausível; progresso distingue esperando, trabalhando (com quanto falta) e pronto. Revisar com dado e volume reais ([review §6a3](playbooks/review.md)).

1. Se o HM Orbit não está no contexto, ler [references/orbit.md](references/orbit.md).
2. Ler o profile da casa em [references/profile.md](references/profile.md). Brief do Owner vence o profile; profile vence default de IA.
3. Ler o real antes de propor: rotas, componentes, tokens, screenshots e o design system existente. Com DS ou referência na mão, copiar o uso exato, nunca inventar wrapper. App de uma família com pacote de design importa o pacote; tipo, peso, paleta ou menu copiado para dentro do app é defeito ([direction §7](playbooks/direction.md)).
3b. **Reler o que o dono já definiu** sobre aquele conteúdo e o destino dele (brief, spec, `MEMORY.md` do projeto, conversa). Requisito dito uma vez vale para todas as telas seguintes e vai para o `MEMORY.md` no momento em que foi dito. Conteúdo que será enviado a produto de terceiros segue a estrutura e o vocabulário daquele produto ([direction §3c](playbooks/direction.md)).
4. **Tela de tipo novo no produto** (conversa, lista, detalhe, painel, formulário, ajustes): antes de construir, abrir em captura real o melhor exemplo daquele tipo e escrever o inventário (hierarquia tipográfica, ações por item, estados, o que persiste). Vale a cada tipo novo, não só na direção: a identidade aprovada não diz o que cada tipo de tela precisa ter ([direction §3c](playbooks/direction.md)). Se um produto da casa já tem aquele tipo aprovado pelo dono, ele é a referência e o ponto de partida é a medida do código dele ([direction §3d](playbooks/direction.md)). Tipo com padrão escrito (ajustes, conversa com agente) segue o padrão; não inventar variação.
4b. **Dado mostrado em mais de um lugar** (duração, estado, contagem, último passo) sai de uma função e de um mapa de rótulos únicos, contando da mesma origem; nenhuma tela recalcula. Teste de paridade pela via de cada tela que mostra o dado (levantadas por busca no código, não só as que o revisor citou) e captura com cada estado fabricado, nunca só o dado do momento ([review §6a3](playbooks/review.md)).
5. Buscar em [references/incidents.md](references/incidents.md) por mídia, fluxo e falha.
6. Carregar o playbook do modo ativo, e só ele.

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

**Palavra por extenso, e a regra vira régua.** Dia, mês, unidade de tempo e termo comum saem inteiros; só unidade e sigla consagradas ficam curtas. Falta de espaço se resolve no layout (tirar a informação que o cabeçalho já dá, quebrar a linha, outra densidade), nunca cortando a palavra. Toda regra de texto do produto vira varredura estática no gate do projeto, cobrindo todas as fontes de texto e não só as strings da tela: padrão de formatador de data e número, lista escrita à mão, unidade dentro de frase e o prompt do LLM, cujo exemplo o modelo reproduz no texto gerado (playbook `llm` de `hm-engineering`, §4). Citação intencional leva marcador explícito de exceção. Porquê: regra de texto conferida só no olho volta pela fonte que ninguém leu. Prova: a varredura falha com um caso plantado de cada fonte e passa no repo limpo.

**Texto inteiro, nunca cortado, e a regra também vira régua.** Nenhum texto de interface termina em reticência por falta de espaço: sem limite de linhas fixo sem faixa, sem modo de truncamento, sem prefixo do texto com `…` anexado no código. Falta de espaço vira mostrar menos itens inteiros e o resto ao abrir, ou quebrar a linha. A varredura estática do gate reprova os três padrões, com marcador explícito de exceção na linha. Porquê: "texto cortado reprova" conferido só no review deixa o corte voltar pelo código que ninguém renderizou com dado real ([review §8](playbooks/review.md)). Prova: um caso plantado de cada padrão faz a varredura falhar, e o repo limpo passa.

**Valor interno nunca entra cru numa frase.** Estado, enum ou identificador que compõe texto de interface passa por um único mapa de rótulos legíveis, escrito para caber na frase que o recebe (concordância, preposição, tempo verbal); nenhuma tela interpola o valor do código. Porquê: o nome técnico do estado e a palavra que o usuário lê são coisas diferentes, e a junção solta produz frase quebrada ("em construindo"). Prova: um teste percorre todos os casos do enum, gera a frase de cada um e confere o texto final, e falha quando um caso novo entra sem rótulo.

**Texto montado por código se prova com os casos reais, e trecho nunca termina pela metade.** Data relativa ("hoje", "ontem", dia por extenso), trecho de resumo, contagem com plural e qualquer frase que o código compõe levam teste com os casos reais: virada do dia, fuso, dado vazio, texto longo e o formato que o dado de verdade tem. Trecho exibido termina em fim de frase ou palavra inteira, nunca em dois-pontos, vírgula ou frase incompleta; corte que não acha fim de frase mostra a frase inteira ou nada. Depois de corrigir um defeito apontado, reler o texto inteiro da tela com os dados reais, não só a linha devolvida ([review §2b](playbooks/review.md)). Porquê: o texto composto só aparece com o dado real, e quem conserta só o apontado deixa o vizinho quebrado na mesma tela. Prova: o teste gera cada caso e confere o texto final, e um trecho plantado terminando em dois-pontos falha.

## Render

Interface que não foi vista não foi revisada. Para app local, [scripts/with_server.py](scripts/with_server.py) sobe o servidor e roda um script Playwright (rodar `--help` primeiro, tratar como caixa-preta):

```bash
python3 scripts/with_server.py --server "npm run dev" --port 3000 -- python3 shot.py
```

No script: registrar `page.on("console")` e `page.on("pageerror")` **antes** do `goto`; conferir o status HTTP da resposta; esperar um estado concreto da UI (`get_by_role(...).wait_for()`, fontes e imagens carregadas), não `networkidle`; screenshot em 1440 e 390 de largura, mais o breakpoint onde o conteúdo realmente quebra, salvos em `.orbit/review/` no repo como evidência do review. Reconhecer antes de agir: screenshot e DOM primeiro, seletores depois. Sem browser disponível: `NOT_VERIFIED`, nunca `PASS`.

App nativo macOS: captura por id da janela do próprio processo (`-l`, nunca a tela inteira) antes do render offscreen; janela escolhida pelo PID, visível e de maior área, nunca a primeira da lista; imagem uniforme não vale como prova; o que o sistema desenha por cima da view (barra de rolagem, cursor, destaque de arrastar, menu, alerta) só conta visto na captura da janela real de um pacote `.app` de QA com bundle id próprio (binário solto sai em branco; offscreen só para layout estático), e item de review nunca volta ao Owner como "fica para você conferir" ([review §6c](playbooks/review.md)).

## Fechamento

Fechamento do HM Orbit, mais: direção em uma frase, assinatura visual e razão, estados cobertos, viewports realmente vistos, findings separados entre quebra objetiva, acessibilidade e gosto. `product-ready` é do Owner.
