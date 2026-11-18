# Playbook · Security

Carregado no modo `review` com foco em segurança, no gate de `ship`, e pelos profiles `supabase`, `docker`, `llm` e `regulated`. A barra: se Tempest, Trail of Bits ou Cure53 auditassem amanhã, não encontrariam nada que este playbook não encontrou primeiro.

## Níveis de auditoria

| Nível | Quando | Escopo |
|---|---|---|
| L1 · Baseline | todo projeto, todo deploy | container, secrets, OWASP Top 10, dependências |
| L2 · Enterprise | auth, dados sensíveis, multi-tenant | L1 + API Top 10, business logic, crypto, compliance, AI/LLM |
| L3 · Critical | fintech, saúde, dados regulados | L2 + supply chain, threat modeling (STRIDE) |

Sem certeza do nível: L2. Projeto que manipula dinheiro, dados pessoais ou saúde: L2 é o mínimo. Domínios condicionais (LLM, multi-tenant, upload, Supabase) são obrigatórios em qualquer nível quando o projeto os tem.

## 1. Container e infraestrutura (CIS Docker Benchmark)

### Build

| Check | Critério | Impacto se falhar |
|---|---|---|
| `.dockerignore` | existe em CADA serviço; exclui `.env`, `.env.*`, `.git`, `node_modules`, `__pycache__`, `.venv`, `.next`, `dist`, `.coverage` | secrets vazam nas layers; `docker history` ou registry expõe |
| Multi-stage build | imagem final sem gcc, dev-headers, build tools, pip cache | superfície de ataque expandida; CVEs em tools de build |
| Non-root user | `USER appuser` no Dockerfile | container comprometido = root no host |
| Dev server em prod | sem `npm run dev`, `--reload`, `--debug`, `NODE_ENV=development` | hot reload em prod = info leak + instabilidade + source maps expostos |
| Base image | `slim` ou `alpine`, tag fixa com versão, nunca `latest` | imagens full têm 200+ CVEs a mais; `latest` não é reprodutível |
| Build secrets | nenhum `ARG`/`ENV` com valor real, nenhum `COPY .env` | visível em `docker history`, irrecuperável se publicado |
| EXPOSE | apenas ports necessários; nada de 22, 5432, 6379 | DB/Redis devem ser internos à network |
| Health check | verifica conexão real (DB ping, Redis ping), não só HTTP 200 | false healthy mascara falha; orquestrador roteia pra container quebrado |
| Compose secrets | `${VAR}` ou `env_file`, zero valores literais | compose commitado = secret no git history, permanente |

### Runtime

| Check | Critério |
|---|---|
| Read-only filesystem | `read_only: true` pra containers stateless; tmpfs pra dirs de escrita |
| Capabilities | `cap_drop: [ALL]` + `cap_add` só do necessário |
| Memory limits | `mem_limit` definido; nenhum container pode consumir toda a RAM do host |
| Privileged | nunca `privileged: true`, nunca `--pid=host` |
| Seccomp/AppArmor | perfil default ativo; nunca `security_opt: seccomp:unconfined` |

### Network e ports

- Ports de banco, cache e serviços internos não expostos ao host em produção. Compose expondo 5432/6379/9000 = porta de dev que não vai pra prod.
- Em produção: Docker network interna, não port mapping.
- Em dev: bind em `127.0.0.1`, nunca `0.0.0.0`.
- MinIO/S3: bucket policies configuradas, acesso público desabilitado.

### Database

| Check | Critério |
|---|---|
| SSL | `sslmode=require` ou `verify-full` em produção; nunca `disable` |
| Connection limits | pool dimensionado; `max_connections` configurado |
| Credentials | user/password únicos por ambiente; nunca `postgres`/`postgres` em prod |
| Prepared statements | ORM parametrizado; sem raw SQL com concatenação |
| Backup encryption | backups encriptados, acesso restrito, restore testado |

### Comandos de verificação

```bash
# container roda como root?
docker exec <container> whoami

# .env vazou pra imagem?
docker history <image> --no-trunc | grep -i "env\|secret\|password\|key"

# scan de CVEs na imagem
trivy image <image>
# ou: docker scout cves <image>

# capabilities
docker inspect <container> --format='{{.HostConfig.CapAdd}} {{.HostConfig.CapDrop}}'
```

