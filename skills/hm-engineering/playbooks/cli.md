# Playbook · CLI

Carregado pelo profile `cli` nos modos `init` e `implement` quando o artefato é uma ferramenta de terminal. Barra: o melhor craft de produto portado pro terminal. Denso, intencional, zero ruído. Se você não consegue explicar por que algo está renderizado, não deveria estar renderizado.

## Contrato Unix (vale pra todo CLI, TUI ou não)

- **Exit codes**: `0` sucesso, `1` erro de execução, `2` erro de uso (arg inválido). Scripts e agentes dependem disso.
- **stdout = dado, stderr = diagnóstico.** Output que outro programa consome vai pro stdout; progresso, warnings e erros vão pro stderr. `cli | jq` nunca pode quebrar por causa de spinner no stdout.
- **TTY detection**: `process.stdout.isTTY` decide. Sem TTY (pipe, cron, agente): sem cores, sem spinner, sem prompt interativo, output determinístico.
- **Structured output**: todo comando que produz dado aceita `--json` (uma linha por objeto ou documento único). Agent-first significa que outro agente vai consumir esse CLI.
- **`--version` e `--help`** sempre. `--help` cobre todos os comandos.
- **Fail fast com mensagem útil**: config faltando = mensagem no stderr + exit 1, não stack trace.

```ts
export function requireConfig(): CliConfig {
  const cfg = loadConfig();
  if (!cfg.ready) {
    process.stderr.write("✕ Config incompleta. Roda /config <provider> <key>\n");
    process.exit(1);
  }
  return cfg;
}
```

## Stack recomendada (desvio com razão registrada)

| Camada | Escolha | Por quê |
|---|---|---|
| Runtime | Bun | `bun build --compile` gera single binary, startup instantâneo, sqlite nativo |
| Linguagem | TypeScript strict | zero `any`, `noUncheckedIndexedAccess: true` |
| Render TUI | Ink (React no terminal) | `<Static>` pra scrollback nativo, flexbox real |
| DB local | `bun:sqlite` | `better-sqlite3` é native addon de Node, incompatível com Bun |
| LLM | subprocess `claude -p` (CLI de assinatura) | ferramenta pessoal não chama API paga; ver seção LLM abaixo |
| Distribuição | `bun build --compile` (~60 MB) | binário standalone, sem `node`, sem `npm install` |
| Install path | `~/.local/bin/<name>` | no PATH por padrão, sem sudo. UM caminho canônico de install, nunca dois scripts com defaults diferentes |

Anti-stack: `commander`/`yargs`/`inquirer` (Ink cobre), `chalk` (Ink tem `color`), Node REPL interativo (suja scrollback).

## LLM dentro do CLI: subprocess de assinatura

Ferramenta pessoal/local nunca instancia SDK pago. O cérebro roda via CLI de assinatura:

```ts
const env = { ...process.env };
delete env.ANTHROPIC_API_KEY;   // com a key no env, o CLI cobra na API silenciosamente
delete env.OPENAI_API_KEY;

const proc = Bun.spawn(
  ["claude", "-p", prompt, "--model", "sonnet", "--output-format", "json"],
  { env, stdout: "pipe", stderr: "pipe" },
);
const timeout = setTimeout(() => proc.kill(), 120_000);
const out = await new Response(proc.stdout).text();
clearTimeout(timeout);
```

- Timeout + handler de erro sempre. Parsear o JSON de saída por schema antes de usar.
- Sessões continuáveis com `--resume <session_id>`.
- Codex: `codex exec --skip-git-repo-check "<prompt>" < /dev/null`. Não passar `-m`: usar o modelo padrão da config, porque modelos fixados podem dar 400 em conta de assinatura.
- SDK pago só em software multi-tenant servindo terceiros, com cost tracking. Detalhe em `playbooks/llm.md`.

## Comportamentos obrigatórios antes de qualquer feature de domínio

