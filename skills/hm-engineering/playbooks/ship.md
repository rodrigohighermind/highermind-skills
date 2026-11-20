# Playbook · Ship

Carregado no modo `ship`: QA + validação de deploy + gate mecânico antes de declarar baseline-ready. Princípio: código não verificado é suposição; segurança é testada ANTES de funcionalidade; deploy frágil = produto frágil.

## Ordem de execução

1. **Security gate.** CRÍTICO de segurança encontrado = parar; rodar o resto só pra mapa, nunca pra shippar.
2. **Gate mecânico** (typecheck, lint, build, testes).
3. **QA funcional + edge cases.**
4. **Checks do modelo de distribuição.**
5. **Smoke do fluxo real.**
6. **Evidence bundle.**

Owner pode pedir override ("ship mesmo com X aberto"): reportar o estado, Owner decide. Informar, não bloquear autoritariamente; mas nunca declarar baseline-ready com mínimo vermelho.

## 1. Security gate (bloqueante)

Quick pass; auditoria profunda em `playbooks/security.md`.

- `npm audit --production` / `pip audit`: zero HIGH/CRITICAL.
- Docker: `.dockerignore` presente, multi-stage, non-root, sem `--reload`/dev server, zero secret em Dockerfile/compose.
- Grep de secrets: `sk-ant-`, `sk_live_`, `AKIA`, `password=`, `-----BEGIN.*KEY`. `.env` no `.gitignore`. `git log --all -S "sk-ant"` limpo.
- Por endpoint: auth presente, input validation, IDOR mental (`'; DROP TABLE`, `<script>`, `../../etc/passwd`), rate limit em rota pública, CORS restrito, headers.
- Supabase: `supabase db advisors --linked --level error` = `No issues found` + `scripts/audit-rls.sh` verde.

## 2. Gate mecânico

Rodar `scripts/hm_gate.py --root <projeto> --distribution personal|saas` quando aplicável, mais os checks que o gate não descobre:

```bash
tsc --noEmit          # ou mypy/pyright: zero erros
eslint . / ruff check # zero erros
<test runner>         # total, passando, falhando, flaky
bun run build         # build de produção sobe
```

- **O commit depende do código de saída do gate, não da leitura do texto.** O gate sai 0 em `PASS`, 1 em `FAIL` e 2 em `NOT_VERIFIED`; encadear como `gate && commit`, com o gate sozinho no lado esquerdo. Passar a saída por pipe (`gate | grep ... && commit`) troca o código do gate pelo do último comando do pipe, e o commit entra com o gate reprovado. Para filtrar a saída, gravar em arquivo e ler depois, ou usar `set -o pipefail`. Porquê: veredicto lido por texto depende de alguém ler; código de saída barra sozinho. Prova: forçar um `FAIL` e conferir que o encadeamento usado não chega ao commit. Vale também para o relato: "gate verde" só com o `$?` lido e igual a 0; o fim da saída parecer limpo não é veredicto.
- **Gate vermelho fora do diff se conserta na mesma entrega.** O gate vale para o repositório inteiro, não para as linhas tocadas: falha que já estava lá bloqueia o commit igual, e entregar com ela é entregar com o gate reprovado. Consertar a causa (é a exceção à lei do cirúrgico, porque o pedido inclui o gate verde) e declarar no fechamento o que foi consertado fora do pedido. Porquê: "não fui eu" deixa o gate vermelho para sempre e ensina todo mundo a ignorá-lo. Prova: o `$?` do gate é 0 no fim, e o fechamento lista o conserto fora do diff.
- **Todo check roda sobre a árvore que está sendo entregue.** Script do gate recebe a raiz do projeto (a mesma `--root` do gate) e nunca lê o código por caminho fixo. Porquê: rodado numa cópia de trabalho (worktree), check com caminho fixo audita o checkout principal, reprova ou aprova pelo código errado e não vê o diff em revisão. Prova: plantar um defeito só na cópia de trabalho e conferir que o check reprova ali; o mesmo check no checkout principal limpo passa.
- Zero `console.error` novo e zero TODO crítico novo nos arquivos tocados na branch (TODO cosmético é aceitável).
- Reportar a suíte com números: total, passando, falhando (com detalhe de cada), skipped, flaky. "Tudo passando" sem checar se os testes testam a coisa certa não é evidência.

### Gaps de teste

O que NÃO está testado importa mais do que o que está:

