#!/usr/bin/env python3
"""Instala o HM Orbit no Claude Code e no Codex. Dry-run por padrão; nada é apagado.

    python3 scripts/install.py                 mostra o plano
    python3 scripts/install.py --apply         instala
    python3 scripts/install.py --uninstall     plano de remoção (--apply executa)

O que faz:
  · copia dist/<skill> para <home>/skills/<skill> com marcador `.hm-skill-install.json` (hash do conteúdo);
  · aposenta skills da geração anterior (marcador suite=highermind-skills) que não existem no Orbit;
  · no Claude Code, instala os hooks SessionStart (kernel) e PreToolUse (guard destrutivo, onFailure=block).
Garantias: preflight completo antes da primeira mutação, lock por home, journal com rollback em falha,
backup de tudo que sai em <home>/skills/.hm-skills-backup/<id>/. Pasta sem marcador nosso, ou com
conteúdo modificado localmente, é do usuário: vira CONFLITO e não é tocada.
Exit 0 aplicado · 1 erro (nada mudou) · 3 aplicado com conflitos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build import build, load_manifest

MARKER = ".hm-skill-install.json"
HOOK_MARKER = ".hm-orbit-install.json"
SUITE = "hm-skills-orbit"
LEGACY_SUITE = "highermind-skills"
HOOK_DIR = "hm-orbit"
HOOK_TAG = f"/hooks/{HOOK_DIR}/"
ON_FAILURE_MIN = (2, 1, 295)
# Evento → (matcher, script, bloquear se o hook falhar).
HOOKS: dict[str, tuple[str | None, str, bool]] = {
    "SessionStart": (None, "session_start.py", False),
    "PreToolUse": ("Bash|Write|Edit|MultiEdit|Skill", "guard_destructive.py", True),
}
EXIT_OK, EXIT_ERROR, EXIT_CONFLICT = 0, 1, 3


@dataclass
class Plan:
    home: Path
    runtime: str
    install: list[str] = field(default_factory=list)
    replace: list[str] = field(default_factory=list)
    retire: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    hook: str = ""

    def empty(self) -> bool:
        return not (self.install or self.replace or self.retire or self.hook)


@dataclass
class Journal:
    """Mutações aplicadas, para desfazer em ordem reversa se algo falhar no meio."""

    moves: list[tuple[Path, Path]] = field(default_factory=list)
    created: list[Path] = field(default_factory=list)
    settings: list[tuple[Path, bytes | None]] = field(default_factory=list)

    def rollback(self) -> list[str]:
        """Desfaz em ordem reversa e devolve o que não conseguiu restaurar (vazio = estado original)."""
        problems: list[str] = []
        for path, original in reversed(self.settings):
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        for path in reversed(self.created):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists() or path.is_symlink():
                path.unlink()
        for source, destination in reversed(self.moves):
            if source.exists() and destination.exists():
                shutil.rmtree(source, ignore_errors=True) if source.is_dir() else source.unlink()
            if destination.exists():
                shutil.move(str(destination), str(source))
            if not source.exists():
                problems.append(str(source))
        return problems


def stage_copy(source: Path, target: Path, journal: Journal) -> Path:
    """Copia para staging irmão do destino, registrado no journal antes da primeira escrita."""
    staging = target.with_name(f".{target.name}.staging-{os.getpid()}")
    journal.created.append(staging)
    shutil.copytree(source, staging)
    if tree_digest(staging) != tree_digest(source):
        raise RuntimeError(f"cópia de {source.name} não confere com a origem")
    return staging


def publish(staging: Path, target: Path, journal: Journal) -> None:
    staging.rename(target)
    journal.created.remove(staging)
    journal.created.append(target)


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file() and p.name not in {MARKER, HOOK_MARKER, ".DS_Store"} and "__pycache__" not in p.parts):
        digest.update(str(file.relative_to(path)).encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def read_marker(path: Path, name: str = MARKER) -> dict[str, str] | None:
    marker = path / name
    if not marker.is_file():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else None


def load_settings(home: Path) -> dict[str, object]:
    path = home / "settings.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} não é objeto JSON")
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict) or any(not isinstance(hooks.get(e, []), list) for e in HOOKS):
        raise TypeError(f"{path}: estrutura de hooks inesperada, nada será alterado")
    return data


def hook_command(home: Path, script: str) -> str:
    return f'python3 "{home / "hooks" / HOOK_DIR / script}"'


def is_ours(handler: object, home: Path | None = None) -> bool:
    """Handler nosso = comando idêntico ao que o installer escreve. Substring não basta."""
    if not isinstance(handler, dict):
        return False
    command = str(handler.get("command", ""))
    if home is not None:
        return command in {hook_command(home, script) for _, script, _ in HOOKS.values()}
    return bool(re.fullmatch(r'python3 "[^"]*/hooks/' + HOOK_DIR + r'/(session_start|guard_destructive)\.py"', command))


def settings_has_hook(settings: dict[str, object], home: Path | None = None) -> bool:
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return False
    for entries in hooks.values():
        for entry in entries if isinstance(entries, list) else []:
            handlers = entry.get("hooks") if isinstance(entry, dict) else None
            if isinstance(handlers, list) and any(is_ours(h, home) for h in handlers):
                return True
    return False


def without_orbit_hook(settings: dict[str, object], home: Path | None = None) -> dict[str, object]:
    """Remove só os handlers do Orbit, preservando irmãos e matcher de terceiros."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return settings
    for event in list(hooks):
        entries = hooks[event]
        if not isinstance(entries, list):
            continue
        kept: list[object] = []
        for entry in entries:
            handlers = entry.get("hooks") if isinstance(entry, dict) else None
            if not isinstance(entry, dict) or not isinstance(handlers, list):
                kept.append(entry)
                continue
            remaining = [h for h in handlers if not is_ours(h, home)]
            if remaining:
                kept.append({**entry, "hooks": remaining})
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks:
        settings.pop("hooks", None)
    return settings


