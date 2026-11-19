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
   Saída obrigatória: matriz feature × referência × nosso × estado (`TEM`, `PARCIAL`, `FALTA`, `MELHOR`, `N/A`) × prioridade × evidência, versionada no repo (`docs/paridade/<referência>.md`). Declarar paridade sem essa matriz é `NOT_VERIFIED`.

1. **Medir antes de construir.** Capturar a referência em 2x e medir posição e tamanho em pt, pesos e cores dos elementos estruturais (barra de título, controles da janela, sidebar, ícones, espaçamentos). Esses números viram a especificação; estimativa de olho erra por 2 pt sem ninguém perceber.
2. **Régua automática.** Um script mede a mesma coisa na referência e na captura do produto e compara com tolerância de no máximo 1 pt. Contraprova obrigatória: referência contra ela mesma passa, versão com defeito plantado falha. Régua sem contraprova não é evidência. Posição de texto se mede pelo centro entre o topo da maiúscula e a linha de base, nunca pela caixa do texto: a caixa muda conforme a linha tem descendentes ou não, e a mesma linha parece mover entre telas.
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
- **Captura sem roubar a máquina.** Em máquina que o dono está usando, a janela de QA só fica em primeiro plano o tempo da captura e fecha logo depois; preferências e estado de QA vivem em domínio separado do app de uso. Janela de QA esquecida na frente rouba o foco e recebe o que o dono digita. Prova: depois da rodada de QA, nenhuma janela de QA aberta e as preferências do app de uso intactas.

O que não foi visto renderizado não recebe veredito: recebe NOT_VERIFIED com o motivo (ferramenta indisponível, estado não reproduzível).

## 4. Como executar

1. **Levantar a referência.** DS, mock, screen do bundle ou direção aprovada. Sem referência nenhuma, o review compara contra a tese visual e a barra (§5), e diz explicitamente que rodou sem referência.
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

Estado que só existe com permissão do sistema ou hardware (gravação ativa, câmera, localização) ganha gancho de QA: a interface aceita o estado injetado por variável de ambiente, alimentado por dados reais produzidos por outro processo. Assim o estado é revisado e capturado sem a permissão, e a prova de "estado forçado e visto" (§6a) vale para ele também.

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

## 6c. App nativo (macOS)

App criado pelo starter de `hm-engineering` (`templates/macos-app`) já traz os ganchos de revisão: `APP_PREVIEW` abre página e estado, `APP_SLOW_MOTION` desacelera toda transição para a prova quadro a quadro, `APP_DEMO_MODAL` abre a camada por cima, e `tools/design_parity.py` é a régua.

Render de app nativo não passa por browser. Receita:

- Capturar a janela real: `screencapture -l <windowid>`, com o id vindo de `CGWindowListCopyWindowInfo` (filtrar pelo nome do processo).
- Duas larguras: a janela padrão e a **janela mínima**, que é o "mobile" do desktop. Nas duas, modo claro e escuro.
- Lado a lado com a referência, na resolução real (sem escala), mesma tela e mesmo estado.
- Conferir que toda descrição de uso do Info.plist tem o entitlement correspondente na assinatura (`codesign -d --entitlements - --xml`). Com hardened runtime, permissão sem entitlement é negada sem janela e sem erro: o botão "Conectar" simplesmente não faz nada. O `hm_gate` faz esse check.
- Conferir o SDK gravado no binário (`otool -l` em `LC_BUILD_VERSION`, `sdk` maior ou igual ao sistema alvo): SDK antigo desenha chrome legado.
- **Tema do app contra tema do sistema.** Controle nativo (menu suspenso, `NSPopUpButton`, checkbox, `Picker` em estilo menu) herda a aparência da **janela**, não o tema que o conteúdo desenha. App com tema próprio claro em sistema escuro (ou o contrário) deixa o controle invisível. Correção: fixar a aparência da janela no tema do app (`preferredColorScheme`/`NSAppearance`) ou usar componente próprio que desenha com os tokens do app. A revisão roda com o **sistema** nos dois modos, para cada tema do app.
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
