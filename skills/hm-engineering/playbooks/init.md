# Playbook · Init

Carregado no modo `init`. O primeiro commit define o padrão: projeto world-class não se torna, nasce. Terminal condition: outra pessoa clona, sobe, testa e entende as decisões só com o repo.

## 0. Antes de criar qualquer coisa

- **Checar a pasta antes de criar.** Nunca `mkdir` cego: nome de produto colide com projeto existente. Listar o diretório pai, confirmar que o slug está livre.
- Se o projeto é CLI, carregar também `playbooks/cli.md` (stack e patterns cravados).
- Se a descrição do Owner é vaga, UMA pergunta de esclarecimento. Não mais.

## 1. Stack pela natureza do produto

Não a popular, não a que você conhece. A melhor pra ESSE produto, considerando time, distribuição, dados, custo e operação:

| Critério | Peso | Pergunta |
|---|---|---|
| Fit pro problema | CRÍTICO | resolve o core melhor que as alternativas? |
| Performance | ALTO | latência, throughput, cold start atendem? |
| Custo em produção | ALTO | API calls, hosting, bandwidth, egress em escala |
| Segurança | ALTO | histórico de CVEs, supply chain confiável |
| Maturidade | MÉDIO | docs, comunidade, edge cases resolvidos |
| Ecossistema | MÉDIO | libs e tooling resolvem ou você reinventa? |
| DX | MÉDIO | iteração, debugging, deploy fluidos |
| Hiring pool | BAIXO | conta só se o time vai escalar |

Justificar cada escolha em uma frase. Anti-razões: "todo mundo usa", "é o que eu conheço", "pode ser que a gente precise".

**Providers: world-class only.** Dados que importam vivem em big cloud (AWS, GCP, Azure, Vercel, Cloudflare, Supabase, Neon). Tier-2 barato (Backblaze, Wasabi, Oracle free tier) só pra dado descartável, cache puro ou experimento <30 dias com trade-off aceito explicitamente. Dúvida de custo = levar cálculo pro Owner (X/mês big cloud vs Y/mês tier-2 + risco de switching); o default é big cloud.

**Runtime real decide o driver.** Em Bun, `bun:sqlite`; `better-sqlite3` é native addon de Node e falha em build/compile. Não transportar stack de Node por hábito.

## 2. Arquitetura agent-first (quando há componente AI)

O agente executa; a UI dá visibilidade e override. Antes de criar tela: "o agente resolve via conversa?". Dashboard existe pra visibilidade, não pra input principal. Projeto que vai ter agente nasce agent-first; "adiciona agente depois" vira formulário com IA enxertada.

## 3. Estrutura e qualidade day 1

- Estrutura de pastas que torna a arquitetura visível; boundaries claros; engenheiro senior entende em 10 minutos.
- TypeScript strict / type hints completos. Lint + format com config opinada. Framework de testes pronto.
- Quality commands funcionando desde o commit zero: `typecheck`, `lint`, `test`, `build`. São os comandos que o gate de ship vai rodar; se não existem, baseline-ready nunca é verificável.
- Sem arquivo placeholder, sem TODO no dia um. Tudo que existe funciona. O projeto RODA após o init.

## 3b. App nativo macOS: nasce do starter

App macOS novo não começa do zero nem de projeto copiado: nasce do starter, que já traz SDK atual, chrome nativo, tokens claro e escuro, transição de camada correta, ganchos de QA, régua de paridade e o gate verde.

```bash
python3 <skill>/templates/macos-app/new_app.py "Nome do App" com.empresa.app <destino>
```

O gerador renomeia tudo, cria o git com o primeiro commit e recusa destino existente. Detalhes do que vem pronto em `templates/macos-app/README.md`. Divergir do starter é decisão declarada no `CLAUDE.md` do projeto, com o motivo.

Quando a casa tem um criador de projeto próprio (comando que define localização, git, arquivos de contexto e primeiro commit), os dois não compõem direto: ambos criam o git e recusam destino existente. A ordem: o criador da casa cria o projeto; o starter é gerado em pasta temporária e copiado para dentro sem o `.git` e sem sobrescrever arquivo existente; o `.gitignore` é mesclado, não substituído. Porquê: escolher um dos dois em silêncio perde ou a organização da casa ou o piso do starter. Prova: build e testes verdes no projeto resultante, um só histórico git e os arquivos do criador da casa intactos.

## 4. Infra local Docker-first (quando há serviços)

- `docker compose up` sobe tudo: banco, cache, serviços. Um comando.
- Ports documentados e não colidentes com os outros projetos da máquina (registro vivo: API 8000+N, Web 3000+N, Postgres 5432+N, Redis 6379+N). Bind em `127.0.0.1` em dev.
- Volumes NOMEADOS, nunca anonymous. Dados sobrevivem a `docker compose down` sem `-v`.
- Health checks nos serviços; migrations automáticas no boot.

