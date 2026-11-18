# Playbook · Experiment

Carregado sob demanda quando o modo ativo é `experiment` ou `decide`: desenho de experimento, A/B, leitura de resultado, decisão por dado.

## Princípio central

Experimento existe pra falsificar uma hipótese, não pra confirmar uma vontade. O threshold de decisão é cravado ANTES de olhar o dado. Depois que o resultado apareceu, qualquer mudança de critério é leitura oportunista e invalida a conclusão.

## Desenho · cravado antes do início

Todo experimento nasce com este registro preenchido. Campo vazio = experimento não começa.

```yaml
hypothesis: "se <mudança>, então <métrica primária> move <direção> porque <mecanismo>"
randomization_unit: user | household | session | request
population: quem entra, quem é excluído e por quê
primary_metric: uma só, com fórmula e grain do contrato de métrica
guardrails: [custo por outcome, erro, latência, retenção]
baseline: valor atual da métrica primária
mde: menor efeito que muda a decisão (não o menor detectável estatisticamente)
duration: janela fixa, incluindo ciclo semanal completo
stopping_rule: quando para (data ou n), decidido antes
decision_threshold: "se efeito >= X com CI excluindo zero: GO. senão: KILL ou ITERATE"
```

Regras de desenho:

- **Hipótese falsificável.** "Melhorar a experiência" não é hipótese. "Reduzir passos do onboarding de 5 pra 2 aumenta activation_rate_d7 em >= 3pp" é.
- **Uma métrica primária.** Guardrails vigiam efeitos colaterais; secundárias geram hipótese nova, não veredito.
- **Unidade de randomização coerente com a unidade de análise.** Randomizar por sessão e analisar por usuário contamina os braços.
- **MDE vem da decisão, não da estatística.** Se só vale a pena shippar com +3pp, o experimento é dimensionado pra detectar 3pp, não 0.5pp.

## Poder estatístico pragmático

Aproximação suficiente pra proporções (α=0.05, power 0.8, bicaudal):

```text
n por braço ≈ 16 · p(1-p) / δ²

p = taxa baseline · δ = MDE absoluto
ex: baseline 20%, MDE 3pp → n ≈ 16 · 0.16 / 0.0009 ≈ 2.845 por braço
```

Pra métrica contínua: `n por braço ≈ 16 · σ² / δ²`.

Com o `n` na mão, confrontar com o tráfego real:

- Tráfego fecha o `n` em até ~4 semanas: A/B clássico.
- Tráfego não fecha: NÃO rodar A/B decorativo. Alternativas honestas: aumentar o MDE (só detectar efeito grande), switchback/before-after com caveats explícitos de confundimento, ou decidir por qualidade + reversibilidade (shippar atrás de flag com rollback barato e medir depois). Dizer qual caminho foi escolhido e por quê.
- Produto em estágio inicial costuma ser low-traffic: preferir mudanças de efeito grande e reversível a micro-otimização que nenhum experimento local tem poder pra ler.

## Leitura honesta

Vieses que invalidam leitura, checar todos antes de concluir:

- **Peeking.** Olhar o resultado todo dia e parar quando "deu significativo" infla falso positivo brutalmente. A stopping rule cravada no desenho é a única parada válida.
- **Múltiplas comparações.** 20 métricas olhadas = 1 falso positivo esperado a p<0.05. Só a primária decide; o resto exige correção ou vira hipótese.
- **Segmento escondido na média.** Efeito médio +2% pode ser +15% num segmento e -10% no segmento crítico. Ler os segmentos que importam pro produto, definidos antes.
- **Novelty/primacy effect.** Primeiros dias medem curiosidade, não comportamento. Janela inclui estabilização.
- **Mudança concorrente.** Deploy, campanha ou sazonalidade no período contamina. Registrar o que mais mudou durante a janela.
- **Significância ≠ relevância.** p=0.01 com efeito abaixo do MDE é "não vale a pena" com confiança, não vitória.

## Conclusão tipada

Classificar o que o dado permite concluir:

- descritiva: o que aconteceu na janela;
- diagnóstica: associação e mecanismo plausível, sem prova causal;
- causal: efeito de intervenção sob desenho válido (randomização + poder + janela íntegra);
- preditiva: probabilidade futura, com calibração declarada;
- prescritiva: ação recomendada com utilidade e risco.

Correlação apresentada como causalidade é o erro mais caro da classe. Experimento quebrado (randomização furada, peeking, n insuficiente) rebaixa a conclusão de causal pra diagnóstica: dizer isso explicitamente.

## Quando o veredito é NOT_VERIFIED ou UNCERTAIN

Declarar `NOT_VERIFIED` (e nunca forçar conclusão) quando:

- o `n` coletado não alcança o poder desenhado;
- a stopping rule foi violada (parada precoce, extensão pós-hoc);
- a randomização se provou quebrada (SRM: sample ratio mismatch entre braços);
- guardrail rompeu e o experimento foi interrompido por segurança;
- a instrumentação da métrica primária falhou durante a janela (ver playbook measure, dimensão volume).

Check de SRM, executado antes de qualquer leitura de resultado:

```sql
SELECT variant, count(DISTINCT unit_id) AS n
FROM assignments
WHERE experiment = '<slug>'
GROUP BY variant;
-- split 50/50 esperado: desvio relevante entre braços (regra prática: > ~2%
-- com n na casa dos milhares) = randomização ou logging quebrado.
-- Resultado não se lê antes de explicar o mismatch.
```

`UNCERTAIN` é o veredito de produto quando o dado é honesto mas não fecha a decisão: efeito com CI cruzando o threshold, segmentos em direções opostas. Nesse caso o output diz o que coletaria a seguir e qual evidência mudaria a decisão.

## Registro e handoff

Ao fechar, persistir no repo do projeto: desenho original, dados finais, leitura, caveats e o que mudaria a decisão. Experimento sem registro vira anedota em duas semanas.

`hm-engineering` (playbooks `data-*`) entrega a conclusão tipada com evidência e caveats. A decisão de shippar, iterar ou matar pertence a `hm-product` e ao Owner: recomendação com threshold, nunca decreto.
