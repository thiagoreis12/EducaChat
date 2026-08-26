# EducaChat

Assistente virtual escolar (protótipo acadêmico — ADS / ETEP 2026.2). O chat não entrega a resposta pronta: guia o aluno pelo método socrático e usa só conteúdo da série informada no cadastro (a partir do 6º ano).

Matérias do MVP: Matemática, Português, Ciências e conhecimentos gerais.

## Stack prevista

| Camada | Tecnologia |
|---|---|
| Front | Vue 3 + Vite |
| Back | Python + FastAPI |
| Usuários / série | Supabase (PostgreSQL, plano free) |
| Material da série | ChromaDB local |
| IA | OpenRouter (modelo `:free`) — API entra depois |
| Quadro | Trello (Kanban) |

Ainda não há código do app neste repositório. O que está versionado agora é o planejamento: artigo extensionista (Fase 1 em rascunho) e recortes de decisão.

## Pastas

- `Artigo/` — entregas do artigo (Fase 1: 02/09/2026, 20h)
- `resumos/` — recorte do projeto, resumo 1.1 e decisão OpenRouter

## Próximo passo

Não ligar a API ainda. Seguir os cards do Trello, um por vez.
