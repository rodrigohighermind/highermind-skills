# Playbook · Review Visual

Carregado sob demanda pelo modo `review`. Review avalia o olho; fluxo cognitivo é o `flow.md`.

## 1. Pixel perfect contra a referência

Quando existe Design System ou referência visual, a entrega tem que bater EXATAMENTE: bordas, espaçamentos laterais simétricos, padding, tipografia, cores, raios. Zero desvio.

**Por quê:** imperfeição visual quebra confiança de forma desproporcional: uma borda assimétrica pesa mais que dez features. Repetir esse erro é grave.

**Como aplicar:**

- Com DS ou referência, **copiar o uso exato**: estrutura HTML + classes/estilos como a referência usa. Nunca inventar classe, wrapper, `max-width` ou `margin` que o DS não usa. Exemplo: um `max-width` sem `margin: 0 auto` inventado no app shell gera borda direita gigante quando o DS põe o conteúdo direto no container com padding simétrico.
- **Ler o CSS/HTML real da referência antes de montar o layout.** Não deduzir de memória.
- **Se algo foi adicionado fora do DS, é bug, não escolha.** Reportar como FAIL com o wrapper/classe inventado nomeado.

## 2. Comparação lado a lado é gate de baseline-ready

Antes de qualquer entrega visual ser declarada baseline-ready:

1. Renderizar a entrega e abrir a referência (DS, mock, screen do bundle) lado a lado.
2. Comparar elemento a elemento: padding lateral, alinhamentos, raios, pesos, cores, espaçamento vertical.
3. Screenshot da entrega + apontador pra referência entram como evidência. Review apenas mental não produz PASS; render não visto é NOT_VERIFIED, nunca aprovação.

Sem comparação lado a lado registrada, a entrega visual não está pronta pra passar ao Owner.

## 2b. Régua de paridade (clone ou referência)

Vale desde o primeiro build de qualquer produto que tem referência.

0. **Inventário antes de qualquer captura.** Extrair do próprio artefato da referência o que ele faz, nesta ordem: catálogo de strings e i18n do bundle (agrupado por prefixo, vira o mapa de telas, menus, estados e erros); código, para comportamento ambíguo; dados locais do app, para o comportamento real; só então capturas, incluindo hover, menus "…" e estados escondidos. Em catálogo multilíngue, todos os idiomas vivem no mesmo bundle: ler o objeto do idioma-alvo por uma âncora conhecida, nunca a primeira ocorrência da chave.
   Saída obrigatória: matriz feature × referência × nosso × estado (`TEM`, `PARCIAL`, `FALTA`, `MELHOR`, `N/A`) × prioridade × evidência, versionada no repo (`docs/paridade/<referência>.md`). Declarar paridade sem essa matriz é `NOT_VERIFIED`. A matriz mede comportamento; rótulo e ordem da navegação não se copiam ([flow §4](flow.md)).
   **A matriz é viva e é a única fonte do que falta.** A coluna de estado leva data e evidência e muda no mesmo commit da feature que a altera; progresso de paridade não se registra em prosa noutro arquivo. Porquê: matriz sem estado atualizado é só o inventário da referência, e "o que falta" volta a ser cruzamento manual entre arquivos, sujeito a erro. Prova: a contagem de `FALTA` e `PARCIAL` por prioridade sai da matriz por um comando (`python3 <skill>/scripts/parity_count.py docs/paridade/<referência>.md`, que também reprova linha sem estado), sem abrir outro documento, e o diff de cada feature de paridade toca a linha correspondente. Matriz sem coluna de estado preenchida, ou mais velha que a última feature de paridade, é `NOT_VERIFIED`.

