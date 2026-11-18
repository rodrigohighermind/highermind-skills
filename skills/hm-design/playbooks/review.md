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

## 3. Screenshots como evidência

Finding visual sem screenshot é hipótese. Disciplina de captura:

- **Capturar o que vai ser julgado.** Viewport desktop (>= 1440px de largura útil) e mobile (375-430px). Estado real, com conteúdo real ou representativo, nunca lorem ipsum em review final.
- **Um screenshot por finding material.** O finding aponta o elemento na imagem (região, componente, rota). "O padding tá estranho" sem imagem não entra no report.
- **Par entrega × referência quando existe referência.** Os dois screenshots lado a lado, mesmo viewport, mesma tela. A diferença apontada é o finding.
- **Estados capturados, não descritos.** Loading, empty e error são screenshots próprios; forçar o estado (rede lenta, dado zerado, erro provocado) faz parte do review.
- **Console junto.** Print ou log do console do fluxo revisado. console.error novo é FAIL objetivo.

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

## 6b. Acessibilidade que costuma escapar (WCAG 2.2)

Além de contraste, foco visível e teclado:

- **Foco não encoberto (2.4.11):** header fixo, toast ou cookie bar não cobrem o elemento focado.
- **Alvo mínimo (2.5.8):** área clicável de pelo menos 24×24 px, ou espaçamento equivalente.
- **Alternativa a arrastar (2.5.7):** toda ação de drag tem caminho por clique.
- **Entrada redundante (3.3.7):** não pedir de novo o que o usuário já informou no fluxo.
- **Autenticação acessível (3.3.8):** sem teste cognitivo; colar senha e gerenciador de senha funcionam.
- **Ajuda consistente (3.2.6):** suporte e ajuda no mesmo lugar em todas as telas.
- **Status anunciado:** mudança de estado relevante (salvo, erro, contador) chega ao leitor de tela via `aria-live`.

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
