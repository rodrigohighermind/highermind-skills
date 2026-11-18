# Playbook · Integrity

Carregado sob demanda quando o modo ativo é `integrity` ou `migrate`: schema, migration, RLS, backup, restore, retenção, operação destrutiva, incidente de perda ou corrupção.

## Princípio central

A única perda aceitável de dado é a explicitamente autorizada pelo Owner. Todo o resto é bug. Se um comando errado, um crash mal tratado ou uma migration apressada podem perder dados, o sistema não está pronto pra ter usuários, nem sendo o próprio Owner o único usuário.

Toda perda potencial de dado é finding CRÍTICO. Não existe severidade média ou baixa nesta classe.

## Níveis de criticidade

| Nível | Quando | Regime |
|---|---|---|
| Local single-user | CLI/app pessoal ainda em dev, dado descartável | Backup local automático, migration safety, undo de destrutivos |
| Produção pessoal | App instalado (`.app`, Tauri/Electron com DB em `userData`), single-user em uso real | Tudo do local + TODO destrutivo tratado como prod, confirmação por operação |
| Multi-user privado | CRM interno, ferramenta de time | Tudo acima + replicação, RTO/RPO, audit trail |
| Produção pública | SaaS com clientes | Tudo acima + DR plan, geo-redundância, LGPD/GDPR |

Produção pessoal é a armadilha clássica: roda numa máquina só e parece dev, mas o SQLite em `userData` carrega a única cópia de histórico real (notas, fatos, decisões, finanças). Tratar como prod desde o primeiro build que vai pra `/Applications`. "Local" descreve topologia, não descartabilidade (incident: `personal-production-is-production`).

## Disciplina de schema e migration

Classificar toda migration antes de escrever SQL:

| Classe | Exemplo | Exigência |
|---|---|---|
| Additive | nova tabela, nova coluna nullable, novo índice | preflight + idempotência |
| Dual-write / backfill | coluna nova NOT NULL, mudança de tipo, split de tabela | plano em fases: add nullable → backfill → constraint → cutover |
| Breaking | DROP COLUMN, DROP TABLE, rename com consumidores | backup verificado + confirmação do Owner + janela + rollback plan escrito |

Checklist mecânico:

- Migrations versionadas e sequenciais (Drizzle, Prisma, Alembic, `supabase/migrations`). Journal do ORM bate com o estado real do DB.
- Idempotentes: re-rodar não quebra (`IF NOT EXISTS`, guards, auto-migrate no boot não explode).
- Produção é roll-forward only. Ainda assim o rollback plan existe por escrito antes de aplicar.
- Backup ANTES de qualquer migration não trivial. Automático ou manual, mas documentado e verificado.
- Migration testada contra cópia de prod antes de prod real.
- Índice grande em Postgres: `CREATE INDEX CONCURRENTLY` fora de transaction, nunca lock silencioso.

Anti-patterns que reprovam direto:

- `ALTER COLUMN ... SET NOT NULL` em coluna nova sem default/backfill com rows existentes.
- `DROP COLUMN` sem etapa intermediária read-only (código ainda lê a coluna em algum consumer).
- Schema mudou no código sem migration correspondente (drift silencioso).
- Migration destrutiva executada sem confirmação explícita (DROP, TRUNCATE nunca são silenciosos).

## Dado de teste em banco real

Teste ou smoke que escreve em banco com dado real cria registros com **marcador próprio** (coluna, prefixo ou tag de teste) e remove **só por id exato** dos registros que criou. Nunca por janela de tempo, padrão de texto ou "os últimos N".

Antes de qualquer `DELETE`, rodar `SELECT` com o mesmo `WHERE` e conferir que a contagem é exatamente a esperada. Comparação de data entre formatos diferentes (ISO com `T` contra texto com espaço, timezone, epoch) erra em silêncio: normalizar os dois lados ou comparar por id.

## RLS · regra absoluta (Supabase / Postgres com PostgREST)

Lei `rls-in-same-migration`. O modo de falha clássico: migrations que deixam tabelas dias sem RLS e uma view DEFINER vazando dados entre tenants até alguém notar. Sem RLS, qualquer pessoa com a URL do projeto + anon key lê, edita e deleta a tabela.

