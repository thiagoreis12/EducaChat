# EducaChat

Protótipo acadêmico (ETEP / EXPOETEP 2026.2). Chatbot que tutora alunos da educação básica a partir do 6º ano pelo método socrático e restringe o conteúdo à série informada no cadastro.

Componentes do MVP: Matemática, Português, Ciências e conhecimentos gerais.

Roda só na sua máquina. Não há deploy.

## Stack

| Camada | Tecnologia |
|---|---|
| Front | Vue 3 (`<script setup>`) + Vite + Tailwind — pasta `web/` |
| Back | Python 3.12 + uv + FastAPI — pasta `api/` (código do Marcus) |
| Usuários / série | Supabase (auth + tabela `perfis`; a série nunca vem do body) |
| Material da série | ChromaDB local (`PersistentClient`) + embedding `intfloat/multilingual-e5-base` |
| IA | OpenRouter, modelo `:free`, com retry e backoff |

Não usamos Pinia. Estado fica no próprio componente (como campos de um controller, sem um store global).

## Pastas

- `api/` — back-end do Marcus, trazido de [MarcusSant0s/educachat](https://github.com/MarcusSant0s/educachat): parser da BNCC, ingestão no Chroma, geração (baseline × protótipo), avaliação e API FastAPI. Fases, decisões e comandos no [README do back-end](api/README.md) e em [`api/docs/decisoes.md`](api/docs/decisoes.md)
- `web/` — Vue
- `Artigo/` — entregas do artigo extensionista
- `resumos/` — recortes de decisão

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) (instala e isola o Python do projeto)
- Node.js 20+ e npm
- Duas janelas de terminal (API e front sobem separados)

## Setup da API

```powershell
cd api
copy .env.example .env
uv sync
uv run python -m educachat.parsing.cli
uv run python -m educachat.ingestion.cli --recriar
uv run uvicorn educachat.api.main:app --reload --host 127.0.0.1 --port 8001
```

- `uv sync` lê o `pyproject.toml`, cria `.venv` e instala o que está no `uv.lock`. Pense no `pom.xml` + o repositório Maven local.
- `parsing.cli` extrai as habilidades do PDF da BNCC (já versionado em `api/data/raw/`). `ingestion.cli --recriar` grava as 730 habilidades do 6º ao 9º ano no Chroma (`api/data/chroma/`, fora do Git).
- A API só sobe com `SUPABASE_URL` e `SUPABASE_ANON_KEY` no `.env`. O `/chat` também precisa de `OPENROUTER_API_KEY`. Não invente valor: preencha com os dados do seu projeto.
- A porta é **8001**: neste Windows a 8000 já responde um nginx/Laravel.
- Checagem: http://127.0.0.1:8001/health → `{"status":"ok"}`
- Testes: `uv run pytest -m "not integracao"` (os de integração exigem a base Chroma gerada).

## Setup do front

Em outro terminal:

```powershell
cd web
copy .env.example .env
npm install
npm run dev
```

Abre em http://localhost:5173. A tela inicial consulta `VITE_API_URL/health` (padrão `http://127.0.0.1:8001`). Variáveis `VITE_*` são as únicas que o Vite expõe ao browser — o restante ficaria só no Node, como um `application.properties` que não pode vazar para o cliente.

## Regras de domínio e estado atual

1. A série nunca vem do corpo da requisição. A API lê do perfil autenticado (tabela `perfis`); campo extra no body do `/chat` é rejeitado com 422.
2. O Chroma filtra pelo intervalo de anos da habilidade (`ano_inicial <= ano <= ano_final`), sem restringir componente (decisão D17 do back-end).
3. Os três modos (`duvida`, `trabalho`, `exercicio`) ainda não existem na API: hoje o `/chat` aceita só o modo `prototipo`.
4. Pedido de resposta pronta ou de conteúdo de outra série é recusado e redirecionado pelo prompt de sistema.

## Atualizar com o repositório do Marcus

```powershell
git fetch marcus
git merge -X subtree=api marcus/master
```