- Lógica de negócio sem unit test; endpoint sem teste de integração; fluxo de usuário sem cobertura e2e.
- Fluxos de auth/authz sem teste; estados de erro assumidos mas nunca verificados; edge cases (vazio, limite, concorrência).
- **Um placar só.** Todo teste que existe no repo, inclusive e2e e integração de servidor de ferramentas, roda pelo comando canônico do gate. Porquê: teste fora do placar quebra em silêncio e ninguém vê. Prova: listar os arquivos de teste do repo e conferir que cada um aparece na saída do comando canônico; teste que só roda à mão é finding.
- **Superfície conferida como lista exata.** Teste de superfície pública (tools de um servidor MCP, comandos de CLI, rotas, exports) compara o conjunto exato de nomes, nunca a contagem. Porquê: contagem fica obsoleta sem dizer o que mudou; lista exata obriga a declarar cada adição ou remoção.
- Gap crítico encontrado = escrever o teste, não só descrever. Prioridade: auth/authz/input validation > fluxos críticos (pagamento, features core) > edge cases > estados de erro.

### Verificação de agente (se o projeto tem agente AI)

- O loop termina (max iterations, timeout, token limits)?
- Tools executam e retornam feedback; o agente não alucina tool inexistente.
- Erro em uma tool não quebra o loop inteiro.
- Contexto não estoura; custo por interação dentro do esperado.

## 3. Distribution model define os checks

Identificar o modelo ANTES de auditar. Pular o que não se aplica é parte do trabalho; marcar `NOT_APPLICABLE` no bundle. App Electron não tem `.dockerignore`; library npm não tem migrations.

### Container/Docker

Seção 4 inteira, abaixo.

### Serverless/Edge (Vercel, CF Workers)

- Build output dentro do limite (Vercel: 50MB unzipped por function).
- Cold start <1s em rota crítica; senão, warming ou edge runtime.
- Env vars sensíveis no dashboard, NUNCA em `next.config`.
- Constraints de edge runtime respeitadas: sem `node:` modules, sem fs, sem native addon.
- ISR/cache headers configurados. Domain + SSL prontos pré-deploy.

