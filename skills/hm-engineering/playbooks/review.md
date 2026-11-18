# Playbook · Review

Carregado no modo `review`: auditoria de engenharia por risco, em 6 eixos ordenados pelo risco do código. A barra: se o comprador do software contratasse os melhores engenheiros do mundo pra auditar o codebase, eles não encontrariam nada que este review não encontrou primeiro.

## Como conduzir

1. Mapear o escopo real: diff, arquivos tocados, superfícies afetadas (dados? auth? custo variável? LLM?).
2. Ordenar os eixos por risco DESSE código, não pelo tamanho do checklist. Diff que toca migration começa no eixo 1; diff de endpoint público começa no eixo 2.
3. Varrer o baseline senior primeiro (abaixo): é grep barato e cada hit é CRÍTICO automático.
4. Nos eixos, revisar por pergunta ("o que acontece se..."), não por leitura passiva.
5. Antes de escrever qualquer código, o autor deveria ter respondido: isso falha silenciosamente? isso escala? isso é seguro? O review verifica as três respostas.

## Baseline senior · inegociável

Qualquer ocorrência abaixo é finding CRÍTICO automático, antes de qualquer eixo:

- Bare `except Exception` / `catch` sem tipo e sem contexto.
- `any` sem narrow; `as` cast sem comentário justificando.
- Fire-and-forget: task async sem error handler (`asyncio.create_task` nu, promise sem catch).
- Secret hardcoded, mesmo "de dev".
- Query sem limit/paginação; endpoint de lista devolvendo tabela inteira.
- Boundary sem validação de input (body, query param, header).
- `print` em produção no lugar de logging estruturado.
- Singleton stale: credencial/config capturada no module-load em vez de factory.
- `JSON.parse` + cast de payload externo sem schema (Zod/Pydantic).
- Chat history sem sliding window com limite explícito.
- Catch silencioso em degradação graceful: `catch {}` ou `catch { return null }` sem log. Mesmo quando degradar é correto, o erro loga em warn com o input que falhou; falha primária que some silenciosa torna "comportamento estranho" indebugável.
- `--force` destrutivo sem `--yes` ou prompt interativo.

## Eixo 1 · Integridade e perda de dados

O eixo mais grave. Dado em risco é sempre CRÍTICO, nunca MÉDIO.

- Operação destrutiva (DELETE em massa, DROP, TRUNCATE, overwrite, `rm -rf`, `down -v`) sem confirmação + backup prévio.
- Migrations: reversíveis ou no mínimo não destrutivas; roll-forward preserva dado; ordem sem gaps.
- Docker volumes nomeados; nenhum dado produtivo em anonymous volume.
- Transações onde atomicidade importa; writes concorrentes com constraint/lock.
- Idempotência de imports e jobs (hash, upsert); replay não duplica nem corrompe.
- Produção pessoal é produção: app desktop com DB em `userData` guarda a única cópia de dados reais; backup e confirmação valem igual.
- Soft-delete eterno de PII também é finding (retention).

## Eixo 2 · Auth, acesso, secrets e superfícies externas

Quick pass aqui; profundidade em `playbooks/security.md`.

| OWASP | Check mínimo |
|---|---|
| A01 | rota protegida tem auth+authz; sem IDOR; RBAC no backend |
| A02 | secrets em env; bcrypt/argon2; JWT com alg seguro |
| A03 | SQL parametrizado; XSS encodado; sem command injection |
| A04 | rate limit público; input validation em toda boundary |
| A05 | CORS restrito; debug off em prod; headers |
| A06 | audit limpo; lock files |
| A07 | brute force; session timeout; reset seguro |
| A08 | sem eval/pickle/yaml.load de dado externo |
| A09 | eventos de segurança logados; zero secret em log |
| A10 | URL externa validada; metadata endpoints bloqueados |

Container: `.dockerignore` ausente = CRÍTICO; dev server em Dockerfile = CRÍTICO; root user = ALTO. Grep de secrets no código e no git history.

## Eixo 3 · Correção, concorrência e failure modes

- Error handling preserva contexto: log com `exc_info`/stack + identificadores da operação; distinguir erro recuperável (retry) de fatal (alerta).
- Retry com backoff exponencial e teto; retry sem backoff amplifica a falha. Circuit breaker em dependência instável.
- Timeouts explícitos em TODA chamada externa (HTTP, DB, subprocess LLM).
- Race conditions: duplo submit, duas abas, job concorrente; TOCTOU entre check e uso.
- Sessões de DB abertas e fechadas no mesmo escopo; shutdown graceful (`cancel()` + await).
- Estados de erro renderizados; happy path sozinho não é correção.
- Cleanup: useEffect com clearInterval/removeEventListener/abort; streams fechadas.
- Se há agente AI: loop com max iterations, token limit, timeout; erro em uma tool não derruba o loop; agente não alucina tool inexistente; contexto não estoura; custo por interação dentro do esperado.

### Checks por linguagem (padrão senior)

Python/backend:
- Catch de tipos específicos, log com `exc_info=True` + contexto (ids da operação); rollback explícito em falha de DB.
- Background task com wrapper de error handling; nunca `asyncio.create_task()` nu.
- I/O independente com `asyncio.gather()`; sessão de DB aberta e fechada no mesmo escopo, nunca reusada entre contexts.