def claude_supports_on_failure() -> bool:
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if match is None:
        return False
    return tuple(int(g) for g in match.groups()) >= ON_FAILURE_MIN


def make_plan(home: Path, runtime: str, skills: tuple[str, ...], dist: Path, uninstall: bool) -> Plan:
    plan = Plan(home, runtime)
    skills_dir = home / "skills"
    existing = sorted(p for p in skills_dir.iterdir() if p.is_dir() or p.is_symlink()) if skills_dir.exists() else []
    for path in existing:
        marker = read_marker(path)
        if path.name.startswith(".") or marker is None or marker.get("suite") not in {SUITE, LEGACY_SUITE}:
            continue
        if not (uninstall or path.name not in skills):
            continue
        if path.is_symlink():
            plan.conflicts.append(f"{path.name} (symlink, não aposentado)")
        elif marker.get("installed_digest") and tree_digest(path) != marker["installed_digest"]:
            plan.conflicts.append(f"{path.name} (modificada localmente, não aposentada)")
        else:
            plan.retire.append(path.name)
    if not uninstall:
        for skill in skills:
            target = skills_dir / skill
            marker = read_marker(target)
            if not target.exists() and not target.is_symlink():
                plan.install.append(skill)
            elif marker is None or marker.get("suite") not in {SUITE, LEGACY_SUITE}:
                plan.conflicts.append(skill)
            elif marker.get("suite") == LEGACY_SUITE:
                plan.replace.append(skill)
            elif marker.get("installed_digest") and tree_digest(target) != marker["installed_digest"]:
                plan.conflicts.append(f"{skill} (modificada localmente)")
            elif marker.get("source_digest") != tree_digest(dist / skill):
                plan.replace.append(skill)
    if runtime == "claude":
        hook_dir = home / "hooks" / HOOK_DIR
        hook_marker = read_marker(hook_dir, HOOK_MARKER)
        if hook_dir.exists() and (hook_marker is None or hook_marker.get("suite") != SUITE):
            plan.conflicts.append(f"hooks/{HOOK_DIR} (sem marcador do Orbit)")
            return plan
        if hook_marker and hook_marker.get("installed_digest") and tree_digest(hook_dir) != hook_marker["installed_digest"]:
            plan.conflicts.append(f"hooks/{HOOK_DIR} (modificado localmente)")
            return plan
        has_hook = settings_has_hook(load_settings(home), home)
        if uninstall and (has_hook or hook_dir.exists()):
            plan.hook = "remover"
        elif not uninstall:
            plan.hook = "atualizar" if has_hook else "registrar"
    return plan


