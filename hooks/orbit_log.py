"""Telemetria local dos hooks do HM Orbit. Nada sai da máquina.

Grava uma linha JSON por evento em telemetry.jsonl, ao lado dos hooks (chmod 600).
Comando comum entra só como contagem; texto de comando só aparece quando o guard
intervém, truncado e com secrets mascarados. Rotação: acima de 2 MB mantém a metade
mais recente. Falha de log nunca afeta o hook.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

LOG = Path(__file__).resolve().parent / "telemetry.jsonl"
MAX_BYTES = 2_000_000
SECRET = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{8,}|\bsk-(proj-)?[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[abprs]-[A-Za-z0-9-]{10,}|eyJhbGciOi[A-Za-z0-9_.-]{20,}|(?i:(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)\S+"
)


def redact(text: str, limit: int = 160) -> str:
    return SECRET.sub("<redacted>", text)[:limit]


def log(event: dict[str, object]) -> None:
    if os.environ.get("HM_ORBIT_TELEMETRY", "").lower() == "off":
        return
    try:
        if LOG.exists() and LOG.stat().st_size > MAX_BYTES:
            lines = LOG.read_text(encoding="utf-8").splitlines()
            LOG.write_text("\n".join(lines[len(lines) // 2 :]) + "\n", encoding="utf-8")
        new = not LOG.exists()
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": round(time.time(), 3), **event}, ensure_ascii=False) + "\n")
        if new:
            LOG.chmod(0o600)
    except OSError:
        return
