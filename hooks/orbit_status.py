#!/usr/bin/env python3
"""O HM Orbit está funcionando nesta máquina? Diagnóstico em uma tela, sem rede e sem LLM.

    python3 ~/.claude/hooks/hm-orbit/orbit_status.py            últimos 7 dias
    python3 ~/.claude/hooks/hm-orbit/orbit_status.py --days 30

Confere: hooks registrados no settings.json · autoteste do guard com casos conhecidos ·
erros dos hooks · latência · sessões com kernel · motivos que mais pedem confirmação
(candidatos a falso positivo) · skills acionadas.
Veredito: OK · ATENÇÃO (algo a olhar) · PROBLEMA (corrigir já). Exit 0 / 1 / 2.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard_destructive

SELF_TEST: dict[str, str | None] = {
    "rm -rf ~": "deny",
    "git reset --hard": "ask",
    "psql -c 'DROP TABLE users'": "ask",
    "bash -c 'rm -rf /srv/app/dados'": "ask",
    "git status": None,
    "npm test": None,
}
SLOW_MS = 300
FALSE_POSITIVE_HINT = 5


def load(days: int) -> list[dict[str, object]]:
    log = HERE / "telemetry.jsonl"
    if not log.exists():
        return []
    since = time.time() - days * 86400
    events: list[dict[str, object]] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        ts = event.get("ts") if isinstance(event, dict) else None
        if isinstance(ts, (int, float)) and ts >= since:
            events.append(event)
    return events


def registered(settings_path: Path) -> tuple[bool, bool]:
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, False
    hooks = json.dumps(settings.get("hooks", {}))
    return "hm-orbit/session_start.py" in hooks, "hm-orbit/guard_destructive.py" in hooks


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--settings", type=Path, default=Path.home() / ".claude" / "settings.json")
    args = parser.parse_args()

    problems: list[str] = []
    attention: list[str] = []

    session_hook, guard_hook = registered(args.settings)
    if not session_hook or not guard_hook:
        problems.append(f"hooks não registrados no settings.json (kernel={session_hook}, guard={guard_hook})")

    failed = []
    for command, expected in SELF_TEST.items():
        result = guard_destructive.decide(command, Path("/srv/app"))
        if (result[0] if result else None) != expected:
            failed.append(command)
    if failed:
        problems.append(f"autoteste do guard falhou em: {', '.join(failed)}")

    events = load(args.days)
    kinds = Counter(str(e.get("ev")) for e in events)
    errors = [e for e in events if e.get("ev") == "error"]
    if errors:
        problems.append(f"{len(errors)} erro(s) de hook: {Counter(str(e.get('err')) for e in errors).most_common(3)}")
    latencies = [float(str(e["ms"])) for e in events if e.get("ev") in {"allow", "ask", "deny"} and "ms" in e]
    p95 = percentile(latencies, 0.95)
    if p95 > SLOW_MS:
        attention.append(f"guard lento: p95 {p95:.0f} ms")
    reasons = Counter(str(e.get("reason")) for e in events if e.get("ev") in {"ask", "deny"})
    noisy = [(reason, count) for reason, count in reasons.most_common(5) if count >= FALSE_POSITIVE_HINT]
    if noisy:
        attention.append("motivos que mais pedem confirmação (conferir se são falso positivo): " + "; ".join(f"{r} ({c}x)" for r, c in noisy))
    sessions = [e for e in events if e.get("ev") == "session"]
    if not events:
        attention.append("sem telemetria no período: hooks ainda não rodaram ou HM_ORBIT_TELEMETRY=off")

    verdict = "PROBLEMA" if problems else ("ATENÇÃO" if attention else "OK")
    print(f"HM Orbit · {verdict} · últimos {args.days} dias")
    print(f"  sessões: {len(sessions)} ({sum(1 for s in sessions if s.get('injected'))} com kernel)")
    print(f"  guard: {kinds['allow']} liberados · {kinds['ask']} pediram confirmação · {kinds['deny']} negados · p95 {p95:.0f} ms")
    skills = Counter(str(e.get("name")) for e in events if e.get("ev") == "skill")
    print(f"  skills acionadas: {', '.join(f'{n} {c}x' for n, c in skills.most_common()) or 'nenhuma'}")
    recent = [e for e in events if e.get("ev") in {"ask", "deny"}][-5:]
    for event in recent:
        print(f"  · {event.get('ev')} · {event.get('reason')} · {event.get('cmd')}")
    for item in problems:
        print(f"  PROBLEMA · {item}")
    for item in attention:
        print(f"  ATENÇÃO · {item}")
    return {"OK": 0, "ATENÇÃO": 1, "PROBLEMA": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
