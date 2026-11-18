# Playbook · Performance e custo variável

Carregado nos modos `diagnose` e `review` (eixo 5) quando o risco é latência, throughput ou custo variável. Princípio: medir antes de otimizar. Bottleneck é onde o número está fora do alvo, não onde você acha que está. Otimização prematura é bug; falta de measurement também.

## Ferramentas por camada

| Camada | Tool |
|---|---|
| Bundle Next.js | `bun run build` (tamanho por rota) ou `@next/bundle-analyzer` |
| React renders | React DevTools Profiler |
| Node/Bun | `clinic.js`, `0x` flamegraphs |
| Postgres | `EXPLAIN ANALYZE`, `pg_stat_statements`, `log_min_duration_statement = 1000` |
| Web vitals | Lighthouse, web-vitals package |
| Network | DevTools Network, `openssl s_client` pra TLS |
| Memory | heap snapshot no DevTools |
| LLM | usage por call + dashboard interno (ver `playbooks/llm.md`) |

## Frontend · bundle

| Métrica | Alvo | Crítico se |
|---|---|---|
| First-load JS | <200KB gzipped | >400KB |
| Per-route JS | <100KB gzipped | >200KB |
| Total JS | <500KB gzipped | >1MB |
| CSS | <50KB gzipped | >100KB |
| Imagens primeira tela | <200KB | >500KB |

```bash
bun run build                       # Next: tamanho por rota
du -sh .next/static/chunks/*.js | sort -h | tail
```

Anti-patterns: import de lib inteira (`import _ from 'lodash'`), moment.js (usar date-fns ou `Intl`), chart lib pesada pra 1 gráfico, component lib gigante usada em 3 componentes.

## Frontend · render

| Métrica | Alvo |
|---|---|
| LCP | <2.5s |
| INP | <200ms |
| CLS | <0.1 |
| TTFB | <600ms |

Anti-patterns: inline object/array como prop (quebra memo), useEffect com deps erradas, lista >200 itens sem virtualização, imagem sem otimização/lazy, web font sem `font-display: swap`.

## Backend · latência de API

| Métrica | Alvo |
|---|---|
| p50 | <100ms |
| p95 | <300ms |
| p99 | <800ms (>1s user-facing = bloqueio) |
| LLM streaming | first token <2s |

Medição: logging estruturado com `duration_ms` por request; `curl -w` pra teste manual; APM quando existe.

Anti-patterns:
- **N+1**: 1 query parent + N por filho. Fix: JOIN ou batch (`inArray`).
- Query sem index em coluna de WHERE/ORDER BY; full table scan em tabela >10k rows.
- Operação bloqueante no event loop; sync I/O em path quente.
- I/O independente sequencial (usar `Promise.all` / `asyncio.gather`).

## Latência percebida

Interface "ao vivo" (transcrição, streaming, colaboração, progresso) mede o **atraso que a pessoa vê**, não o tempo de processamento. Atraso visível = do evento real até aparecer na tela. Rascunho parcial mostrado cedo, com o resultado final vindo da unidade completa, corta o atraso visível sem perder precisão. Métrica de aceite: mediana e p95 do atraso visível, comparados com a referência do produto.

**Contexto lido durante o evento, não depois.** Insumo que o passo final vai precisar (contexto da tela, documento aberto, seleção) é coletado de forma assíncrona enquanto a pessoa ainda fala ou digita, e não no momento em que ela solta a tecla. Comando de voz é reconhecido por uma palavra de chamada no início, para o roteamento começar antes do fim da frase.

**Especular para esconder pós-processamento.** Passo caro que roda depois da unidade completa (formatação, classificação, enriquecimento) roda antes, no parcial, enquanto o evento ainda acontece. Quando o final chega, se a entrada do passo bate com a do parcial, o resultado é reaproveitado; se não bate, roda de novo. A conferência é por igualdade da entrada, nunca "parecido o bastante".

## Database

- Todo FK indexado; WHERE frequente = composite index. `EXPLAIN ANALYZE` prova, opinião não.
- Pool dimensionado (`pool_size`, `pool_pre_ping`, `pool_recycle`); pgbouncer quando aplicável.
- Slow query log ativo (`log_min_duration_statement = 1000`). Vacuum + autoanalyze configurados.
- Pagination obrigatória em toda lista. Cursor-based pra lista grande (>1k rows): OFFSET alto faz o Postgres escanear até lá.

```ts
// não: OFFSET 50000
// sim: cursor pela última createdAt vista
const items = await db.select().from(messages)
  .where(lt(messages.createdAt, cursor))
  .orderBy(desc(messages.createdAt))
  .limit(20)
```

- JSON path consultado = GIN index.

