# Playbook · Measure

Carregado sob demanda quando o modo ativo é `measure` ou `quality`: definição de métrica, tracking de eventos, instrumentação, qualidade de dado, reconciliação contra fonte de verdade.

## Princípio central

Métrica existe pra mudar uma decisão. Antes de instrumentar qualquer coisa, nomear a decisão que o dado precisa mudar e quem a toma. Se nenhuma decisão muda com o número, não instrumentar: é vanity metric ocupando contexto, custo e atenção.

## Contrato de métrica

Nenhuma métrica entra no sistema sem os sete campos. Métrica sem owner é número órfão; métrica sem ação de threshold é decoração.

| Campo | O que crava |
|---|---|
| Nome + definição | fórmula exata, sem ambiguidade ("ativação" = qual evento, em qual janela) |
| Fonte | tabela/evento/query de origem, com grain explícito |
| Grain | por usuário, por sessão, por household, por dia. Misturar grain quebra toda agregação |
| Cadência | quando é calculada e quando é olhada (diária, semanal, por sprint) |
| Owner | quem responde pelo número e age quando ele se move |
| Threshold | valor que dispara ação, cravado ANTES de olhar o dado |
| Ação | o que acontece quando o threshold rompe. Sem ação, sem alerta |

Exemplo de registro (formato mínimo, vive no repo do projeto, não na skill):

```yaml
metric: activation_rate_d7
formula: users with >=1 core_action within 7d of signup / signups
source: events.core_action, events.signup
grain: user cohort (weekly)
owner: Owner (decisão) · hm-engineering (cálculo)
threshold: "< 0.25 por 2 semanas seguidas"
action: pausar aquisição, investigar onboarding
```

## Driver tree

Começar pelo outcome e decompor até chegar em métrica acionável. North Star sem comportamento causal claro por trás é vanity metric com título pomposo.

```text
Outcome (o que o produto protege ou cria)
├── North Star (proxy mensurável do outcome)
├── Driver 1 (acionável: uma equipe/decisão consegue movê-lo)
│   ├── Input metric A
│   └── Input metric B
├── Driver 2 (acionável)
│   └── Input metric C
└── Guardrails (não podem cair enquanto os drivers sobem)
```

Guardrails obrigatórios:

- **Custo por outcome.** Em qualquer sistema com LLM, custo de inferência é guardrail de primeira classe: não pode crescer mais rápido que o valor entregue. Medir chamadas e custo por tarefa concluída, não por request.
- **Qualidade.** Taxa de erro, retrabalho, correção manual do Owner.
- **Risco.** Incidentes de dados, ações destrutivas bloqueadas, RLS advisories.

Vanity metrics (pageviews, downloads, signups sem ativação) são ruído: reconhecer, nomear como vanity e não construir decisão em cima.

## Tracking plan de eventos

Evento é contrato, não log solto.

- **Naming:** `snake_case`, `objeto_ação` (`file_uploaded`, `bill_paid`), passado, em inglês. Sem sinônimos: um conceito, um evento.
- **Schema por evento:** propriedades tipadas, obrigatórias vs opcionais explícitas, exemplo de payload. Propriedade nova é additive; renomear ou mudar semântica exige versão (`schema_version` na propriedade ou evento novo).
- **Grain e identidade:** todo evento carrega o id da entidade dona (user_id, household_id) e timestamp em UTC com timezone explícito na leitura. Moeda e unidade sempre nomeadas (`amount_brl_cents`, nunca `amount`).
- **Dados sensíveis:** classificar na definição (PII, financeiro, saúde). Evento com dado sensível herda o regime de retenção e acesso do playbook de integrity.
- **Destino:** o tracking plan vive versionado no repo do projeto (`docs/` ou schema de eventos), nunca só na cabeça ou na tool de analytics.

Anti-patterns:

- Evento genérico `action` com `type` dentro (impossível de tipar e de agregar).
- Instrumentar tudo "pra garantir": cada evento tem consumidor nomeado ou não existe.
- Mudar semântica de evento existente sem versão: quebra toda série histórica silenciosamente.

## Instrumentação mínima

Instrumentar o menor conjunto que fecha a decisão. Ordem de preferência:

1. **Dado que já existe** (tabela transacional, log estruturado): query antes de tracking novo.
2. **Evento novo no fluxo de servidor** (confiável, sem adblock, sem race de client).
3. **Evento de client** só quando o comportamento só existe no client (scroll, hover, abandono).