1. **Toda `CREATE TABLE` em schema `public` inclui `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY` para cada operação que o app faz pela API (SELECT, INSERT, UPDATE, DELETE), na MESMA migration.** Policy só de leitura numa tabela que o app escreve deixa a feature quebrada; o teste de cada operação prova os dois lados: o dono consegue, o outro tenant é negado. Operação que o app não faz fica sem policy de propósito, e isso se declara. "Faço o RLS depois" é proibido.
2. **Toda `CREATE VIEW` (ou materialized view) que toca fonte com RLS inclui `WITH (security_invoker=true)`.** Postgres 15+ trata view como SECURITY DEFINER por default e bypassa as policies das tabelas-fonte. Exceção só com justificativa escrita de por que precisa rodar como definer.
3. **Antes de fechar sprint em projeto Supabase:** `supabase db advisors --linked --level error` e esperar `No issues found`. Advisor limpo é evidência adicional, não substituto do audit local.
4. Email semanal do Supabase Security Advisor é ping de produção, não spam.

### Padrões SQL executáveis

Tabela multi-tenant por `household_id` (padrão canônico):

```sql
CREATE TABLE public.<name> (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id uuid NOT NULL REFERENCES public.households(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.<name> ENABLE ROW LEVEL SECURITY;

CREATE POLICY "<name>: same household all"
  ON public.<name> FOR ALL TO authenticated
  USING (household_id = public.current_household_id())
  WITH CHECK (household_id = public.current_household_id());
```

Tabela por usuário (`user_id`):

```sql
ALTER TABLE public.<name> ENABLE ROW LEVEL SECURITY;

CREATE POLICY "<name>: owner all"
  ON public.<name> FOR ALL TO authenticated
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (user_id = (SELECT auth.uid()));
```

Tabela interna, só backend (service_role bypassa RLS; habilitar RLS sem policy nega tudo pra anon/authenticated):

```sql
ALTER TABLE public.<name> ENABLE ROW LEVEL SECURITY;
-- sem policy: deny-all para anon e authenticated, service_role continua acessando.
-- comentar a intenção na migration para o audit não flagar como esquecimento:
COMMENT ON TABLE public.<name> IS 'RLS deny-all intencional: acesso exclusivo via service_role';
```

View sobre fonte com RLS:

```sql
CREATE VIEW public.<name> WITH (security_invoker=true) AS
SELECT ...;
```

### Storage policies (Supabase Storage)

Bucket privado sem policy = mesmo furo da tabela sem RLS. `storage.objects` já tem RLS habilitado; sem policy, nada é lido nem escrito por authenticated. Padrão com prefixo de tenant no path (`<household_id>/...`):

```sql
CREATE POLICY "arquivos: same household read"
  ON storage.objects FOR SELECT TO authenticated
  USING (
    bucket_id = 'arquivos'
    AND (storage.foldername(name))[1] = public.current_household_id()::text
  );

CREATE POLICY "arquivos: same household write"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'arquivos'
    AND (storage.foldername(name))[1] = public.current_household_id()::text
  );
```

DELETE e UPDATE ganham policies próprias e explícitas, nunca `FOR ALL` por conveniência em storage: apagar objeto é destrutivo e merece policy pensada.

### Detecção automatizada

- Referência canônica: um `scripts/audit-rls.sh` mais `scripts/git-hooks/pre-commit` (esqueleto no playbook security). Copiar pra todo projeto Supabase novo no setup, não reescrever do zero.
- O audit estático varre migrations novas: todo `CREATE TABLE public.*` precisa de `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY` adjacentes no mesmo arquivo; todo `CREATE [MATERIALIZED] VIEW` precisa de `security_invoker=true` ou comentário de justificativa.
- Grep mínimo quando o script não existe ainda:

```bash
grep -RlE 'CREATE TABLE (IF NOT EXISTS )?public\.' supabase/migrations \
  | xargs grep -LE 'ENABLE ROW LEVEL SECURITY'
grep -RlE 'CREATE (MATERIALIZED )?VIEW' supabase/migrations \
  | xargs grep -LE 'security_invoker'
```

Saída não vazia = migration furada = FAIL antes de commit.

