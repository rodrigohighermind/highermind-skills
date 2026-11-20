# Playbook · Operate

Carregado no modo `operate` e pelo profile `docker` em manutenção de infra local. Princípio: preservar serviço e dados; diagnosticar com o menor blast radius; runbook destrutivo começa por inventário e backup, nunca por prune, reset ou delete amplo.

## Faxina Docker segura

### Automação primeiro: lixo trivial não precisa de julgamento

Manutenção recorrente é o binário `docker-gc` (bash conservador, agendável no launchd semanal):

- `docker-gc`: `builder prune -f` + `image prune -f` (só dangling). NUNCA toca volume, imagem com tag ou container.
- `docker-gc --dry-run`: diagnóstico sem remover.
- `docker-gc --deep`: inclui `builder prune -a`; pede confirmação no TTY.
- `docker-gc --auto`: modo launchd, silencioso, não abre o Docker se fechado, notifica, loga.

Se o problema é acúmulo de rotina, roda isso e para. O protocolo abaixo é pro caso que exige julgamento: imagens grandes de produto, decidir o que sai.

### Proibições absolutas

- `docker volume prune`. Nunca.
- `docker system prune -a --volumes`. Nunca.
- `docker volume rm <qualquer>` sem confirmação explícita do Owner na sessão.
- Remover imagem com tag de produto sem antes provar onde o dado vive.

### Protocolo assistido (a ordem importa)

1. **Inventário, sem tocar em nada:**
   ```bash
   docker system df -v   # imagens, cache, containers, VOLUMES
   docker volume ls      # mapear cada volume ao produto dono
   ```
   Volumes são o ativo sagrado: não saem nesta faxina, em hipótese alguma.
2. **Descartável puro, sem perguntar:** `docker builder prune -f` + `docker image prune -f` (só dangling; nunca `-a` sem confirmar).
3. **PARE antes de containers e imagens de produto.** `container prune -f` não apaga volume (dado nomeado reconecta no `compose up`), mas costuma listar produtos do Owner: confirmar listando exatamente o que sai. Imagem com tag de produto: provar onde o dado vive antes (grep por Dockerfile/compose que a referencia; dado costuma estar em volume ou Supabase, não na imagem). Custo real de remover imagem = rebuild depois; dizer isso ao Owner.
4. **Cache pesado** (`builder prune -a`): libera cache de builds vivos; próximo build do zero. Confirmar o trade-off.
5. **Docker.raw não encolhe sozinho.** Apagar imagem libera espaço DENTRO do arquivo; devolver disco ao macOS exige quit/reopen do Docker Desktop ou Settings → Resources → Reclaim space. Passo do Owner (afeta o app inteiro), só depois de remover as imagens grandes.
6. **Balanço final:** `docker system df`; contagem de volumes idêntica ao passo 1; containers de produto vivo ainda UP.

Comunicação: sempre separar "espaço liberado dentro do Docker" de "espaço devolvido ao disco" (só o reclaim faz o segundo).

## Observabilidade mínima de qualquer serviço operado

- Logs estruturados (JSON por linha) com contexto suficiente pra debugar, sem secret/token/PII. Rotação por tamanho ou dia.
- **Todo arquivo que cresce sozinho tem teto.** Log, cache, fila, histórico e gerações de backup levam limite de tamanho ou idade e rotação automática, definidos quando o arquivo nasce. Porque crescimento sem limite só aparece quando o disco enche. Arquivo mantido aberto por outro processo (gerenciador de serviços, processo filho) rotaciona por copiar e esvaziar, não por renomear: quem segura o descritor continuaria escrevendo no arquivo antigo. Prova: listar os arquivos que o serviço escreve, o teto de cada um, e forçar uma rotação conferindo que o processo vivo segue escrevendo no arquivo novo.
- Health endpoint que verifica dependências reais; monitorável de fora.
- Erro de produção chega em alguém (alerta, email, canal); não morre em arquivo de log que ninguém lê.
- Jobs agendados (launchd/cron) logam cada run com resultado; job que falha silenciosamente por semanas é incidente em câmera lenta. Verificação: data do último log de sucesso, não existência do plist.

## Job agendado e processo externo