def apply(plan: Plan, dist: Path, version: str, stamp: str, on_failure: bool, journal: Journal) -> None:
    skills_dir = plan.home / "skills"
    backup_root = skills_dir / ".hm-skills-backup" / stamp
    skills_dir.mkdir(parents=True, exist_ok=True)
    staged = {name: stage_copy(dist / name, skills_dir / name, journal) for name in plan.install + plan.replace}
    for name in plan.retire + plan.replace:
        backup_root.mkdir(parents=True, exist_ok=True)
        source, destination = skills_dir / name, backup_root / name
        shutil.move(str(source), str(destination))
        journal.moves.append((source, destination))
    for name, staging in staged.items():
        target = skills_dir / name
        marker = {"suite": SUITE, "version": version, "skill": name, "source_digest": tree_digest(dist / name), "installed_digest": tree_digest(staging)}
        (staging / MARKER).write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
        publish(staging, target, journal)
    if not plan.hook:
        return
    settings_path = plan.home / "settings.json"
    before = settings_path.read_bytes() if settings_path.exists() else None
    settings = without_orbit_hook(load_settings(plan.home), plan.home)
    hook_dir = plan.home / "hooks" / HOOK_DIR
    hook_staging: Path | None = None
    if plan.hook != "remover":
        hook_dir.parent.mkdir(parents=True, exist_ok=True)
        hook_staging = stage_copy(dist / "hooks", hook_dir, journal)
        (hook_staging / HOOK_MARKER).write_text(json.dumps({"suite": SUITE, "version": version, "installed_digest": tree_digest(hook_staging)}) + "\n", encoding="utf-8")
    if hook_dir.exists():
        backup_root.mkdir(parents=True, exist_ok=True)
        destination = backup_root / f"hook-{HOOK_DIR}"
        shutil.move(str(hook_dir), str(destination))
        journal.moves.append((hook_dir, destination))
    if hook_staging is not None:
        publish(hook_staging, hook_dir, journal)
        hooks = settings.setdefault("hooks", {})
        assert isinstance(hooks, dict)  # garantido por load_settings
        for event, (matcher, script, block) in HOOKS.items():
            handler: dict[str, object] = {"type": "command", "command": hook_command(plan.home, script), "timeout": 5}
            if block and on_failure:
                handler["onFailure"] = "block"
            entry: dict[str, object] = {"hooks": [handler]}
            if matcher:
                entry["matcher"] = matcher
            entries = hooks.setdefault(event, [])
            assert isinstance(entries, list)
            entries.append(entry)
    current = settings_path.read_bytes() if settings_path.exists() else None
    if current != before:
        raise RuntimeError(f"{settings_path} mudou durante a instalação; nada foi sobrescrito")
    if before is not None:
        backup_root.mkdir(parents=True, exist_ok=True)
        (backup_root / "settings.json").write_bytes(before)
    journal.settings.append((settings_path, before))
    tmp = settings_path.with_name(f".settings.json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings_path)


def describe(plan: Plan) -> str:
    rows = [f"[{plan.runtime}] {plan.home}"]
    for label, items in (("instalar", plan.install), ("substituir", plan.replace), ("aposentar", plan.retire), ("CONFLITO (intocado)", plan.conflicts)):
        if items:
            rows.append(f"  {label}: {', '.join(items)}")
    if plan.hook:
        rows.append(f"  hooks SessionStart + PreToolUse(Bash/Write/Edit): {plan.hook}")
    if plan.empty() and not plan.conflicts:
        rows.append("  nada a fazer")
    return "\n".join(rows)


def acquire_lock(home: Path) -> Path:
    lock = home / ".hm-orbit-install.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"outra instalação em andamento ({lock}); remova o lock se não houver") from error
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return lock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime", choices=("claude", "codex", "both"), default="both")
    parser.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-fail-open", action="store_true", help="registrar o guard mesmo sem onFailure=block")
    args = parser.parse_args()

    manifest = load_manifest(ROOT)
    dist = ROOT / "dist"
    findings = build(ROOT, dist)
    if findings:
        for finding in findings:
            print(finding)
        print("FAIL · build com erro, nada instalado")
        return EXIT_ERROR

    homes = {"claude": args.claude_home, "codex": args.codex_home}
    runtimes = ("claude", "codex") if args.runtime == "both" else (args.runtime,)
    plans: list[Plan] = []
    for runtime in runtimes:
        if not homes[runtime].exists():
            print(f"[{runtime}] ignorado: {homes[runtime]} não existe")
            continue
        try:
            plans.append(make_plan(homes[runtime], runtime, manifest.skills, dist, args.uninstall))
        except (TypeError, ValueError) as error:
            print(f"FAIL · preflight [{runtime}]: {error}")
            return EXIT_ERROR
    for plan in plans:
        print(describe(plan))
    if not plans:
        print("FAIL · nenhum destino disponível")
        return EXIT_ERROR
    if not args.apply:
        print("\nDry-run. Rodar com --apply para executar.")
        return EXIT_OK

    stamp = f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    on_failure = claude_supports_on_failure()
    if any(plan.runtime == "claude" and plan.hook not in {"", "remover"} for plan in plans) and not on_failure and not args.allow_fail_open:
        print("FAIL · Claude Code sem suporte a onFailure (precisa >= 2.1.295): o guard falharia aberto. Atualize ou use --allow-fail-open.")
        return EXIT_ERROR
    journal = Journal()
    locks: list[Path] = []
    try:
        for plan in plans:
            locks.append(acquire_lock(plan.home))
        fresh = [make_plan(plan.home, plan.runtime, manifest.skills, dist, args.uninstall) for plan in plans]
        if [describe(p) for p in fresh] != [describe(p) for p in plans]:
            raise RuntimeError("o estado mudou entre o plano e a aplicação; rode de novo")
        for plan in fresh:
            apply(plan, dist, manifest.version, stamp, on_failure, journal)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        leftovers = journal.rollback()
        if leftovers:
            print(f"FAIL · {error}. Rollback INCOMPLETO, conferir: {', '.join(leftovers)} (backup em .hm-skills-backup/{stamp})")
        else:
            print(f"FAIL · {error}. Estado original restaurado.")
        return EXIT_ERROR
    finally:
        for lock in locks:
            lock.unlink(missing_ok=True)
    print(f"\nPASS · aplicado. Backup em <home>/skills/.hm-skills-backup/{stamp}/")
    if any(plan.hook for plan in plans):
        print("Hooks valem para sessões novas do Claude Code.")
    if any(plan.conflicts for plan in plans):
        print("Atenção: há conflitos intocados, ver acima.")
        return EXIT_CONFLICT
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