Instrumentação também é código: tipada, testada, com evento disparado exatamente uma vez por ocorrência real (dedupe por idempotency key quando retry é possível; incident: `expensive-generation-is-idempotent` vale pra evento de billing também).

## Qualidade de dado

Testar as dimensões aplicáveis, com owner e ação por alerta (alerta sem dono e sem ação é ruído que treina todo mundo a ignorar):

| Dimensão | Teste típico |
|---|---|
| Freshness | último registro dentro da janela esperada da cadência |
| Completeness | % de nulls em campo obrigatório, eventos por fluxo vs baseline |
| Validity | valores dentro do domínio (enum, range, formato) |
| Uniqueness | duplicatas na chave natural do grain |
| Referential | FKs órfãs entre evento e entidade |
| Volume | contagem diária dentro de banda esperada (queda = instrumentação quebrou) |
| Distribution drift | shift de distribuição que invalida comparação histórica |

Para sistemas LLM, ground truth e eval set são dados de primeira classe: versionar exemplos, rubrica, segmentação e resultado de regressão. Eval sem versão não prova melhora, só mudança.

## Governança de definição

Mudar a definição de uma métrica é breaking change na série histórica:

- Definição nova ganha nome novo ou sufixo de versão (`activation_rate_d7_v2`). Nunca sobrescrever a série antiga silenciosamente: comparação histórica com definição trocada é mentira involuntária.
- Registrar no repo a data da mudança, o motivo e o delta esperado entre v1 e v2 no mesmo período (rodar as duas em paralelo numa janela de overlap quando possível).
- Backfill de métrica recalculada é operação sobre dado derivado: aceitável, mas anotado. Backfill que reescreve evento bruto entra no regime destrutivo do playbook de integrity.

## Cohort e retenção

Métrica de retenção sem safra explícita engana:

- Retenção sempre por cohort (semana/mês de entrada), nunca blended: mix de safras novas crescendo esconde churn das antigas.
- Definir a ação que conta como "retido" (evento core, não login) e a janela (D7, D30, semana 4).
- Curva de retenção que flatten em valor > 0 indica núcleo retido; curva que vai a zero indica produto sem hábito, e nenhuma média esconde isso.

## Análise reproduzível

Toda análise apresentada ao Owner preserva o caminho até o número:

```text
pergunta: qual decisão este número fecha
fonte: tabela/evento + período + filtros + exclusões
query: SQL/comando literal, executável por qualquer sessão futura
resultado: número + unidade + grain
caveats: o que este dado não permite concluir
```

Query que não pode ser re-executada não é evidência, é lembrança. Em sessão futura, a análise se refaz a partir do registro, não da memória.

## Reconciliação contra fonte de verdade selada

Lei operacional. Modo de falha: o banco operacional guarda um valor recorrente desatualizado enquanto o documento de fatos selados já tem o valor novo, e o número errado chega ao Owner. Quebra de confiança direta.

Regra geral, válida pra qualquer projeto que tem um "cérebro" (fatos selados em docs/decisões) e um store operacional (DB, planilha, API):

- **Nunca reportar número operacional ao Owner sem reconciliar contra os fatos selados.** O cérebro é fonte de verdade dos fatos; o DB é operacional e dessincroniza.
- Divergência encontrada = corrigir o store operacional na hora (backup antes, alvo por id real, nunca por posição em lista) e avisar o que foi corrigido, sem esperar o Owner apontar.
- A reconciliação é etapa do fluxo, não boa vontade: entra no início da sessão ou antes de apresentar qualquer número de decisão.
- Quando as duas fontes divergem e não dá pra determinar qual está certa, o número reportado sai como `NOT_VERIFIED` com as duas versões lado a lado. Nunca escolher silenciosamente.

## Comunicação de número

- Sempre com contexto: período, população, filtros, fonte e query reproduzível. Número solto não é evidência.
- Precisão honesta: não dizer "melhorou". Dizer "melhorou 12.3% (95% CI: 8.1 a 16.5%, n=1.240)". Se o intervalo não existe, dizer que não existe.
- Explicitar o que o dado NÃO diz: janela curta, seleção enviesada, mudança concorrente no período.
- Média que esconde segmento crítico é leitura errada: reportar por segmento quando o produto tem populações heterogêneas.

Definição, instrumentação e análise pertencem a `hm-engineering` (playbooks `data-*`). A decisão de growth, pricing e prioridade construída sobre o número pertence a `hm-product` e ao Owner.
