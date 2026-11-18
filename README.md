# HM Skills Orbit

Três skills para construir produto de tecnologia no nível mais alto, sem cerimônia. Produto decide o que vale construir, design dá forma e identidade, engenharia constrói e prova. Para Claude Code e Codex.

```text
ORBIT.md            o kernel: doze leis, racionalizações, evidência, fechamento
skills/
  hm-engineering/   arquitetura, código, debug, review, segurança, API, dados, LLM, CLI, ship, operação
  hm-design/        direção visual, fluxo, construção e review com render real
  hm-product/       direção, spec, plano, lançamento, growth
hooks/              SessionStart (kernel onde há software) · PreToolUse (guard de dados) · telemetria local e diagnóstico
scripts/            build (audita e gera dist/) · install
```

## As doze leis

Evidência antes de afirmação · critério de sucesso antes de agir · simples primeiro · causa, não caso · referência é piso · cirúrgico · suposição explícita, pergunta rara · autoridade · dados sagrados · segurança day 1 · custo é design · memória com destino. O texto completo, com a tabela de racionalizações que precedem cada falha, está em [ORBIT.md](ORBIT.md).

## Como funciona

**Portas por domínio, profundidade por momento.** Cada skill tem um `SKILL.md` curto que roteia pelo momento do trabalho (build, debug, review, ship, launch...) para um playbook carregado sob demanda. A profundidade só entra no contexto quando é necessária.

**Kernel só onde importa.** O hook SessionStart injeta o `ORBIT.md` quando a sessão abre num repo git com marcador de software. `.orbit` liga em qualquer pasta, `.orbit-off` desliga.

**Dados sagrados como barreira.** O hook PreToolUse pede confirmação antes de comando destrutivo (`rm -rf` fora do temporário da sessão, `reset --hard`, `push --force`, `down -v`, `DROP`, `TRUNCATE`, `DELETE` sem `WHERE` efetivo) e antes de sobrescrever `.env`, banco local ou migration existente. Analisa dentro de `bash -c`, `eval`, `env`, `sudo`, `xargs`, `npx`, substituição de comando e heredoc. Nega só o irreversível de disco e home. É rede de segurança heurística, não sandbox. `HM_ORBIT_GUARD=off` desliga por sessão.

**Evidência executável.** `hm_gate.py` roda typecheck, lint, test e smoke do projeto. `floor_guard.py` mede o trabalho desde o início da sessão e falha quando o diff rebaixa a barra: teste que some, assert trivializado, skip, supressão nova, threshold afrouxado, secret. `NOT_VERIFIED` nunca vira verde.

## Está funcionando?

Os hooks registram o que fazem num log local (`~/.claude/hooks/hm-orbit/telemetry.jsonl`, chmod 600, com rotação; nada sai da máquina): sessões com kernel, decisões e erros do guard, latência e skills acionadas. Comando comum entra só como contagem; texto de comando só quando o guard intervém, com secrets mascarados.

```bash
python3 ~/.claude/hooks/hm-orbit/orbit_status.py          # veredito OK · ATENÇÃO · PROBLEMA
python3 ~/.claude/hooks/hm-orbit/orbit_status.py --days 30
```

Confere hooks registrados, autoteste do guard, erros, latência p95, motivos que mais pedem confirmação (candidatos a falso positivo) e uso das skills. `HM_ORBIT_TELEMETRY=off` desliga o log.

## Instalar

```bash
python3 scripts/install.py            # plano (dry-run)
python3 scripts/install.py --apply    # instala no Claude Code e no Codex
python3 scripts/install.py --uninstall --apply
```

Transacional: preflight antes de qualquer mudança, cópia verificada, lock, rollback que confere o estado restaurado. Nada é apagado; o que sai vai para `~/.claude/skills/.hm-skills-backup/`. Pasta que não é do Orbit, ou modificada por você, nunca é tocada. Hooks de terceiros são preservados. O guard exige Claude Code 2.1.295 ou superior (`onFailure: block`).

## Adaptar à sua casa

`profiles/highermind.md` concentra o gosto e a barra da casa (design, produto, engenharia). Troque pelo seu e rode `python3 scripts/build.py`. O kernel e as skills continuam iguais.

## Licença

MIT.
