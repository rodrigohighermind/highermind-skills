# Playbook · build

Feature ou refactor autorizado. Do pedido ao diff comprovado, sem cerimônia e sem perder o fio em trabalho longo.

## 1. Tamanho decide o processo

| Tamanho | Processo |
|---|---|
| Até ~1 hora, 1 a 3 arquivos | Critério + implementar + provar, inline. Sem plano escrito. |
| Várias fatias, várias horas | Plano curto no repo (`docs/plans/<slug>.md`), execução fatia a fatia. |
| Plano grande e estável, fatias independentes | Plano + um subagente por fatia + review em dois estágios (seção 4). |

Cerimônia proporcional. Plano para mudança de 20 linhas é desperdício; trabalho de 6 horas sem plano perde o fio na compactação.

## 2. Plano

Escrito para um executor competente sem nenhum contexto do projeto. Cada fatia tem:

```text
### Fatia N · <nome>
Arquivos:  path exato (criar | alterar)
Faz:       o que muda, em 1 a 3 linhas
Teste:     qual teste nasce ou muda (seguir a regra de testes da skill)
verify:    comando exato + resultado esperado
```

Regras:

- Fatia é uma mudança coerente e verificável sozinha. Se o `verify:` dela não consegue falhar de forma útil, está grande ou vaga demais.
- Fatia vertical: entrega comportamento observável, não "camada".
- Ordem por dependência e risco: o que pode invalidar o plano vai primeiro.
- Nada de "tratar erros adequadamente" ou "adicionar validação": dizer qual erro, qual validação.
- Decisão de produto que aparece no plano vai para o Owner antes de executar, não no meio.

## 3. Execução inline

Uma fatia por vez: implementar, rodar o `verify:`, ler a saída. Commit quando a mudança é coerente e verificada, não por cronômetro, mensagem `tipo(escopo): descrição`. Fatia que falha não avança: corrigir e rodar o `verify:` de novo, sozinho; se a mesma falha resiste a três tentativas com hipóteses diferentes, aplicar o playbook debug ou replanejar, nunca devolver o erro ao Owner como se fosse decisão dele. Desvio do plano é declarado e registrado no próprio plano.

## 4. Execução com subagentes

Usar quando o plano é grande, as fatias são independentes e o contexto principal precisa ficar limpo para coordenar.

**Brief do subagente** (é o único contexto que ele terá):

```text
Objetivo:     a fatia, com o critério de sucesso
Contexto:     paths relevantes, convenções do repo, o que já foi decidido
Limites:      arquivos que pode tocar; o que é proibido (escopo, destrutivo, deps novas)
Prova:        o verify: exato que precisa rodar e colar no relatório
Relatório:    arquivos alterados, saída do verify, desvios, dúvidas
```

**Review em dois estágios**, nesta ordem, depois de cada fatia:

1. **Conformidade com a spec:** o diff faz exatamente o que a fatia pede? Nada a menos, nada a mais? Linha fora do escopo é defeito.
2. **Qualidade:** correção, segurança, simplicidade, padrões do repo, testes reais (não teste que passa sem exercitar o código).

O revisor recebe o diff e a fatia, não a conclusão do implementador. Problema crítico volta para correção antes da próxima fatia.

**Nunca confiar no relatório.** `git diff` + rodar o `verify:` no contexto principal. "Subagente disse que passou" não é evidência.

Paralelismo só para fatias que não compartilham arquivo nem estado. Na dúvida, sequencial.

## 5. Fechamento

- `floor_guard.py` mede desde o SHA do início da sessão (o hook grava em `.git/orbit-base`); sem hook, anotar `git rev-parse HEAD` antes da primeira mudança e passar `--since`.
- Reler o plano e checar fatia por fatia contra o diff final.
- Rodar o gate completo (`scripts/hm_gate.py`) e o smoke do fluxo principal.
- Plano concluído: mover decisões duráveis para `MEMORY.md`/ADR; o arquivo de plano pode ser apagado ou arquivado.
- Branch e worktree só quando o repo tem colaborador ou o Owner quer ver o diff em PR. Default é commit disciplinado na `main`.