- **Exit**: `exit`, `quit`, `q`, `sair`, `/sair`, `/quit`, `/exit` saem imediatamente, sem confirmação. Ctrl+C: primeira vez avisa, segunda sai.
- **Help**: `/help`, `help`, `--help`, `-h`.
- **Version**: `--version`, `-v` imprime `<nome> v<versão>` e sai.
- **Config**: `/config` mostra estado das keys (configurada ou não, nunca o valor). `/config <provider> <key>` salva em `~/.<nome>/config.json` com chmod 600.
- **Erros**: mensagem humana, nunca stack trace. Try/catch defensivo em tudo assíncrono. Cache com fallback silencioso (mas logado) se o DB corromper.

## Filosofia agentic-first

CLI agêntica é um agente operando num terminal, não um menu de comandos. Conversa é a interface primária; slash commands são atalhos. O agente age quando tem certeza e confirma quando é destrutivo ou irreversível. LLM tempera, não regurgita: local-first sempre que o dado bruto resolve.

### 4 camadas de resposta, em ordem

```
1. SLASH COMMAND          zero token, instantâneo
2. INTENT LOCAL (regex)   zero token, milissegundos
3. LLM COM CONTEXTO       custo por turn
4. TOOL CALL → resposta   zero LLM, dado bruto
```

Regra de ouro: listagem, total, status = camadas 1-2. LLM só pra análise e pergunta aberta.

## Boot lifecycle

```ts
// 1. clear screen + scrollback + cursor home (sem isso, lixo da sessão anterior)
process.stdout.write("\x1b[2J\x1b[3J\x1b[H");

// 2. app controla o exit
const app = render(<App />, { exitOnCtrlC: false });
await app.waitUntilExit();
```

Bracketed paste mode (`?2004h`): NÃO ativar sem o sistema completo de paste detection (buffer, timer 120ms, flush, placeholder `[Pasted text #N +M lines]`). Ativar sem tratar os markers gera input boxes fantasma e alerta "paste bracketing left on" no iTerm. Detecção conservadora: marker `\x1b[200~`/`\x1b[201~` ou `\n` no chunk; nunca timing heuristic (digitação rápida vira falso positivo).

## Arquitetura TUI

Estrutura:

```
src/
├── cli.tsx              entry point (--version, --help, render)
├── agent/
│   ├── app.tsx          root: states, streaming, boot, handlers
│   ├── system-prompt.ts prompt + tool definitions
│   └── tools.ts         dispatch de tool calls
├── tui/
│   ├── types.ts         UIMessage, AgentState, AppMode
│   ├── theme.ts         COLORS, glifos, formatters
│   ├── markdown.tsx     tokenizer parser
│   ├── message-list.tsx histórico + streaming
│   ├── input-box.tsx    cursor real, disabled, callbacks
│   └── status-bar.tsx   rodapé com state dot
├── pipeline/            domínio
└── lib/                 cache, config, clients
```

### theme.ts

```ts
export const COLORS = {
  textPrimary: "#E8E6E1",
  textSecondary: "#A8A29E",
  textDim: "#52524F",
  accent: "#XXXXXX",   // signature do produto; um produto, uma accent
  success: "#65BB7D",
  warning: "#E0A85C",
  danger: "#C56B5C",
  separator: "#2A2A28",
};
```

80% do texto em primary/secondary/dim. Accent com restrição. Formatters obrigatórios: `pad`, `rpad`, `fmtTime`, `truncate`.

### types.ts: discriminated union

```ts
export type UIMessage =
  | { kind: "logo" }
  | { kind: "greeting"; text: string }
  | { kind: "user"; text: string }
  | { kind: "assistant"; text: string }
  | { kind: "tool_call"; name: string; status: "pending" | "done" | "error"; summary?: string }
  | { kind: "system"; text: string; variant: "info" | "warn" | "error" }
  | { kind: "result"; title: string; body: string };

export type AgentState = "idle" | "thinking" | "streaming" | "tool";
```