## 2. Aplicação · OWASP Top 10 (2025)

Para CADA endpoint, verificar:

### A01 · Broken Access Control
- Toda rota protegida tem middleware de auth? RBAC/ABAC enforced no backend, não só no frontend?
- IDOR: trocar `user_id`, `tenant_id`, `resource_id` na request retorna dado de outro usuário?
- Escalation vertical (user comum acessa rota admin?) e horizontal (user A edita recurso do user B?).
- Multi-tenant: isolamento por `tenant_id` em TODA query. RLS ativo.
- `X-HTTP-Method-Override` permite bypassar restrição de método?

### A02 · Cryptographic Failures
- Secrets em env vars, nunca hardcoded, nem "dev default" que parece real.
- Passwords com bcrypt (cost >= 12) ou Argon2id. Nunca MD5, SHA1, SHA256 puro.
- JWT: HS256 com secret >= 256 bits ou RS256/ES256. Rejeitar `alg: none`.
- Dados sensíveis encriptados at rest. TLS em toda comunicação externa.
- Comparação timing-safe pra token/secret: `hmac.compare_digest()` (Python), `crypto.timingSafeEqual()` (Node). Nunca `==`.

### A03 · Injection
- SQL via ORM parametrizado, sem concatenação.
- XSS: output encoding em todo render de dado do usuário.
- Command injection: sem `os.system()`, `subprocess.run(shell=True)`, `eval()`, `exec()` com input externo.
- Path traversal: sem `../` em caminho derivado de input.
- NoSQL injection (Mongo/Redis), CRLF em headers HTTP, `\r\n` em campos que vão pra header de email.

### A04 · Insecure Design
- Rate limiting em endpoints públicos (login, registro, reset password).
- Input validation em toda boundary: body, query params, headers.
- Limites de tamanho em upload, request body, query results. Timeout em toda chamada externa.
- User enumeration: mensagem e timing IDÊNTICOS pra user existente e inexistente ("Email ou senha incorretos", nunca "Usuário não encontrado").
- ReDoS: regex que aceita input do usuário sem catastrophic backtracking (ex: `(a+)+$` com input longo).

### A05 · Security Misconfiguration
- CORS: lista explícita de origens via env var. Nunca `*` em produção.
- `/docs`, `/redoc`, `/swagger`, stack traces e debug desabilitados quando `APP_ENV != development`.
- Headers obrigatórios:
  ```
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Content-Security-Policy: default-src 'self'; script-src 'self'; frame-ancestors 'none'
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  ```
- Mensagens de erro genéricas pro cliente. GraphQL introspection desabilitada em prod. Sem TRACE/TRACK.

### A06 · Vulnerable Components
- `npm audit --production` / `pip audit` limpo. Zero HIGH/CRITICAL.
- Lock files commitados com integrity hashes. Sem `*` ou `latest` em versões.
- Dependências abandonadas (2+ anos sem commit) ou com 1 maintainer em função crítica (crypto, auth): finding.

### A07 · Authentication Failures
- Brute force: lockout após 5 tentativas, progressive delay.
- Session: HttpOnly + Secure + SameSite em cookies. Idle timeout ~30min, absolute ~8h, invalidação no logout.
- Access token curto (15-60min), refresh token com rotation a cada uso.
- Password reset: token único, single-use, expira em 15-30min. Link não expõe token na URL após uso.
- Host header poisoning no reset: link usa host CONFIGURADO, nunca o host do request.
- OAuth/SSO: `redirect_uri` em allowlist exata, `state` validado, PKCE em public clients, scopes mínimos.

### A08 · Software & Data Integrity Failures
- Payload externo validado antes de deserializar. Sem `pickle.loads()`, `yaml.load()` (usar `yaml.safe_load()`), `eval()` com dado externo.
- Migrations versionadas e auditáveis. Sem auto-update de dependência em produção.

### A09 · Logging & Monitoring Failures
- DEVE logar: login success/failure (IP, UA, timestamp), authorization failures, validation failures, mudança de role, operação admin, acesso a dado sensível, password reset, MFA enable/disable.
- NUNCA nos logs: password (nem hashed), token de sessão/JWT, API key, dado de cartão, PII sem necessidade, body de endpoint de login, header Authorization.
- Logs append-only, retenção >= 90 dias, acesso restrito, não serviveis via web.