## Cache

- Anthropic prompt caching pra system prompt + few-shot fixos. Hit rate >50% corta ~90% do custo do prefixo; medir via `usage.cache_read_input_tokens`.

```ts
system: [
  { type: 'text', text: largeStaticInstructions, cache_control: { type: 'ephemeral' } },
  { type: 'text', text: dynamicContext },  // não cacheado, sempre por último
]
```

- Cache in-memory sempre com bound (LRU). Map sem limite é leak.
- Resultado reutilizável entre runs vai pra cache persistente (sqlite) antes de repetir trabalho.

## Network

| Check | Critério |
|---|---|
| HTTP/2 ou HTTP/3 | ativo (verificar via `openssl s_client` / DevTools) |
| Compression | `Content-Encoding: gzip` ou `br` nas respostas |
| CDN | assets estáticos servidos por CDN |
| Cache headers | `Cache-Control: public, max-age=31536000, immutable` em asset versionado |
| Preconnect | `<link rel="preconnect">` pra origens críticas (fonts, API) |
| Requests desnecessários | polling onde cabia push; fetch duplicado entre componentes |

## Memory

- Heap não cresce indefinidamente em sessão longa (snapshot antes/depois).
- Cleanup em todo useEffect: clearInterval, removeEventListener, abort controller.
- Streams fechadas, readers liberados.
- Leak em processo background = bloqueio: vai cair em horas ou dias.

## S3 multipart · part size × banda (lei cravada)

Em multipart upload pro S3, cada PUT individual precisa completar em **menos de ~10s** sob a banda de upload realista do usuário. O idle timeout do S3 é ~20-30s (não documentado); PUT que chega perto disso cai com jitter de wifi.

```
tempo_por_part = PART_SIZE / (banda_upload / paralelismo)   → manter << 10s
```

Exemplo: `PART_SIZE=50MB` com `MAX_PARALLEL=4` em banda de 75 Mbps = ~22s por PUT. Falha sistemática em todos os arquivos. Fix: `PART_SIZE=16MB`, `MAX_PARALLEL=2` = ~3.5s por PUT, mesmo throughput agregado, longe do timeout.

- Dimensionar pela banda medida; sem dado, assumir piso pessimista (10 Mbps). AWS recomenda 8-16MB em rede residencial; 50MB só faz sentido em data center.
- Limite S3 de 10k parts: arquivo de 12GB com parts de 16MB = 768 parts, folga.
- Diagnóstico: `Unable to connect. Is the computer able to access the url?` (Bun fetch) ou `RequestTimeout` (S3) tem como PRIMEIRA hipótese idle timeout, não falha de rede. Bun fetch mascara o timeout como erro genérico; olhar os logs dos PUTs reais.

## Egress é custo de arquitetura, não rodapé de fatura

Exemplo: backend em PaaS lendo acervo de vídeo direto do S3, repetido, furando o CloudFront que já existia = terabytes de egress e uma fatura dezenas de vezes maior que o storage recorrente saudável. Regras:

- Leitura recorrente de objeto grande passa por CDN (CloudFront) ou cache local. Pipeline que reprocessa mídia baixa UMA vez e cacheia; `ffmpeg` lendo direto do bucket em loop é incêndio.
- Custo de egress entra no desenho: quem lê, de onde, quantas vezes. "Storage barato" não é a conta; DataTransfer-Out é.
- Guard-rails desde o day 1 em qualquer conta cloud: budget mensal com alerta (real + forecast) e Cost Anomaly Detection com threshold baixo (~$20). Alerta de custo é ping de produção.
- Provider de dados que importam é big cloud (AWS/GCP/Azure/Cloudflare/Supabase). Tier-2 barato só pra dado descartável.

## LLM

Patterns completos em `playbooks/llm.md`. Métricas pro perf review:

| Métrica | Alvo |
|---|---|
| Tokens input por turn | <3000 descontado o system prompt |
| Custo por turn | conhecido e registrado; chat normal barato, geração longa com teto |
| First token latency | <2s |
| Cache hit rate | >50% quando há prefixo estático |
| Working memory | ~15 turns |
| Contexto injetado | trecho relevante, não documento inteiro |
| Custo por usuário/mês | estimado, com alerta definido |

## Build

- Hot reload <2s. Cold build <60s pra projeto médio.
- CI com build cache. `tsc --build` incremental em monorepo.

## Regras

- Sem números vira especulação. Todo finding de perf cita a medição.
- Bundle 2x do alvo, DB sem index em query quente, p99 >1s user-facing, memory leak em background: bloqueiam ship.
- Custo variável (LLM, egress, API paga) é métrica de performance. Call desnecessária é bug.
