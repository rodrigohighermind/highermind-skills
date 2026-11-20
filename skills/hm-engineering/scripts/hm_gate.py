#!/usr/bin/env python3
"""Evidence-first baseline gate for heterogeneous repositories."""

from __future__ import annotations

import argparse
import json
import os
import platform
import plistlib
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

IGNORED_PARTS = {".git", "node_modules", ".next", "dist", "build", "coverage", ".venv", "vendor"}
SOURCE_SUFFIXES = {".c", ".cpp", ".go", ".java", ".js", ".jsx", ".kt", ".mjs", ".php", ".py", ".rb", ".rs", ".swift", ".ts", ".tsx"}
LLM_CLIENT_PATTERNS = (
    re.compile(r"\bnew\s+Anthropic\s*\("),
    re.compile(r"\bnew\s+OpenAI\s*\("),
    re.compile(r"\bAsyncAnthropic\s*\("),
)
LLM_KEY_PATTERN = re.compile(r"\b(?:ANTHROPIC|OPENAI)_API_KEY\b")
KEY_REMOVAL_PATTERNS = (
    re.compile(r"\b(?:os\.environ|env)\.pop\(\s*['\"](?:ANTHROPIC|OPENAI)_API_KEY['\"]"),
    # filtro de exclusão: {k: v for k, v in env.items() if k != "...KEY"} ou "not in (...KEY...)"
    re.compile(r"(?:!=|\bnot\s+in\b)\s*[\(\[\{]?\s*['\"](?:ANTHROPIC|OPENAI)_API_KEY['\"]"),
    re.compile(r"\bdel\s+\w+\[\s*['\"](?:ANTHROPIC|OPENAI)_API_KEY['\"]\s*\]"),
    re.compile(r"['\"](?:ANTHROPIC|OPENAI)_API_KEY['\"][^#\n]*\b(?:not\s+in|!=)\b"),
    re.compile(r"\b(?:unset|delete)\s+(?:process\.env\.)?(?:ANTHROPIC|OPENAI)_API_KEY\b"),
    re.compile(r"\bprocess\.env\.(?:ANTHROPIC|OPENAI)_API_KEY\s*=\s*(?:undefined|null)\b"),
)
QUALITY_ROLES = ("typecheck", "lint", "test", "smoke")
SOFTWARE_MARKERS = ("pyproject.toml", "setup.py", "requirements.txt", "Package.swift", "Cargo.toml", "go.mod", "deno.json", "Gemfile", "composer.json", "pom.xml", "build.gradle", "build.gradle.kts", "mix.exs", "Makefile")


def missing_quality_check(root: Path) -> Check:
    """Repo de software sem comandos de qualidade declarados não é 'não aplicável': é não verificado."""
    found = [marker for marker in SOFTWARE_MARKERS if (root / marker).exists() or any(root.glob(f"*/{marker}"))]
    if found:
        return Check(
            "quality commands",
            "NOT_VERIFIED",
            f"repo de software ({', '.join(found[:3])}) sem typecheck/lint/test/smoke declarados: criar hm-quality.json com os comandos reais",
        )
    return Check("quality commands", "NOT_APPLICABLE", "nenhum marcador de software e nenhum hm-quality.json/package.json")
TEST_ROOTS = {"test", "tests", "fixtures"}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    evidence: str
    duration_ms: int = 0


def run_process(command: list[str], root: Path, timeout: int = 20) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def run_command(command: list[str], root: Path, timeout: int) -> Check:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return Check(" ".join(command), "NOT_VERIFIED", f"comando ausente: {command[0]}")
    except subprocess.TimeoutExpired:
        duration = int((time.monotonic() - started) * 1000)
        return Check(" ".join(command), "FAIL", f"timeout após {timeout}s", duration)
    duration = int((time.monotonic() - started) * 1000)
    output = (result.stdout + "\n" + result.stderr).strip()
    tail = "\n".join(output.splitlines()[-12:]) if output else "sem output"
    return Check(" ".join(command), "PASS" if result.returncode == 0 else "FAIL", tail, duration)


def package_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        return "bun"
    return "npm"


