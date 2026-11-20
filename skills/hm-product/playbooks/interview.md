# Playbook · Interview

Carregado sob demanda quando o modo é `interview`: o Owner quer ser entrevistado para construir o próximo produto, ou chega com uma ideia falada, solta, de uma linha ou de dez minutos. É a entrada do funil: `interview` → `direction` → `spec` → `plan` → `init` (em `hm-engineering`).

Este playbook aprofunda o modo. Autoridade, evidência e fechamento vêm do HM Orbit e não se repetem aqui.

## Por que este modo existe

Todo o resto de produto pressupõe a ideia formada. Quando ela não está, as decisões que só o Owner sabe ficam implícitas e aparecem tarde, como defeito: menu que mistura uso diário com configuração, item copiado da referência que ele não reconhece, organização que não segue o jeito dele de pensar, dado irrepetível sem backup. Cada uma custa uma volta ao Owner depois da entrega. A entrevista paga essas voltas antes, de uma vez.

**Relação com a Lei 7 (pergunta rara).** A lei continua valendo fora deste modo. Aqui o Owner pediu para ser perguntado, mas a disciplina é a mesma: só se pergunta o que é dele e que nenhum arquivo responde, e cada pergunta já traz a hipótese. Entrevista não é licença para questionário.

## Antes da primeira pergunta

Ler, nesta ordem, e anotar o que cada fonte já responde:

1. Estratégia e Source of Truth da empresa ou do Owner, se existirem: tese, público, o que foi encerrado.
2. Memória e projetos existentes: **já existe algo que resolve isso, total ou parcialmente?** Produto duplicado é a primeira pergunta, não a última.
3. Lições de campo e incidentes de produtos anteriores: o que o Owner já reprovou, o que ele aprovou, o vocabulário dele.
4. A referência que ele citou, aberta de verdade (site, app, preços), nunca de memória.

A primeira mensagem da entrevista já mostra o que foi lido ("Li X e Y; parece que Z. Confere?"), para o Owner corrigir em vez de repetir.

## Cobertura

A entrevista só termina com todos os campos fechados: dito pelo Owner, lido em fonte, ou suposto e marcado como suposição. Cada campo existe porque `direction` ou `spec` o consome, ou porque sua ausência já virou defeito tardio.

| # | Campo | O que precisa sair | Evita |
|---|---|---|---|
| 1 | **Para quem e a cena** | Quem usa, onde, quando, com qual dispositivo e com qual mão livre. Uma cena concreta, não um persona. | Produto certo na forma errada (web onde era voz, desktop onde era celular). |
| 2 | **Outcome** | O que muda na vida de quem usa, em comportamento, tempo, dinheiro ou risco, e como se nota. | Feature que entrega "visibilidade" e nada muda. |
| 3 | **Origem do impulso** | Por que agora, o que disparou. Insumo direto do Passo 1 de `direction`. | Construir por reação a concorrente ou ansiedade. |
| 4 | **Referência e desvio** | O melhor produto que existe para isso (piso da Lei 5), o que nele o Owner **quer**, o que **não quer** e onde precisa ser diferente. | Clone que copia rótulo, ordem e item que ninguém entende. |
| 5 | **Forma** | Agente, CLI, app nativo, web, mobile. Teste agent-first: a conversa resolve? Interface é visibilidade e override. | Formulário onde bastava um agente. |
| 6 | **Uso diário e ordem** | O que o usuário abre primeiro, o que é uso diário, o que é consulta, o que é configuração feita uma vez, na ordem **dele**. Vira a navegação. | Menu misturando níveis; ordem herdada da referência. |
| 7 | **Como ele organiza o mundo** | Os eixos pelos quais o usuário agrupa e procura (pessoa, cliente, projeto, data, lugar) e qual é o principal. | Conteúdo misturado que ele precisa separar à mão. |
| 8 | **Vocabulário e tratamento** | Os nomes que o usuário usa para as coisas e como o produto se dirige a ele. Item cujo nome ele não reconhece não entra. | Rótulo técnico ou importado que ninguém entende. |
| 9 | **Prioridade sob conflito** | A ordem quando dois valores brigam: precisão ou velocidade, ao vivo ou lote, privacidade ou conveniência, simples ou completo. | Engenharia escolhendo sozinha o lado errado de um trade-off. |
| 10 | **Dado** | O que entra, quanto acumula em um ano, o que é irrepetível (precisa de backup), onde pode morar (aparelho, nuvem, provedor externo), quão sensível é. | Dado irrepetível sem backup; dado sensível indo para onde não podia. |
| 11 | **Custo** | Teto mensal aceitável e quem paga; assinatura de ferramenta ou API. | Custo variável descoberto na fatura. |
| 12 | **Non-goals** | O que o produto explicitamente não faz nesta versão. | Escopo que cresce escondido. |
| 13 | **Pronto aos olhos dele** | `product-ready` como cena observável: "abro, faço X, em Y vejo Z". Mais o que o faria abandonar o produto. | Entregar algo que passa nos testes e não serve. |

