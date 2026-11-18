#!/usr/bin/env python3
"""Floor guard: falha quando o diff rebaixa a barra em vez de cumpri-la.

    python3 floor_guard.py --root <projeto>               desde o início da sessão (SHA em .git/orbit-base, gravado pelo hook)
    python3 floor_guard.py --root <projeto> --since <sha>  desde um SHA explícito
Sem base conhecida: NOT_VERIFIED (exit 2). Nunca troca "o trabalho feito" por "o último commit" em silêncio.

Compara a base com o estado final real (index + working tree + arquivos novos), num diff só.
Detecta: teste ou assert removido (inclusive arquivo de teste apagado) · assert trivializado ·
skip/only novo · supressão nova de lint/tipo/cobertura · threshold de qualidade afrouxado ou removido ·
secret com cara de credencial. É heurística: "nenhum rebaixamento detectado" não prova a barra.
Exceção legítima é por linha e por regra, com motivo: `floor-guard: allow <regra> <motivo>` (regras: skip,
supressao, assert). Secret nunca tem exceção.
Exit 0 nada detectado · 1 violação · 2 não rodou (nunca tratar como 0).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

EXIT_CLEAN, EXIT_VIOLATION, EXIT_NOT_RUN = 0, 1, 2
ALLOW = re.compile(r"floor-guard:\s*allow\s+(skip|supressao|assert)\s+\S.{3,}")
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".swift", ".rb", ".php", ".c", ".cpp", ".cs"}
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(_test|\.test|\.spec|test_)[^/]*$")
TEST_UNIT = re.compile(r"^\s*(async\s+)?def test_|\b(it|test|describe)\s*\(|^\s*func Test|#\[test\]")
TEST_NAME = re.compile(r"def (test_\w+)|\b(?:it|test|describe)\s*\(\s*['\"`]([^'\"`]+)|func (Test\w+)")
ASSERTION = re.compile(r"\bassert\b|\bexpect\s*\(|\.assert\w*\(|\bassert_eq!|t\.(Error|Fatal)")
TRIVIAL_ASSERT = re.compile(
    r"\bassert\s+(True|1)\s*(#.*)?$|\bassert\s+(?P<a>\w+)\s*==\s*(?P=a)\b|assertTrue\(\s*True\s*\)|assertEqual\(\s*(?P<b>\w+)\s*,\s*(?P=b)\s*\)|"
    r"expect\(\s*(true|1)\s*\)\.(toBe|toEqual)\(\s*(true|1)\s*\)|expect\(\s*(true|1)\s*\)\.toBeTruthy\(\)|assert!\(\s*true\s*\)"
)
SKIP = re.compile(
    r"\.(skip|only)\s*\(|\bx(it|describe|test)\s*\(|@pytest\.mark\.(skip|xfail)|@unittest\.skip|\bt\.Skip\(|#\[ignore\]|"
    r"\bpytest\.(skip|xfail)\(|\.skipTest\("
)
SUPPRESSION = re.compile(
    r"#\s*noqa|#\s*type:\s*ignore|@ts-(ignore|expect-error|nocheck)|eslint-disable|"  # floor-guard: allow supressao definição do próprio detector
    r"#\s*pragma:\s*no cover|//\s*nolint|#\[allow\(|@SuppressWarnings|biome-ignore"  # floor-guard: allow supressao definição do próprio detector
)
SECRET = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{20,}|\bsk-(proj-)?[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|"
    r"xox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJhbGciOi[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{30,}"
)
THRESHOLD = re.compile(
    r"\b(fail_under|fail-under|coverageThreshold|minimum_coverage|branches|statements|functions|lines|threshold)[^\w-]+(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
CONFIG_FILE = re.compile(r"(pyproject\.toml|setup\.cfg|\.coveragerc|package\.json|(jest|vitest|vite)\.config\.\w+|codecov\.yml|hm-quality\.json)$")


@dataclass
class FileDiff:
    path: str
    added: list[tuple[int, str]] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Violation:
    where: str
    rule: str
    snippet: str

    def __str__(self) -> str:
        return f"FLOOR · {self.where} · {self.rule} · {self.snippet.strip()[:120]}"


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def choose_base(root: Path, since: str | None) -> str:
    if since:
        return since
    git_dir = git(root, "rev-parse", "--git-dir")
    if git_dir.returncode != 0:
        raise RuntimeError(git_dir.stderr.strip())
    marker = (root / git_dir.stdout.strip() / "orbit-base")
    if marker.is_file():
        sha = marker.read_text(encoding="utf-8").strip()
        if git(root, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0:
            return sha
    raise RuntimeError("base do trabalho desconhecida (.git/orbit-base ausente): passe --since <sha do início>")


def collect_diff(root: Path, base: str) -> str:
    done = git(root, "-c", "core.quotepath=off", "diff", "--unified=0", "--no-color", "--no-renames", base)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip())
    return done.stdout


def parse(diff: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    old_path = ""
    line_no = 0
    for line in diff.splitlines():
        if line.startswith("--- "):
            old_path = line[4:].removeprefix("a/")
        elif line.startswith("+++ "):
            new_path = line[4:].removeprefix("b/")
            current = FileDiff(old_path if new_path == "/dev/null" else new_path)
            files.append(current)
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            line_no = int(match.group(1)) if match else 0
        elif current and line.startswith("+"):
            current.added.append((line_no, line[1:]))
            line_no += 1
        elif current and line.startswith("-"):
            current.removed.append(line[1:])
    return files


def untracked_files(root: Path) -> list[FileDiff]:
    """Arquivo novo não aparece em `git diff`: entra como adição pura, sem tocar no index."""
    done = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip())
    files: list[FileDiff] = []
    for name in filter(None, done.stdout.split("\0")):
        try:
            lines = (root / name).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        files.append(FileDiff(name, added=list(enumerate(lines, start=1))))
    return files


def thresholds(lines: list[str]) -> dict[str, list[float]]:
    """Valores por chave, na ordem em que aparecem: duas seções com a mesma chave não se escondem."""
    values: dict[str, list[float]] = {}
    for line in lines:
        for key, value in THRESHOLD.findall(line):
            values.setdefault(key.lower(), []).append(float(value))
    return values


def test_name(line: str) -> str:
    match = TEST_NAME.search(line)
    return next((group for group in match.groups() if group), "") if match else ""


def test_losses(files: list[FileDiff]) -> list[Violation]:
    """Conta no conjunto dos arquivos de teste: mover teste entre arquivos não é remover."""
    tests = [f for f in files if TEST_PATH.search(f.path)]
    removed = [t for f in tests for t in f.removed]
    added = [t for f in tests for _, t in f.added if not ALLOW.search(t)]
    names_added = {test_name(t) for t in added} - {""}
    violations: list[Violation] = []
    vanished = sorted({test_name(t) for t in removed} - {""} - names_added)
    if vanished:
        where = ", ".join(sorted({f.path for f in tests if f.removed}))
        violations.append(Violation(where, "teste sumiu pelo nome", ", ".join(vanished)))
        return violations
    for pattern, rule in ((TEST_UNIT, "teste removido"), (ASSERTION, "assert removido")):
        lost = sum(bool(pattern.search(t)) for t in removed) - sum(bool(pattern.search(t)) for t in added)
        if lost > 0:
            gone = sorted({test_name(t) for t in removed} - {""} - names_added)
            where = ", ".join(sorted({f.path for f in tests if f.removed}))
            violations.append(Violation(where, rule, f"{lost} a menos" + (f": {', '.join(gone)}" if gone else "")))
    return violations


def inspect(files: list[FileDiff]) -> list[Violation]:
    violations = test_losses(files)
    for diff in files:
        is_source = Path(diff.path).suffix in SOURCE_SUFFIXES
        for number, text in diff.added:
            where = f"{diff.path}:{number}"
            if SECRET.search(text):
                violations.append(Violation(where, "secret no diff", SECRET.sub("<redacted>", text)))
            if not is_source:
                continue
            allowed = ALLOW.search(text)
            rule = allowed.group(1) if allowed else ""
            if SKIP.search(text) and rule != "skip":
                violations.append(Violation(where, "skip/only novo", text))
            if SUPPRESSION.search(text) and rule != "supressao":
                violations.append(Violation(where, "supressão nova", text))
            if TEST_PATH.search(diff.path) and TRIVIAL_ASSERT.search(text) and rule != "assert":
                violations.append(Violation(where, "assert trivializado", text))
        if CONFIG_FILE.search(diff.path):
            before, after = thresholds(diff.removed), thresholds([t for _, t in diff.added])
            for key, olds in before.items():
                news = after.get(key, [])
                for index, old in enumerate(olds):
                    if index >= len(news):
                        violations.append(Violation(diff.path, "threshold removido", f"{key}: {old:g}"))
                    elif news[index] < old:
                        violations.append(Violation(diff.path, "threshold afrouxado", f"{key}: {old:g} -> {news[index]:g}"))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--since", default=None, help="SHA ou ref do início do trabalho")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        base = choose_base(root, args.since)
        files = parse(collect_diff(root, base)) + untracked_files(root)
    except (RuntimeError, OSError) as error:
        print(f"NOT_VERIFIED · floor guard não rodou: {error}")
        return EXIT_NOT_RUN
    scope = f"escopo {base[:12]} -> estado atual, {len(files)} arquivo(s)"
    violations = inspect(files)
    for violation in violations:
        print(violation)
    if violations:
        print(f"FAIL · {len(violations)} rebaixamento(s) de barra · {scope}. Corrigir, ou `floor-guard: allow <regra> <motivo>` na linha.")
        return EXIT_VIOLATION
    print(f"PASS · nenhum rebaixamento detectado (heurística) · {scope}")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
