# Playbook · Direção Visual

Carregado sob demanda pelo modo `direction` (e consultado por `build` quando a direção já está aprovada e falta materializar). Profundidade: a tese visual, a barra de referência, os tokens e as regras técnicas de implementação visual.

## 1. Princípio central

Não construir software pro passado. A barra de design não é o que é bonito agora: é o que ainda vai parecer certo em 2030. Igualar o padrão de hoje já é estar atrasado.

Corolário: nunca dizer "clean e moderno". Essa frase não significa nada. Direção visual se declara em decisões concretas: hex, fonte, peso, espaçamento, motion, assinatura.

## 2. A tese visual

A tese vem do profile da casa e do assunto do produto, nesta ordem de autoridade: brief do Owner, profile, assunto. Sem profile, partir de três princípios:

- **Intencional.** Cada elemento tem razão de existir. Restrição de cor: uma paleta sóbria com um acento que significa algo.
- **Editorial.** Tipografia carrega a voz. Hierarquia clara, contraste de escala, ritmo vertical, alinhamento rigoroso.
- **Nascida do assunto.** Material, vocabulário e ofício do mundo do produto, não um template.

Dark ou light, densidade, ousadia: o produto e o público decidem. Se o produto pede os dois modos, os dois são projetados, não um derivado às pressas do outro.

## 3. Barra de referência

Referências são compressão de barra e taste, nunca pedido de cópia. O que cada uma comprime:

| Referência | O que ela ensina |
|---|---|
| Apple | restrição, qualidade material, cada pixel considerado |
| Airbnb | design de experiência, ressonância emocional, storytelling pela interface |
| Linear | densidade com elegância, maestria em dark mode, arquitetura de informação, IA integrada sem fricção |
| Stripe | sofisticação de layout, tipografia editorial, documentação como produto |
| Vercel | whitespace como elemento, precisão tipográfica, minimalismo que comunica |

Regra de comparação: nunca comparar com produtos medianos. Se a interface não impressiona alguém com gosto, reprovou.

## 4. O que a direção precisa cravar

Uma direção pronta declara, no mínimo:

1. **Emoção e registro.** O que usar esse produto deve fazer sentir. Não neutro, não invisível.
2. **Referências e anti-referências.** 2-3 de cada, com o motivo.
3. **Palette de 4-6 tokens nomeados.** Hex exato, papel semântico de cada um.
4. **Type roles.** Display, body e utility: fonte, peso, tracking, escala.
5. **Composição e densidade.** Full-width vs contido, grid, respiração.
6. **Motion com função.** O que anima, por quê, em quanto tempo.
7. **Uma assinatura.** Um elemento que só faz sentido neste produto. Se a direção servir sem alteração a outro produto, ainda não existe identidade.

Teste de diferenciação: trocar o logo. Se a interface poderia ser qualquer coisa, o design reprovou. Identidade não é logo: é como tudo se sente junto.

## 5. Reprovação imediata (e por quê)

Cada item abaixo reprova porque viola um princípio nomeável, não por implicância:

- **Energia de template / UI kit com conteúdo trocado.** Viola diferenciação: o produto não tem identidade própria.
- **Tudo padrão** (fontes do sistema, espaçamento default, cores default). Viola sofisticação: nenhuma decisão foi tomada.
- **Um modo só quando o produto pede os dois.** O segundo modo derivado às pressas quebra contraste e hierarquia.
- **Card grid com borda cinza e botão azul.** O look genérico de SaaS. Viola diferenciação e hierarquia: borda virou muleta de estrutura.
- **Hierarquia visual plana, tudo com o mesmo peso.** Viola o editorial: tipografia não está trabalhando.
- **Estética de painel admin de 2015 / Rails-era UI.** Viola Futuro > Passado.
- **Energia de "a gente faz bonito depois" / hackathon MVP feel.** Viola a barra: craft não é fase 2.
- **Dead avatars** (círculos com iniciais genéricas, fotos stock). Elemento sem razão de existir.
- **Formulário onde um agente deveria estar executando.** Viola Autopilot > Copilot (ver §6).
- **Spinner genérico como loading state.** Viola "todo estado é desenhado". Usar shimmer/skeleton com o shape do conteúdo final.
- **Layout centralizado com barras vazias nas laterais em tela grande.** Viola full-width como padrão (ver §9).
- **Emoji semáforo (🔴🟡🔵) ou pictograma colorido em interface séria.** Quebra o registro em terminal financeiro, dashboard executivo ou qualquer produto com tipografia editorial. Stripe, Linear e Bloomberg nunca usariam. Usar glyphs ASCII (`●` `◆` `▲` `·` `○`) + cor semântica dos tokens.
- **Em TUI: output rico como string plain.** Formatter que gera `╭─ HEADER ╰─` como string e manda como texto perde todas as cores. Se o framework tem componentes próprios (Ink, Bubble Tea), construir componente dedicado pra cada bloco de output rico. String é fallback, não solução.