1. **Medir antes de construir.** Capturar a referência em 2x e medir posição e tamanho em pt, pesos e cores dos elementos estruturais (barra de título, controles da janela, sidebar, ícones, espaçamentos). Esses números viram a especificação; estimativa de olho erra por 2 pt sem ninguém perceber.
2. **Régua automática.** Um script mede a mesma coisa na referência e na captura do produto e compara com tolerância de no máximo 1 pt. Contraprova obrigatória: referência contra ela mesma passa, versão com defeito plantado falha. Régua sem contraprova não é evidência. A régua cobre três camadas, não só a tipografia: texto (fonte, peso, tamanho), superfície (borda, raio, sombra, fundo) e chrome do sistema (barra de rolagem, controles da janela). Porquê: régua que só olha texto passa com cartão sem contorno e com a barra de rolagem padrão do sistema, e o dono acha a diferença no olho. Prova: borda medida pixel a pixel na captura em 2x (espessura e cor do contorno contra o fundo) nos dois produtos, e a contraprova falha com um cartão sem contorno plantado. Posição de texto se mede pelo centro entre o topo da maiúscula e a linha de base, nunca pela caixa do texto: a caixa muda conforme a linha tem descendentes ou não, e a mesma linha parece mover entre telas.
3. **Depois da régua, o olho.** Lado a lado na mesma escala. A régua não vê forma de glifo nem cor: ícone preenchido contra contorno, controle cinza contra branco, botão ausente.
4. **Estados e tamanhos obrigatórios:** janela padrão e mínima, painéis recolhidos e abertos, claro e escuro. Painel recolhido costuma revelar conteúdo encostado na borda.
5. **Configuração de build é design.** O sistema desenha o chrome conforme o SDK gravado no binário: app macOS linkado contra SDK antigo ganha controles de janela e materiais legados no sistema novo. Check: `otool -l <binário> | grep -A5 LC_BUILD_VERSION`, com `sdk` maior ou igual à versão do sistema alvo. O `hm_gate` faz esse check sozinho: acha os `.app` do repo ou lê `macos_apps` no `hm-quality.json`, e reprova SDK anterior ao sistema.

Defeito apontado pelo dono do produto entra aqui como checagem nova da régua ou do checklist, no mesmo trabalho da correção.

## 3. Screenshots como evidência

Finding visual sem screenshot é hipótese. Disciplina de captura:

- **Capturar o que vai ser julgado.** Viewport desktop (>= 1440px de largura útil) e mobile (375-430px). Estado real, com conteúdo real ou representativo, nunca lorem ipsum em review final.
- **Um screenshot por finding material.** O finding aponta o elemento na imagem (região, componente, rota). "O padding tá estranho" sem imagem não entra no report.
- **Par entrega × referência quando existe referência.** Os dois screenshots lado a lado, mesmo viewport, mesma tela. A diferença apontada é o finding.
- **Estados capturados, não descritos.** Loading, empty e error são screenshots próprios; forçar o estado (rede lenta, dado zerado, erro provocado) faz parte do review.
- **Console junto.** Print ou log do console do fluxo revisado. console.error novo é FAIL objetivo.
- **Captura sem roubar a máquina.** Bateria visual de app desktop roda sem tomar foco nem exigir tela livre: um modo de QA abre a janela atrás das outras, sem ativar o app, e a captura é feita pelo id da janela, que funciona com ela encoberta (receita em §6c). Onde isso não for possível, a janela de QA só fica em primeiro plano o tempo da captura e fecha logo depois. Preferências e estado de QA vivem em domínio separado do app de uso. Porquê: QA que toma o foco recebe o que o dono digita e acaba adiado para quando a máquina está livre, ou vira `NOT_VERIFIED`. Prova: o app em primeiro plano é o mesmo antes, durante e depois da bateria; ao final, nenhuma janela de QA aberta e as preferências do app de uso intactas.
- **Input sintético só com a sessão desbloqueada.** Todo roteiro de QA que envia clique, arraste ou tecla sintética confere antes de cada bloco de interação se a tela está bloqueada (no macOS, `CGSSessionScreenIsLocked` em `CGSessionCopyCurrentDictionary()`). Bloqueada: a interação é `NOT_VERIFIED` com o motivo, e o roteiro segue só com o que não depende de input. Porquê: com a tela bloqueada os eventos vão para a tela de bloqueio, mas a captura por janela continua devolvendo imagem, então o roteiro termina sem erro e conclui sobre uma interação que nunca aconteceu. Prova: rodar o roteiro com a tela bloqueada e ver o relatório marcar as interações como `NOT_VERIFIED`, nunca PASS nem FAIL.

