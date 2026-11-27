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

import ast
import json
import os
import re
import shlex
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orbit_log

Verdict = tuple[str, str]

TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
PROTECTED = {"/", "/Users", "/System", "/Applications", "/Library", "/usr", "/bin", "/etc", "/opt", "/private", "/var", "/Volumes"}
SHELLS = {"bash", "sh", "zsh", "dash", "fish", "ksh"}
SQL_CLIENTS = {"psql", "sqlite3", "mysql", "mariadb", "duckdb", "pgcli", "litecli", "clickhouse-client"}
WRAPPERS_NO_ARG = {"command", "exec", "nohup", "time", "builtin"}
SHELL_KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "{", "!"}
WRAPPER_ARG_FLAGS = {"nice": {"-n"}, "caffeinate": {"-t", "-w"}, "ionice": {"-c", "-n"}, "stdbuf": {"-i", "-o", "-e"}}
RUNNERS = {"npx": 1, "bunx": 1, "pnpx": 1, "uvx": 1, "pnpm": 2, "yarn": 2, "npm": 2, "bun": 2}
SUDO_ARG_FLAGS = {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U"}
XARGS_ARG_FLAGS = {"-I", "-n", "-P", "-L", "-d", "-s", "-E", "-a", "-J", "-R", "-S"}
GIT_ARG_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
RISKY_WORDS = re.compile(r"\b(rm|reset|clean|push|drop|truncate|delete|prune|down|mkfs|dd|diskutil|restore|checkout)\b", re.IGNORECASE)
DESTRUCTIVE_CODE = re.compile(r"rmtree|os\.remove|os\.unlink|unlinkSync|rmSync|rm_rf|FileUtils\.rm|\bdrop\s+table\b|\btruncate\b|delete\s+from", re.IGNORECASE)
PY_DELETERS = {"rmtree", "unlink", "rmdir", "removedirs", "truncate"}
PY_RUNNERS = {"system", "popen", "run", "call", "check_call", "check_output", "Popen"}
PY_SQL = re.compile(r"exec|sql|query", re.IGNORECASE)
GLOB_OR_VAR = re.compile(r"[*?\[\]$`]")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`|<\(([^()]*)\)")
MAX_DEPTH = 4
PROTECTED_BRANCHES = {"main", "master"}
ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
# Pasta que a ferramenta regenera sozinha: apagar nunca perde dado. dist/ e build/ ficam de fora (podem ter entregável).
REGENERABLE = {"node_modules", ".build", "DerivedData", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next", ".turbo", ".parcel-cache", ".cache"}
VOLATILE_ROOTS = ("/private/tmp/", "/private/var/folders/")




def resolve(path: str, cwd: Path) -> str:
    expanded = os.path.expanduser(os.path.expandvars(path))
    return os.path.realpath(expanded if os.path.isabs(expanded) else cwd / expanded)


TEMP_VARS: set[str] = set()
MKTEMP_ASSIGN = re.compile(r"\b([A-Za-z_]\w*)=\$\(\s*mktemp\b[^)]*\)")


def is_temp_var(path: str) -> bool:
    """`rm -rf $X` onde X=$(mktemp ...) no mesmo comando é limpeza de pasta temporária criada ali."""
    match = re.fullmatch(r"\$\{?([A-Za-z_]\w*)\}?(/.*)?", path)
    if match is None:
        return False
    return match.group(1) in TEMP_VARS and ".." not in (match.group(2) or "")


KNOWN_VARS: dict[str, str] = {}
# `$X:h`, `$X[1]` e `$X(:h)` são modificadores do zsh que trocam o caminho (pai, elemento): ficam sem resolver.
VAR_REF = re.compile(r"(?:\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*))(?![\w:\[(])")
DECLARATORS = {"export", "local", "readonly"}
BLOCK_OPENERS = {"if", "while", "until", "for", "case", "select"}
BLOCK_CLOSERS = {"fi", "done", "esac"}
RELOADS_VARS = re.compile(r"(?:^|[;&|\n(])\s*(?:source|eval|\.)\s")


def block_state(tokens: list[str], blocks: int, parens: int) -> tuple[int, int, bool]:
    """Acompanha if/laço/case/função e subshell. Devolve os níveis depois do segmento e se ele roda dentro de um.

    Atribuição dentro de bloco pode não ter rodado (condição falsa, função nunca chamada) ou não valer
    fora dele (subshell), então nunca serve para liberar um rm.
    """
    opened = closed = 0
    for token in tokens:
        if token in BLOCK_OPENERS:
            opened += 1
        elif token in BLOCK_CLOSERS:
            closed += 1
        elif token not in SHELL_KEYWORDS and token != "}":
            break
    opened += tokens.count("{")
    closed += tokens.count("}")
    paren_open = 1 if tokens[0].startswith("(") and not tokens[0].startswith("((") else 0
    paren_close = sum(1 for token in tokens if token.endswith(")") and "(" not in token.lstrip("("))
    inside = blocks + opened > 0 or parens + paren_open > 0
    return max(0, blocks + opened - closed), max(0, parens + paren_open - paren_close), inside


def expand_known(path: str) -> str:
    """Troca `$X` pelo caminho literal que o próprio comando atribuiu a X; o resto fica como veio."""
    return VAR_REF.sub(lambda m: KNOWN_VARS.get(m.group(1) or m.group(2), m.group(0)), path)


def track_assignments(tokens: list[str], unconditional: bool, command: str) -> bool:
    """Registra `X=/caminho/literal` para o rm seguinte ser julgado pelo caminho real, não por `$X`.

    Só vale atribuição que com certeza rodou e é a única do comando: segmento só de atribuições, fora
    de bloco e de subshell, sem `||` nem `&&` vindo de algo que pode falhar, nome não reatribuído nem
    alvo de for/read/unset, e sem source/eval no comando.
    Na dúvida a variável fica desconhecida e o rm pede confirmação. Devolve se o segmento é puro.
    """
    names = tokens[1:] if tokens and tokens[0] in DECLARATORS else tokens
    if not names or not all(ASSIGNMENT.match(token) for token in names):
        return False
    reloads = RELOADS_VARS.search(command) is not None  # source/eval podem reatribuir qualquer nome
    for token in names:
        name, value = token.split("=", 1)
        KNOWN_VARS.pop(name, None)
        if not unconditional or reloads or len(re.findall(rf"(?<![\w$]){name}\+?=", command)) != 1:
            continue
        if re.search(rf"\b(for|select)\s+{name}\b|\b(read|unset|getopts|printf|mapfile|readarray|let)\b[^;&|\n]*\b{name}\b", command):
            continue
        if "$" in value and re.search(rf"(?<![\w$]){name}=[^\s;&|]*'", command):
            continue
        value = expand_known(value)
        # Valor com espaço se divide em vários alvos quando usado sem aspas: não dá para julgar como um caminho.
        if value and not GLOB_OR_VAR.search(value) and not re.search(r"\s", value):
            KNOWN_VARS[name] = value
    return True


def is_disposable(path: str, cwd: Path) -> bool:
    if is_temp_var(path):
        return True
    if GLOB_OR_VAR.search(os.path.expanduser(path).replace("$HOME", "").replace("${HOME}", "")):
        return False
    if re.search(r"\{[^}]*(,|\.\.)[^}]*\}", path):
        return False  # expansão de chaves vira vários caminhos que o realpath não enxerga
    resolved = resolve(path, cwd)  # realpath: symlink já existente é julgado pelo destino real
    if resolved.startswith("/private/tmp/claude-"):
        # /private/tmp/claude-<uid>/<projeto> guarda o scratchpad de todas as sessões: só abaixo dele é descartável.
        return resolved.count("/") >= 5
    tmpdir = os.path.realpath(os.environ.get("TMPDIR", "") or "/private/tmp")
    if resolved.startswith(tmpdir.rstrip("/") + "/") or resolved.startswith(VOLATILE_ROOTS):
        return resolved.count("/") >= 3  # subpasta de pasta volátil, nunca a raiz dela
    return Path(resolved).name in REGENERABLE and ".." not in path


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
        if tokens[0].startswith("(") and not tokens[0].startswith("(("):
            # Subshell `( cmd )`: o comando de dentro é analisado como qualquer outro.
            inner = [tokens[0].lstrip("("), *tokens[1:]]
            inner[-1] = inner[-1].rstrip(")")
            tokens = [token for token in inner if token]
            continue
        head = Path(tokens[0]).name
        if ASSIGNMENT.match(tokens[0]) or tokens[0] in SHELL_KEYWORDS:
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
    targets = [expand_known(a) for a in args if not a.startswith("-")]
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


RANGE_WHERE = re.compile(r"<|>|\bbetween\b|\blike\b|\bglob\b|\b(date|datetime|julianday|strftime|now)\s*\(|\binterval\b|current_(date|timestamp)", re.IGNORECASE)


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
        if RANGE_WHERE.search(tail):
            return "ask", "DELETE por faixa ou padrão (data, <, >, BETWEEN, LIKE): rode SELECT com o mesmo WHERE antes; dado de teste sai por id exato"
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
            texts.append(Path(resolve(expand_known(name), cwd)).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return "ask", f"script SQL não legível para análise: {name}"
    for text in texts:
        verdict = check_sql(text)
        if verdict:
            return verdict
    return None


def literal_text(node: ast.expr) -> str | None:
    """Texto de um argumento literal; trecho interpolado de f-string vira `x`, lista vira linha de comando."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "x" for part in node.values)
    if isinstance(node, (ast.List, ast.Tuple)):
        parts = [literal_text(item) for item in node.elts]
        return shlex.join(part if part is not None else "$x" for part in parts)
    return None


def check_python(code: str, cwd: Path, depth: int) -> Verdict | None:
    """Julga o que o Python executa, não o texto que ele carrega: string que edita arquivo não é comando."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # escape inválido no código analisado não é assunto do guard
            tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return ("ask", "código Python não analisável com termo destrutivo") if DESTRUCTIVE_CODE.search(code) else None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        # `x.remove(...)` de lista não apaga arquivo; `os.remove(...)` e `remove(...)` importado apagam.
        os_remove = name == "remove" and (isinstance(func, ast.Name) or (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os"))
        if name in PY_DELETERS or os_remove:
            return "ask", f"código Python apagando arquivo ou dado ({name})"
        texts = [text for text in (literal_text(arg) for arg in node.args) if text]
        for text in texts:
            verdict = None
            if depth >= MAX_DEPTH:
                verdict = ("ask", "código aninhado demais") if name in PY_RUNNERS | {"exec", "eval"} else None
            elif name in {"exec", "eval"}:
                verdict = check_python(text, cwd, depth + 1)
            elif name in PY_RUNNERS:
                verdict = decide(text, cwd, depth + 1)
            elif PY_SQL.search(name):
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
    if program in {"python", "python3"} and "-c" in args[:-1]:
        return check_python(args[args.index("-c") + 1], cwd, depth)
    if program in {"node", "ruby", "perl", "deno", "bun"} and any(a in {"-c", "-e", "--eval"} for a in args):
        code = " ".join(args)
        if DESTRUCTIVE_CODE.search(code):
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


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n(.*?)\n\s*\2\b", re.DOTALL)
READS_SHELL = re.compile(r"\b(bash|sh|zsh|dash|ksh|eval)\b")
PIPES_TO_SHELL = re.compile(r"\|\s*(bash|sh|zsh)\b")
READS_PYTHON = re.compile(r"\bpython3?\b")
PIPES_TO_PYTHON = re.compile(r"\|\s*python3?\b")
READS_CODE = re.compile(r"\b(node|ruby|perl)\b")


def strip_heredocs(command: str) -> tuple[str, list[tuple[str, str]]]:
    """Corpo de heredoc é dado, não comando: sai do texto e volta com quem o lê (shell, python, code)."""
    bodies: list[tuple[str, str]] = []

    def keep(match: re.Match[str]) -> str:
        reader = re.split(r"[|;&\n]", command[: match.start()])[-1]
        if READS_SHELL.search(reader) or PIPES_TO_SHELL.search(match.group(3)):
            kind = "shell"
        elif READS_PYTHON.search(reader) or PIPES_TO_PYTHON.search(match.group(3)):
            kind = "python"
        else:
            kind = "code" if READS_CODE.search(reader) else "data"
        bodies.append((kind, match.group(4)))
        return f"<<HEREDOC{match.group(3)}"

    return HEREDOC.sub(keep, command), bodies


def decide(command: str, cwd: Path, depth: int = 0) -> Verdict | None:
    if depth == 0:
        TEMP_VARS.clear()
        TEMP_VARS.update(MKTEMP_ASSIGN.findall(command))
        KNOWN_VARS.clear()
    command = command.replace("\\\n", " ")
    command, bodies = strip_heredocs(command)
    verdicts: list[Verdict] = []
    # Cada heredoc é julgado por quem o lê: shell passa pela análise inteira, Python pela árvore do
    # código, node/ruby/perl por chamada destrutiva conhecida. Texto gravado em arquivo é só dado.
    for kind, body in bodies:
        verdict = None
        if kind == "shell" and depth < MAX_DEPTH:
            verdict = decide(body, cwd, depth + 1)
        elif kind == "python":
            verdict = check_python(body, cwd, depth)
        elif kind == "code" and DESTRUCTIVE_CODE.search(body):
            verdict = ("ask", "código em heredoc apagando arquivo ou dado")
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
        verdict = check_sql("\n".join(body for _, body in bodies))
        if verdict:
            verdicts.append(verdict)
    # Só ln e mv fazem um caminho temporário passar a apontar para dado real; cp e rsync copiam, não movem.
    relinks = any(Path(strip_wrappers(t, cwd)[0][0]).name in {"ln", "mv"} for t, _, _ in parsed if strip_wrappers(t, cwd)[0])
    created: set[str] = set()
    verified: set[tuple[str, str]] = set()
    effective_cwd = cwd
    chain_certain = True
    blocks = parens = 0
    for tokens, before, after in parsed:
        if depth == 0:
            blocks, parens, inside = block_state(tokens, blocks, parens)
            # Certo de ter rodado: fora de bloco, no começo, depois de `;`, ou `&&` numa cadeia só de atribuições.
            certain = not inside and (before in {"", ";"} or (before == "&&" and chain_certain))
            chain_certain = track_assignments(tokens, certain and after in {"", ";", "&&"}, command) and certain
        stripped, _ = strip_wrappers(tokens, effective_cwd)
        if stripped and stripped[0] == "cd":
            # cd dentro de pipeline roda num subshell e não muda o diretório dos próximos comandos.
            if "|" not in (before, after):
                effective_cwd = Path(resolve(expand_known(stripped[1]) if len(stripped) > 1 else str(Path.home()), effective_cwd))
            continue
        program = Path(stripped[0]).name if stripped else ""
        plain = [expand_known(a) for a in stripped[1:] if not a.startswith("-")]
        literal = bool(plain) and not any(GLOB_OR_VAR.search(a) or re.search(r"\{.*[,.].*\}", a) for a in plain)
        if program in {"cp", "install"} and literal and len(plain) >= 2 and "-t" not in stripped:
            # Destino que ainda não existe nasce neste comando e o original fica intacto.
            dest = resolve(plain[-1], effective_cwd)
            if not os.path.lexists(dest):
                created.add(dest)
        if program == "cmp" and literal and len(plain) == 2 and after == "&&":
            # `cmp A B && rm A`: a outra cópia foi conferida byte a byte no mesmo comando.
            a, b = (resolve(x, effective_cwd) for x in plain)
            if a != b:
                verified.update({(a, b), (b, a)})
        if program == "rm" and literal:
            targets = {resolve(a, effective_cwd) for a in plain}
            kept = all(any(t == x and y not in targets for x, y in verified) for t in targets) and before == "&&"
            if targets <= created or kept:
                verified = {(x, y) for x, y in verified if x not in targets and y not in targets}
                continue  # apaga só a cópia que o comando criou, ou um original cuja cópia conferida fica
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
