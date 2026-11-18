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


def read_cwd() -> Path:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if raw.strip():
        payload = json.loads(raw)
        if isinstance(payload, dict) and isinstance(payload.get("cwd"), str):
            return Path(payload["cwd"]).resolve()
    return Path(os.getcwd()).resolve()


def main() -> int:
    started = time.monotonic()
    try:
        cwd = read_cwd()
        if not should_inject(cwd):
            orbit_log.log({"ev": "session", "injected": False, "ms": round((time.monotonic() - started) * 1000, 1)})
            return 0
        kernel = KERNEL.read_text(encoding="utf-8")
        record_base(cwd)
    except (OSError, ValueError) as error:
        orbit_log.log({"ev": "error", "hook": "session_start", "err": type(error).__name__})
        return 0
    orbit_log.log({"ev": "session", "injected": True, "repo": cwd.name, "ms": round((time.monotonic() - started) * 1000, 1)})
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": kernel,
        }
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