O que não foi visto renderizado não recebe veredito: recebe NOT_VERIFIED com o motivo (ferramenta indisponível, estado não reproduzível).

## 4. Como executar

1. **Levantar a referência.** DS, mock, screen do bundle ou direção aprovada. Sem referência nenhuma, o review compara contra a tese visual e a barra (§5), e diz explicitamente que rodou sem referência. Tela de tipo novo no produto (conversa, lista, detalhe, painel, formulário, ajustes) entra com a referência daquele tipo e o inventário marcado ([direção §3c](direction.md)); sem eles, `NOT_VERIFIED`.
2. **Rodar o produto de verdade.** Build local, rota real, dados reais/representativos. Review de código-fonte sem render não é review visual.
3. **Percorrer a ação primária inteira** capturando os viewports e estados da cobertura mínima (§6).
4. **Comparar lado a lado** (§2) e varrer o checklist de reprovação (§8).
5. **Testar teclado, foco, contraste e reduced motion** no fluxo principal.
6. **Escrever o veredito** separando quebra objetiva de taste (§9).

## 5. Barra de comparação

Comparar com os melhores, nunca com a média: Apple (restrição, cada pixel considerado), Linear (densidade elegante, dark mode), Stripe (layout e tipografia editorial), Vercel (whitespace e precisão). A pergunta do review não é "está bonito?": é "isso envergonharia alguém desses times?".

## 6. Cobertura mínima do review

Proporcional ao trabalho, mas o baseline é:

- viewport desktop e mobile;
- ação primária completa, do início ao fim;
- estados loading, empty, error e success relevantes;
- teclado e foco visível;
- contraste e `prefers-reduced-motion`;
- console sem erro;
- comparação com a tese visual aprovada (direção) e com a referência (pixel perfect).

## 6a. Acabamento: a classe de defeito

A barra é um app nativo da Apple: se a Apple não deixaria passar, reprova. Os defeitos abaixo são uma classe; cada um é FAIL e cada um tem a sua prova.

| Defeito | Prova |
|---|---|
| Transição seca ou com emenda | gravação ou burst de screenshots durante a animação, quadros intermediários conferidos |
| Camada por cima mal composta: scrim parcial, escalando ou piscando | idem, com o scrim cobrindo a janela inteira em todos os quadros ([direção §11b2](direction.md)) |
| Salto de layout ou de texto ao carregar ou trocar estado | quadros antes, durante e depois da troca, mesma posição dos elementos estáveis |
| Flicker | burst durante carga, troca de rota e revalidação |
| Animação sem curva ou longa demais | duração e curva lidas no código e conferidas nos quadros ([direção §11b](direction.md)) |
| Estado sem desenho: vazio, carregando, erro, sucesso | cada estado forçado (fixture, rede bloqueada, mock) e visto em screenshot |
| Foco ou hover inconsistente | navegação por teclado e hover em todos os elementos interativos do fluxo |
| Elemento cortado ou desalinhado | janela mínima, padrão e larga, claro e escuro |

Sem a prova da linha, o item é `NOT_VERIFIED`, nunca PASS. Screenshot parado só prova estado parado.

**Achou um, procure os irmãos.** Defeito da classe encontrado num lugar é hipótese de que o mesmo mecanismo existe em outros: varrer o produto inteiro pelo mecanismo (a mesma transição, o mesmo componente, o mesmo padrão de carga) e corrigir na fonte compartilhada. Reportar só o caso pedido é corrigir o caso, não a causa.

## 6a2. Estado que exige permissão ou hardware

Estado que só existe com permissão do sistema ou hardware (gravação ativa, câmera, localização) ganha gancho de QA: a interface aceita o estado injetado por variável de ambiente, alimentado por dados reais produzidos por outro processo. Assim o estado é revisado e capturado sem a permissão, e a prova de "estado forçado e visto" (§6a) vale para ele também. Gancho de QA que depende de dado assíncrono dispara na chegada do dado, nunca por espera fixa: espera fixa captura tela vazia na máquina lenta e desperdiça tempo na rápida.