Nunca `{ role: string; text: string }` genérico: union tipada permite exhaustive switch.

### Gotchas de layout Ink (custam horas se ignorados)

- Mensagens finalizadas vão pro array `past[]` dentro de `<Static>`; a streaming fica FORA, renderizada com cursor pulsante `▌`.
- **Indent por string** (`"  "` nível 1, `"    "` nível 2). `paddingLeft` é inconsistente dentro de `<Static>`.
- **Linha vazia do LLM** (`\n\n`) renderiza como `<Text>{" "}</Text>`. Ink colapsa `<Box>` vazio pra altura 0 e os parágrafos colam.
- `flexShrink={0}` em todo bloco de mensagem (terminal pequeno esmaga conteúdo sem isso). `width="100%"` explícito.
- `borderStyle="round"` (`╭─╮`); bordas pesadas glitcham.
- Root com `paddingX={2}`. Greeting é componente Ink com `<Box marginBottom={1}>` entre seções, nunca string com `\n`.
- Keys explícitas e estáveis em `<Static items>`.
- Tick interval de 500ms quando busy pra re-render de elapsed/ETA sem mutar state de negócio.

### input-box.tsx

- Cursor visual (bloco invertido com `backgroundColor={accent}`), setas navegam, Ctrl+A/Ctrl+E, backspace na posição.
- Disabled state quando o agente responde ("respondendo…" em dim).
- Callbacks, não `useInput` global: `onCtrlC`, `onEsc`, `onArrow`, `onTab`. O InputBox é o ÚNICO componente com `useInput`.
- `onChange("")` + `setCursor(0)` dentro do submit handler.

### status-bar.tsx

```
  sonnet · ⠹ categorizando · 3s · esc cancela · v0.1.0
  sonnet · ● pronto · v0.1.0
```