## Operações destrutivas

Lista canônica que EXIGE confirmação explícita do Owner. Autorização vale só pra sessão atual e operação específica: não retroage, não se estende a operações parecidas.

- `docker compose down -v` (apaga volumes nomeados, destrói DB)
- `rm -rf` em path não temporário
- `git push --force` em qualquer branch
- `git reset --hard` em branch publicada · delete de branch publicada no remote
- `DROP TABLE` · `DROP DATABASE` · `DROP SCHEMA`
- `TRUNCATE` em tabela com dados
- `DELETE` ou `UPDATE` em massa sem `WHERE` específico
- Kill de processo de produção
- Reset/sobrescrever DB em produção pessoal (SQLite em `userData`/`AppData`)
- Reset de profile/facts/memória persistente em app pessoal em uso
- Restore de backup que sobrescreve estado atual sem snapshot do atual antes

Guardas de implementação:

- Soft-delete por default (`deleted_at`), hard-delete é exceção auditada com recovery window antes do purge real.
- DELETE sem WHERE bloqueado na camada de dados (ORM/raw SQL não executa `DELETE FROM x` puro).
- Backup automático antes de bulk operation, mesmo autorizada.
- Audit log de destrutivos: quem, quando, o quê.
- Alvo sempre resolvido por id real, nunca por posição em lista ou nome parecido.

Padrão de confirmação em CLI:

```text
$ tool delete user 123
ERROR: Destructive operation. Add --force to confirm.

$ tool delete user 123 --force
Backing up 48 affected rows to ~/.tool/backups/delete-user-123.json
Deleted 1 user, 47 related records. Undo: tool restore <backup-path>
```

## Scripts de teste auditados antes de rodar

Exemplo do modo de falha: um script de teste começa com `await db.delete(schedules)` e o cascade de FK destrói milhares de linhas de um cronograma real de produção. A recuperação depende de sorte (um arquivo de importação que ainda existia).

Regra: antes de rodar QUALQUER script de teste que toque banco (`npm run test:*`, `scripts/test-*.ts`, seeds, fixtures), ler o arquivo inteiro e procurar:

```bash
grep -nE 'db\.delete\(|TRUNCATE|DROP |DELETE FROM|CASCADE|deleteMany|\.destroy\(' scripts/test-*.ts
```

- Achou operação em tabela-raiz: PARAR. Refatorar antes de rodar.
- Padrão correto: escopo efêmero isolado (project/tenant/schedule com slug `__test-*` ou `__smoke-*`), `try/finally` que limpa SÓ esse escopo pelo id criado.
- Não confiar no nome do script. "Smoke test" pode destruir.
- Em projeto com dados reais (de cliente ou pessoais), essa leitura é gate, não sugestão.

## Backup

| Check | Critério |
|---|---|
| Automático | Existe e dispara sozinho (schedule ou evento como `before-quit`) |
| Atômico | Snapshot consistente: sqlite `.backup`/`VACUUM INTO`, `pg_dump --serializable`, nunca `cp` de DB quente |
| Versionado | Múltiplas gerações com timestamp, não só "o último" |
| Criptografado | Em repouso e em trânsito quando sai da máquina |
| Off-site | Cópia geográfica separada pra dado que importa (S3 outra região, git remoto privado) |
| Testado | Já restaurou de verdade? Se não, não é backup, é esperança |

Patterns por nível:

```bash
# SQLite (produção pessoal): snapshot atômico com timestamp
sqlite3 ~/.app/db.sqlite ".backup '~/.app/backups/db-$(date +%Y%m%d-%H%M%S).sqlite'"

# Postgres/Supabase
pg_dump "$DATABASE_URL" --format=custom --file="backup-$(date +%Y%m%d).dump"
supabase db dump --linked -f "backup-$(date +%Y%m%d).sql"

# Files/blob: incremental criptografado
rclone sync ~/data remote:bucket --backup-dir remote:bucket-versions/$(date +%Y%m%d)
```

Multi-user e produção pública: backup contínuo (wal-g ou PITR do provider) + bucket versionado. Blob crítico: checksum SHA256 no upload, versioning no bucket, replication cross-region, object lock quando compliance exigir.

## Restore testado