### Desktop (Electron/Tauri)

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true` (nunca `false`).
- Preload exporta só APIs mínimas via `contextBridge`; nada perigoso exposto ao renderer.
- Code signing configurado, ou warning documentado se dev sem identity.
- Auto-update definido (electron-updater) ou ship manual declarado.
- ALERTA: `.env` copiado pro bundle (`Resources/`) vaza secret se o app for distribuído. Documentar.
- Native modules (sqlite, sharp) com rebuild de ABI correto pro Electron; versão do Electron sem CVE HIGH.
- Bundle id (macOS) / `setAppUserModelId` (Windows) corretos.
- App com janela no macOS tem menu principal com Editar padrão; sem ele, colar, copiar, recortar, selecionar tudo e desfazer morrem em todo campo de texto. O smoke confere o item de colar na barra de menus pela acessibilidade. Regra em `hm-design/playbooks/review.md` §6c.
- **Quem insere texto em outro app não confia no atalho de colar sintético.** Ferramenta que escreve no app em foco (ditado, snippet, expansão de texto) confere antes, pela barra de menus do app alvo lida por acessibilidade, se existe item de colar com a tecla V e modificador só Comando. Sem o item, insere pelo texto selecionado do elemento em foco (`kAXSelectedTextAttribute`) ou digita os caracteres como evento de teclado Unicode. Porquê: o atalho sintético é entregue sem erro mesmo quando o app alvo não tem quem o trate, e o texto some em silêncio. Prova: teste contra um app alvo sem menu Editar e outro com, lendo o valor do campo depois da inserção nos dois.
- Smoke ou QA com input sintético (clique, arraste, tecla) checa antes se a tela está bloqueada; bloqueada, a interação é `NOT_VERIFIED`, não resultado. Regra em `hm-design/playbooks/review.md` §3.

### Mobile (Expo/RN)

- EAS build profiles (development, preview, production) configurados.
- Certificados/provisioning iOS via EAS; keystore Android em local seguro, FORA do repo.
- `app.json` com bundle ID, version, build number corretos.
- Permissions declaradas com justificativa (camera, location).
- App Transport Security: zero `NSAllowsArbitraryLoads = true` em prod.
- OTA updates (`expo-updates`) configuradas ou versão nativa pinada; native modules compatíveis com o SDK.

### Library/SDK (npm, PyPI)

- Lock file commitado; `exports` map (ESM + CJS quando aplicável); types corretos.
- `files` limita o publish: sem `node_modules`, sem `.env`, sem testes.
- Zero `any` no surface público. Semver honesto: breaking = major.
- README com install + quick start + API reference.
- Supply chain: provenance (npm provenance ou cosign); CI de publish via OIDC, sem token secreto no repo; tag git assinada por release.

### CLI tool

- Cross-platform builds quando há chance de share futuro, mesmo entre máquinas pessoais: adicionar target agora é mais barato que retrofit.
- Binário assinado (Apple Developer ID, Authenticode) quando distribui.
- UM caminho canônico de install. Nunca dois scripts com defaults diferentes (`/usr/local/bin` com sudo vs `~/.local/bin` sem): quem retoma o projeto não sabe qual rodar. Padronizar um, deletar o outro.
- `--help` cobre todos os comandos; `--version` reporta. Update check opt-in, sem auto-update silencioso.
- Logs no path padrão do OS (`XDG_STATE_HOME`, `~/Library/Logs`).
- First-run from scratch testado de verdade: `HOME=/tmp/scratch <comando>` valida dirs 0700, config 0600, DB inicializado.

## 4. Container: subida, rebuild, dados

- `docker compose up` sobe tudo; containers HEALTHY, não só running; ordem de dependência correta; logs de startup limpos.
- Rebuild reflete mudança de código (`compose build <svc> && compose up -d <svc>`). Imagem final razoável (Python slim <200MB, Node alpine <150MB).
- **Dados sagrados**: volumes nomeados; `docker compose down` sem `-v` preserva tudo; dado sobrevive a rebuild.
- `.env.example` com TODAS as variáveis; ports documentados sem colisão com outros projetos; port hardcoded em código é finding.

### Registro de ports (projetos paralelos na mesma máquina)

Manter registro vivo dos ports de todos os projetos do ecossistema. Faixa pra projeto novo: API 8000+N, Web 3000+N, Postgres 5432+N, Redis 6379+N, onde N é o próximo livre. Anti-patterns: dois projetos disputando 5432 ou 3000; port hardcoded em código; port divergente entre `.env.example` e `docker-compose.yml`.

## 5. Migrations e rollback

- Migrations rodam automaticamente no boot, em ordem, sem gaps. Schema atual = soma das migrations.
- Nenhuma migration destrutiva sem backup + confirmação. Roll-forward não destrói dado existente.
- Plano de rollback explícito antes do deploy: como voltar a versão anterior de código E o que acontece com o schema. Rollback frágil é finding ALTO.
- Mudança de schema incompatível segue expand/contract: 1) migration aditiva (coluna nova, nullable), 2) código novo escreve nos dois, 3) backfill, 4) código lê do novo, 5) migration de remoção só depois que o rollback window fechou. Assim a migration nova é sempre backward-compatible com o código anterior durante a janela de rollback.
- Backup verificado ANTES de deploy que toca schema em produção. "Verificado" = restore testado, não arquivo existente.

## 6. Health e observabilidade

- `/health` verifica dependências reais (DB ping, Redis ping), nunca `{"status":"ok"}` fixo. False healthy mascara falha.
- Logs estruturados, com contexto pra debugar, sem secrets/tokens/PII.
- Erro de produção chega em alguém (alerta, email, canal), não morre em log.

## 7. Smoke do fluxo real

Responsabilidade do Dev Team, nunca do Owner. Não é "build compila": é dirigir o fluxo principal de verdade.

- Subir o build local, navegar o fluxo primário end-to-end como usuário, observar resultado e console.
- Forms: submit, validação, duplo submit bloqueado, reset limpa de verdade.
- O que não foi possível exercitar (sem browser, sem device, sem credencial) declara-se `NOT_VERIFIED` com motivo. "Não testei UI" é resposta válida; "tudo ok" sem ter olhado não é.
- **Efeito em dado se relata com o lugar onde aconteceu.** Antes de afirmar que o dado real do dono mudou, conferir na fonte real e citar o caminho ou a query; efeito observado numa cópia de QA, pasta temporária ou banco descartável se relata como "na cópia". Porquê: smoke e QA rodam de propósito longe do dado real, e o relato que apaga essa diferença faz o dono confiar num efeito que não existe. Prova: a afirmação traz o caminho conferido, e ele é o da fonte real.

### Edge cases recorrentes (rede final, 80% dos bugs vivem aqui)

- **Forms**: vazio, 1 char, max+1, paste de 1MB, unicode/emoji, null bytes; validação client + server idênticas; fallback manual quando lookup falha.
- **Streaming**: conexão cortada no meio tem retry; marker de interrupção no DB; timeout no request inteiro; dedupe de geração cara.
- **Erros 4xx/5xx**: cada erro com CTA acionável; mensagem nunca é código cru ("HTTP 500", "ECONNRESET"); 429 diz quando tentar de novo.
- **Estados de UI**: empty desenhado, loading com skeleton (não spinner genérico), disabled claro, hover e focus visíveis.
- **Mobile**: media queries <920px e <540px, touch targets >=44px, font-size >=16px em input iOS (zoom), sem scroll horizontal.
- **LLM-app**: conversa 50+ turns não quebra; refresh duplo não cobra 2x; key trocada via UI vale sem restart; custo por sessão conhecido.
- **Concorrência**: 2 abas simultâneas não colidem; click duplo em mutação protegido; write race com transaction + unique index.
- **Dados**: operação destrutiva confirma; backup automático em momento chave; dado persiste entre restarts. Produto que guarda dado do usuário só fecha com backup e restauração provados nos dados reais e com teto em todo arquivo que cresce sozinho (ver [data-integrity](data-integrity.md) · Backup e Restore testado; [operate](operate.md) · Observabilidade mínima).

Smoke que escreve em dado real limpa o que criou: marcador próprio nos registros de smoke e remoção por id exato ao final, conferida por `SELECT`.

Serviço que já roda: varrer o log de produção desde o último ship por `Traceback`, `panic`, `Unhandled`, `FATAL` e erro não tratado faz parte de todo fechamento, não só quando alguém reclama. Erro achado vira caso de teste antes de virar fix.

## 8. Reprodutibilidade: clone limpo

1. Clone do repo. 2. `cp .env.example .env`. 3. Comando único de subida. 4. Funciona?

Cada passo manual não documentado é dívida. O padrão: engenheiro novo na segunda-feira roda o projeto antes do almoço.

**Pacote que embute binário nativo se prova importando, não instalando.** Pacote do registro que carrega biblioteca nativa ou dados compilados pode instalar sem erro e quebrar no primeiro uso, porque traz caminho fixo da máquina onde foi construído. Conferir a versão instalada com um import e uma chamada real em ambiente limpo antes de escrever contra ela. Se o pacote está quebrado, a saída é a biblioteca do sistema, com três condições: a substituição mora num módulo único e comentado com o motivo, não espalhada pelos pontos de uso; o instalador do projeto garante a dependência de sistema e falha com mensagem clara quando ela falta; e o smoke do clone limpo exercita a chamada real. Porquê: o contorno feito à mão na máquina de quem desenvolveu não existe na próxima instalação. Prova: instalação do zero, numa máquina ou conta sem a dependência, termina com a chamada real funcionando ou com o erro que diz o que instalar.

## 9. Custo (se usa APIs pagas)

- Quantas calls um fluxo típico gera; contexto enviado é o mínimo; calls redundantes cacheadas.
- Background tasks sem custo desnecessário. Estimativa por usuário/mês aceitável e registrada.
- Ferramenta pessoal com LLM: confirmar padrão CLI de assinatura, sem `*_API_KEY` no env (ver `playbooks/llm.md` §0).

## 9b. Acessibilidade básica (quick pass)

Contraste WCAG AA; navegação por teclado; focus states em interativos; alt text; labels em forms. Auditoria visual profunda é território de `hm-design`; aqui é rede mínima antes do baseline.

## 9b2. Exceção declarada no gate

Quando um teste precisa de uma key falsa para provar que a real não vaza, a linha leva `# hm-gate: sentinel <motivo>`. Sem motivo não vale, e linha com client de API paga nunca é exceção.