Decoração sem propósito reprova. Complexidade sem clareza reprova. Se um elemento não tem razão explicável pra existir, não deveria estar na tela.

## 6. Agent-first (quando o produto tem agente)

- UI = visibilidade + override, não input principal.
- A conversa é a interface primária. Formulário é exceção, não regra.
- Antes de aprovar uma tela com formulário, perguntar: "o agente não deveria fazer isso?"
- Dashboard existe pra mostrar o que o agente fez ou está fazendo, não pra o usuário operar.

Produto puramente ferramenta/website sem agente ignora este bloco.

## 7. Tipografia

- Editorial: hierarquia via tipo (tamanho, peso, tracking, cor de texto), não via borda ou fundo de card.
- Headings: letter-spacing negativo (`-0.02em` baseline), weight 600 como partida.
- Corpo: contraste suficiente sem branco puro sobre preto puro.
- Set de fontes definido na direção do produto: um papel de display, um de corpo e, se houver dado denso, um utilitário.
- Texto cortado, truncation não tratada ou orphan feio em heading reprova em review.

## 7b. Peso tipográfico entre motores

Clonando referência web (Chromium, Electron) num app nativo, o mesmo `font-weight` renderiza mais pesado no CoreText do macOS. Não copiar o número: calibrar pelo eixo `wght` da fonte variável, lado a lado com a referência na mesma resolução, até o peso visual bater. Registrar a tabela de equivalência no DS do projeto.

## 8. Tokens

O design system do projeto é a fonte dos tokens: paleta semântica (fundo, superfície, texto, acento, estados), escala tipográfica, espaçamento, raio, elevação e motion. Status semânticos (saudável, atenção, em risco, crítico, bloqueado, concluído) têm cor própria e nunca dependem só da cor para serem lidos. Projeto sem DS nasce com tokens nomeados na direção (seção 12), não com hex espalhado pelo código.

## 9. Layout: full-width e padding simétrico

- **Full-width como padrão.** Não centralizar conteúdo em caixa estreita quando a tela tem espaço. Sem `maxWidth` no main.
- **Padding lateral 24/24 simétrico**, idêntico entre header e content, em todas as telas do app, não só uma:

```tsx
// AppShell: header e main com o MESMO padding lateral
<header style={{ paddingLeft: 24, paddingRight: 24 }}>...</header>
<main style={{ paddingLeft: 24, paddingRight: 24 }}>...</main>
```

Margem desigual entre header e content, ou conteúdo espremido por `maxWidth` inventada, é reprovação direta. Exemplo: um `max-width` sem `margin: 0 auto` enfiado no app shell gera uma borda direita gigante; se o DS não usa max-width, o conteúdo vai direto no container com padding simétrico.

- **Margem de página é token, nunca número na tela.** Laterais, topo, base, largura máxima (quando existe) e altura da faixa de título vivem no DS, e um único contêiner de página os aplica, com ou sem rolagem. Página nova nasce dentro desse contêiner. Porquê: número copiado à mão em cada tela diverge alguns pontos de página para página, e o dono vê no olho antes de qualquer régua. Prova: busca no código não acha padding de página literal fora do contêiner, e a régua mede a primeira linha de texto de toda página na mesma faixa, com tolerância de 1 pt ([review §2](review.md)).

- **Centralizado se ancora no contêiner visual a que pertence, nunca na janela.** Aviso flutuante, estado vazio, spinner ou caixa que fala do conteúdo se centra no painel de conteúdo; só o que pertence à janela inteira se centra nela (o scrim de uma camada por cima cobre a janela, a caixa segue o painel a que responde, ver §11b2). Porquê: com barra lateral ou painel aberto, o centro da janela não é o centro do painel, e o elemento parece deslocado sobre o conteúdo. Prova: na captura, medir o centro do elemento e o centro do contêiner, com diferença de no máximo 1 pt, com a barra lateral aberta e recolhida; conferir no olho não vale.

