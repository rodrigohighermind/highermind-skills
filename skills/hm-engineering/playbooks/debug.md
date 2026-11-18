# Playbook · debug

Bug, teste falhando, build quebrado, comportamento inesperado, lentidão súbita, custo que explodiu.

## Lei

**Nenhum fix definitivo sem causa raiz.** Fix de sintoma é falha adiada. Vale principalmente sob pressão: urgência torna o chute tentador e o chute torna tudo mais lento.

**Contenção é permitida e não é fix.** Produção quebrada: rollback, feature flag ou desligar o job primeiro, de forma reversível e declarada como mitigação. A causa raiz continua obrigatória para fechar.

Pedido de diagnóstico autoriza investigação, não correção.

## Fase 1 · Reproduzir e ler

1. Ler a mensagem de erro inteira: stack trace, linha, código de erro. Ela costuma conter a resposta.
2. Reproduzir de forma confiável. Passos exatos, frequência. Não reproduz: coletar mais dado, não chutar.
3. O que mudou? `git log`, `git diff`, dependência nova, config, ambiente, dado de entrada.

## Fase 2 · Localizar

**Sistema com várias camadas** (CI → build → assinatura, API → serviço → banco, UI → estado → rede): antes de propor qualquer fix, instrumentar cada fronteira com o que entra e o que sai. Rodar uma vez. A evidência diz em qual camada quebra; investigar só aquela.

**Erro fundo na pilha:** rastrear para trás. De onde vem o valor ruim? Quem chamou com ele? Subir até a origem e corrigir na origem, não onde explodiu.

**Comparar com o que funciona:** achar código parecido que funciona no mesmo repo e listar todas as diferenças, inclusive as que parecem irrelevantes.

**Teste que polui outro:** bisseção da suíte até achar o teste que deixa estado sujo.

**Espera com sleep fixo:** trocar por espera de condição (polling com timeout). Sleep fixo é flaky por definição.

## Fase 3 · Hipótese

Uma hipótese por vez, escrita: "X é a causa porque Y". Teste mínimo que discrimina, uma variável por vez. Não confirmou: nova hipótese, não pilha de fixes.

## Falha de qualidade (classe, não bug pontual)

Transcrição, OCR, extração, ranking, saída de LLM, layout em vários tamanhos: o exemplo reportado é uma amostra de uma classe. Antes do fix:

1. Montar o conjunto de verdade conhecida: o caso reportado, os vizinhos que falham pelo mesmo motivo e casos que hoje passam (para pegar regressão).
2. Medir o número atual (taxa de erro, WER, acerto) e, se existir referência best-in-class, medir ela no mesmo conjunto.
3. Achar o mecanismo (contexto, normalização, tokenização, threshold, modelo) e corrigir ali.
4. Provar no conjunto inteiro: o número sobe, nenhum caso que passava quebra, e o caso reportado passa sem regra específica para ele.

Entrada de dicionário, `if` para o valor reportado ou retry cego são remendo: só como contenção declarada, removida quando o estrutural entra.

## Fase 4 · Corrigir

1. Escrever a regressão que falha pelo defeito. Ver falhar.
2. Um fix, na causa raiz. Sem "aproveitar e melhorar".
3. Ver a regressão passar e a suíte continuar verde.
4. Defesa em profundidade quando o dado ruim cruzou várias camadas: validar na entrada, na regra de negócio e no ponto de uso, para o bug ficar estruturalmente impossível.

## Três hipóteses refutadas

Parar de tentar fix. Três hipóteses que não se confirmam, ou cada fix revela um problema novo em outro lugar, indicam que o modelo causal está errado: reprodução insuficiente, ambiente diferente ou arquitetura que não comporta o caso. Voltar à Fase 1 com o que cada tentativa revelou, e considerar uma segunda opinião independente (outro modelo ou subagente sem a sua conclusão). Escalar ao Owner só quando a saída exigir decisão de produto, custo ou escopo.

## Sinais de que você está chutando

- "Vou só tentar mudar X para ver."
- Vários ajustes de uma vez antes de rodar.
- Propor solução antes de rastrear o fluxo de dados.
- `try/except` ou `?.` para o erro sumir.
- "Provavelmente é X" sem um teste que discrimine.

## Fechamento

Causa raiz em uma frase, com localizador. Regressão (nome do teste) red → green. Se o bug ensinou algo transversal, `incidents/<data>-<slug>.md` com Falha, Correção e lei.
