# EducaChat

Protótipo acadêmico (ETEP / EXPOETEP 2026.2). Chatbot que tutora alunos da educação básica a partir do 6º ano pelo método socrático e restringe o conteúdo à série informada no cadastro.

Componentes do MVP: Matemática, Português, Ciências e conhecimentos gerais.

Roda só na sua máquina. Não há deploy.

## Stack

| Camada | Tecnologia |
|---|---|
| Front | Vue 3 (`<script setup>`) + Vite + Tailwind — pasta `web/` |
| Back | Python 3.11 + uv + FastAPI — pasta `api/` |
| Usuários / série | Supabase (auth + `profiles`; a série nunca vem do body) |
| Material da série | ChromaDB local (`PersistentClient`) + embeddings em pt-BR |
| IA | OpenRouter, modelo `:free`, atrás de uma interface trocável |

Não usamos Pinia. Estado fica no próprio componente (como campos de um controller, sem um store global).

## Pastas

- `api/` — FastAPI
- `web/` — Vue
- `Artigo/` — entregas do artigo extensionista
- `resumos/` — recortes de decisão

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) (já instala e isola o Python 3.11 do projeto)
- Node.js 20+ e npm
- Duas janelas de terminal (API e front sobem separados)

O `uv` baixa o Python 3.11 sozinho, mesmo se o `python` do sistema for 3.12. É o equivalente a ter um JDK 17 no `pom.xml` enquanto o Java padrão da máquina é outro.

## Setup da API

```powershell
cd api
copy .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

- `uv sync` lê o `pyproject.toml`, cria `.venv` e instala o que está no `uv.lock`. Pense no `pom.xml` + o repositório Maven local.
- `--reload` recarrega o processo quando um `.py` muda (parecido com o DevTools do Spring Boot).
- A porta é **8001**: neste Windows a 8000 já responde um nginx/Laravel, e o EducaChat não pode dividir porta com outro sistema.
- Docs interativas: http://127.0.0.1:8001/docs
- Checagem: http://127.0.0.1:8001/health → `{"status":"ok"}`

O arquivo `.env` fica vazio nesta etapa. Chaves do Supabase e do OpenRouter entram depois — não invente valor. Se ainda não tiver o projeto no Supabase, pare e avise antes da etapa 3.

Se o `uv sync` falhar com `No module named 'encodings'`, a cópia do Python 3.11 do uv está incompleta. Corrija com:

```powershell
uv python uninstall 3.11
uv python install 3.11
```

Coloque o PDF oficial da BNCC em `api/data/bncc.pdf` (não vai para o Git). Ingestão — um chunk por código `EF06MA01`:

```powershell
cd api
uv sync
uv run python -m app.ingest_bncc
```

A primeira execução baixa o modelo `paraphrase-multilingual-MiniLM-L12-v2` (o default do Chroma é em inglês e não serve para pt-BR). O script imprime a contagem por série/componente e roda 3 consultas com filtro.

## Setup do front

Em outro terminal:

```powershell
cd web
copy .env.example .env
npm install
npm run dev
```

Abre em http://localhost:5173. A tela inicial consulta `VITE_API_URL/health` (padrão `http://127.0.0.1:8001`). Variáveis `VITE_*` são as únicas que o Vite expõe ao browser — o restante ficaria só no Node, como um `application.properties` que não pode vazar para o cliente.

## Ordem de construção

1. Scaffold (esta etapa) — as duas pastas sobem
2. Ingestão da BNCC (um chunk por habilidade `EF<ano><COMPONENTE><nn>`)
3. Schema Supabase (`profiles` + RLS) e validação do JWT no FastAPI
4. Endpoint de chat com os modos `duvida`, `trabalho` e `exercicio`
5. Telas de login/cadastro (com série) e chat (com seletor de modo)

## Regras de domínio (já valem para o código seguinte)

1. A série nunca vem do corpo da requisição. O back resolve pelo JWT do Supabase, na tabela `profiles`.
2. Toda consulta ao ChromaDB filtra por série e componente. Sem filtro, não consulta.
3. Três modos, cada um com system prompt próprio: `duvida`, `trabalho`, `exercicio`.
4. Pedido de resposta pronta ou de conteúdo de outra série é recusado e redirecionado.
