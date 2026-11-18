# Starter de app nativo macOS

Gera um app SwiftUI/AppKit que já nasce no padrão: chrome nativo atual, tokens claro/escuro, camada por cima com transição correta, QA embutido e gate verde desde o primeiro commit. Ninguém edita o template à mão.

```bash
python3 new_app.py "Meu App" com.empresa.meu-app ~/Projetos/meu-app
cd ~/Projetos/meu-app && ./scripts/install.sh     # termina com "installed and alive"
```

O gerador troca nome visível (aceita espaço e acento), módulo Swift e bundle id em conteúdo e caminhos, cria o git com o primeiro commit e recusa destino existente sem tocar em nada.

## O que o app gerado já traz

| Área | Padrão |
|---|---|
| Build | `platforms: .macOS("26.0")`: o binário grava o SDK atual (com piso antigo o sistema desenha chrome legado). Zero warning. |
| Janela | botões nativos na geometria de `Layout.swift`, reaplicada em todo resize; chrome segue o sistema, conteúdo segue o tema; tamanho mínimo honesto; barra lateral recolhível; conteúdo centraliza quando sobra largura |
| Tokens | cores dinâmicas e papéis tipográficos em `Theme.swift`; curva de movimento nomeada |
| Camada por cima | fundo em camada própria só com fade cobrindo a janela inteira; caixa sem fantasma, com mola; saída junto; reduzir movimento = fade |
| Instalação | assina com "Apple Development" se houver (mantém permissões entre builds); senão ad-hoc com aviso; verificação de vida |
| QA | `APP_PREVIEW`, `APP_SLOW_MOTION`, `APP_DEMO_MODAL`, `APP_SMOKE`; `tools/design_parity.py` (≤1 pt, com contraprova); evidência em `.orbit/review/` |
| Gate | `hm-quality.json`: typecheck, lint (release sem warning), `swift test`, smoke e `macos_apps` para o check de SDK |

## Testes do starter

```bash
python3 -m unittest discover -s tests
```
