# OpenRouter — IA free só com conteúdo escolar

**Status:** implementado no back-end (`api/src/educachat/generation/openrouter.py`). Falta a chave real (`OPENROUTER_API_KEY`) para rodar a avaliação e o chat de ponta a ponta.

## Decisão

Usar [OpenRouter](https://openrouter.ai/docs/guides/routing/model-variants/free) com um modelo `:free` fixo como motor de linguagem do EducaChat. O padrão do `.env.example` é `meta-llama/llama-3.3-70b-instruct:free`.

- Lista de modelos: https://openrouter.ai/models
- Limites: https://openrouter.ai/docs/api_reference/limits
- Roteador aleatório (não usar): https://openrouter.ai/openrouter/free

O OpenRouter **não** é uma IA escolar. É um LLM geral. Quem restringe à série do aluno é o EducaChat.

## Como está implementado

1. A série vem do perfil autenticado (tabela `perfis`), nunca da requisição.
2. **Chroma + BNCC:** o protótipo recupera as 5 habilidades mais próximas da pergunta, só entre as válidas no ano do aluno (`ano_inicial <= ano <= ano_final`), em qualquer um dos 9 componentes.
3. Antes de chamar o OpenRouter, o protótipo confere que nenhuma habilidade recuperada é de outra série. Se houver, ele para sem chamar o LLM.
4. **Prompt de sistema** (`generation/prompts.py`): explicar com linguagem da série; recusar tarefa, redação ou exercício pronto e orientar; redirecionar pergunta não escolar; citar o código BNCC usado.
5. O protótipo manda usar só as habilidades recebidas e avisar quando o conteúdo não é da série do aluno.
6. **Cliente:** retry com backoff exponencial e jitter em 429, 408, 5xx, timeout e falha de rede, respeitando `Retry-After`. Erros definitivos (400, 401, 402, 404) sobem na hora.

Diferença em relação ao plano: o plano previa condução pelo método socrático em três modos. O prompt atual explica em vez de conduzir só por perguntas, e há um único modo.

## Limites free (para o artigo)

- Cerca de 50 pedidos/dia e 20/minuto nos modelos `:free` ([limites](https://openrouter.ai/docs/api_reference/limits), [preço Free](https://openrouter.ai/pricing)).
- Após crédito único de US$ 10: cerca de 1000/dia.
- A avaliação completa são 151 consultas × 2 condições = 302 chamadas. No limite de 50/dia, isso leva vários dias. O harness salva o progresso e retoma com `--retomar-ultimo`.
- Serve para **demo da disciplina**; não serve para uma escola inteira (limitação do protótipo).

## LGPD

A conversa do aluno vai para o OpenRouter, que é tratamento internacional de dados (art. 33 da LGPD; ver 1.4 do artigo). No protótipo: só contas de teste, sem nome real nem dado sensível. Conversa de aluno real fica bloqueada até haver termo de responsável e cláusulas-padrão (Resolução CD/ANPD nº 19/2024).