- **Script que roda pelo agendador se prova rodando pelo agendador.** Disparar o job real (`launchctl kickstart -k gui/$UID/<label>` ou equivalente) e ler o estado que ele gravou (log, arquivo de resultado, registro no banco); rodar no terminal não conta. Porque o agendador tem outro ambiente: `PATH` mínimo, sem shell de login, outro diretório de trabalho, e a falha só existe lá. Consequência no código: nada de executável resolvido pelo `PATH` (chamar o próprio runtime pelo caminho do processo atual, como `process.execPath` ou `sys.executable`, e o resto por caminho absoluto). Prova: o log do disparo pelo agendador com resultado de sucesso, de data posterior à mudança.
- **Filho destacado não segura o pipe do pai.** Processo que sobe outro de vida longa (navegador, servidor, daemon) e lê a resposta por pipe espera o filho fechar o pipe herdado, e o filho não fecha. Resposta volta por arquivo (ou socket) e o filho sobe com stdio desligado do pai. Porque o leitor só recebe fim de arquivo quando todo processo que herdou o pipe sai. Prova: a chamada retorna com o processo filho ainda vivo.
- **Tempo de espera sai de medição, não de palpite.** Antes de fixar o limite de espera de um processo externo, medir o maior tempo observado, inclusive a primeira execução a frio, e fixar o limite acima dele com folga declarada. O erro separa as causas: "não abriu dentro do tempo" é diferente de "abriu sem sessão" ou "respondeu com erro". Porque um limite curto disfarçado de outra falha manda o diagnóstico para o lugar errado. Prova: a medição registrada ao lado da constante e um teste ou log que mostra cada causa com mensagem própria.

## Diagnóstico em produção com menor blast radius

- Ler antes de tocar: logs, health, métricas, `git log` do deploy recente. Read-only primeiro.
- Hipóteses ordenadas por probabilidade × custo de verificação; coletar o sinal discriminante mais barato.
- Mitigação reversível antes de correção invasiva: rollback de deploy, feature flag off, restart de UM serviço. Nunca "reseta tudo pra ver se volta".
- Estado suspeito de corrupção: snapshot/backup ANTES de qualquer tentativa de reparo.
- Kill de processo de produção, restore, reset em branch publicada: confirmação explícita do Owner.

## Runbooks

Todo procedimento operacional repetível vira runbook versionado no repo (`docs/runbooks/<nome>.md`) com esta espinha:

1. **Preflight**: pré-condições, o que checar antes.
2. **Inventário**: estado atual capturado (comandos + output esperado).
3. **Backup**: o que salvar e onde, quando o passo é destrutivo.
4. **Ação**: comandos exatos, em ordem, com ponto de parada antes de cada passo irreversível.
5. **Verify**: como provar que funcionou.
6. **Rollback**: como voltar se não funcionou.

Runbook que começa com prune, reset ou delete amplo está errado por construção.

## Guard-rails de custo cloud

Custo é sinal operacional. Em qualquer conta cloud ativa:

- Budget mensal com alertas em degraus (valor real + forecast) apontando pro email do Owner.
- Cost Anomaly Detection com threshold baixo (~$20): pegar o incêndio no dia 1, não na fatura.
- Alerta de custo e email de security advisor são ping de produção, não spam.
- Spike de egress: primeira pergunta é "quem está lendo o quê, de onde, quantas vezes" (CloudTrail data events apontam identidade + IP). Ver `playbooks/performance.md` pra prevenção arquitetural.

## Fechamento de incidente

Incidente fechado sem registro é incidente que volta. Template:

```md
# <slug do incidente>
data: YYYY-MM-DD
sinal: como foi detectado (quem viu, qual alerta)

## Timeline
detecção → diagnóstico → mitigação → resolução, com timestamps

## Causa raiz
a técnica E a sistêmica (o que permitiu que acontecesse)

## Correção
fix aplicado + o permanente (automação, gate, guard-rail) que impede recorrência

## Detecção futura
como será pego mais cedo da próxima vez (alerta, check no gate, script)
```

- **Lei reaproveitável**: se a lição é transversal, cristalizar no incident corpus ou na memória do projeto; se só aplicou padrão conhecido, dizer isso honestamente.
- Incidente com fix pendente (mitigado mas não corrigido) fica marcado como PENDENTE com dono e gatilho; mitigação não encerra causa raiz.