def package_commands(root: Path) -> list[tuple[str, list[str]]]:
    package_path = root / "package.json"
    if not package_path.exists():
        return []
    package = json.loads(package_path.read_text(encoding="utf-8"))
    scripts = package.get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    manager = package_manager(root)
    commands: list[tuple[str, list[str]]] = []
    for role, candidates in (
        ("typecheck", ("typecheck", "type-check", "check-types")),
        ("lint", ("lint",)),
        ("test", ("test", "test:ci")),
        ("smoke", ("smoke", "test:smoke", "build")),
    ):
        script = next((candidate for candidate in candidates if candidate in scripts), None)
        if script is None:
            continue
        command = [manager, "run", script] if manager in {"npm", "bun"} else [manager, script]
        commands.append((role, command))
    return commands


def declared_commands(root: Path) -> list[tuple[str, list[str]]]:
    path = root / "hm-quality.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_commands = payload.get("commands", {})
    if not isinstance(raw_commands, dict):
        return []
    commands: list[tuple[str, list[str]]] = []
    for role in QUALITY_ROLES:
        raw = raw_commands.get(role)
        if not isinstance(raw, list) or not raw or not all(isinstance(item, str) and item for item in raw):
            continue
        commands.append((role, list(raw)))
    return commands


def project_commands(root: Path) -> list[tuple[str, list[str]]]:
    return declared_commands(root) or package_commands(root)


def git_base(root: Path, explicit_base: str | None = None) -> tuple[str | None, str]:
    inside = run_process(["git", "rev-parse", "--is-inside-work-tree"], root)
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != "true":
        return None, "diretório não está em um repositório git"
    if explicit_base:
        valid = run_process(["git", "rev-parse", "--verify", explicit_base], root)
        return (explicit_base, f"base explícita {explicit_base}") if valid and valid.returncode == 0 else (None, f"base inválida: {explicit_base}")

    upstream = run_process(["git", "rev-parse", "--verify", "@{upstream}"], root)
    head = run_process(["git", "rev-parse", "HEAD"], root)
    if upstream and upstream.returncode == 0 and head and head.returncode == 0:
        upstream_ref = upstream.stdout.strip()
        head_ref = head.stdout.strip()
        if upstream_ref != head_ref:
            merge_base = run_process(["git", "merge-base", "HEAD", "@{upstream}"], root)
            if merge_base and merge_base.returncode == 0:
                return merge_base.stdout.strip(), "merge-base com upstream"
    parent = run_process(["git", "rev-parse", "--verify", "HEAD^"], root)
    if parent and parent.returncode == 0:
        return parent.stdout.strip(), "commit anterior"
    return "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "árvore vazia"


def parse_added_lines(diff_text: str) -> list[tuple[str, int, str]]:
    current_file = ""
    new_line = 0
    added: list[tuple[str, int, str]] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            new_line = int(match.group(1)) if match else 0
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append((current_file, new_line, line[1:]))
            new_line += 1
        elif line.startswith("-"):
            continue
        elif current_file:
            new_line += 1
    return added


def is_test_only_path(relative: str) -> bool:
    parts = Path(relative).parts
    return bool(parts) and parts[0].lower() in TEST_ROOTS


def changed_added_lines(root: Path, explicit_base: str | None = None) -> tuple[list[tuple[str, int, str]], str | None]:
    base, reason = git_base(root, explicit_base)
    if base is None:
        return [], reason
    diff = run_process(["git", "diff", "--no-ext-diff", "--unified=0", base, "--"], root)
    if diff is None or diff.returncode not in {0, 1}:
        return [], "git diff não executou"
    added = [
        item
        for item in parse_added_lines(diff.stdout)
        if Path(item[0]).suffix.lower() in SOURCE_SUFFIXES
        and not is_test_only_path(item[0])
    ]

    untracked = run_process(["git", "ls-files", "--others", "--exclude-standard", "-z"], root)
    if untracked is None or untracked.returncode != 0:
        return [], "não foi possível enumerar arquivos untracked"
    for relative in (item for item in untracked.stdout.split("\0") if item):
        path = root / relative
        if (
            not path.is_file()
            or path.suffix.lower() not in SOURCE_SUFFIXES
            or is_test_only_path(relative)
        ):
            continue
        for line_number, text in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            added.append((relative, line_number, text))
    return added, f"{reason}; untracked incluídos"


