# Playbook · Provar que o conselho vale

Conselho que não vence um modelo sozinho com o mesmo gasto é teatro caro. Provar antes de confiar, e de novo quando trocar membros.

## Método (barato e honesto)

1. **Casos:** 20 a 30 decisões reais com desfecho conhecido (bug que existia, número já medido, decisão revertida), mais alguns defeitos plantados de propósito (premissa falsa, número contraditório). Congele o contexto como estava antes do desfecho. Use 10 para ajustar prompts e o resto reservado.
2. **Configurações, mesmo briefing e orçamento comparável:**
   1. o melhor modelo sozinho;
   2. o mesmo modelo N vezes (self-consistency);
   3. vários modelos sem contraste;
   4. o conselho completo.
3. **Métricas definidas antes:** defeitos plantados encontrados, afirmações falsas, achados verdadeiros que o modelo sozinho não deu, violações de restrição, minutos de revisão humana, custo e latência.
4. **Julgamento:** fatos por teste ou evidência; utilidade por humano às cegas (sem saber a configuração). Nunca um LLM como juiz único, e nunca o presidente avaliando o próprio resultado.
5. **Relato:** vitórias, empates e derrotas por caso, com a incerteza. Vinte casos são triagem, não certificação.

## Decisão

Se uma etapa do protocolo não adiciona ganho consistente, corte-a. Se um membro não traz achado exclusivo verdadeiro ao longo dos casos, ele custa sem cobrir. Reavalie quando trocar modelos ou versões.