Proteção que impede a própria captura (janela excluída de compartilhamento de tela) fica desligada só no bundle de QA, por opção explícita, e ligada em todo o resto. A captura falhar no bundle normal é o teste de que a proteção vale.

## 6a3. Honestidade do dado

Para cada campo exibido, perguntar: **de onde vem isso e qual a certeza?** Em produto onde o dado decide algo (saúde, dinheiro, prazo), dado errado na tela é pior que tela feia.

- **Desconhecido não vira default.** Hora, valor ou nome que o sistema não sabe tem estado próprio no modelo (`time_known=false`, `estimated=true`, `null` com motivo) e aparência própria na interface (só o dia, traço, "estimado", "não informado"). Metadado de arquivo (hora de criação, de exportação) não é a hora do evento.
- **Progresso diz a verdade.** Esperando, trabalhando (com porcentagem ou tempo real restante) e pronto são estados distintos. Spinner em item que está só na fila é mentira.
- **Ação sem objeto fica desabilitada.** Copiar, exportar ou enviar sem conteúdo não aparece ativo.
- **Revisar com dado real e volume real.** O defeito aparece com a fila cheia, a lista longa e o dado importado, não com um item de exemplo.

## 6b. Acessibilidade que costuma escapar (WCAG 2.2)

Além de contraste, foco visível e teclado:

- **Foco não encoberto (2.4.11):** header fixo, toast ou cookie bar não cobrem o elemento focado.
- **Alvo mínimo (2.5.8):** área clicável de pelo menos 24×24 px, ou espaçamento equivalente.
- **Alternativa a arrastar (2.5.7):** toda ação de drag tem caminho por clique.
- **Entrada redundante (3.3.7):** não pedir de novo o que o usuário já informou no fluxo.
- **Autenticação acessível (3.3.8):** sem teste cognitivo; colar senha e gerenciador de senha funcionam.
- **Ajuda consistente (3.2.6):** suporte e ajuda no mesmo lugar em todas as telas.
- **Status anunciado:** mudança de estado relevante (salvo, erro, contador) chega ao leitor de tela via `aria-live`.
- **Controle só de ícone tem nome explícito (4.1.2):** botão ou menu sem texto visível recebe nome acessível no idioma do produto (`aria-label` na web, `accessibilityLabel` em SwiftUI). Tooltip não é nome: em app nativo de desktop, `.help` só desenha a dica, e o leitor de tela anuncia o identificador do símbolo, em inglês e sem sentido para o usuário. O mecanismo é um modificador único que aplica dica e nome juntos, usado nos componentes reaproveitados, para que o caso novo já nasça nomeado. Prova: varredura estática no gate do projeto, que delimita cada controle até o seu estilo e falha em ícone sem nome. Revisão manual não segura essa classe, porque o defeito é invisível no render.

## 6c. App nativo (macOS)

App criado pelo starter de `hm-engineering` (`templates/macos-app`) já traz os ganchos de revisão: `APP_PREVIEW` abre página e estado, `APP_SLOW_MOTION` desacelera toda transição para a prova quadro a quadro, `APP_DEMO_MODAL` abre a camada por cima, e `tools/design_parity.py` é a régua.

Render de app nativo não passa por browser. Receita:

- Capturar a janela real: `screencapture -l <windowid>`, com o id vindo de `CGWindowListCopyWindowInfo` (filtrar pelo nome do processo). Listar com `.optionAll`, não só as janelas visíveis na tela: a captura por id funciona com a janela atrás de outras. O modo de QA em segundo plano usa `orderBack` no lugar de `makeKeyAndOrderFront` e não chama `NSApp.activate`.
- **Janela certa e imagem conferida.** Processo pode ter mais de uma janela na camada normal (auxiliar, overlay, janela de serviço), e a primeira da lista não é a principal. Escolher pelo título ou pela maior área em `kCGWindowBounds`, nunca pela ordem. Antes de usar a captura como prova, reprovar imagem uniforme (toda branca, toda preta, um pixel só de cor). Porquê: captura da janela errada sai sem erro e vira prova falsa de tela vazia ou de tela aprovada. Prova: a captura tem variância de pixel acima do fundo liso e mostra o conteúdo esperado da tela pedida.
- **Agente nunca captura a tela inteira.** Toda captura feita por agente leva `-l <id da janela do próprio app>`, com caminho absoluto (`/usr/sbin/screencapture -x -o -l <id>`: sem som, sem sombra). Porquê: `screencapture` sem `-l` grava a tela de quem está usando a máquina, com o que estiver aberto nela, e esse arquivo vai parar no relatório. Alerta e sheet seguem a mesma regra: hospedar a view do alerta numa janela própria do app aberta com `orderBack` e capturar o id dessa janela. Prova: varredura no gate do projeto que reprova chamada de `screencapture` sem `-l`, e a captura do alerta mostra o texto que o render offscreen não desenha.
- **Captura sem permissão de gravação de tela.** Agente disparado em segundo plano (CLI chamada por outro app, launchd) não herda a permissão de gravação de tela e pode nem achar `screencapture` no `PATH`; a captura da janela falha. Caminho alternativo: render offscreen da view dentro de um teste ou gancho de QA (`NSHostingView` com `cacheDisplay(in:to:)` em AppKit, `ImageRenderer` em SwiftUI), que não passa pela permissão. Porquê: a revisão não pode depender de um consentimento que o processo do agente não tem. Limite declarado: render offscreen não mostra o que o sistema desenha fora da view (alerta, menu aberto, popover, chrome da janela, vibrancy); esses estados ficam `NOT_VERIFIED` no relatório, nunca `PASS` por omissão. Prova: a mesma tela capturada pelos dois caminhos bate na régua de paridade, e o relatório lista os estados que só a captura real cobre.
- **Artefato do método antes de defeito do componente.** Render offscreen pode desenhar o que a tela real não mostra: risco fino nas pontas de contorno arredondado (cápsula com borda interna), serrilhado em curva, linha de meio pixel. Antes de reprovar um contorno visto só nesse caminho, renderizar a forma sozinha, fora do componente, pelo mesmo método. Porquê: reprovar artefato de captura manda corrigir um componente que está certo e esconde o limite do método. Prova: a forma isolada reproduz o risco (é do método: item `NOT_VERIFIED` para aquele detalhe, conferido depois na captura real) ou não reproduz (é do componente: reprova).
- Duas larguras: a janela padrão e a **janela mínima**, que é o "mobile" do desktop. Nas duas, modo claro e escuro. Produto com janela redimensionável acrescenta uma captura **larga**: defeito de alinhamento de container flexível só aparece quando sobra espaço.
- **Frame flexível declara alinhamento.** Coluna ou bloco que se estica (`.frame(maxWidth: .infinity)` e equivalentes) declara o alinhamento do conteúdo, por exemplo `alignment: .topLeading`. Porquê: sem ele o conteúdo é centrado no espaço que sobra, e o alinhamento do container pai não corrige; o topo de colunas vizinhas desencontra só em janela larga, fora do tamanho em que a bateria de telas captura. Prova: régua que mede a mesma borda (topo de colunas vizinhas) em pelo menos dois tamanhos de janela, com a diferença dentro da tolerância em ambos.
- Lado a lado com a referência, na resolução real (sem escala), mesma tela e mesmo estado.
- Conferir que toda descrição de uso do Info.plist tem o entitlement correspondente na assinatura (`codesign -d --entitlements - --xml`). Com hardened runtime, permissão sem entitlement é negada sem janela e sem erro: o botão "Conectar" simplesmente não faz nada. O `hm_gate` faz esse check.
- Conferir o SDK gravado no binário (`otool -l` em `LC_BUILD_VERSION`, `sdk` maior ou igual ao sistema alvo): SDK antigo desenha chrome legado.
- **Tema do app contra tema do sistema.** Controle nativo (menu suspenso, `NSPopUpButton`, checkbox, `Picker` em estilo menu) herda a aparência da **janela**, não o tema que o conteúdo desenha. App com tema próprio claro em sistema escuro (ou o contrário) deixa o controle invisível. Correção: fixar a aparência da janela no tema do app (`preferredColorScheme`/`NSAppearance`) ou usar componente próprio que desenha com os tokens do app. A revisão roda com o **sistema** nos dois modos, para cada tema do app.
- **Barra de título própria mantém os gestos do sistema.** Com barra transparente e conteúdo por baixo, a camada de interface consome o duplo clique que o sistema usa na barra. O controlador da janela devolve o gesto: duplo clique na faixa da barra, fora dos controles da janela e dos botões do app, segue a preferência do usuário no sistema (`AppleActionOnDoubleClick`: ampliar, minimizar ou nada). Ampliar vai explícito para a área visível da tela e guarda o frame anterior para voltar, porque o zoom padrão não restaura quando o frame salvo não bate com o padrão. Porquê: gesto de sistema que some lê como app quebrado, e nenhuma captura parada mostra. Prova: teste da decisão (ponto do clique e preferência dão a ação certa) mais a interação real nas três preferências, com ida e volta do frame. Só compilar ou só capturar deixa o item `NOT_VERIFIED`. Agente que não opera o mouse prova assim: a faixa livre é função pura do ponto e do tamanho da janela, com teste unitário (nunca sobre controle da janela nem sobre botão do app), e um gancho de prova por variável de ambiente posta cliques duplos reais na fila de eventos do próprio app e imprime o frame antes, ampliado e restaurado, sem mover o ponteiro de quem está usando a máquina.
- **App com janela tem menu principal com Editar padrão.** Todo app de política regular (ícone no Dock, janela própria) monta o menu principal com o menu do app, Editar e Janela. Editar traz os itens padrão (`undo:`, `redo:`, `cut:`, `copy:`, `paste:`, `selectAll:`) com alvo nulo, para a ação descer pela cadeia de respondedores até o campo em foco. Porquê: os atalhos de desfazer, recortar, copiar, colar e selecionar tudo não são do campo de texto, chegam pelo menu; app montado à mão sem menu principal perde todos, em todo campo, e nenhuma captura parada mostra. Vale também para shell web de desktop que substitui o menu padrão. Prova: smoke que lê a barra de menus do app pela API de acessibilidade (`kAXMenuBarAttribute`) e confere que existe item com a tecla V e modificador só Comando, mais colar de verdade num campo. Só compilar deixa o item `NOT_VERIFIED`.
- **Formatação por locale explícito.** Todo formatter de data, número e moeda exibido leva o locale do produto (ou formato numérico fixo). Formatter sem locale segue o do processo e solta mês em inglês num app em português. A varredura procura formatter criado sem locale.
- **Alinhar ao texto, não à decoração.** Controle ao lado de rótulo (botão junto a abas, ícone junto a título) alinha pelo texto do rótulo, nunca pelo bloco que inclui sublinhado, indicador ou padding de seleção: o deslocamento a compensar é a soma do gap e da decoração. Alinhar ao bloco faz o controle encostar na linha ou flutuar fora do eixo do texto. Prova: captura em 2x com a linha de base do texto e o centro do controle medidos na mesma régua. Estilo nativo de menu ou botão pode descartar o fundo do rótulo customizado; conferir no render, não no código.
- Conferir que o `minSize` declarado é o tamanho que o conteúdo realmente aceita: abaixo dele nada corta, nada sobrepõe, nada some.