TypeScript/frontend:
- `React.memo()` em componentes de lista; `useMemo()` pra derived state; `useCallback()` com deps corretas (deps vazias = stale closure).
- Fetches independentes com `Promise.all()`; `useState` initializer síncrono pra localStorage (evita render extra).
- Error Boundary em área crítica; loading state em toda tela com fetch; erro de API com feedback visual.
- Types compartilhados em `types/`, não duplicados por página.

Database:
- Todo FK com index; WHERE frequente com composite index; CASCADE DELETE onde parent-child faz sentido.
- Pool configurado: `pool_size`, `pool_pre_ping`, `pool_recycle`.

## Eixo 4 · Arquitetura e custo de mudança

- Responsabilidades separadas; boundaries respeitados; data flow óbvio pela estrutura.
- Dependências circulares; lógica duplicada; abstração no nível certo (nem over nem under; abstração antes de repetição demonstrada é suspeita).
- Engenheiro novo entende o sistema em 30 minutos?
- Acoplamento a vendor/formato que trava migração futura (caso xlsx: dep abandonada vira lock-in).
- Escala: onde quebra em 10x? Em 100x? Queries eficientes em escala; o agent loop escala ou serializa tudo? Arquitetura escala horizontalmente se precisar?

## Eixo 5 · Performance medida e custo variável

Metas e profiling em `playbooks/performance.md`; custo LLM em `playbooks/llm.md`. No review:

- N+1 queries; index nas colunas consultadas; full scan em tabela grande.
- Re-render desnecessário (memo/useMemo/useCallback com deps corretas); lista grande sem virtualização.
- I/O independente paralelizado; operação bloqueante fora do event loop; memoização de computação cara.
- Custo é finding: API call desnecessária, contexto LLM inflado, background task sem justificativa, polling onde cabia push.
- Ferramenta pessoal com client de API paga (`new Anthropic(`, `new OpenAI(`, `*_API_KEY`): avisar o Owner, propor migração pro CLI de assinatura, não construir por cima.

## Eixo 6 · Qualidade, legibilidade e operação

- Testes testam a coisa certa, não cobertura de linha. Fluxo crítico sem teste é risco declarado (não prova automática de bug).
- Naming claro e consistente; sem dead code; imports limpos.
- Logs úteis: nem verbose demais, nem silêncio; acessíveis; estruturados.
- Infra operável: `.env.example` atualizado; migrations automáticas e em ordem; health checks verificando dependência real; ports documentados sem colisão; rebuild de container reflete mudança de código.
- Dependências mantidas; deprecated substituído.

## Formato e conduta

Cada finding:

```
[CRÍTICO|ALTO|MÉDIO|BAIXO] Título
Onde: arquivo:linha ou área
Problema: o que está errado
Impacto: o que acontece se não corrigir
Fix: mudança específica
```

- "Melhore X" não é fix. Fix nomeia a mudança concreta, com código quando o código é o ponto.
- Severidade proporcional ao impacto real: SQL injection = CRÍTICO; health check raso = MÉDIO. Não inflar; não rebaixar dado em risco.
- Zero apontamento de estilo (tabs vs spaces não é finding).
- Revisar TODAS as camadas, não a mais fácil. Segurança primeiro, sempre.
- Código sólido: dizer em uma linha e parar. Não inventar problema pra justificar o review.
- Fechamento: total por severidade + recomendação (shippa · corrige primeiro · repensa).

## Intenção vs implementação

Quando existe intenção documentada (spec, `permissions.md`, papéis, matriz de acesso, ADR), auditar o código contra ela citando os dois lados com `path:linha`. Divergência é finding mesmo com teste verde. Em Supabase, a matriz de papéis documentada contra as policies reais de RLS é o caso clássico.

## Revisor sem a conclusão

Review independente recebe o artefato e o contrato (spec, fatia, critério), nunca a afirmação de quem fez ("está pronto", "testei tudo"). Pedido adversarial: achar o que quebra. Veredito na primeira palavra: `ship`, `fix` ou `rethink`.

## Severidade

- `CRÍTICO`: perda de dados, acesso indevido, secret exposto, execução arbitrária, ship impossível.
- `ALTO`: falha provável com impacto material, rollback frágil, custo explosivo.
- `MÉDIO`: correção, operação ou manutenção degradada sem impacto material imediato.
- `BAIXO`: melhoria localizada sem risco funcional.

Calibrar por impacto, explorabilidade, exposição e reversibilidade. Segurança não é automaticamente crítica; dado realmente em risco é.

## Perfis de risco

Carregar só quando o artefato pede: `web` (cache, Core Web Vitals, acessibilidade técnica) · `supabase` (RLS, `security_invoker`, advisor, storage policy, service role) · `desktop` (produção pessoal, updater, DB em `userData`) · `mobile` (lifecycle, offline, permissões) · `docker` (imagem mínima, non-root, healthcheck; `Docker.raw` só devolve disco após Reclaim space) · `regulated` (PII, audit trail, retenção). Em Bun, `bun:sqlite`; `better-sqlite3` não roda no runtime.