## 10. Inline styles vs Tailwind (regra técnica: Tailwind v4 com Turbopack)

Tailwind v4 com Turbopack não resolve classes arbitrárias/customizadas confiavelmente (`bg-petrol-bright`, `rounded-card`, `text-text-primary` falharam em produção num SaaS de cliente: design saiu genérico e quebrado). Regra:

- **Todas as propriedades visuais via inline styles** `style={{}}`: `backgroundColor`, `color`, `fontFamily`, `fontSize`, `border`, `borderRadius`, `padding`, `margin`, `letterSpacing`, `textTransform`, `boxShadow`.
- **Valores literais do design system** (`'#09090b'`, `"'Instrument Serif', serif"`), tipicamente importados de um `tokens.ts`. Não depender de CSS variable resolvida por classe Tailwind customizada.
- **Tailwind só pra primitivos de layout** estáveis entre versões: `flex`, `grid`, `min-h-screen`, `items-center`.
- Verificar o build do Next depois de aplicar.

Isto é regra técnica da stack, não estética universal: projeto fora de Tailwind v4/Turbopack pode usar o mecanismo que a stack suportar com confiabilidade provada.

## 11. Motion e estados

- Transições intencionais, 200-300ms. Nunca instantâneo pra mudança de estado importante, nunca lento demais.
- Motion guia, não distrai: entrada de conteúdo, mudança de contexto, confirmação de ação.
- `prefers-reduced-motion` respeitado sempre.
- Todo estado é desenhado, não padrão: loading (shimmer/skeleton com shape do conteúdo), empty (explica + CTA + preview), error (diz como consertar), success. Detalhe de cada estado no playbook `flow.md`.

## 11b. Motion pela frequência de uso

Quanto mais frequente a ação, menos animação:

- Ação repetida dezenas de vezes por dia (atalho, toggle, navegação de lista): sem animação, resposta instantânea.
- Ação ocasional (abrir painel, expandir, confirmar): 150 a 250 ms, mostrando o que mudou.
- Momento raro (primeira carga, conquista, onboarding): onde a orquestração cabe, uma vez.

Saída mais rápida que entrada. Nunca `scale(0)` (partir de ~0.95 com opacidade). Easing que desacelera no fim para entrada. Toda animação respeita `prefers-reduced-motion`. Review de motion no formato Antes · Depois · Por quê.

## 11b2. Camada por cima: scrim e conteúdo separados

Vale para modal, sheet, dialog, popover e drawer.

1. **Scrim e conteúdo são camadas separadas.** O scrim só faz fade (0,2 a 0,25 s, ease-in-out) e cobre a janela ou viewport inteira durante toda a transição. Nunca escala nem desliza: transform no conjunto scrim + caixa encolhe o scrim no meio da animação e expõe as bordas sem escurecer.
2. **O conteúdo entra com mola suave:** escala 0,96 para 1, cerca de 8 px de deslocamento e opacidade. Sai mais rápido e mais simples: cerca de 0,14 s ease-in, opacidade e escala 0,98.
3. **Reduce motion** (`prefers-reduced-motion` ou o ajuste do sistema): só fade.

## 11c. Destino da direção

Direção aprovada vive no repo como `DESIGN.md` (tokens com a razão de cada escolha em prosa) ou no design system existente, nunca só na conversa. Mudança de direção é diff nesse arquivo.

## 12. Formato de entrega da direção

Se a direção passou na barra: uma frase sobre o que funciona e seguir. Se reprovou, cada issue com:

1. **O quê:** elemento ou pattern específico.
2. **Por quê:** qual princípio deste playbook viola.
3. **Como corrigir:** específico e executável. Não "melhorar o contraste": "mudar o background pra `#101013` e subir o font-weight do heading pra 600 com letter-spacing `-0.02em`".

Regras finais:

- Nunca aprovar trabalho mediano.
- Nunca sugerir adicionar quando remover seria melhor.
- Nunca ignorar dark mode.
- O profile da casa é o padrão. Em produto de cliente, o brand context do cliente substitui o taste profile, a barra de craft permanece.
