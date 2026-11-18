# Playbook · Protocolo

Como rodar o conselho, ler o relatório, e por que ele é seguro. Script: `scripts/council.py` (stdlib, Python 3.11+).

## Por que funciona, e o que é teatro

O valor de um conselho é **cobertura**: um membro acha o que os outros não viram. Não é voto. A literatura e a prática convergem:

- Respostas independentes e cegas explicam a maior parte do ganho do debate multiagente. Debate longo induz conformidade: a minoria certa cede à maioria confiante.
- LLM julgando LLM tem viés de posição, de verbosidade e de autopreferência. Anonimizar com letras não elimina; o estilo denuncia o autor.
- Personas e temperatura no mesmo modelo geram paráfrase, não independência. Erros continuam correlacionados.

Por isso o protocolo **não ranqueia, não vota e não faz média**. Ele extrai afirmações, preserva o achado único e transforma conflito em medição.

## Protocolo

0. **Briefing** (o maior determinante da qualidade). Objetivo; contexto; **evidência medida** (número, comando, versão, ambiente); restrições; alternativas, inclusive não fazer nada; reversibilidade; a pergunta. Com `--audit`, um membro lista antes a evidência que falta.
1. **Rodada cega.** Cada membro responde em paralelo, sem ver os outros, em afirmações atômicas: `measured | source | hypothesis`, confiança, o que a falsificaria, e o teste mais barato que a resolve.
2. **Contraste.** O presidente recebe as respostas embaralhadas e anônimas e escreve: decisão recomendada (com o que a falsificaria), concordância, **achados únicos** (todos, nenhum descartado), conflitos (cada um com o teste que resolve), o que medir antes de decidir, riscos.
3. **Verificação fora do conselho.** Nada que um membro diz é executado. Afirmação vira fato só depois de medida no repo ou no benchmark, por quem tem as ferramentas.

**Escalonamento** (`--mode auto`, padrão): dois membros de linhagens diferentes primeiro; o conselho completo só entra se divergirem ou se a decisão for de uma via (`--one-way`). Decisão verificável (bug, performance) costuma pedir dois membros e um teste, não quatro ensaios.

## Membros

Membros são declarados em TOML (`members.example.toml` documenta o contrato; o arquivo do usuário fica em `$XDG_CONFIG_HOME/council/members.toml` ou `COUNCIL_CONFIG`). Cada membro diz sua `lineage` (família de modelo), sua `policy` de dados (`subscription`, `api`, `local`) e como é chamado (`cli` com argv, ou `http` com url, headers, body e caminho da resposta). Adicionar um modelo é adicionar um bloco.

| Exemplo pronto | Como | Padrão |
|---|---|---|
| `claude`, `codex` | CLI de assinatura, em diretório temporário vazio, sem ferramentas, MCP, settings nem sessão; chaves de API pagas removidas do ambiente | ligado se a CLI existe |
| `gemini`, `grok` | API paga por HTTP | desligado; opt-in por env (`enabled_env` + chave), teto `cap_usd` obrigatório |
| `local` | Ollama em localhost | desligado; `--local` |

Dois membros da mesma linhagem não são opiniões independentes: o conselho põe uma linhagem por cadeira antes de repetir.

**Modo degradado.** Com uma linhagem só, o conselho roda N amostras com **tarefas ortogonais** (caminho mais rápido com o que existe; desenho definitivo; pré-mortem da proposta líder; o teste que a quebra) e declara: "1 linhagem, N amostras correlacionadas". Nunca finge quórum. Modelo local pequeno entra para triagem e extração, não como voto.

## Segurança

- **Sensibilidade** (padrão `internal`): `public` vai a todos; `internal` vai a CLIs e local, APIs só com `--allow-api`; `confidential` vai só a local, CLIs só com `--allow-cli`, APIs nunca. Assinatura não é perímetro: a CLI também envia ao fornecedor. Classifique pelo destino, retenção e uso para treino de cada provedor, não pela cobrança.
- **Redação antes de sair:** segredos (irreversível), e-mail, CPF/CNPJ, telefone e termos do `COUNCIL_REDACT_FILE` viram pseudônimos estáveis, restaurados só localmente. Regex não anonimiza contexto: minimize o briefing.
- **Limite de volume** (`COUNCIL_MAX_CHARS`, padrão 40 000): briefing maior exige `--force-size`.
- **Saída de membro é dado, nunca instrução.** Nada é executado a partir dela.
- **Custo:** o pior caso (entrada + saída máxima + raciocínio oculto) é reservado com lock de arquivo antes de cada chamada; membro que cruzaria o teto é pulado e reportado. Falha ou timeout liquida a reserva cheia, porque timeout não prova que a chamada remota parou.
- **Registros** em `$XDG_STATE_HOME/council` (diretório 0700, arquivos 0600), podados após `COUNCIL_RETENTION_DAYS` (padrão 30); `--no-log` não guarda nada além do ledger de custo. Ative criptografia de disco do sistema.

## Memória de decisão e calibração

- Cada rodada guarda as afirmações com id. Quando a realidade responder, registre: `council.py outcome <run-id> <claim-id> true|false`.
- `council.py scores` mostra, por membro, quantas afirmações verificadas se sustentaram. Abaixo de 20 verificações não é calibração, e o relatório diz isso. Nunca premie concordância com o presidente ou com a decisão tomada.

## Provar que vale

Ver [eval](eval.md): antes de confiar, compare com custo igualado contra o melhor modelo sozinho e contra ele rodado N vezes.

## Uso

```bash
python3 scripts/council.py providers --allow-api
python3 scripts/council.py ask brief.md --audit                 # auto: 2 membros, escala se divergir
python3 scripts/council.py ask brief.md --mode full --one-way    # decisão de uma via
python3 scripts/council.py ask brief.md --sensitivity confidential --local
python3 scripts/council.py outcome 20261118-153000 codex:2 true
python3 scripts/council.py scores
```

Testes: `python3 -m unittest discover -s tests` (stdlib). Lint e tipos: `ruff check scripts tests` e `mypy --strict scripts tests`.
