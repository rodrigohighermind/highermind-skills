#!/usr/bin/env python3
"""SessionStart do HM Orbit: injeta o kernel só onde há software sendo construído.

Liga quando, subindo a partir do cwd:
  1. existe `.orbit` (opt-in explícito, vale fora de git), ou
  2. a raiz git tem um marcador de software (package.json, pyproject.toml, ...).
`.orbit-off` em qualquer nível da cadeia desliga e vence qualquer opt-in. Fora disso (finanças, mídia, ops, home) não injeta nada.

Nunca derruba a sessão: qualquer falha de leitura resulta em silêncio e exit 0.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orbit_log

KERNEL = Path(__file__).resolve().parent / "ORBIT.md"
OPT_IN = ".orbit"
OPT_OUT = ".orbit-off"
SOFTWARE_MARKERS = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "deno.json",
    "Package.swift",
    "Gemfile",
    "composer.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "mix.exs",
    "supabase",
    "Dockerfile",
    "hm-quality.json",
)


def should_inject(cwd: Path) -> bool:
    home = Path.home().resolve()
    chain = (cwd, *cwd.parents)
    if any((directory / OPT_OUT).exists() for directory in chain):
        return False
    for directory in chain:
        if (directory / OPT_IN).exists():
            return True
        # A home nunca é projeto, mesmo que alguém tenha rodado git init nela.
        is_project = (directory / ".git").exists() and directory != home
        if is_project and any((directory / m).exists() for m in SOFTWARE_MARKERS):
            return True
    return False


def record_base(cwd: Path) -> None:
    """Grava o SHA do início da sessão em .git/orbit-base: o floor guard mede o trabalho a partir dele."""
    for directory in (cwd, *cwd.parents):
        git_dir = directory / ".git"
        if git_dir.is_dir():
            head = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3, check=False)
            if head.returncode == 0 and head.stdout.strip():
                (git_dir / "orbit-base").write_text(head.stdout.strip() + "\n", encoding="utf-8")
            return


STATE = Path(__file__).resolve().parent / ".sessions"


def read_payload() -> dict[str, object]:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    payload = json.loads(raw) if raw.strip() else {}
    return payload if isinstance(payload, dict) else {}


def already_injected(session: str) -> bool:
    return bool(session) and (STATE / session).exists()


def mark_injected(session: str) -> None:
    if not session or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", session):
        return
    STATE.mkdir(exist_ok=True)
    (STATE / session).touch()
    cutoff = time.time() - 7 * 86400
    for old in STATE.iterdir():
        if old.stat().st_mtime < cutoff:
            old.unlink(missing_ok=True)


def touched_dirs(payload: dict[str, object], cwd: Path) -> list[Path]:
    """Onde o agente foi de fato: destinos de `cd`/`-C` no comando e o arquivo lido ou editado.
    O cwd do payload continua sendo o de início quando o `cd` sai da pasta de trabalho."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    found: list[Path] = []
    command = tool_input.get("command")
    if isinstance(command, str):
        for match in re.finditer(r"(?:^|[;&|]\s*|\bcd\s+|-C\s+)(?:cd\s+)?(['\"]?)([~/.][^\s;&|'\"]*)\1", command):
            raw = match.group(2)
            target = Path(os.path.expanduser(raw))
            found.append((target if target.is_absolute() else cwd / target).resolve())
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            path = Path(os.path.expanduser(value))
            path = (path if path.is_absolute() else cwd / path).resolve()
            found.append(path if path.is_dir() else path.parent)
    return [p for p in found if p.exists()][:8]


def main() -> int:
    """SessionStart injeta se a sessão abre num repo de software. PostToolUse (Bash) cobre a sessão que
    começa fora e entra num repo depois: injeta uma vez, na primeira vez que o diretório vira software."""
    started = time.monotonic()
    try:
        payload = read_payload()
        event = str(payload.get("hook_event_name") or "SessionStart")
        session = str(payload.get("session_id") or "")
        cwd = Path(str(payload.get("cwd") or os.getcwd())).resolve()
        if event != "SessionStart" and already_injected(session):
            return 0
        candidates = [cwd] + touched_dirs(payload, cwd) if event != "SessionStart" else [cwd]
        cwd = next((c for c in candidates if should_inject(c)), cwd)
        if not should_inject(cwd):
            if event == "SessionStart":
                orbit_log.log({"ev": "session", "injected": False, "ms": round((time.monotonic() - started) * 1000, 1)})
            return 0
        kernel = KERNEL.read_text(encoding="utf-8")
        record_base(cwd)
        mark_injected(session)
    except (OSError, ValueError) as error:
        orbit_log.log({"ev": "error", "hook": "session_start", "err": type(error).__name__})
        return 0
    orbit_log.log({"ev": "session", "injected": True, "via": event, "repo": cwd.name, "ms": round((time.monotonic() - started) * 1000, 1)})
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": kernel}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