### A10 · SSRF
- URL externa validada contra allowlist. Sem user input direto em URL de request interno.
- Metadata endpoints bloqueados: `169.254.169.254`, `fd00::`, `localhost`. DNS rebinding tratado.
- Webhook callbacks não alcançam rede interna.

## 3. API Top 10 (se expõe API)

| # | Risco | Check |
|---|---|---|
| API1 | BOLA | todo endpoint com ID verifica ownership |
| API2 | Broken Auth | tokens expiram; rate limit em auth; credential em header, não query param |
| API3 | Property Level Auth | response filtra campos sensíveis; sem mass assignment |
| API4 | Resource Consumption | rate limit por IP/user; limite de paginação; timeout em query pesada |
| API5 | Function Level Auth | endpoint admin separado e protegido |
| API6 | Sensitive Flows | pagamento/reset com proteção extra (re-auth, CAPTCHA) |
| API7 | SSRF | validação em webhooks, callbacks, imports |
| API8 | Misconfiguration | métodos desnecessários off; CORS restrito; versioning |
| API9 | Inventory | endpoints deprecados removidos; sem shadow APIs |
| API10 | Unsafe Consumption | resposta de API terceira sanitizada antes de usar |

GraphQL: introspection off em prod, depth limit, complexity limit, batching limit, alias limit, authorization field-level.
WebSocket: auth no handshake (não na message), Origin verificado, message size limit, rate limit por mensagem.

## 4. Dependências e supply chain

```bash
npm audit --production        # ou: npx audit-ci --critical
pip audit                     # ou: safety check
npx depcheck                  # deps não usadas
```

- Zero HIGH/CRITICAL. MEDIUM com plano de mitigação registrado.
- L3: dependência crítica com 3+ maintainers, release < 12 meses, SBOM gerado, artefatos assinados (cosign/sigstore).

### Dependência abandonada no npm com canal alternativo

Exemplo: CVE-2023-30533 em `xlsx@0.18.5`. Autor parou de publicar no npm; versão patched só no CDN oficial (`https://cdn.sheetjs.com/xlsx-<ver>/xlsx-<ver>.tgz`). Scanner que só olha npm flaga o CVE como permanente.

Pra cada dep HIGH/CRITICAL sem upgrade no npm:
1. Confirmar que upstream parou de publicar lá (não é só semver lock).
2. Buscar canal alternativo oficial (CDN do autor, GitHub releases).
3. Apontar via URL direta no `package.json`: `"name": "https://...tgz"`.
4. Documentar a decisão no repo pra reviewer futuro.

Anti-pattern: ignorar o warning porque "esse CVE não me afeta". Debt acumula até virar vendor lock-in.

## 5. Secrets

### Scan no codebase

Patterns mínimos:
```
sk-ant-           (Anthropic)        ghp_ gho_ ghs_    (GitHub)
AKIA[0-9A-Z]{16}  (AWS)              xoxb- xoxp-       (Slack)
SG\.              (SendGrid)         sk_live_ rk_live_ (Stripe)
sbp_              (Supabase)         eyJ[A-Za-z0-9]    (JWT base64)
-----BEGIN.*PRIVATE KEY-----
password\s*=\s*["'][^"']+["']       api_key\s*=\s*["'][^"']+["']
mongodb(\+srv)?://[^:]+:[^@]+@      postgres(ql)?://[^:]+:[^@]+@
redis://:[^@]+@                     Bearer [A-Za-z0-9\-._~+/]+=*
```

```bash
grep -rn "sk-ant-\|sk_live_\|AKIA\|xoxb-\|SG\.\|-----BEGIN" \
  --include="*.py" --include="*.ts" --include="*.js" --include="*.env*" .

# secrets no git history (remover do código não remove do history)
git log --all --diff-filter=A -p | grep -E "sk-ant-|sk_live_|AKIA|password\s*=" | head -20
git log --all --diff-filter=A -- "*.env" ".env"

# ferramenta dedicada quando disponível
gitleaks detect
# trufflehog git file://. --only-verified
```

Secret no código: CRÍTICO. Secret no git history: CRÍTICO + rotação imediata, sem exceção.

### Environment

