#!/usr/bin/env python3
"""Audita a fonte do HM Orbit e gera dist/ instalável.

    python3 scripts/build.py           audita e gera dist/
    python3 scripts/build.py --check   só audita (exit 1 se houver erro)

dist/<skill>/ = skills/<skill>/ + references/{orbit,profile,incidents}.md gerados.
dist/hooks/   = hook SessionStart + ORBIT.md que ele injeta.
Fonte única: ORBIT.md, profiles/highermind.md e incidents/*.md nunca são copiados à mão.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESCRIPTION_LIMIT = 1024
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
INCIDENT_FIELDS = ("id", "date", "domains", "signal", "law")
# Incidentes nasceram com domínios da 3.x; dev e data agora são engenharia.
DOMAIN_TO_SKILL = {
    "dev": "hm-engineering",
    "data": "hm-engineering",
    "engineering": "hm-engineering",
    "design": "hm-design",
    "product": "hm-product",
}
GENERATED_REFERENCES = ("orbit.md", "profile.md", "incidents.md")
IGNORED = {".DS_Store", "__pycache__", ".ruff_cache", ".mypy_cache", ".venv"}


@dataclass(frozen=True)
class Finding:
    where: str
    message: str

    def __str__(self) -> str:
        return f"ERRO · {self.where} · {self.message}"


@dataclass(frozen=True)
class Incident:
    path: Path
    meta: dict[str, str]
    body: str

    @property
    def skills(self) -> set[str]:
        raw = self.meta.get("domains", "").strip("[] ")
        return {DOMAIN_TO_SKILL[d.strip()] for d in raw.split(",") if d.strip() in DOMAIN_TO_SKILL}


@dataclass(frozen=True)
class Manifest:
    version: str
    skills: tuple[str, ...]
    skill_line_budget: int
    forbidden_characters: tuple[str, ...] = ()


def load_manifest(root: Path) -> Manifest:
    raw = json.loads((root / "suite.json").read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("suite.json precisa ser objeto")
    skills = raw.get("skills")
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        raise ValueError("suite.json: skills precisa ser lista de strings")
    forbidden = raw.get("forbidden_characters", [])
    if not isinstance(forbidden, list) or not all(isinstance(c, str) and len(c) == 1 for c in forbidden):
        raise ValueError("suite.json: forbidden_characters precisa ser lista de caracteres")
    return Manifest(str(raw["version"]), tuple(skills), int(raw["skill_line_budget"]), tuple(forbidden))


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.startswith(" "):
            meta[key.strip()] = value.strip()
    return meta, text[end + 5 :]


def load_incidents(root: Path) -> tuple[list[Incident], list[Finding]]:
    incidents: list[Incident] = []
    findings: list[Finding] = []
    for path in sorted((root / "incidents").glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        missing = [field for field in INCIDENT_FIELDS if not meta.get(field)]
        if missing:
            findings.append(Finding(str(path.relative_to(root)), f"frontmatter sem {', '.join(missing)}"))
            continue
        incident = Incident(path, meta, body.strip())
        if not incident.skills:
            findings.append(Finding(str(path.relative_to(root)), f"domains sem skill conhecida: {meta['domains']}"))
            continue
        incidents.append(incident)
    return incidents, findings


def incident_corpus(incidents: list[Incident], skill: str) -> str:
    selected = [incident for incident in incidents if skill in incident.skills]
    lines = [
        "# Incidentes",
        "",
        "Gerado por `scripts/build.py` a partir de `incidents/*.md`. Não editar aqui.",
        "Buscar por stack, artefato e risco; carregar só o que se aplica.",
        "",
        "| Lei | Sinal |",
        "|---|---|",
    ]
    lines += [f"| `{i.meta['law']}` | {i.meta['signal']} |" for i in selected]
    for incident in selected:
        lines += ["", "---", "", f"<!-- {incident.meta['id']} · {incident.meta['date']} -->", incident.body]
    return "\n".join(lines) + "\n"


def audit_skill(root: Path, skill: str, budget: int) -> list[Finding]:
    findings: list[Finding] = []
    skill_md = root / "skills" / skill / "SKILL.md"
    where = str(skill_md.relative_to(root))
    if not skill_md.is_file():
        return [Finding(where, "SKILL.md ausente")]
    text = skill_md.read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(text)
    if meta.get("name") != skill:
        findings.append(Finding(where, f"name {meta.get('name')!r} difere da pasta {skill!r}"))
    if not NAME_PATTERN.match(skill):
        findings.append(Finding(where, "nome precisa ser kebab-case minúsculo"))
    description = meta.get("description", "")
    if not description.startswith("Use "):
        findings.append(Finding(where, "description precisa começar por 'Use ' (só quando usar, nunca o workflow)"))
    if len(description) > DESCRIPTION_LIMIT:
        findings.append(Finding(where, f"description com {len(description)} chars (limite {DESCRIPTION_LIMIT})"))
    lines = text.count("\n") + 1
    if lines > budget:
        findings.append(Finding(where, f"{lines} linhas (teto {budget}); profundidade vai para playbook"))
    return findings


def audit_links(dist_skill: Path, root_label: str) -> list[Finding]:
    findings: list[Finding] = []
    for markdown in sorted(dist_skill.rglob("*.md")):
        for target in LINK_PATTERN.findall(markdown.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (markdown.parent / target).exists():
                rel = markdown.relative_to(dist_skill)
                findings.append(Finding(f"{root_label}/{rel}", f"link quebrado: {target}"))
    return findings


def audit_text(root: Path, forbidden: tuple[str, ...]) -> list[Finding]:
    """Caracteres que a suíte proíbe no próprio texto (configurados em suite.json)."""
    findings: list[Finding] = []
    if not forbidden:
        return findings
    sources = [root / "ORBIT.md", root / "README.md", root / "CHANGELOG.md", root / "profiles"]
    sources += [root / "skills", root / "incidents", root / "hooks", root / "evals", root / "scripts"]
    for source in sources:
        files = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
        for path in files:
            if path.suffix not in {".md", ".py", ".json", ".yaml"} or "__pycache__" in path.parts:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                for char in forbidden:
                    if char in line:
                        findings.append(Finding(f"{path.relative_to(root)}:{number}", f"caractere proibido pela suíte: U+{ord(char):04X}"))
    return findings


def build(root: Path, out: Path) -> list[Finding]:
    manifest = load_manifest(root)
    skills = list(manifest.skills)
    budget = manifest.skill_line_budget
    findings: list[Finding] = []

    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if version != manifest.version:
        findings.append(Finding("VERSION", f"{version!r} difere de suite.json {manifest.version!r}"))
    on_disk = sorted(p.parent.name for p in (root / "skills").glob("*/SKILL.md"))
    if on_disk != sorted(skills):
        findings.append(Finding("skills/", f"suite.json={sorted(skills)} disco={on_disk}"))

    incidents, incident_findings = load_incidents(root)
    findings += incident_findings + audit_text(root, manifest.forbidden_characters)
    for skill in skills:
        findings += audit_skill(root, skill, budget)
        source_refs = root / "skills" / skill / "references"
        if any((source_refs / name).exists() for name in GENERATED_REFERENCES):
            findings.append(Finding(f"skills/{skill}/references", "arquivo gerado commitado na fonte"))

    staging = out.with_name(out.name + ".tmp")
    if staging.exists():
        shutil.rmtree(staging)
    orbit = (root / "ORBIT.md").read_text(encoding="utf-8")
    profile = (root / "profiles" / "highermind.md").read_text(encoding="utf-8")
    for skill in skills:
        target = staging / skill
        shutil.copytree(root / "skills" / skill, target, ignore=shutil.ignore_patterns(*IGNORED))
        refs = target / "references"
        refs.mkdir(exist_ok=True)
        (refs / "orbit.md").write_text(orbit, encoding="utf-8")
        (refs / "profile.md").write_text(profile, encoding="utf-8")
        (refs / "incidents.md").write_text(incident_corpus(incidents, skill), encoding="utf-8")
        (target / ".orbit-version").write_text(version + "\n", encoding="utf-8")
        findings += audit_links(target, f"dist/{skill}")
    hooks = staging / "hooks"
    hooks.mkdir(parents=True)
    for hook in sorted((root / "hooks").glob("*.py")):
        shutil.copy2(hook, hooks / hook.name)
    (hooks / "ORBIT.md").write_text(orbit, encoding="utf-8")
    (staging / "VERSION").write_text(version + "\n", encoding="utf-8")

    if out.exists():
        shutil.rmtree(out)
    staging.rename(out)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="só audita; não deixa dist/")
    args = parser.parse_args()
    root: Path = args.root.resolve()
    out: Path = (args.out or root / "dist").resolve()
    if args.check:
        out = out.with_name(out.name + ".check")
    findings = build(root, out)
    if args.check:
        shutil.rmtree(out, ignore_errors=True)
    for finding in findings:
        print(finding)
    if findings:
        print(f"FAIL · {len(findings)} erro(s)")
        return 1
    print(f"PASS · {'audit' if args.check else f'build em {out}'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
