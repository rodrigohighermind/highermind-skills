# __APP_NAME__

App nativo macOS gerado pelo starter. Nada aqui é livre: cada escolha abaixo já foi medida e provada.

## O que já vem pronto

- **Build:** SwiftPM com `platforms: .macOS("26.0")`. O binário grava o SDK atual, então o sistema desenha o chrome atual (com piso antigo, desenha o legado: botões menores e cinza). Zero warning é regra.
- **Janela:** botões nativos reposicionados numa geometria fixa (`Layout.swift`), reaplicada a cada resize; o chrome segue o sistema e o conteúdo segue o tema do app; tamanho mínimo honesto; barra lateral recolhível pelo botão do título; conteúdo centraliza quando sobra largura.
- **Tokens:** cores claro/escuro e papéis tipográficos em `Theme.swift`; uma curva de movimento nomeada (`Motion.state`) para toda mudança de estado.
- **Camada por cima:** fundo escurecido em camada própria, só com fade, cobrindo a janela inteira; caixa com opacidade rápida (sem fantasma do texto de trás) e escala com mola; sai junto com o fundo; reduzir movimento = só fade.
- **Instalação:** `scripts/install.sh` monta o `.app` em `~/Applications`, assina com a identidade "Apple Development" se existir (senão ad-hoc, com aviso de que as permissões serão pedidas a cada build) e termina com `installed and alive`.

## Ganchos de QA

| Variável | Efeito |
|---|---|
| `APP_PREVIEW=<page>` | abre direto na página |
| `APP_SLOW_MOTION=8` | todas as animações 8 vezes mais lentas, para conferir quadro a quadro |
| `APP_DEMO_MODAL=1` | abre e fecha o modal de exemplo sozinho |
| `APP_SMOKE=1` | abre a janela e encerra em 2 s (usado pelo smoke) |

Paridade com uma referência: capture as duas janelas em 2x (`screencapture -o -l <id>`) e rode
`python3 tools/design_parity.py <nosso.png> <referencia.png>` (tolerância de 1 pt; a referência contra ela mesma tem de dar PASS).
Evidência visual vai em `.orbit/review/` (fora do git).

## Gate

`hm-quality.json` declara typecheck, lint (build release sem warning), testes (`swift test`), smoke e o app instalado para o check de SDK:

```bash
python3 ~/.claude/skills/hm-engineering/scripts/hm_gate.py --root . --distribution personal
```
