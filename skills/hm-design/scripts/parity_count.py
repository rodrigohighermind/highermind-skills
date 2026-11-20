#!/usr/bin/env python3
"""Conta a matriz de paridade contra a referência e reprova linha sem estado.

    python3 parity_count.py docs/paridade/<referencia>.md

Lê toda tabela Markdown do arquivo cujo cabeçalho tem a coluna de estado ("Estado" ou "Status"),
pelo nome da coluna, não pela posição. Estados válidos: TEM, PARCIAL, FALTA, MELHOR, N/A. Imprime a
contagem por estado e, se houver coluna "Prioridade", por estado × prioridade. Sai 1 se alguma linha
estiver sem estado ou com estado fora do conjunto, 2 se o arquivo não tiver matriz.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

STATES = ("TEM", "PARCIAL", "FALTA", "MELHOR", "N/A")
STATE_COLUMNS = {"estado", "status"}


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        head, rule = lines[i], lines[i + 1]
        if head.lstrip().startswith("|") and set(rule.replace("|", "").replace(":", "").strip()) <= {"-"} and "-" in rule:
            names = [n.lower().strip("* ") for n in cells(head)]
            if STATE_COLUMNS & set(names):
                i += 2
                while i < len(lines) and lines[i].lstrip().startswith("|"):
                    values = cells(lines[i])
                    rows.append(dict(zip(names, values + [""] * (len(names) - len(values)))))
                    i += 1
                continue
        i += 1
    return rows


def state_of(row: dict[str, str]) -> str:
    raw = next((row[c] for c in STATE_COLUMNS if c in row), "")
    return raw.strip("*` ").upper()


def report(text: str) -> tuple[int, str]:
    rows = read_rows(text)
    if not rows:
        return 2, "nenhuma matriz com coluna Estado/Status"
    bad = [i + 1 for i, row in enumerate(rows) if state_of(row) not in STATES]
    by_state = Counter(state_of(r) for r in rows if state_of(r) in STATES)
    out = [f"{len(rows)} itens · " + " · ".join(f"{s} {by_state.get(s, 0)}" for s in STATES)]
    if any("prioridade" in r for r in rows):
        grid = Counter((state_of(r), r.get("prioridade", "")) for r in rows if state_of(r) in STATES)
        for prio in sorted({p for _, p in grid}):
            out.append(f"  {prio or '(sem prioridade)'}: " + " · ".join(f"{s} {grid.get((s, prio), 0)}" for s in STATES if grid.get((s, prio))))
    if bad:
        out.append(f"FAIL: {len(bad)} linha(s) sem estado válido (linhas da matriz: {bad[:20]})")
    return (1 if bad else 0), "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[2].strip())
        return 2
    code, text = report(Path(argv[0]).read_text(encoding="utf-8"))
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
