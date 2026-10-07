# EducaChat

Protótipo acadêmico (ETEP / EXPOETEP 2026.2) de Thiago Reis (ADS) e Marcus Paulo Pereira de Oliveira (Ciência da Computação). Assistente pedagógico ancorado na BNCC para alunos do 6º ao 9º ano: a série vem do perfil do aluno, a busca no currículo é filtrada por ela, e o assistente recusa trabalho pronto e redireciona perguntas fora da escola.

Escopo atual: as 730 habilidades da BNCC do Ensino Fundamental II, nos 9 componentes (Arte, Ciências, Educação Física, Ensino Religioso, Geografia, História, Língua Inglesa, Língua Portuguesa e Matemática).

Roda só na sua máquina. Não há deploy.

## Stack

| Camada | Tecnologia |
|---|---|
| Front | Vue 3 + Vite + TypeScript + Pinia + vue-router + Tailwind 4 (`api/frontend/`) |
| Back | Python 3.12 + uv + FastAPI (`api/src/educachat/`) |
| Usuários / série | Supabase Auth + tabela `perfis` com RLS; a série nunca vem do body |
| Material da série | ChromaDB local (`PersistentClient`) + embedding `intfloat/multilingual-e5-base` |
| IA | OpenRouter, modelo `:free`, com retry e backoff |

O front usa Pinia só para a sessão (access token em memória) e para o histórico do chat. É o equivalente a um bean singleton de sessão no Spring: um único lugar guarda o estado e as telas o leem.

## Pastas

- `api/`: projeto do Marcus, trazido de [MarcusSant0s/educachat](https://github.com/MarcusSant0s/educachat). Tem parser da BNCC, ingestão no Chroma, geração (baseline × protótipo), avaliação, a API FastAPI e o front em `api/frontend/`. Fases, decisões e comandos estão no [README do projeto](api/README.md), em [`api/docs/decisoes.md`](api/docs/decisoes.md) (D01–D30) e em [`api/docs/artigo.md`](api/docs/artigo.md), com os números prontos para citar.
- `Artigo/`: entregas do artigo extensionista.
- `resumos/`: recortes e decisões do projeto.

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) (instala e isola o Python do projeto)
- Node.js 22+ e npm
- Um projeto Supabase com `supabase/migrations/0001_perfis.sql` aplicado (ver o [README do projeto](api/README.md#fase-55-api))
- Duas janelas de terminal (API e front sobem separados; o `scripts/dev.sh` do Marcus é bash e não roda no PowerShell)

## Setup da API

```powershell
cd api
copy .env.example .env
uv sync
uv run python -m educachat.parsing.cli
uv run python -m educachat.ingestion.cli --recriar
uv run uvicorn educachat.api.main:app --reload --host localhost --port 8001
```

- `uv sync` lê o `pyproject.toml`, cria `.venv` e instala o que está no `uv.lock`. Pense no `pom.xml` + o repositório Maven local.
- `parsing.cli` extrai as habilidades do PDF da BNCC (já versionado em `api/data/raw/`). `ingestion.cli --recriar` grava as 730 habilidades do 6º ao 9º ano no Chroma (`api/data/chroma/`, fora do Git).
- A API só sobe com `SUPABASE_URL` e `SUPABASE_ANON_KEY` no `.env`. O `/chat` também precisa de `OPENROUTER_API_KEY`. Não invente valor: preencha com os dados do seu projeto.
- A porta é **8001**: neste Windows a 8000 já responde um nginx/Laravel.
- Use `localhost`, nunca `127.0.0.1`: o cookie de refresh é `SameSite=Strict`, e o navegador trata os dois como sites diferentes.
- Checagem: http://localhost:8001/health → `{"status":"ok"}`
- Testes: `uv run pytest -m "not integracao"` (os de integração exigem a base Chroma gerada).

## Setup do front

Em outro terminal:

```powershell
cd api\frontend
npm install
Set-Content .env.development.local "VITE_API_BASE_URL=http://localhost:8001"
npm run dev
```

Abre em http://localhost:5173, com cadastro (e-mail, senha e série), login e chat.

- O `.env.development` versionado aponta para a porta 8000. O `.env.development.local` sobrepõe só nesta máquina e fica fora do Git, então não conflita com as atualizações do Marcus.
- Variáveis `VITE_*` são as únicas que o Vite expõe ao navegador. É como um `application.properties` que vai para o cliente, então nunca coloque segredo nelas.
- Testes: `npm test` (Vitest) e `npm run typecheck`.

## Regras de domínio e estado atual

1. A série nunca vem do corpo da requisição. A API valida o JWT do Supabase e lê a série da tabela `perfis`, usando o token do próprio aluno (o RLS vale também para a API). Campo extra no body do `/chat` é rejeitado com 422.
2. O Chroma filtra pelo intervalo de anos da habilidade (`ano_inicial <= ano <= ano_final`), sem restringir componente (decisão D17).
3. Há um único modo de conversa (`prototipo`). Os três modos planejados no artigo (dúvida, trabalho e exercício) não foram implementados.
4. O prompt de sistema manda recusar trabalho pronto e redirecionar perguntas não escolares. Antes de chamar o LLM, o protótipo confere se nenhuma habilidade recuperada é de outra série.

O que ainda depende de nós (lista completa no [README do projeto](api/README.md#o-que-só-você-pode-fazer)): criar o `.env` com as chaves reais, aplicar o SQL no Supabase, fazer o fluxo manual cadastro → chat, rodar a avaliação com o OpenRouter e aplicar o SUS.

## Atualizar com o repositório do Marcus

```powershell
git fetch marcus
git merge -X subtree=api marcus/master
```
