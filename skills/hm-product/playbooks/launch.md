# Playbook · launch

Do baseline-ready ao produto nas mãos do usuário, sem apostar a reputação num deploy. Produto é dono do go/no-go e da leitura; engenharia executa a mecânica (playbook `ship` da `hm-engineering`). O Owner crava o GA.

## 1. Antes de lançar: o contrato de lançamento

```text
Outcome:       o comportamento que deve mudar, com número
Métrica:       a primária, com baseline e alvo
Guardrails:    o que não pode piorar (erro, latência p95, custo por usuário, churn, ticket)
Kill criteria: o número que, se cruzado, desliga a feature sem reunião
Público:       quem vê primeiro e por quê
Rollback:      como desligar em menos de 5 minutos (flag, não deploy)
```

Lançamento sem kill criteria escrito antes vira debate depois.

## 2. Degraus proporcionais a quem usa

- **Distribuição pessoal ou interna** (o Owner, a família, o time): dogfood com os usuários reais, flag para desligar e os guardrails que importam para o dano possível. Sem beta externo.
- **Produto externo:** dogfood, depois um grupo pequeno e escolhido com canal direto, depois abertura gradual atrás de flag, olhando os guardrails em cada passo. GA é decisão do Owner.

Dinheiro, dado sensível ou IA voltada ao público não pula dogfood. O tamanho do degrau segue o dano possível, não um percentual fixo.

## 3. Feature de IA tem degrau extra

Antes de abrir para quem não é do time, o eval da feature (playbook `llm` da `hm-engineering`) precisa passar o threshold combinado, incluindo os casos adversariais: injeção de prompt, pedido fora de escopo, dado de outro usuário, recusa correta. Em produção, amostrar conversas reais (com consentimento e sem PII exposta) e reavaliar semanalmente; regressão de qualidade é incidente.

## 4. Durante

- Painel com a métrica primária e os guardrails, olhado a cada degrau, não no fim.
- Guardrail cruzado: desligar pela flag primeiro, entender depois.
- Feedback qualitativo do beta tem canal único e é lido inteiro.

## 5. Depois: leitura honesta

Duas a quatro semanas depois, ou um ciclo natural de uso:

- Hipótese vs comportamento observado, por segmento, não só na média.
- Veredicto `GO` (manter e investir), `ITERATE`, `KILL` (remover o código também) ou `UNCERTAIN` (o que falta medir).
- Feature que não moveu o outcome e não tem próximo passo é removida. Código morto de feature morta é débito.
- Registrar no `MEMORY.md` do projeto: o que se esperava, o que aconteceu, o que muda na próxima aposta.