## 7. Os sete eixos de avaliação

1. **Sofisticação.** Todo elemento tem razão explicável pra existir. Decoração sem propósito reprova; complexidade sem clareza reprova.
2. **Diferenciação.** Trocando o logo, a interface ainda só poderia ser deste produto? Se poderia ser qualquer coisa, reprovou.
3. **Experiência.** Usar o software parece alguma coisa. Todo estado é desenhado, não default: transições, micro-interações, loading, empty, error.
4. **Encantamento.** As pequenas coisas: hover que parece exatamente certo, transição que guia, tipografia que respira, cor que significa.
5. **Usabilidade.** O usuário nunca fica na dúvida do que fazer. Hierarquia clara, ação primária óbvia, interface que se ensina sozinha.
6. **Beleza.** Comparada aos melhores produtos, não aos comuns. Tipografia com intenção, whitespace generoso, cor com restrição.
7. **Pixel perfect.** Nenhum pixel fora do lugar. 1px de desalinhamento entre elementos que deveriam alinhar reprova. Texto cortado reprova. Componente quebrando em qualquer viewport reprova. Nunca shipar quebrado.

## 8. Checklist de reprovação imediata

Qualquer item presente = FAIL direto, com localizador:

- [ ] energia de template / UI kit com conteúdo trocado
- [ ] tudo padrão: fonte do sistema, espaçamento default, cor default
- [ ] somente light mode
- [ ] card grid com borda cinza e botão azul (SaaS genérico)
- [ ] hierarquia visual plana, tudo com o mesmo peso
- [ ] estética admin 2015 / Rails-era
- [ ] energia "a gente faz bonito depois" / hackathon MVP
- [ ] dead avatars
- [ ] formulário onde um agente deveria executar (produto agent-first)
- [ ] link, botão, aba, item de menu ou linha clicável sem cursor de mão. Na web o navegador só dá a mão ao link, e o reset do Tailwind 4 tira do botão: a regra global `cursor: pointer` é obrigatória. No app nativo, aplicar no estilo base, nunca item a item. O `hm_gate` reprova (check "cursor de clique"); projeto que siga a seta da plataforma declara `"pointer_cursor": false` no `hm-quality.json`
- [ ] spinner genérico como loading state
- [ ] layout centralizado com laterais vazias em tela grande / maxWidth inventada
- [ ] padding lateral assimétrico entre header e content (o padding lateral do DS)
- [ ] emoji semáforo ou pictograma colorido em interface séria (usar `●` `◆` `▲` `·` `○` + cor semântica)
- [ ] em TUI: bloco rico renderizado como string plain quando o framework tem componentes (Ink, Bubble Tea)
- [ ] wrapper/classe/margin fora do DS quando existe referência
- [ ] console.error durante o fluxo revisado
- [ ] qualquer defeito da classe de acabamento (§6a)
- [ ] campo que afirma mais do que o dado sabe: default plausível no lugar de desconhecido, progresso falso, ação ativa sem objeto (§6a3)
- [ ] movimento ou estado aprovado sem a prova da linha correspondente em §6a
- [ ] texto corrido maior que o título da página, ou parágrafo longo dentro de cartão com borda ([direção §7](direction.md))
- [ ] resposta de agente sem ação de copiar ou sem histórico persistente ([direção §6](direction.md))
- [ ] palavra abreviada onde cabe por extenso (dia, mês, unidade de tempo)
- [ ] conteúdo estruturado todo em tinta e cinza, sem cor por categoria do domínio, ou cor de categoria sem ícone e nome ([direção §8](direction.md))
- [ ] conteúdo que vai para produto de terceiros com estrutura ou vocabulário diferentes dos do destino ([direção §3c](direction.md))