Backup nunca restaurado permanece `NOT_VERIFIED`, e no audit marca FAIL. O drill é barato:

```bash
# restaurar em alvo descartável e validar contagens
createdb restore_drill && pg_restore --dbname=restore_drill backup.dump
psql restore_drill -c "SELECT count(*) FROM <tabela_core>;"  # comparar com prod

sqlite3 /tmp/drill.sqlite ".restore '~/.app/backups/db-<ts>.sqlite'"
sqlite3 /tmp/drill.sqlite "PRAGMA integrity_check; SELECT count(*) FROM <tabela_core>;"
```

Registrar data do último drill. Multi-user/produção: drill completo ao menos 1x/ano, cenário "disco morto" obrigatório no plano.

## Retenção

- Owner aprova a política. Default conservador: não apagar nada que pode ser útil.
- Baseline quando não há exigência específica: daily 7d · weekly 4w · monthly 12m.
- Retenção também vale pra backup: purge de gerações antigas é operação destrutiva, entra no regime de confirmação na primeira definição da política, depois roda automático.
- LGPD/GDPR quando aplicável: right to erasure inclui backups após a janela de retention; right to access exporta tudo em formato legível; breach notification de 72h documentado. Compliance falha = não shippa pra mercado regulado.

## Integridade em runtime

- Multi-table writes em transaction. Atomicidade não é otimização, é correção.
- Foreign keys com `ON DELETE` decidido conscientemente (CASCADE vs RESTRICT vs SET NULL), sem orphans.
- `UNIQUE`, `NOT NULL` e `CHECK` no banco, não só na aplicação (`amount >= 0`, enum válido).
- Optimistic concurrency (`version` ou `updated_at` no WHERE do UPDATE) onde há write concorrente.
- Idempotency key em operação disparada externamente (webhook, payment, email).
- JSON persistido tem `schemaVersion` + `safeParse` (Zod/Pydantic) em toda leitura. Cast cego de `JSON.parse` é corrupção esperando data pra aparecer. Migração v1→v2 documentada e app lê ambas durante a transição.

## Disaster recovery (multi-user / produção pública)

| Métrica | Pergunta | Típico |
|---|---|---|
| RPO | quanto dado pode perder? | 5min a 1h conforme criticidade |
| RTO | quanto tempo pra voltar? | 15min a 4h |

Cenários mínimos documentados: DB corrompido, região do provider down, ransomware, dev errou comando. Runbook passo a passo acessível mesmo com o app fora do ar.

## Identidade não-mergeável

Lei `identity-merge-needs-evidence-and-undo`. Similaridade de nome nunca prova que duas entidades humanas são a mesma pessoa. Exemplo: dois contatos com o mesmo primeiro nome, um deles com um qualificador entre parênteses, eram pessoas distintas; o qualificador era distinção intencional do Owner, não duplicata.

- Identidade de pessoa, contrato e transação é decisão do Owner. O agente não decide quem é quem.
- Nome com qualificador ("X (relação)", "Tia X", "Pai") é sinal forte de distinção, não de duplicação.
- Sugerir merge só quando: dois placeholders genéricos similares, ou o Owner perguntou explicitamente se são a mesma pessoa.
- Merge autorizado exige: evidência forte, consequências mostradas antes, confirmação, e unmerge auditável (guardar o estado pré-merge). Merge sem undo é destrutivo.

## Observabilidade de integridade

Detectar cedo, não descobrir na perda:

- Alerta quando backup falha (silêncio de backup é o pior modo de falha).
- Alerta de crescimento anômalo de DB e de rate alto de DELETE (bug ou ataque).
- `PRAGMA integrity_check` / checksum periódico em arquivo que é ativo.
- Painel mínimo: volume, data do último backup ok, data do último restore drill.

## Veredicto

- Perda potencial de dado: CRÍTICO, sem exceção.
- Backup nunca restaurado: FAIL.
- Migration sem rollback plan em produção: CRÍTICO.
- Tabela `public` sem RLS na mesma migration: FAIL, bloqueia commit.
- Destrutivo sem confirmação em superfície exposta: CRÍTICO.
- Advisor não rodado ao fechar sprint Supabase: sprint não fecha.
