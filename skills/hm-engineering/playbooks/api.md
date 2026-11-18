# Playbook · api

Contrato público ou entre serviços: REST, RPC, webhook, SDK, schema de evento. API é decisão de uma via: depois que alguém integra, mudar custa caro para os dois lados. Desenhar o contrato antes do código.

## 1. Contrato primeiro

- Schema versionado no repo (OpenAPI, JSON Schema, Zod ou Pydantic exportado) é a fonte; tipos e docs derivam dele.
- Nomear por recurso e intenção do consumidor, não pela tabela do banco. Campo exposto é campo que você vai manter para sempre.
- Exemplo de request e response reais no contrato. Contrato sem exemplo é ambíguo.

## 2. Modelo de erro único

```json
{ "error": { "code": "invoice_already_paid", "message": "Fatura já paga.", "request_id": "req_8f2c", "retryable": false } }
```

- `code` estável e legível por máquina; `message` para humanos; `request_id` sempre; `retryable` explícito.
- Status HTTP honesto: 400 entrada inválida, 401 sem identidade, 403 sem permissão, 404 inexistente ou invisível para quem pede, 409 conflito de estado, 422 regra de negócio, 429 limite, 5xx só falha nossa.
- Nunca vazar stack trace, SQL ou nome de tabela.

## 3. Garantias que o consumidor precisa

- **Idempotência:** toda mutação com efeito externo (cobrança, envio, criação) aceita `Idempotency-Key` e devolve o mesmo resultado na repetição.
- **Paginação por cursor**, com limite máximo no servidor. Offset só para listas pequenas e estáveis.
- **Consistência declarada:** o que é síncrono, o que é eventual, e em quanto tempo.
- **Rate limit** por identidade, com `429` e `Retry-After`.
- **Timeout e cancelamento** dos dois lados; operação longa vira job com status consultável.

## 4. Evolução sem quebrar

- Mudança aditiva (campo novo opcional, endpoint novo) é livre. Remover, renomear ou mudar tipo ou semântica é breaking.
- Breaking exige versão nova, período de coexistência, aviso de depreciação (`Deprecation`/`Sunset`) e medição de quem ainda usa a versão antiga antes de desligar.
- Consumidor tolerante: ignorar campo desconhecido, nunca falhar por campo extra.

## 5. Webhooks

Assinatura HMAC com timestamp (rejeitar acima de 5 minutos), entrega pelo menos uma vez com retry exponencial, `event_id` para dedupe no receptor, payload mínimo com o id para buscar o estado atual. O receptor responde 2xx rápido e processa assíncrono.

## 6. Autorização

Toda rota checa identidade **e** posse do recurso, no servidor. Id difícil de adivinhar não é autorização. Multi-tenant: o tenant vem da sessão, nunca do body ou da query. Teste de negação (usuário A pedindo recurso de B) é obrigatório em rota nova.

## 7. Verificação

Teste de contrato (request real contra o schema), teste de erro para cada `code`, teste de idempotência (mesma key duas vezes), teste de autorização negativa. Mudança no schema roda o diff de compatibilidade antes do merge.