Falso positivo em código que remove as keys do ambiente, numa linguagem cujo idioma de remoção o gate não reconhece: reescrever a remoção como filtro explícito de exclusão (`!=` contra o nome da key), que vale em qualquer linguagem, e reportar o idioma que faltou. Nunca desligar o check nem seguir com ele em `FAIL`. Porquê: o scan reconhece remoção por padrão de texto, e cada linguagem escreve remoção de um jeito. Prova: o gate passa nesse check com o código reescrito e o subprocess continua sem as keys.

## 9c. Floor guard (o diff não pode rebaixar a barra)

`python3 scripts/floor_guard.py --root <projeto>` (base: `.git/orbit-base` gravado no início da sessão, ou `--since <sha>`) lê o diff contra a base e falha quando a mudança rebaixa a barra em vez de cumpri-la: teste ou assert removido, `.skip`/`.only`/`xit`, supressão nova (`noqa`, `type: ignore`, `ts-ignore`, `eslint-disable`, `@ts-expect-error`), threshold de cobertura afrouxado, secret com cara de credencial. Exit 0 limpo · 1 violação · 2 não rodou (nunca lido como 0). Violação justificada é declarada no fechamento, com motivo, nunca silenciada.

## 10. Evidence bundle

Consolidar tudo em um bundle único, cada check com resultado real:

```
GATE MECÂNICO      typecheck · lint · build · testes (números, não adjetivos)
SECURITY GATE      cada check: PASS/FAIL + fix se FAIL
DISTRIBUIÇÃO       checks do modelo: PASS/FAIL/NOT_APPLICABLE
DADOS              migrations, rollback plan, backup: PASS/FAIL
SMOKE              fluxo dirigido + o que ficou NOT_VERIFIED e por quê
CUSTO              estimativa por operação/usuário quando aplicável
```

Separar `PASS`, `FAIL`, `NOT_APPLICABLE` e `NOT_VERIFIED` sem misturar. Baseline-ready só com todos os mínimos verdes; qualquer FAIL bloqueante ou mínimo `NOT_VERIFIED` = declarar o estado exato que impede, não compensar com "passou no resto". Product-ready segue sendo do Owner.