Spinner Braille 80ms (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`), elapsed timer 500ms quando busy, activity label humana via mapa `TOOL_ACTIVITY`, "esc cancela" só quando busy. Estados: idle = ● verde, thinking/streaming = spinner accent, tool = spinner warning.

### markdown.tsx

Tokenizer, nunca `.replace()` chains: acha o match mais próximo entre bold, code, link, italic; emite plain antes; emite token tipado; continua do fim do match. Fallback obrigatório: parsear tabela markdown (`^\s*\|.+\|\s*$`) e converter pra bloco alinhado sem pipes, porque o LLM às vezes gera tabela mesmo instruído a não gerar.

## App root: padrões obrigatórios

```ts
const [past, setPast] = useState<UIMessage[]>([]);
const [streaming, setStreaming] = useState("");
const [agentState, setAgentState] = useState<AgentState>("idle");
const hist = useRef<Message[]>([]);                    // limitado a ~15 turns
const abortRef = useRef<AbortController | null>(null);
```

- `onSubmit` delega pra `processInput`; NUNCA chama a si mesmo (stack overflow com slash suggester).
- Terminal resize: listener em `stdout.on("resize")` com cleanup.
- Working memory: histórico truncado a 15 turns (30 mensagens).

## Abort/cancellation

```ts
const ctrl = new AbortController();
abortRef.current = ctrl;
try {
  const res = await runTurn({ signal: ctrl.signal }); // signal propagado às tools
} catch (e) {
  if (ctrl.signal.aborted) {
    push({ kind: "system", text: "Cancelado.", variant: "warn" });
    return; // não é erro
  }
  throw e;
} finally {
  setAgentState("idle");
  abortRef.current = null; // previne double-abort
}
```

Flag `cancelled` previne callbacks zombie. Checar `signal.aborted` em todo ponto async dentro de tools. Tool limpa estado parcial no abort (ex: sessão marcada "interrupted").

## Error classification

```ts
type ErrorKind = "network" | "auth" | "quota" | "internal" | "unknown";

const PATTERNS = [
  { kind: "auth",    match: /401|403|unauthorized/i,          human: "Credencial inválida ou expirada." },
  { kind: "quota",   match: /429|rate.?limit|quota/i,          human: "Limite de requests atingido. Espera um pouco." },
  { kind: "network", match: /ECONNRESET|ETIMEDOUT|fetch failed/i, human: "Erro de rede. Provavelmente transitório." },
] as const;
```

Erro nunca vai raw pro user. Pipeline e tool dispatch com catch global que converte pra mensagem humana truncada. Stack trace no terminal é bug.

## DispatchContext: DI pra tools

```ts
interface DispatchContext {
  config: CliConfig;
  cache: Database;
  abortSignal?: AbortSignal;
  onProgress?: (event: ProgressEvent) => void;
}
```

Tools nunca acessam globals. Testável (mock context), cancelável (signal propagado).

## Tool call UX

Toda tool call na UI tem: glifo de status (`▸` running, `✓` ok, `✕` erro), nome humano via `TOOL_LABELS`, args humanizados, duração (`145ms` ou `2.3s`), result summary de 1 linha com `↳` (ex: `↳ 127 transações · 8.543,21`).

## Padrão visual

Dado estruturado = block visual alinhado, nunca bullet markdown solto. Colunas com largura fixa (`pad`/`rpad`). Bars `█░` pra proporção, sparklines `▁▂▃▄▅▆▇█` pra série temporal. Tabelas com pipes banidas.

Glifos com cor semântica: `★` destaque (accent), `✓` sucesso, `⚠` alerta (danger), `●` ativo (warning), `○` pendente (dim), `↳` subitem (dim), `›` prompt do user (accent), `▌` cursor streaming.

System prompt do agente inclui bloco de formatação: proibir tabela com pipes, proibir `---` como separador, headers no máximo `###`, na língua do usuário, com acentuação correta, datas dd/MM/yyyy, sem jargão técnico (`API`, `JSON`, `null`) no output ao user.

## Structured JSON logging

```ts
// ~/.<nome>/logs/app-YYYY-MM-DD.log · uma linha JSON por evento
function log(level: string, event: string, meta?: Record<string, unknown>) {
  const entry = { ts: new Date().toISOString(), level, event, ...meta };
  try { appendFileSync(logPath, JSON.stringify(entry) + "\n"); } catch {}
}
```

Safe append (nunca crasha o app), throttle de eventos frequentes (max 1/5s pra progress), rotação por 10MB ou dia, chmod 600.

## Dados sagrados no CLI

- **Idempotência**: import com hash SHA-256; re-import do mesmo dado é no-op.
- **Migrations versionadas**: schema mudou = migration explícita, idempotente, roll-forward sem destruir dado.
- **Confirmação destrutiva**: DELETE em massa, DROP, sobrescrever dado importante = confirmação. Flag `--force` que apaga dado exige `--yes` OU prompt "digite 'sim'"; typo executado por engano não pode destruir trabalho.
- **First-run testado de verdade**: `HOME=/tmp/scratch <comando>` valida criação de diretórios (0700), init do DB, config 0600.

## Aprendizado persistente

- Decisão manual do user vira regra permanente: `source='manual'` com `confidence=1.0` sobrescreve LLM, sempre.
- Memórias contextuais (fatos, preferências, metas) consultadas antes de responder: contexto enriquecido sem custo recorrente.
- Padrões detectados são sugeridos; user marca expected/ignored.

## Operation overlay (tarefas > 2s)

Dois modos do mesmo state: full overlay (progress detalhado, arquivos ativos, erros, ETA) e mini-banner de 1 linha (% + throughput + ETA). Toggle via `m`/`Esc`. State é reducer puro (`applyEvent(state, event)`), UI é view. Throughput inclui bytes in-flight, não só completados.