def scan_changed_code(root: Path, explicit_base: str | None = None) -> list[Check]:
    added, error = changed_added_lines(root, explicit_base)
    if error and not added and error.startswith(("diretório", "base inválida", "git diff", "não foi possível")):
        return [
            Check("zero console.error novo", "NOT_VERIFIED", error),
            Check("zero TODO crítico novo", "NOT_VERIFIED", error),
        ]
    console_hits = [(path, line) for path, line, text in added if re.search(r"\bconsole\.error\s*\(", text)]
    todo_hits = [
        (path, line, text.strip())
        for path, line, text in added
        if re.search(r"(?:^|\s)(?:#|//|/\*|\*)\s*TODO\b", text, re.IGNORECASE)
    ]
    critical_todos = [hit for hit in todo_hits if re.search(r"critical|crítico|security|data loss|migration|billing", hit[2], re.IGNORECASE)]
    todo_status = "FAIL" if critical_todos else ("NOT_VERIFIED" if todo_hits else "PASS")
    todo_evidence = str(critical_todos or todo_hits) if todo_hits else f"nenhum desde {error}"
    return [
        Check("zero console.error novo", "FAIL" if console_hits else "PASS", str(console_hits) if console_hits else f"nenhum desde {error}"),
        Check("zero TODO crítico novo", todo_status, todo_evidence),
    ]


def sql_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.sql")
        if not any(part in IGNORED_PARTS for part in path.parts)
        and ("migration" in str(path).lower() or "supabase" in str(path).lower())
    )