## 5. Segurança desde o primeiro commit (obrigatório)

### .dockerignore em CADA serviço com Dockerfile

```
.git
.env
.env.*
!.env.example
node_modules
__pycache__
*.pyc
.pytest_cache
.coverage
.venv
.next
dist
.vscode
.DS_Store
docker-compose*.yml
```

Sem `.dockerignore` o projeto não está pronto. Ponto.

### Dockerfile production-ready

Multi-stage, non-root, deps copiadas antes do código, sem dev server, EXPOSE mínimo.

```dockerfile
# backend Python
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --target=/deps .

FROM python:3.12-slim
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages
COPY . .
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend Next.js (exige output: 'standalone' no next.config.ts)
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER app
EXPOSE 3000
ENV PORT=3000 HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

### Entrypoints separados

`entrypoint.sh` (prod, sem `--reload`) e `entrypoint.dev.sh` (dev, com reload). Compose aponta pro prod; `docker-compose.override.yml` sobrescreve pro dev (volume mounts, ports de debug).

### Secrets, headers, deps

- Zero secret hardcoded, nem "dev default" que parece real. `.env` no `.gitignore`; `.env.example` completo com placeholders (`change-me-*`). Compose só com `${VAR}`/`env_file`.
- Security headers no backend desde o init. CORS via env var, nunca `*` como default.
- `npm audit`/`pip audit` no init: zero HIGH/CRITICAL. Lock files commitados.

## 6. Fundação de código

- Auth se o produto precisa. Schema com migrations. Estrutura de API com middleware e tratamento de erro.
- Health check endpoint que verifica dependências reais (DB ping, Redis ping), não `{"status":"ok"}` fixo.
- Backup: qualquer projeto que persiste dado nasce com estratégia de backup, mesmo local (snapshot agendado ou no close do app).

## 7. Restrições de custo no desenho

- LLM: ferramenta pessoal nasce no padrão CLI de assinatura (`claude -p`, sem `*_API_KEY` no env do subprocess); API só em produção servindo terceiros, com cost tracking. Ver `playbooks/llm.md`.
- Background jobs com frequência justificada. Documentar custo estimado por operação principal.
- Conta cloud nova: budget mensal com alerta + anomaly detection no setup, não depois do incidente.

## 8. Memória e documentação

- **`AGENTS.md`** na raiz: contexto do produto pro agente. Stack, decisões cravadas, módulos, glossário do domínio, comandos de qualidade. Endurecer o baseline aqui se aplicável (nunca afrouxar).
- **`MEMORY.md`** na raiz: resumo vivo do estado, limite ~200 linhas; detalhe vai pra `docs/topics/<assunto>.md`.
- **ARCHITECTURE.md** (ou ADR inicial): stack e por quê, trade-offs, como rodar, ports, estrutura, decisões de segurança.

## 9. Configurações obrigatórias por stack

### Next.js (13+)

```ts
// next.config.ts
export default {
  devIndicators: false,   // overlay de devtools é lixo visual, sempre off
  output: 'standalone',   // se roda em Docker
}
```

### Supabase / Postgres via PostgREST

- Copiar `scripts/audit-rls.sh` + pre-commit hook do projeto-template (esqueleto em `playbooks/security.md` §11).
- Inscrever no email semanal do Security Advisor e tratar como ping de produção.
- Gate de sprint: `supabase db advisors --linked --level error` = `No issues found`.
- Projeto Supabase sem audit-rls + hook NÃO está inicializado: sem automação a regra vive em disciplina, e disciplina falha.

### Tailwind v4 + Turbopack

Design tokens (cores, spacing específico, gradients) via inline styles: a resolução de classes arbitrárias (`bg-[#3a7a8c]`) não é confiável. Tailwind só pra primitivos de layout (`flex`, `grid`, breakpoints).

### Tauri / Electron (desktop com DB local)

- DB em `userData` é produção pessoal desde o primeiro build instalado. Dados reais, dados sagrados.
- Backup automático no `before-quit`. Reset de profile/DB exige confirmação explícita por operação.

## 10. Checklist de saída do init

Após o init, o Owner consegue:

1. Entender cada escolha técnica e o porquê.
2. Subir o projeto com um comando.
3. Construir features sem fricção de setup.
4. Saber quanto custa rodar em produção.
5. Confiar que está seguro desde o commit zero (`.dockerignore`, multi-stage, non-root, secrets fora).
6. Encontrar `AGENTS.md` + `MEMORY.md` na raiz prontos pra acumular contexto.
7. Em Supabase: audit-rls + hook funcionando. Em Next: zero overlay de devtools.
8. Com fila, job longo ou fluxo ao vivo: prioridade por fila, checkpoint e métrica de atraso visível desenhados desde o início ([build §4b](build.md), [performance · latência percebida](performance.md)).

Fechar o init rodando o review de segurança L1 (`playbooks/security.md`) sobre a fundação.
