#!/usr/bin/env python3
"""Creates a native macOS app from the starter template. Nobody edits the template by hand.

    python3 new_app.py "<Nome do App>" <bundle.id> <destino>

Copies template/ to <destino>, replacing __APP_NAME__ (display name, may have spaces and accents),
__TARGET__ (Swift module name derived from the display name) and __BUNDLE_ID__ in file contents and
paths, then creates the git repository with a first commit. Refuses an existing destination: it never
overwrites anything.

    python3 new_app.py "<Nome do App>" <bundle.id> <repo existente> --into-existing

Composes with a project that already exists (for example one born from `hm new`, with its own git,
CLAUDE.md and .gitignore): adds the starter files that are missing, skips (and lists) every file that
already exists, merges .gitignore line by line and never creates or touches git history.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "template"
BUNDLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$")
TEXT_SUFFIXES = {".swift", ".sh", ".py", ".json", ".md", ".plist", ".txt", ""}
SKIP = {".build", ".swiftpm", "__pycache__", ".DS_Store"}


def target_name(display: str) -> str:
    """'Análise Ção App' -> 'AnaliseCaoApp': ASCII, CamelCase, starts with a letter."""
    ascii_ = unicodedata.normalize("NFKD", display).encode("ascii", "ignore").decode()
    words = re.findall(r"[A-Za-z0-9]+", ascii_)
    name = "".join(w[:1].upper() + w[1:] for w in words)
    if not name or not name[0].isalpha():
        name = "App" + name
    return name


def validate(display: str, bundle_id: str) -> None:
    if not display.strip() or any(c in display for c in '/:"\\$`'):
        raise ValueError(f"nome inválido: {display!r} (sem / : \" \\ $ `)")
    if not BUNDLE_ID.match(bundle_id):
        raise ValueError(f"bundle id inválido: {bundle_id!r} (ex.: com.empresa.app)")


def create(display: str, bundle_id: str, dest: Path, into_existing: bool = False) -> Path:
    validate(display, bundle_id)
    if into_existing:
        if not (dest / ".git").exists():
            raise FileExistsError(f"--into-existing pede um repo git existente, nada foi alterado: {dest}")
    elif dest.exists():
        raise FileExistsError(f"destino já existe, nada foi alterado: {dest}")
    target = target_name(display)
    values = {"__APP_NAME__": display, "__TARGET__": target, "__BUNDLE_ID__": bundle_id}

    def sub(text: str) -> str:
        for k, v in values.items():
            text = text.replace(k, v)
        return text

    if into_existing:
        return compose(dest, sub)
    dest.mkdir(parents=True)
    try:
        for src in sorted(TEMPLATE.rglob("*")):
            rel = src.relative_to(TEMPLATE)
            if any(part in SKIP for part in rel.parts):
                continue
            out = dest / sub(str(rel))
            if src.is_dir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            if src.suffix in TEXT_SUFFIXES or src.name == ".gitignore":
                out.write_text(sub(src.read_text(encoding="utf-8")), encoding="utf-8")
            else:
                shutil.copyfile(src, out)
            shutil.copymode(src, out)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)  # we created it above: never leave a half-made app
        raise
    leftovers = [str(p) for p in dest.rglob("*") if p.is_file() and "__" in p.name and "__init__" not in p.name]
    if leftovers:
        raise RuntimeError(f"placeholders sobraram em nomes de arquivo: {leftovers}")
    init_git(dest, display)
    return dest


def compose(dest: Path, sub) -> Path:  # type: ignore[no-untyped-def]
    """Adds what is missing, never overwrites, merges .gitignore by line, leaves git history alone."""
    added: list[str] = []
    skipped: list[str] = []
    for src in sorted(TEMPLATE.rglob("*")):
        rel = src.relative_to(TEMPLATE)
        if any(part in SKIP for part in rel.parts) or src.is_dir():
            continue
        out = dest / sub(str(rel))
        if src.name == ".gitignore" and out.exists():
            have = out.read_text(encoding="utf-8").splitlines()
            extra = [line for line in sub(src.read_text(encoding="utf-8")).splitlines() if line and line not in have]
            if extra:
                out.write_text("\n".join(have + extra) + "\n", encoding="utf-8")
                added.append(f"{out.relative_to(dest)} (+{len(extra)} linhas)")
            continue
        if out.exists():
            skipped.append(str(out.relative_to(dest)))
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT_SUFFIXES:
            out.write_text(sub(src.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copyfile(src, out)
        shutil.copymode(src, out)
        added.append(str(out.relative_to(dest)))
    print(f"adicionados: {len(added)}" + "".join(f"\n  + {a}" for a in added))
    if skipped:
        print(f"já existiam, intocados: {len(skipped)}" + "".join(f"\n  = {s}" for s in skipped))
    return dest


def init_git(dest: Path, display: str) -> None:
    """Every project is born versioned: the quality gate diffs new code against history."""
    if shutil.which("git") is None:
        print("aviso: git não encontrado; crie o repositório antes de rodar o gate", file=sys.stderr)
        return
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=dest, check=True, capture_output=True)
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", f"chore: {display} gerado pelo starter macOS")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    ap.add_argument("nome", help='nome visível do app, ex.: "Meu App"')
    ap.add_argument("bundle_id", help="ex.: com.empresa.meu-app")
    ap.add_argument("destino", type=Path)
    ap.add_argument("--into-existing", action="store_true", help="compor com um repo git que já existe: só adiciona o que falta")
    a = ap.parse_args(argv)
    try:
        out = create(a.nome, a.bundle_id, a.destino.expanduser(), a.into_existing)
    except (ValueError, FileExistsError, RuntimeError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    print(f"criado: {out}  (módulo Swift: {target_name(a.nome)})")
    print(f"próximo: cd {str(out)!r} && ./scripts/install.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
