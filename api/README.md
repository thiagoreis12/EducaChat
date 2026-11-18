# EducaChat

Assistente pedagógico para alunos do Ensino Fundamental II (6º ao 9º ano), com respostas ancoradas na **BNCC**.

O aluno se cadastra informando a série e faz perguntas no chat. O sistema busca as habilidades da BNCC válidas para aquela série (RAG com filtro por ano) e usa esse contexto para responder, sem antecipar conteúdo de séries posteriores e sem entregar trabalho pronto.

## Stack

- **Back-end:** Python 3.12, FastAPI, ChromaDB, `multilingual-e5-base` (embeddings), OpenRouter (LLM)
- **Front-end:** Vue 3, Vite, Pinia, Tailwind
- **Auth e banco:** Supabase

## Como rodar

Pré-requisitos: [uv](https://docs.astral.sh/uv/), Node 22 e um projeto no Supabase.

```bash
# 1. Dependências e configuração
uv sync
cp .env.example .env                  # preencha OPENROUTER_API_KEY, SUPABASE_URL e SUPABASE_ANON_KEY
cd frontend && npm install && cp .env.example .env.development && cd ..

# 2. Banco: rode supabase/migrations/0001_perfis.sql no SQL Editor do Supabase

# 3. Base da BNCC (extração do PDF + indexação no Chroma)
uv run python -m educachat.parsing.cli
uv run python -m educachat.ingestion.cli --recriar

# 4. Subir API e front
./scripts/dev.sh                      # API em :8000, front em http://localhost:5173
```

> Acesse por `localhost`, não `127.0.0.1`: o cookie de sessão é `SameSite=Strict`.

## Avaliação

O projeto compara um **baseline** (LLM sem contexto) com o **protótipo** (LLM + habilidades recuperadas) sobre um conjunto de 151 consultas de teste.

```bash
uv run python -m test_suite.harness.cli    # executa as consultas nos dois modos
uv run python -m test_suite.metrics.cli    # gera as métricas
```

## Estrutura

```
src/educachat/   parser, ingestão, busca, geração e API
frontend/        aplicação Vue
test_suite/      consultas de teste, harness e métricas
supabase/        migrations do banco
tests/           testes unitários
```

## Testes

```bash
uv run ruff check . && uv run mypy && uv run pytest
cd frontend && npm test && npm run build
```