- `.env` no `.gitignore`. `.env.example` só com placeholders (`change-me-*`).
- Config file local com secret: chmod 600. Secrets não aparecem em log de build ou startup.

## 6. Business logic (L2+, manual, scanner não pega)

- Race conditions: 2 requests simultâneas criam duplicata? Saldo negativo? Double-spend? Testar com `curl` paralelo.
- State manipulation: pular passo em fluxo multi-step (checkout sem pagamento, aprovação sem review).
- Privilege escalation via workflow: user se promove por sequência de ações legítimas?
- Valores extremos: 0, -1, MAX_INT, string vazia, null. Overflow onde só positivo faz sentido.
- TOCTOU: estado muda entre verificação e uso?
- Mass operations: endpoint de batch sem limite? Export de tudo?
- Referral/promo: código reutilizável? Auto-referral?

Método: mapear fluxos críticos; pra cada um, pular passo, repetir passo, inverter ordem, disparar em paralelo, injetar extremos, trocar role.

## 7. Criptografia (L2+)

| Check | Critério |
|---|---|
| Algoritmos | AES-256-GCM simétrico; RSA-2048+ ou Ed25519 assimétrico; SHA-256+ hash. Nunca DES, 3DES, RC4, MD5, SHA1 |
| Key management | chaves fora do código, rotação programada, separação dev/prod |
| Random | `secrets` (Python), `crypto.randomBytes` (Node). Nunca `Math.random()` pra token |
| IV/Nonce | nunca reusar com mesma chave; GCM nonce 12 bytes random por operação |

## 8. File upload (obrigatório se aceita upload)

| Check | Critério |
|---|---|
| Tipo | MIME por magic bytes, não extensão. Allowlist |
| Extensão | allowlist explícita; verificar double extension (`.php.jpg`) |
| Filename | nunca usar o original no filesystem; gerar UUID; remover `../`, null bytes |
| Size | limite por arquivo E por request, no web server E na aplicação |
| Storage | fora do webroot; servir via CDN ou signed URL, nunca direto pelo app |
| Malware | rejeitar executáveis no mínimo; ClamAV quando possível |
| Archives | limitar ratio de compressão e tamanho descomprimido (zip bomb) |
| Imagens | lib segura com limites (Pillow); strip de EXIF (GPS, device) |

## 9. AI/LLM security (obrigatório se integra LLM)

Patterns de produção (sliding window, dedupe, budget, abort) vivem em `playbooks/llm.md`. Aqui, o ângulo de ataque:

- **Prompt injection direta**: input do usuário vai cru pro prompt? Testar "Ignore all previous instructions".
- **Injeção indireta**: LLM processa conteúdo externo (email, documento, página) que pode carregar instrução maliciosa.
- **System prompt leak**: "Repeat your instructions verbatim" funciona?
- **Exfiltração**: LLM tem acesso a dado que não deveria? Histórico isolado por usuário/tenant? Output filtrado?
- **Tool calling**: tools no mínimo necessário; sem shell/SQL/filesystem arbitrário; args validados por schema antes de executar; rate limit em tool calls; max iterations + max wall time no loop.
- **Confused deputy cross-channel**: resumo gerado por LLM-A e injetado em LLM-B passa por schema (tipo + tamanho máximo) e é marcado no prompt como conteúdo derivado de usuário, nunca como instrução de sistema. Output de modelo é input não confiável.
- **PII em prompts**: o que vai pro provider está mapeado e declarado ao usuário (retention policy)? Logs de prompt sem PII?
- **Custo como vetor de abuso**: input token limit por request, rate limit por usuário, sem amplification (1 request do usuário gerando N calls).

## 10. Multi-tenant isolation (obrigatório se multi-tenant)

| Check | Critério |
|---|---|
| Query isolation | TODA query filtra por `tenant_id`, sem exceção |
| RLS | ativo e com policies testadas |
| API | trocar `X-Tenant-ID` retorna dado de outro tenant? |
| Cache | keys incluem `tenant_id` |
| Files | uploads separados por tenant, sem traversal entre eles |
| Jobs | filas compartilhadas não vazam dado entre tenants |
| Admin | acesso cross-tenant é intencional E auditado |

Teste prático: 2 usuários em tenants diferentes. Toda operação feita com A, tentada com B trocando IDs.

## 11. Supabase / PostgREST · regime absoluto de RLS