def split_sql_statements(text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    dollar_tag: str | None = None
    line_comment = False
    block_comment = False
    index = 0
    while index < len(text):
        char = text[index]
        pair = text[index : index + 2]
        if line_comment:
            if char == "\n":
                line_comment = False
                current.append("\n")
            index += 1
            continue
        if block_comment:
            if pair == "*/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote:
            current.append(char)
            if char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    current.append(text[index + 1])
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if dollar_tag:
            if text.startswith(dollar_tag, index):
                current.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
            else:
                current.append(char)
                index += 1
            continue
        if pair == "--":
            line_comment = True
            index += 2
            continue
        if pair == "/*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            index += 1
            continue
        if char == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", text[index:])
            if match:
                dollar_tag = match.group(0)
                current.append(dollar_tag)
                index += len(dollar_tag)
                continue
        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def object_name(statement: str, kind: str) -> tuple[str | None, str] | None:
    if kind == "table":
        prefix = r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?"
    else:
        prefix = r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW"
    match = re.search(
        prefix + r'\s+(?:(?P<schema>"?[A-Za-z_][\w]*"?)\.)?(?P<name>"?[A-Za-z_][\w]*"?)',
        statement,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    schema = match.group("schema")
    return (schema.strip('"').lower() if schema else None, match.group("name").strip('"'))


def scan_rls(root: Path) -> Check:
    migrations = sql_files(root)
    if not migrations:
        return Check("audit RLS", "NOT_APPLICABLE", "nenhuma migration SQL encontrada")
    violations: list[str] = []
    for path in migrations:
        statements = split_sql_statements(path.read_text(encoding="utf-8", errors="replace"))
        public_tables = [name for statement in statements if (parsed := object_name(statement, "table")) is not None and (parsed[0] in {None, "public"}) for name in [parsed[1]]]
        for table in public_tables:
            target = rf'(?:public\.)?"?{re.escape(table)}"?'
            has_rls = any(re.search(rf"ALTER\s+TABLE\s+{target}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY\b", statement, re.IGNORECASE) for statement in statements)
            has_policy = any(re.search(rf"^\s*CREATE\s+POLICY\b[\s\S]*?\bON\s+{target}\b", statement, re.IGNORECASE) for statement in statements)
            if not has_rls or not has_policy:
                violations.append(f"{path.relative_to(root)}: tabela {table} sem RLS+policy na mesma migration")
        for statement in statements:
            parsed_view = object_name(statement, "view")
            if parsed_view is None or parsed_view[0] not in {None, "public"}:
                continue
            if not re.search(r"security_invoker\s*=\s*true", statement, re.IGNORECASE):
                violations.append(f"{path.relative_to(root)}: view {parsed_view[1]} sem security_invoker=true")
    return Check("audit RLS", "FAIL" if violations else "PASS", "\n".join(violations) if violations else "RLS estático sem violações")


def source_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES and not any(part in IGNORED_PARTS for part in path.parts))


KEY_LIST_DEFINITION = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*(?::[^=]+)?=\s*[\(\[\{][^#\n]*(?:ANTHROPIC|OPENAI)_API_KEY")


def key_removal_lists(text: str) -> set[str]:
    """Constantes com nomes de key que o arquivo usa para REMOVER do ambiente (filtro ou pop em laço)."""
    found: set[str] = set()
    for match in (KEY_LIST_DEFINITION.match(line) for line in text.splitlines()):
        if not match:
            continue
        name = re.escape(match.group(1))
        if re.search(rf"\bnot\s+in\s+{name}\b", text):
            found.add(match.group(1))
            continue
        for loop in re.finditer(rf"\bfor\s+(\w+)\s+in\s+[\(\[]?\*?{name}\b", text):
            var = re.escape(loop.group(1))
            if re.search(rf"\.pop\(\s*{var}\b|\bdel\s+\w+\[\s*{var}\s*\]", text[loop.end():loop.end() + 400]):
                found.add(match.group(1))
    return found


def scan_llm_api_cost(root: Path, distribution: str) -> Check:
    hits: list[str] = []
    test_hits: list[str] = []
    for path in source_files(root):
        relative = str(path.relative_to(root))
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        removal_lists = key_removal_lists(text)
        for line_number, line in enumerate(text.splitlines(), start=1):
            has_client = any(pattern.search(line) for pattern in LLM_CLIENT_PATTERNS)
            has_key = bool(LLM_KEY_PATTERN.search(line))
            list_definition = KEY_LIST_DEFINITION.match(line)
            explicit_removal = any(pattern.search(line) for pattern in KEY_REMOVAL_PATTERNS) or bool(list_definition and list_definition.group(1) in removal_lists)
            # Exceção declarada por linha, com motivo: key falsa usada para provar que a real não vaza.
            declared_sentinel = bool(re.search(r"hm-gate:\s*sentinel\s+\S.{3,}", line)) and not has_client
            if has_client or (has_key and not explicit_removal and not declared_sentinel):
                target = test_hits if is_test_only_path(relative) else hits
                target.append(f"{path.relative_to(root)}:{line_number}")
    if test_hits and not hits:
        return Check(
            "custo LLM pessoal",
            "NOT_VERIFIED",
            "client/env de API em teste ou fixture exige confirmação de que não faz chamada paga: " + ", ".join(test_hits),
        )
    if not hits:
        return Check("custo LLM pessoal", "PASS", "nenhum client/env de API paga detectado")
    if distribution == "personal":
        return Check("custo LLM pessoal", "FAIL", "API paga em ferramenta pessoal: " + ", ".join(hits))
    if distribution == "saas":
        return Check("custo LLM pessoal", "NOT_VERIFIED", "SaaS permite API, mas cost tracking exige revisão: " + ", ".join(hits))
    return Check("custo LLM pessoal", "NOT_VERIFIED", "classifique --distribution personal|saas: " + ", ".join(hits))


BUILD_VERSION = re.compile(r"cmd LC_BUILD_VERSION.*?minos (\d+)(?:\.\d+)*.*?sdk (\d+)(?:\.\d+)*", re.DOTALL)
SKIP_DIRS = {".git", "node_modules", ".venv", "Pods", "DerivedData"}


def parse_build_version(otool_output: str) -> tuple[int, int] | None:
    """(minos major, sdk major) do LC_BUILD_VERSION, ou None se o binário não tem o comando."""
    match = BUILD_VERSION.search(otool_output)
    return (int(match.group(1)), int(match.group(2))) if match else None


def sdk_verdict(sdk_major: int, system_major: int) -> str:
    """O macOS desenha o chrome conforme o SDK gravado: SDK anterior ao sistema = visual legado."""
    return "FAIL" if sdk_major < system_major else "PASS"


def swiftpm_release_binaries(root: Path) -> list[Path]:
    """Executáveis do build release do SwiftPM: o SDK gravado é o mesmo que o app instalado terá."""
    release = root / ".build" / "release"
    if not release.is_dir():
        return []
    return sorted(p for p in release.iterdir() if p.is_file() and not p.suffix and os.access(p, os.X_OK))[:5]


def macos_app_binaries(root: Path) -> list[Path]:
    declared: list[Path] = []
    quality = root / "hm-quality.json"
    if quality.exists():
        raw = json.loads(quality.read_text(encoding="utf-8")).get("macos_apps", [])
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, str) and item:
                path = Path(os.path.expanduser(item))
                path = path if path.is_absolute() else root / path
                declared.extend(sorted(p for p in (path / "Contents" / "MacOS").glob("*") if p.is_file()) if path.suffix == ".app" else [path])
    found: list[Path] = []
    for app in root.rglob("*.app"):
        if len(found) >= 10 or SKIP_DIRS.intersection(app.relative_to(root).parts):
            continue
        found.extend(p for p in (app / "Contents" / "MacOS").glob("*") if p.is_file())
    if not declared and not found and is_macos_ui_package(root):
        found.extend(swiftpm_release_binaries(root))
    return declared + found


def declared_missing(root: Path) -> list[str]:
    quality = root / "hm-quality.json"
    if not quality.exists():
        return []
    raw = json.loads(quality.read_text(encoding="utf-8")).get("macos_apps", [])
    items = [item for item in raw if isinstance(item, str) and item] if isinstance(raw, list) else []
    return [item for item in items if not (Path(os.path.expanduser(item)) if Path(os.path.expanduser(item)).is_absolute() else root / item).exists()]


def is_macos_ui_package(root: Path) -> bool:
    manifest = root / "Package.swift"
    if not manifest.exists() or ".macOS(" not in manifest.read_text(encoding="utf-8", errors="replace"):
        return False
    return any(
        re.search(r"^import (SwiftUI|AppKit)\b", source.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
        for source in list(root.rglob("*.swift"))[:400]
        if not SKIP_DIRS.intersection(source.relative_to(root).parts) and ".build" not in source.parts
    )


def scan_macos_sdk(root: Path) -> Check:
    binaries = macos_app_binaries(root)
    if not binaries:
        missing = declared_missing(root)
        if missing:
            return Check("SDK do app macOS", "NOT_VERIFIED", f"app declarado não encontrado ({', '.join(missing)}) e sem build release: rode o build ou o install")
        if is_macos_ui_package(root):
            return Check("SDK do app macOS", "NOT_VERIFIED", "app macOS com UI sem binário encontrado: declarar macos_apps no hm-quality.json")
        return Check("SDK do app macOS", "NOT_APPLICABLE", "nenhum app macOS")
    release = platform.mac_ver()[0]
    if not release:
        return Check("SDK do app macOS", "NOT_VERIFIED", "não é macOS: versão do sistema desconhecida")
    system_major = int(release.split(".")[0])
    problems: list[str] = []
    for binary in binaries:
        result = run_process(["otool", "-l", str(binary)], root)
        if result is None or result.returncode != 0:
            return Check("SDK do app macOS", "NOT_VERIFIED", f"otool indisponível ou falhou em {binary}")
        parsed = parse_build_version(result.stdout)
        if parsed is None:
            return Check("SDK do app macOS", "NOT_VERIFIED", f"sem LC_BUILD_VERSION em {binary}")
        if sdk_verdict(parsed[1], system_major) == "FAIL":
            problems.append(f"{binary.name}: sdk {parsed[1]} < macOS {system_major} (chrome legado)")
    if problems:
        return Check("SDK do app macOS", "FAIL", "; ".join(problems))
    return Check("SDK do app macOS", "PASS", f"{len(binaries)} binário(s) com sdk >= macOS {system_major}")


# Descrição de uso no Info.plist -> entitlement que a assinatura precisa ter. Com hardened runtime ou
# sandbox, o pedido de permissão sem o entitlement é negado sem janela e sem erro.
USAGE_ENTITLEMENTS = {
    "NSMicrophoneUsageDescription": "com.apple.security.device.audio-input",
    "NSCameraUsageDescription": "com.apple.security.device.camera",
    "NSCalendarsUsageDescription": "com.apple.security.personal-information.calendars",
    "NSCalendarsFullAccessUsageDescription": "com.apple.security.personal-information.calendars",
    "NSCalendarsWriteOnlyAccessUsageDescription": "com.apple.security.personal-information.calendars",
    "NSRemindersUsageDescription": "com.apple.security.personal-information.calendars",
    "NSRemindersFullAccessUsageDescription": "com.apple.security.personal-information.calendars",
    "NSContactsUsageDescription": "com.apple.security.personal-information.addressbook",
    "NSLocationUsageDescription": "com.apple.security.personal-information.location",
    "NSLocationWhenInUseUsageDescription": "com.apple.security.personal-information.location",
    "NSLocationAlwaysAndWhenInUseUsageDescription": "com.apple.security.personal-information.location",
    "NSPhotoLibraryUsageDescription": "com.apple.security.personal-information.photos-library",
    "NSHealthShareUsageDescription": "com.apple.developer.healthkit",
    "NSHealthUpdateUsageDescription": "com.apple.developer.healthkit",
}


def missing_entitlements(usage_keys: list[str], entitlements: dict[str, object], restricted: bool) -> list[str]:
    if not restricted:
        return []
    return sorted({f"{key} sem {USAGE_ENTITLEMENTS[key]}" for key in usage_keys if key in USAGE_ENTITLEMENTS and entitlements.get(USAGE_ENTITLEMENTS[key]) is not True})


def has_hardened_runtime(codesign_info: str) -> bool:
    """`flags=0x10000(runtime)` ou `flags=0x10002(adhoc,runtime)`: a flag vem numa lista."""
    match = re.search(r"flags=0x[0-9a-f]+\(([^)]*)\)", codesign_info)
    return bool(match) and "runtime" in match.group(1).split(",") if match else False


def read_signature(app: Path, root: Path) -> tuple[dict[str, object], bool] | None:
    """(entitlements, restrito por hardened runtime ou sandbox) da assinatura do .app."""
    ents = run_process(["codesign", "-d", "--entitlements", "-", "--xml", str(app)], root)
    info = run_process(["codesign", "-dv", str(app)], root)
    if ents is None or info is None or info.returncode != 0:
        return None
    raw = ents.stdout.encode()
    start = raw.find(b"<?xml")
    entitlements = plistlib.loads(raw[start:]) if start >= 0 else {}
    restricted = has_hardened_runtime(info.stderr) or entitlements.get("com.apple.security.app-sandbox") is True
    return (entitlements if isinstance(entitlements, dict) else {}), restricted


def scan_macos_entitlements(root: Path) -> Check:
    apps = sorted({p.parent.parent for p in macos_app_binaries(root) if p.parent.name == "MacOS" and p.parent.parent.name == "Contents"})
    if not apps:
        return Check("entitlements do app macOS", "NOT_APPLICABLE", "nenhum .app assinado para conferir")
    problems: list[str] = []
    for contents in apps:
        app = contents.parent
        plist = contents / "Info.plist"
        if not plist.exists():
            continue
        usage = [k for k in plistlib.loads(plist.read_bytes()) if k.endswith("UsageDescription")]
        signature = read_signature(app, root)
        if signature is None:
            return Check("entitlements do app macOS", "NOT_VERIFIED", f"codesign falhou em {app.name}")
        problems.extend(f"{app.name}: {item}" for item in missing_entitlements(usage, *signature))
    if problems:
        return Check("entitlements do app macOS", "FAIL", "permissão será negada sem janela: " + "; ".join(problems))
    return Check("entitlements do app macOS", "PASS", f"{len(apps)} app(s): toda descrição de uso tem o entitlement")


WEB_UI_SUFFIXES = {".tsx", ".jsx", ".vue", ".svelte"}  # .html solto costuma ser documento, não app
CSS_SUFFIXES = {".css", ".scss"}
CSS_POINTER_RULE = re.compile(r"[^{}]*\b(?:button|\[role=)[^{}]*\{[^}]*cursor:\s*pointer", re.IGNORECASE)
SWIFT_CLICKABLE = re.compile(r"\bButton\s*[\(\{]|\.onTapGesture\b|\bNSButton\b")
SWIFT_POINTER = re.compile(r"\bpointingHand\b|\bpointerStyle\([^)\n]*\.link")


def ui_files(root: Path, suffixes: set[str]) -> list[Path]:
    return [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
        and not any(part in IGNORED_PARTS or part in SKIP_DIRS or part == ".build" for part in path.relative_to(root).parts)
    ]


def scan_pointer_cursor(root: Path) -> Check:
    """Clicável mostra a mãozinha. Web: o navegador só a dá em link; botão, aba e item de menu precisam de regra global."""
    quality = root / "hm-quality.json"
    if quality.exists() and json.loads(quality.read_text(encoding="utf-8")).get("pointer_cursor") is False:
        return Check("cursor de clique", "NOT_APPLICABLE", "pointer_cursor: false em hm-quality.json")
    problems: list[str] = []
    applicable = False
    if ui_files(root, WEB_UI_SUFFIXES):
        applicable = True
        if not any(CSS_POINTER_RULE.search(css.read_text(encoding="utf-8", errors="replace")) for css in ui_files(root, CSS_SUFFIXES)):
            problems.append("web: falta regra global `button, [role=button], [role=tab], [role=menuitem] { cursor: pointer }` (o reset do Tailwind 4 tira a mãozinha do botão)")
    swift = [s for s in ui_files(root, {".swift"}) if re.search(r"^import (SwiftUI|AppKit)\b", s.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)]
    texts = [s.read_text(encoding="utf-8", errors="replace") for s in swift]
    if any(SWIFT_CLICKABLE.search(text) for text in texts):
        applicable = True
        if not any(SWIFT_POINTER.search(text) for text in texts):
            problems.append("macOS: nenhum clicável troca o cursor; aplicar no estilo base `.pointerStyle(.link)` (macOS 15+) ou NSCursor.pointingHand no hover")
    if not applicable:
        return Check("cursor de clique", "NOT_APPLICABLE", "sem interface clicável")
    return Check("cursor de clique", "FAIL" if problems else "PASS", "\n".join(problems) if problems else "regra de mãozinha presente")


def plan_checks(root: Path, base: str | None, distribution: str) -> list[Check]:
    commands = project_commands(root)
    checks = [Check(role, "NOT_VERIFIED", "planejado: " + " ".join(command)) for role, command in commands]
    if commands:
        present = {role for role, _ in commands}
        for required in ("typecheck", "lint", "smoke"):
            if required not in present:
                checks.append(Check(required, "NOT_VERIFIED", "comando não descoberto em hm-quality.json/package.json"))
    else:
        checks.append(missing_quality_check(root))
    checks.extend(scan_changed_code(root, base))
    checks.extend([scan_rls(root), scan_llm_api_cost(root, distribution), scan_macos_sdk(root), scan_macos_entitlements(root), scan_pointer_cursor(root)])
    return checks


def execute_checks(root: Path, timeout: int, base: str | None, distribution: str) -> list[Check]:
    checks: list[Check] = []
    commands = project_commands(root)
    if commands:
        by_role = {role: command for role, command in commands}
        for required in ("typecheck", "lint", "test", "smoke"):
            command = by_role.get(required)
            if command is None:
                if required in {"typecheck", "lint", "smoke"}:
                    checks.append(Check(required, "NOT_VERIFIED", "comando não descoberto em hm-quality.json/package.json"))
                continue
            result = run_command(command, root, timeout)
            checks.append(Check(required, result.status, result.evidence, result.duration_ms))
    else:
        checks.append(missing_quality_check(root))
    checks.extend(scan_changed_code(root, base))
    checks.extend([scan_rls(root), scan_llm_api_cost(root, distribution), scan_macos_sdk(root), scan_macos_entitlements(root)])
    return checks


def verdict(checks: list[Check]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "NOT_VERIFIED" for check in checks):
        return "NOT_VERIFIED"
    return "PASS"


def exit_code(result: str) -> int:
    return {"PASS": 0, "FAIL": 1, "NOT_VERIFIED": 2}.get(result, 2)


def render_markdown(root: Path, checks: list[Check]) -> str:
    lines = [f"VEREDICTO · {verdict(checks)}", f"ROOT · {root}", "", "EVIDÊNCIA"]
    lines.extend(f"- [{check.status}] {check.name}: {check.evidence}" for check in checks)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--plan", action="store_true", help="Apenas listar checks; default executa os comandos descobertos")
    parser.add_argument("--base", help="Ref git explícita para definir código novo")
    parser.add_argument("--distribution", choices=("unknown", "personal", "saas"), default="unknown")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    checks = plan_checks(root, args.base, args.distribution) if args.plan else execute_checks(root, args.timeout, args.base, args.distribution)
    result = verdict(checks)
    payload = {"verdict": result, "root": str(root), "checks": [asdict(check) for check in checks]}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else render_markdown(root, checks))
    return exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
