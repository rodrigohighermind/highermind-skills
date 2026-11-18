# Playbook · Briefing

O conselho só é tão bom quanto o briefing. O erro mais comum de um membro (recomendar o que já foi medido e reprovado) nasce de briefing sem número.

## Estrutura

```markdown
# Decisão: <uma frase>

## Objetivo
O resultado observável que define sucesso.

## Contexto e evidência medida
- Número, comando que o produziu, versão, ambiente e data. "Medido" só com isso.
- O que já foi tentado e reprovado, com o motivo medido.

## Alternativas
Inclusive não fazer nada. Para cada uma: reversibilidade (duas vias ou uma via) e custo de errar.

## Restrições
Orçamento, latência, privacidade, prazo, o que não pode piorar.

## Pergunta
Uma pergunta específica. Peça o desenho do teste que decide.
```

## Regras

- **Mínimo de dado.** Mande o que a decisão precisa, não o repo. Briefing grande custa caro, vaza mais e dilui atenção.
- **Nada confidencial por acidente.** Nomes de cliente e codinomes vão no arquivo de redação (`COUNCIL_REDACT_FILE`); dado pessoal e segredo são redigidos automaticamente, mas regex não anonimiza contexto.
- **Separe fato de opinião.** Escreva "medido", "fonte" ou "hipótese" ao lado de cada afirmação do contexto.
- **`--audit` antes de decisões de uma via:** um membro lista a evidência que falta; meça antes de rodar o conselho completo.