Campos de engenharia (stack, banco, arquitetura) **não** são perguntados: são decisão do Dev Team.

## Como perguntar

- **Uma pergunta por mensagem, com a hipótese na mesa.** "Pelo que li, você abriria isso no celular, andando. Confere, ou é no Mac?" O Owner confirma ou corrige; não precisa formular do zero.
- **Ordem por ganho de informação, não pela tabela.** Começar pelo que muda todo o resto (cena e forma), depois outcome e referência. Campos que uma resposta já cobriu não viram pergunta.
- **Feito para voz.** Aceitar resposta longa, associativa, fora de ordem. Extrair de uma resposta todos os campos que ela toca e devolver em uma linha o que foi entendido, com os campos marcados ("entendi: cena no carro, outcome é não perder decisão de reunião · 1, 2"). Nunca reperguntar o que já foi dito; se ficou ambíguo, perguntar a ambiguidade específica.
- **Ideia lateral não se perde nem desvia.** Vai para uma lista de "depois" no brief e a entrevista segue.
- **Teto declarado:** 12 perguntas por padrão, dito ao Owner no começo. O Owner pode encerrar a qualquer momento ("chega"); o que faltar vira suposição explícita.
- **Sinal de `KILL` ou `DEFER` aparece cedo e é dito na hora.** Se a origem é ruído, se já existe produto que resolve, ou se o timing é errado, dizer na mesma mensagem, com o motivo, e perguntar se ele quer seguir mesmo assim. Não completar a entrevista para depois dar a má notícia.

## Condição de parada

A entrevista termina quando dá para escrever a spec sem voltar ao Owner com pergunta de produto. Prova: listar as perguntas de produto que a spec ainda precisaria; a lista vazia (ou só com suposições aceitas) encerra.

## Saída

Um product brief versionado no projeto, em `docs/product/brief.md` (ou na pasta de produto do repo):

```markdown
# <produto> · brief
Data · versão · perguntas feitas: N de 12

| # | Campo | Conteúdo | Fonte |
|---|---|---|---|
| 1 | Para quem e a cena | ... | Owner, resposta 2 |
| 4 | Referência e desvio | ... | lido: <url ou arquivo> |
| 9 | Prioridade sob conflito | ... | SUPOSIÇÃO: <motivo> |

## Decisões reservadas ao Owner
## Depois (ideias laterais)
```

Fonte é sempre uma de três: `Owner` (com a resposta), `lido:` (com o caminho ou link) ou `SUPOSIÇÃO:` (com o motivo). Suposição nunca aparece como fato.

Em seguida, sem pedir licença: `direction` dá o veredicto sobre o brief. `GO` segue para `spec`, `plan` e `init`, voltando ao Owner só com decisão reservada. `DEFER` ou `KILL` param ali, com o motivo e a condição de retorno.

## Anti-patterns

- Questionário: várias perguntas na mesma mensagem, ou a tabela de campos mandada ao Owner.
- Pergunta sem hipótese ("qual é o público?").
- Perguntar o que um arquivo, a memória ou a referência respondem.
- Perguntar stack, banco ou arquitetura.
- Reperguntar algo já dito, mesmo com outras palavras.
- Brief sem a coluna de fonte, ou suposição escrita como fato.
- Entrevista que nunca termina: passou do teto sem o Owner pedir.
