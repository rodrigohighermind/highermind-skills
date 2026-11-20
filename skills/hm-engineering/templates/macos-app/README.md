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
| Menu e gestos | menu principal com Editar padrão (sem ele ⌘V, ⌘C, ⌘X, ⌘A e ⌘Z não chegam a nenhum campo de texto, nem para quem cola nele); só a faixa livre da barra de título arrasta a janela (o resto do conteúdo seleciona texto); duplo clique nela segue a preferência do sistema (ampliar, minimizar ou nada) e sempre muda o tamanho, inclusive com a janela reaberta ampliada |
| Clique | todo botão usa `.buttonStyle(.clickable)` e toda linha ou cartão clicável `.clickable()`: mãozinha, seta quando desabilitado. Teste do app reprova `.plain`, `.borderless` e toque sem o estilo; exceção declarada na linha com `// pointer: exceção` |
| Texto | palavra por extenso: `WordsTests` reprova formatador `.abbreviated`, `EEE`/`MMM` curtos, "N min", "ex.:" e dia ou mês abreviado em literal; exceção declarada na linha |
| Tokens | cores dinâmicas e papéis tipográficos em `Theme.swift`; curva de movimento nomeada |
| Ajustes | camada de Ajustes da casa: cartão 960 x 660 sobre a janela escurecida, coluna de seções de 220 pt, uma linha por ajuste com o controle à direita; abre por ⌘, (menu do app) e pelo botão da página inicial. Começa com Aparência (tema) e Sobre |
| Camada por cima | fundo em camada própria só com fade cobrindo a janela inteira; caixa sem fantasma, com mola; saída junto; reduzir movimento = fade |
| Instalação | assina com "Apple Development" se houver (mantém permissões entre builds); senão ad-hoc com aviso; verificação de vida |
| Permissões | `permissions.json` é a fonte única: gera as descrições de uso do Info.plist **e** os entitlements da assinatura (hardened runtime). O install confere o app assinado e recusa instalar se faltar entitlement, porque a permissão seria negada sem janela e sem erro. HealthKit, câmera, calendário, contatos, localização, fotos e microfone mapeados. |
| QA | `APP_PREVIEW`, `APP_SLOW_MOTION`, `APP_DEMO_MODAL`, `APP_DEMO_TITLE_DOUBLE_CLICK` (dois cliques duplos reais, imprime o frame antes, ampliado e restaurado), `APP_SMOKE`, `APP_BACKGROUND` (janela atrás de tudo, sem tomar o foco, para capturar com a máquina em uso); `tools/design_parity.py` (≤1 pt, com contraprova); evidência em `.orbit/review/` |
| Gate | `hm-quality.json`: typecheck, lint (release sem warning), `swift test`, smoke e `macos_apps` para o check de SDK |

## Testes do starter

```bash
python3 -m unittest discover -s tests
```
