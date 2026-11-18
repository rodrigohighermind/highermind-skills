#!/usr/bin/env python3
"""PreToolUse do HM Orbit: comando destrutivo pede confirmação; catastrófico é negado.

Lei de dados sagrados como barreira. É uma rede de segurança heurística para o caso comum, não um
sandbox: script opaco ou binário próprio não são analisáveis. O que o parser não entende e contém
termo arriscado vira `ask`; comando sem termo arriscado nunca é bloqueado.

  ask:  rm recursivo/forçado fora de pasta temporária da sessão, git reset --hard, git clean -f,
        git restore/checkout que descarta arquivo, push forçado ou --mirror, deletar branch,
        docker down -v, volume rm, prune amplo, find -delete, supabase db reset, shell lendo do
        stdin, e SQL destrutivo enviado a um executor (DROP, TRUNCATE, DELETE sem WHERE efetivo),
        inclusive via -f, --file=, redirecionamento ou heredoc.
  deny: rm em /, home, pasta de sistema ou raiz temporária, mkfs, dd em disco, diskutil erase.
  Push forçado ou delete remoto de main/master é `ask` com aviso forte (o CLAUDE.md pede confirmação,
  não proíbe). Write/Edit sobre .env, banco SQLite ou migration já existente também pede confirmação.
Analisa dentro de bash/sh -c (inclusive -lc), eval, xargs, env, sudo, timeout, $(...) e crase.
Desligar por sessão: HM_ORBIT_GUARD=off.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orbit_log

Verdict = tuple[str, str]

TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
PROTECTED = {"/", "/Users", "/System", "/Applications", "/Library", "/usr", "/bin", "/etc", "/opt", "/private", "/var", "/Volumes"}
SHELLS = {"bash", "sh", "zsh", "dash", "fish", "ksh"}
SQL_CLIENTS = {"psql", "sqlite3", "mysql", "mariadb", "duckdb", "pgcli", "litecli", "clickhouse-client"}
WRAPPERS_NO_ARG = {"command", "exec", "nohup", "time", "builtin"}
WRAPPER_ARG_FLAGS = {"nice": {"-n"}, "caffeinate": {"-t", "-w"}, "ionice": {"-c", "-n"}, "stdbuf": {"-i", "-o", "-e"}}
RUNNERS = {"npx": 1, "bunx": 1, "pnpx": 1, "uvx": 1, "pnpm": 2, "yarn": 2, "npm": 2, "bun": 2}
SUDO_ARG_FLAGS = {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U"}
XARGS_ARG_FLAGS = {"-I", "-n", "-P", "-L", "-d", "-s", "-E", "-a", "-J", "-R", "-S"}
GIT_ARG_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
RISKY_WORDS = re.compile(r"\b(rm|reset|clean|push|drop|truncate|delete|prune|down|mkfs|dd|diskutil|restore|checkout)\b", re.IGNORECASE)
GLOB_OR_VAR = re.compile(r"[*?\[\]$`]")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`|<\(([^()]*)\)")
MAX_DEPTH = 4
PROTECTED_BRANCHES = {"main", "master"}
ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")




def resolve(path: str, cwd: Path) -> str:
    expanded = os.path.expanduser(os.path.expandvars(path))
    return os.path.realpath(expanded if os.path.isabs(expanded) else cwd / expanded)


def is_disposable(path: str, cwd: Path) -> bool:
    if GLOB_OR_VAR.search(os.path.expanduser(path).replace("$HOME", "").replace("${HOME}", "")):
        return False
    resolved = resolve(path, cwd)
    tmpdir = os.environ.get("TMPDIR", "")
    if tmpdir and resolved.startswith(os.path.realpath(tmpdir).rstrip("/") + "/"):
        return True
    return resolved.startswith("/private/tmp/claude-") and resolved.count("/") >= 4


def is_catastrophic_target(path: str, cwd: Path) -> bool:
    if path in {"~", "~/", "$HOME", "${HOME}", "/*", "~/*", "$HOME/*"}:
        return True
    base = path.rstrip("*").rstrip("/") or "/"
    for candidate in {path, base}:
        resolved = resolve(candidate, cwd)
        if resolved in PROTECTED or resolved == str(Path.home()) or resolved in TEMP_ROOTS:
            return candidate == path or path.endswith("*")
    return False


def strip_wrappers(tokens: list[str], cwd: Path) -> tuple[list[str], Path]:
    while tokens:
        head = Path(tokens[0]).name
        if ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        elif head == "env":
            tokens = tokens[1:]
            while tokens and (tokens[0].startswith("-") or ASSIGNMENT.match(tokens[0])):
                if tokens[0] in {"-C", "--chdir"} and len(tokens) > 1:
                    cwd = Path(resolve(tokens[1], cwd))
                    tokens = tokens[2:]
                elif tokens[0] in {"-S", "--split-string"} and len(tokens) > 1:
                    tokens = shlex.split(tokens[1]) + tokens[2:]
                elif tokens[0].startswith("--chdir="):
                    cwd = Path(resolve(tokens[0].split("=", 1)[1], cwd))
                    tokens = tokens[1:]
                else:
                    tokens = tokens[2:] if tokens[0] == "-u" else tokens[1:]
        elif head in {"sudo", "doas"}:
            tokens = tokens[1:]
            while tokens and tokens[0].startswith("-"):
                tokens = tokens[2:] if tokens[0] in SUDO_ARG_FLAGS else tokens[1:]
        elif head in WRAPPERS_NO_ARG:
            tokens = tokens[1:]
        elif head in WRAPPER_ARG_FLAGS:
            tokens = tokens[1:]
            while tokens and tokens[0].startswith("-"):
                tokens = tokens[2:] if tokens[0] in WRAPPER_ARG_FLAGS[head] else tokens[1:]
        elif head in RUNNERS and len(tokens) > 1:
            rest = tokens[1:]
            if RUNNERS[head] == 2:
                if rest[0] not in {"dlx", "exec", "x", "run"}:
                    return tokens, cwd
                rest = rest[1:]
            while rest and rest[0].startswith("-"):
                rest = rest[1:]
            tokens = rest
        elif head in {"timeout", "gtimeout"}:
            tokens = tokens[1:]
            while tokens and tokens[0].startswith("-"):
                tokens = tokens[2:] if tokens[0] in {"-k", "-s", "--kill-after", "--signal"} else tokens[1:]
            tokens = tokens[1:]
        else:
            return tokens, cwd
    return tokens, cwd


def check_rm(args: list[str], cwd: Path) -> Verdict | None:
    flags = "".join(a.lstrip("-") for a in args if a.startswith("-") and not a.startswith("--"))
    long_flags = {a for a in args if a.startswith("--")}
    if not (set(flags) & {"r", "R", "f"} or long_flags & {"--recursive", "--force"}):
        return None
    targets = [a for a in args if not a.startswith("-")]
    if any(is_catastrophic_target(t, cwd) for t in targets):
        return "deny", f"rm em alvo catastrófico: {' '.join(targets)}"
    outside = [t for t in targets if not is_disposable(t, cwd)]
    if outside:
        return "ask", f"rm recursivo/forçado fora da pasta temporária da sessão: {' '.join(outside)}. Outra cópia conferida?"
    return None


def git_subcommand(args: list[str]) -> list[str]:
    while args:
        head = args[0]
        if head in GIT_ARG_FLAGS:
            args = args[2:]
        elif re.match(r"^-[Cc].+", head) or re.match(r"^--(git-dir|work-tree|namespace|exec-path)=", head) or head in {"--no-pager", "--bare", "-P", "--paginate"}:
            args = args[1:]
        else:
            return args
    return args


def short_flags(args: list[str]) -> str:
    return "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))


def check_git(args: list[str]) -> Verdict | None:
    args = git_subcommand(args)
    if not args:
        return None
    sub, rest = args[0], args[1:]
    flags = short_flags(rest)
    if sub == "push":
        if "--dry-run" in rest or "n" in flags:
            return None
        positional = [a for a in rest if not a.startswith("-")]
        destinations = [spec.lstrip("+").split(":")[-1].removeprefix("refs/heads/") for spec in positional[1:]]
        deleting = "--delete" in rest or "d" in flags or any(a.startswith(":") for a in positional[1:])
        forced = "f" in flags or any(a.startswith("--force") for a in rest) or any(a.startswith("+") for a in positional[1:])
        if "--mirror" in rest:
            return "ask", "git push --mirror reescreve e apaga refs remotas"
        if (forced or deleting) and (set(destinations) & PROTECTED_BRANCHES or destinations in ([], ["HEAD"])):
            return "ask", "ATENÇÃO: push forçado ou delete remoto em branch publicada (main/master ou a atual)"
        if deleting:
            return "ask", f"deletar branch remota: {' '.join(destinations)}"
        if forced:
            return "ask", "push forçado reescreve histórico publicado"
    if sub == "reset" and "--hard" in rest:
        return "ask", "git reset --hard descarta trabalho não commitado"
    if sub == "clean" and ("f" in flags or "--force" in rest):
        return "ask", "git clean -f apaga arquivos não rastreados"
    if sub == "branch" and ("D" in flags or "--delete" in rest or "d" in flags):
        return "ask", "deletar branch local"
    if sub == "restore" and "--staged" not in rest and [a for a in rest if not a.startswith("-")]:
        return "ask", "git restore descarta alterações locais do arquivo"
    if sub == "checkout" and ("--" in rest or "." in rest or "f" in flags):
        return "ask", "git checkout descarta alterações locais"
    if sub == "stash" and rest[:1] in (["drop"], ["clear"]):
        return "ask", "git stash drop/clear apaga trabalho guardado"
    return None


SQL_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
SQL_LITERAL = re.compile(r"'(?:[^']|'')*'")
SQL_DROP = re.compile(r"\b(drop\s+(table|database|schema)|truncate)\b", re.IGNORECASE)
SQL_DELETE = re.compile(r"\bdelete\s+from\s+(only\s+)?[\w.\"]+(?P<tail>[^;]*)", re.IGNORECASE)
TRIVIAL_WHERE = re.compile(
    r"^where\s*\(*\s*(true|1\s*=\s*1)\s*\)*\s*(returning\b.*|or\b.*)?$|\bor\s*\(*\s*(true|1\s*=\s*1)\b",
    re.IGNORECASE | re.DOTALL,
)


def check_sql(sql: str) -> Verdict | None:
    clean = SQL_COMMENT.sub(" ", sql)
    trivial_literals = clean.replace("'1' = '1'", "1=1").replace("'1'='1'", "1=1")
    code = SQL_LITERAL.sub("''", trivial_literals)
    if SQL_DROP.search(code):
        return "ask", "SQL destrutivo (DROP/TRUNCATE). Backup feito?"
    for match in SQL_DELETE.finditer(code):
        tail = match.group("tail").strip()
        if not re.match(r"where\b", tail, re.IGNORECASE) or TRIVIAL_WHERE.search(tail):
            return "ask", "DELETE sem WHERE efetivo"
    return None


def check_sql_client(args: list[str], cwd: Path) -> Verdict | None:
    texts = [a for a in args if not a.startswith("-")]
    files = [args[i + 1] for i, a in enumerate(args[:-1]) if a in {"-f", "--file", "-init", "-i"}]
    files += [a.split("=", 1)[1] for a in args if a.startswith(("--file=", "-f="))]
    files += [a[1:] for a in args if a.startswith("<") and not a.startswith("<<") and len(a) > 1]
    files += [args[i + 1] for i, a in enumerate(args[:-1]) if a == "<"]
    texts = [t for t in texts if t not in files and t != "<"]
    texts += [a.split("=", 1)[1] for a in args if a.startswith("--command=")]
    for name in files:
        try:
            texts.append(Path(resolve(name, cwd)).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return "ask", f"script SQL não legível para análise: {name}"
    for text in texts:
        verdict = check_sql(text)
        if verdict:
            return verdict
    return None


def check_tokens(tokens: list[str], cwd: Path, depth: int) -> Verdict | None:
    tokens, cwd = strip_wrappers(tokens, cwd)
    if not tokens:
        return None
    program, args = Path(tokens[0]).name, tokens[1:]
    if program in SHELLS:
        cluster = next((i for i, a in enumerate(args) if re.match(r"^-[a-zA-Z]*c[a-zA-Z]*$", a)), None)
        if cluster is not None:
            script = next((a for a in args[cluster + 1 :] if not a.startswith("-")), None)
            if not script or depth >= MAX_DEPTH:
                return "ask", "shell -c não analisável"
            if re.fullmatch(r"\s*\$\{?\w+\}?\s*", script):
                return "ask", "shell -c executando conteúdo de variável, não analisável"
            return decide(script, cwd, depth + 1)
        if not [a for a in args if not a.startswith("-")]:
            return "ask", "shell executando comandos vindos do stdin (pipe), conteúdo não analisável"
        return None
    if program in {"python", "python3", "node", "ruby", "perl", "deno", "bun"} and any(a in {"-c", "-e", "--eval"} for a in args):
        code = " ".join(args)
        if re.search(r"rmtree|os\.remove|os\.unlink|unlinkSync|rmSync|rm_rf|FileUtils\.rm|\bdrop\s+table\b|\btruncate\b|delete\s+from", code, re.IGNORECASE):
            return "ask", f"código inline de {program} apagando arquivo ou dado"
        return None
    if program == "eval":
        return decide(" ".join(args), cwd, depth + 1) if depth < MAX_DEPTH else ("ask", "eval aninhado demais")
    if program == "xargs":
        rest = list(args)
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in XARGS_ARG_FLAGS else rest[1:]
        return check_tokens(rest, cwd, depth + 1) if rest and depth < MAX_DEPTH else None
    if program in {"mkfs", "newfs"} or program.startswith(("mkfs.", "newfs_")):
        return "deny", "formatar disco"
    if program == "dd" and any(re.match(r"of=/dev/(r?disk|sd|nvme|hd)", a) for a in args):
        return "deny", "dd sobre disco"
    if program == "diskutil" and args and re.match(r"(erase\w*|zeroDisk|secureErase|partitionDisk|reformat)", args[0], re.IGNORECASE):
        return "deny", "apagar disco"
    if program == "rm":
        return check_rm(args, cwd)
    if program == "git":
        return check_git(args)
    if program == "find" and ("-delete" in args or ("-exec" in args and "rm" in args)):
        return "ask", "find apagando em massa"
    if program in SQL_CLIENTS:
        return check_sql_client(args, cwd)
    joined = " ".join(args)
    if program in {"docker", "docker-compose", "podman"}:
        if re.search(r"\bdown\b", joined) and re.search(r"(^|\s)(-v|--volumes)\b", joined):
            return "ask", "derruba containers e apaga volumes (dados persistidos)"
        if re.search(r"\bvolume\s+(rm|prune)\b", joined):
            return "ask", "apaga volumes Docker"
        if re.search(r"\bsystem\s+prune\b", joined) and re.search(r"--volumes|(^|\s)-a\b|--all", joined):
            return "ask", "docker system prune amplo"
    if program == "supabase" and re.search(r"\bdb\s+reset\b", joined):
        return "ask", "supabase db reset apaga o banco"
    return None


def segments(command: str) -> list[tuple[list[str], str, str]]:
    """Comandos simples com o operador antes e depois, respeitando aspas."""
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    result: list[tuple[list[str], str, str]] = []
    current: list[str] = []
    before = ""
    for token in lexer:
        if token and set(token) <= set(";&|"):
            result.append((current, before, token))
            current, before = [], token
        else:
            current.append(token)
    result.append((current, before, ""))
    return [segment for segment in result if segment[0]]


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\s*\2\b", re.DOTALL)
FEEDS_INTERPRETER = re.compile(r"\b(bash|sh|zsh|dash|ksh|eval|python3?|node|ruby|perl)\b[^|;&\n]*<<|\|\s*(bash|sh|zsh)\b")


def strip_heredocs(command: str) -> tuple[str, list[str]]:
    """Corpo de heredoc é dado, não comando; separado para análise só quando alimenta shell ou SQL."""
    bodies: list[str] = []

    def keep(match: re.Match[str]) -> str:
        bodies.append(match.group(3))
        return "<<HEREDOC"

    return HEREDOC.sub(keep, command), bodies


def decide(command: str, cwd: Path, depth: int = 0) -> Verdict | None:
    command = command.replace("\\\n", " ")
    command, bodies = strip_heredocs(command)
    verdicts: list[Verdict] = []
    for body in bodies:
        if FEEDS_INTERPRETER.search(command) and depth < MAX_DEPTH:
            verdict = decide(body, cwd, depth + 1)
            if verdict:
                verdicts.append(verdict)
    for match in SUBSTITUTION.finditer(command):
        inner = next(group for group in match.groups() if group is not None)
        if depth < MAX_DEPTH:
            verdict = decide(inner, cwd, depth + 1)
            if verdict:
                verdicts.append(verdict)
    try:
        parsed = segments(command)
    except ValueError:
        return ("ask", "comando arriscado que não pôde ser analisado (quoting)") if RISKY_WORDS.search(command) else None
    if bodies and any(Path(strip_wrappers(tokens, cwd)[0][0]).name in SQL_CLIENTS for tokens, _, _ in parsed if strip_wrappers(tokens, cwd)[0]):
        verdict = check_sql("\n".join(bodies))
        if verdict:
            verdicts.append(verdict)
    relinks = any(Path(strip_wrappers(t, cwd)[0][0]).name in {"ln", "mv", "cp", "rsync"} for t, _, _ in parsed if strip_wrappers(t, cwd)[0])
    effective_cwd = cwd
    for tokens, before, after in parsed:
        stripped, _ = strip_wrappers(tokens, effective_cwd)
        if stripped and stripped[0] == "cd":
            # cd dentro de pipeline roda num subshell e não muda o diretório dos próximos comandos.
            if "|" not in (before, after):
                effective_cwd = Path(resolve(stripped[1] if len(stripped) > 1 else str(Path.home()), effective_cwd))
            continue
        verdict = check_tokens(tokens, effective_cwd, depth)
        if verdict is None and relinks and stripped and Path(stripped[0]).name == "rm" and re.search(r"(^|\s)-\w*[rRf]", " ".join(stripped)):
            verdict = ("ask", "rm recursivo no mesmo comando que ln/mv/cp: o alvo temporário pode apontar para dado real")
        if verdict:
            verdicts.append(verdict)
    denies = [v for v in verdicts if v[0] == "deny"]
    return denies[0] if denies else (verdicts[0] if verdicts else None)


def emit(decision: str, reason: str) -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"HM Orbit · dados sagrados: {reason}",
        }
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False))


def main() -> int:
    if os.environ.get("HM_ORBIT_GUARD", "").lower() == "off":
        return 0
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except ValueError:
        if RISKY_WORDS.search(raw):
            emit("ask", "payload do hook ilegível com termo arriscado")
        return 0
    if not isinstance(payload, dict):
        return 0
    started = time.monotonic()
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input")
    cwd = Path(str(payload.get("cwd") or os.getcwd()))
    if tool == "Skill" and isinstance(tool_input, dict):
        orbit_log.log({"ev": "skill", "name": str(tool_input.get("skill", tool_input.get("name", "")))[:60]})
        return 0
    subject = ""
    verdict: Verdict | None = None
    if tool in {"Write", "Edit", "MultiEdit"} and isinstance(tool_input, dict):
        subject = str(tool_input.get("file_path", ""))
        verdict = check_file_write(subject, cwd)
    elif tool == "Bash":
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str):
            return 0
        subject = command
        try:
            verdict = decide(command, cwd)
        except (ValueError, OSError, RecursionError, IndexError) as error:
            orbit_log.log({"ev": "error", "hook": "guard", "err": type(error).__name__})
            verdict = ("ask", f"guard não conseguiu analisar ({type(error).__name__})") if RISKY_WORDS.search(command) else None
    else:
        return 0
    ms = round((time.monotonic() - started) * 1000, 1)
    if verdict:
        orbit_log.log({"ev": verdict[0], "tool": tool, "reason": verdict[1][:120], "cmd": orbit_log.redact(subject), "ms": ms})
        emit(*verdict)
    else:
        orbit_log.log({"ev": "allow", "tool": tool, "ms": ms})
    return 0


def check_file_write(file_path: str, cwd: Path) -> Verdict | None:
    """Sobrescrever segredo, banco local ou migration já existente pede confirmação. Criar é livre."""
    if not file_path:
        return None
    path = Path(resolve(file_path, cwd))
    if not path.exists():
        return None
    if path.name == ".env" or path.name.startswith(".env.") and not path.name.endswith(".example"):
        return "ask", f"sobrescrever arquivo de segredos existente: {path.name}"
    if path.suffix in {".db", ".sqlite", ".sqlite3"}:
        return "ask", f"escrever direto sobre banco existente: {path.name}"
    if "/supabase/migrations/" in str(path) or "/migrations/" in str(path) and path.suffix == ".sql":
        return "ask", f"editar migration que já existe (talvez aplicada): {path.name}. Migration nova é o caminho"
    return None


if __name__ == "__main__":
    sys.exit(main())