Estas rejeições são profile da casa, não lei universal: em trabalho pra outra marca, o brand context do cliente substitui o taste, a barra de craft e o pixel perfect 1 permanecem.

## 9. Formato do veredito

**Passou:** "Atende a barra." Uma frase sobre o que funciona. Seguir em frente. Sem elogio cerimonial.

**Reprovou:** pra cada issue:

1. **O quê:** elemento ou pattern específico, com localizador (screenshot, viewport, rota, componente).
2. **Por quê:** qual princípio ou item do checklist viola. Separar quebra objetiva (medível: 1px, cor errada, overflow) de taste (julgamento, recomendado).
3. **Como corrigir:** exato, executável. Não "melhorar o espaçamento": "mudar o background pra `#101013`, subir o font-weight do heading pra 600 com letter-spacing `-0.02em`, igualar paddingLeft/Right em 24".

## 10. Regras

- Nunca dizer "clean e moderno". Não significa nada.
- Nunca aprovar trabalho mediano. Se não impressiona alguém com gosto, reprovou.
- Nunca sugerir adicionar quando remover seria melhor.
- Nunca ignorar dark mode.
- Comparar com os melhores, nunca com a média.
- O profile da casa é o padrão. Se um pixel está fora do lugar, reprova, sem tolerância.
- Formulário que um agente deveria resolver é desalinhamento arquitetural: apontar, não só estilizar.
- Review declara no máximo baseline visual; product-ready é do Owner.
