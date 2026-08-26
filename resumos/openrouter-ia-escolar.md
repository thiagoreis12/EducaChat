# OpenRouter — IA free só com conteúdo escolar

**Card Trello:** criado no Backlog (`[Stack] OpenRouter — IA free`).  
**Status:** decisão registrada — ainda não implementar a API.

## Decisão

Usar [OpenRouter](https://openrouter.ai/docs/guides/routing/model-variants/free) com um modelo `:free` como motor de IA do EducaChat.

- Lista de modelos: https://openrouter.ai/models
- Limites: https://openrouter.ai/docs/api_reference/limits
- Roteador aleatório (evitar no tutoria): https://openrouter.ai/openrouter/free

O OpenRouter **não** é uma IA escolar. É um LLM geral. Quem restringe a “só conteúdo da série” é o EducaChat.

## Regras do produto

1. Aluno informa a **série** no cadastro (a partir do 6º ano).
2. **Chroma + BNCC:** recuperar só trechos daquela série e das matérias do MVP (Matemática, Português, Ciências, conhecimentos gerais).
3. **Método socrático:** não entregar trabalho pronto; recusar outra série, assunto fora do recorte ou pedido do tipo “faz a redação pra mim”.
4. Se não houver trecho da série no Chroma: dizer que não está no material da série — **não inventar**.

## Limites free (para o artigo)

- Cerca de 50 pedidos/dia e 20/minuto nos modelos `:free` ([limites](https://openrouter.ai/docs/api_reference/limits), [preço Free](https://openrouter.ai/pricing)).
- Após crédito único de US$ 10: cerca de 1000/dia.
- Serve para **demo da disciplina**; não serve para uma escola inteira (limitação do protótipo).
- Usar um **modelo fixo** `:free`, não o roteador `openrouter/free`.

## LGPD

A conversa do aluno vai para o OpenRouter. No protótipo: não pedir nome real, usar e-mail de teste, não guardar dado sensível.

## Prompt para o Cursor (quando o card for para Em Desenvolvimento)

```
Use OpenRouter como único provedor de LLM do EducaChat.
Modelo: um slug `:free` fixo (consultar https://openrouter.ai/models na hora; NÃO usar openrouter/free aleatório).
Base URL: https://openrouter.ai/api/v1
Chave: OPENROUTER_API_KEY no .env (nunca commitar).

NÃO ligue o chat completo neste card. Apenas:
1) registrar a decisão no README
2) arquivo .env.example com OPENROUTER_API_KEY e OPENROUTER_MODEL
3) rascunho do system prompt socrático (recusar trabalho pronto; só série do aluno; só Matemática, Português, Ciências, conhecimentos gerais; se não houver trecho no Chroma, não inventar).

Não instale Vue, FastAPI ou Chroma neste card se ainda não existirem. Pare para validação.
```