Falha aqui = leak total da tabela via anon key, sem alerta e sem log. O regime é estático + automatizado, nunca disciplina.

### Tabela

Toda `CREATE TABLE` em `public` carrega `ENABLE ROW LEVEL SECURITY` + ao menos uma `CREATE POLICY` na MESMA migration. Policy escopa por dono (`auth.uid()`, `household_id = public.current_household_id()`), nunca `USING (true)`. "Faço o RLS depois" é proibido.

```sql
CREATE TABLE public.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id uuid NOT NULL REFERENCES public.households(id),
  content text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "documents: same household all"
  ON public.documents FOR ALL TO authenticated
  USING (household_id = public.current_household_id())
  WITH CHECK (household_id = public.current_household_id());
```

### View

Postgres 15+ trata view como SECURITY DEFINER por default: bypassa RLS das tabelas-fonte. Toda `CREATE [OR REPLACE] VIEW` que toca tabela com RLS exige `WITH (security_invoker=true)`. Materialized view não tem o atributo: restringir via GRANT explícito.

```sql
CREATE VIEW public.document_summary
  WITH (security_invoker=true)
AS SELECT household_id, count(*) FROM public.documents GROUP BY household_id;
```

### Gate e automação

```bash
# antes de fechar sprint: esperar "No issues found"
supabase db advisors --linked --level error
```

Todo projeto Supabase tem `scripts/audit-rls.sh` + pre-commit hook que roda o audit quando `supabase/migrations/` muda. Esqueleto:

```bash
#!/usr/bin/env bash
set -euo pipefail
MIG_DIR="${1:-supabase/migrations}"
fail=0
for f in "$MIG_DIR"/*.sql; do
  if grep -qE 'CREATE TABLE\s+public\.' "$f"; then
    has_rls=$(grep -cE 'ENABLE ROW LEVEL SECURITY' "$f" || true)
    has_policy=$(grep -cE 'CREATE POLICY' "$f" || true)
    if [ "$has_rls" -eq 0 ] || [ "$has_policy" -eq 0 ]; then
      echo "FAIL: $f cria tabela em public sem RLS+policy"; fail=1
    fi
  fi
  if grep -qE 'CREATE\s+(OR\s+REPLACE\s+)?VIEW\s+public\.' "$f"; then
    if ! grep -qE 'security_invoker\s*=\s*true' "$f"; then
      echo "FAIL: $f cria view em public sem security_invoker=true"; fail=1
    fi
  fi
done
exit $fail
```

### service_role

Bypassa RLS por design. Só em código server-side com autenticação prévia. Nunca no client. Auditar `git log -S "service_role"` pra confirmar que a key nunca foi commitada.

## Contrato do finding

Finding de segurança só existe quando nomeia a cadeia inteira:

```text
ATACANTE    quem (anônimo, usuário autenticado, outro tenant, insider)
ENTRADA     por onde (endpoint, campo, header, arquivo, prompt)
CONTROLE    qual defesa falha ou não existe
FRONTEIRA   qual limite de confiança é cruzado
ALVO        o que é afetado (dado, conta, dinheiro, disponibilidade)
RESULTADO   o que o atacante obtém, com PoC
```

- Severidade só para finding confirmado. Critério entre ALTO e MÉDIO: o finding **derrota** o controle ou só o **enfraquece**?
- Confirmado um padrão, varrer o resto do código pelo mesmo padrão. A severidade é a do pior caso encontrado.
- UUID não é autorização. Identificador difícil de adivinhar não substitui checagem de posse.
- O relatório abre declarando a cobertura: `completa`, `parcial` (o que ficou de fora) ou `não avaliado`. Orientação rápida não se apresenta como auditoria.

## Regras de execução

- L1 é o mínimo absoluto. Nenhum projeto passa sem L1 completo.
- Todo finding inclui fix específico com código. "Melhore a segurança" não é fix.
- Finding de segurança é CRÍTICO até que se prove o contrário. O ônus de rebaixar é de quem rebaixa.
- PoC em finding CRÍTICO/ALTO: comando curl, script ou passo a passo. Se não reproduz, rebaixa.
- Não assumir que framework = seguro. Verificar. Não pular domínio porque "o projeto é simples".
- Projeto limpo: reportar em uma linha e parar. Sem floreio.
