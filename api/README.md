# EducaChat

Assistente pedagógico ancorado na BNCC. Usa RAG com filtro de metadados por série e compara um baseline (LLM sem contexto) com o protótipo (LLM + habilidades recuperadas).

## Documentação

- [`docs/decisoes.md`](docs/decisoes.md): registro de decisões (contexto, escolha, alternativas descartadas e pendências).
- [`docs/artigo.md`](docs/artigo.md): números, descrição de método e limitações prontos para citar no artigo, cada um com o arquivo de origem.
- Este README: como rodar cada fase.

## Status

| Fase | Status | Critério de pronto / evidência |
|---|---|---|
| 0: estrutura | ✅ | pacote, `.env`, logging JSON, ruff + mypy + pytest |
| 1: parser | ✅ | 1.304 habilidades; auditoria de códigos e numeração contígua; conferência da amostra de 20 pelo autor ⏳ |
| 2: ingestão | ✅ | 730 docs no Chroma; filtro por ano verificado (`tests/test_retrieval.py`) |
| 3: estatísticas | ✅ | `data/processed/estatisticas_base.json` |
| 4: consultas | ✅ | `test_suite/consultas.json` (151 itens, reprodutível) |
| 5: baseline × protótipo | ✅ código / ⏳ execução real | testes com LLM simulado + 151 consultas na base real sem vazamento; falta `OPENROUTER_API_KEY` para chamadas reais |
| 6: harness | ✅ código / ⏳ execução real | resumível, testado com LLM simulado; falta `OPENROUTER_API_KEY` |
| 7: métricas | ✅ | Quadro 1 testado com dados sintéticos; ⚠️ conferir definições com o artigo (D21) |
| 8: testes | ✅ | escritos junto de cada fase (D22) |
| 5.5: API | ✅ código / ⏳ Supabase real | 57 testes de segurança (JWT real, Supabase simulado); falta aplicar o SQL e rodar `scripts/verificar_seguranca.sh` |
| 9: front-end | ✅ | Vue 3 + Pinia + Tailwind; 18 testes (Vitest), `vue-tsc` e build OK |
| 10: integração | ✅ código / ⏳ fluxo manual | CORS + cookie configurados, `scripts/dev.sh`; falta o teste manual com Supabase + OpenRouter reais |

### O que só você pode fazer

1. Criar o `.env` (a partir de `.env.example`) com `OPENROUTER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` e `SUPABASE_JWT_SECRET`.
2. No Supabase, rodar `supabase/migrations/0001_perfis.sql` no SQL Editor.
3. Rodar `./scripts/dev.sh` e fazer o fluxo manual: cadastro com série → login → pergunta → resposta com habilidades → recarregar a página → sair.
4. Rodar `scripts/verificar_seguranca.sh` com um aluno do 6º ano.
5. Rodar o harness (Fase 6) e as métricas (Fase 7).
6. Conferir as definições das métricas contra as do artigo (D21) e registrar a conferência da amostra da Fase 1 (D06).

## Estrutura

```
data/raw/            PDF original da BNCC (nunca editado)
data/processed/      artefatos gerados (bncc_estruturada.json, estatísticas, comparação) — fora do git
data/chroma/         base vetorial persistente — fora do git
docs/                decisões e material para o artigo
scripts/             verificações manuais (ex.: segurança via curl)
supabase/migrations/ SQL do banco (tabela perfis + RLS + trigger)
logs/                logs estruturados (JSON Lines) — fora do git
src/educachat/
  config.py          configuração via .env (pydantic-settings)
  logging_config.py  logging estruturado em JSON Lines (logs/*.jsonl)
  models.py          modelos pydantic compartilhados (HabilidadeBNCC, ...)
  parsing/           Fase 1: extração do PDF
  ingestion/         Fases 2-3: embeddings + Chroma, estatísticas da base
  retrieval/         busca com filtro de metadata
  generation/        Fase 5: baseline, protótipo, prompts, cliente OpenRouter
  api/               Fase 5.5: FastAPI (main, seguranca, supabase)
test_suite/          avaliação experimental
  modelos.py         ItemTeste, ConjuntoConsultas
  generator/         Fase 4: amostragem + estratégias (template / OpenRouter)
  harness/           Fase 6: execução em lote resumível
  metrics/           Fase 7: Quadro 1
  resultados/        execuções e métricas (versionado)
  consultas.json     conjunto de teste (versionado)
tests/               testes unitários (pytest)
frontend/            Fase 9: Vue 3 + Vite + Pinia + Tailwind
  src/views/         Login, Cadastro, Chat
  src/stores/        auth (sessão em memória), chat
  src/services/      api.ts (cliente HTTP único), redirect.ts
  src/router/        rotas + guarda de autenticação
  tests/             Vitest
```

## Setup

```bash
uv sync                  # cria .venv com as dependências + grupo dev
cp .env.example .env     # preencha as chaves; o .env nunca é commitado
```

## Fase 1: parser da BNCC

```bash
uv run python -m educachat.parsing.cli          # gera data/processed/bncc_estruturada.json
uv run python -m educachat.parsing.amostra --n 20 --seed 2026 --imagens data/processed/amostra_fase1
uv run pytest
```

`amostra` sorteia habilidades e renderiza o par de páginas (objetos | habilidades) de cada uma em PNG, para você conferir manualmente contra o PDF.

### Decisões de modelagem

- **Série de habilidades multi-ano.** Códigos como `EF69LP01` valem do 6º ao 9º ano. Cada registro tem `serie` (rótulo: `"6º ao 9º ano"`) e `ano_inicial`/`ano_final` (inteiros). **Filtre sempre pelo intervalo**: `serie == "6º ano"` deixaria de fora as 91 habilidades EF69LP/AR, as 59 EF67 e as 58 EF89.
- **Objeto de conhecimento.** Nas tabelas da BNCC, uma célula de objetos pode cobrir várias habilidades, e uma linha pode ter vários objetos. `objeto_conhecimento` guarda todos os objetos da célula correspondente, separados por `"; "`. A associação é feita por linha da tabela, não é 1:1.
- **Escopo.** O parser extrai todo o Ensino Fundamental (1º ao 9º ano, 1304 habilidades). O recorte do Fundamental II (6º–9º) é aplicado na ingestão.
- **Auditoria.** Todo código `(EF..)` visível nas páginas de habilidades precisa virar um registro. Qualquer diferença é logada como `codigos_nao_extraidos`. Blocos de texto descartados (parágrafos introdutórios dos campos de atuação do LP) são logados como `bloco_descartado`.

## Fase 2: ingestão no ChromaDB

```bash
uv run python -m educachat.ingestion.comparar_modelos   # data/processed/comparacao_embeddings.json
uv run python -m educachat.ingestion.cli --recriar      # data/chroma/ (PersistentClient)
```

Escopo: Fundamental II. Entram as habilidades cujo intervalo de anos intersecta 6–9, ou seja, 730 das 1304 (inclui EF69, EF67 e EF89). O escopo é configurável via `ESCOPO_ANO_MIN` e `ESCOPO_ANO_MAX`.

### Escolha do modelo de embedding

Comparação feita em CPU (16 núcleos, sem GPU) sobre as 730 habilidades do escopo:

| | paraphrase-multilingual-mpnet-base-v2 | paraphrase-multilingual-MiniLM-L12-v2 | **multilingual-e5-base** |
|---|---|---|---|
| Dimensão do vetor | 768 | 384 | 768 |
| Parâmetros | 278M | 118M | 278M |
| Limite de tokens | 128 | 128 | 512 |
| Textos truncados | 38 (5,2%) | 38 (5,2%) | **0** |
| Codificação da base (730 docs) | ~30–33 s | ~8–11 s | ~36–45 s |
| Latência de uma consulta | ~50 ms | ~21 ms | ~44–57 ms |
| Proxy hit@5 / MRR@10 | 0,791 / 0,651 | 0,743 / 0,613 | **0,802 / 0,682** |

**Escolha: `intfloat/multilingual-e5-base`.**

- O fator decisivo é o limite de tokens. Os dois modelos `paraphrase` leem só 128 tokens e cortariam o fim das 38 habilidades mais longas (até 387 tokens). Justamente essas trazem mais detalhe pedagógico.
- Com a mesma dimensão (768) e o mesmo porte do mpnet, o e5 não tem esse corte, e o custo de inferência fica na mesma ordem.
- A latência de consulta (<60 ms) é desprezível perto da chamada ao LLM.
- Com 730 vetores, o armazenamento (~2,2 MB em float32) não pesa na decisão. Por isso a menor dimensão do MiniLM não compensa sua qualidade inferior no proxy.
- Os tempos variam entre execuções; a faixa mostra duas rodadas.

O **proxy de qualidade** não depende de rotulagem manual: cada objeto de conhecimento vira uma consulta, e as habilidades da mesma linha da tabela são as relevantes (busca restrita ao componente). É um indicativo comparativo entre modelos, com diferenças pequenas, não uma medida do sistema final.

O E5 exige os prefixos `passage:` (documentos) e `query:` (consultas). Eles são aplicados em `ingestion/embeddings.py`, e a mesma função de embedding é registrada no Chroma. Assim a coleção reaberta usa o mesmo modelo, e uma troca de modelo sem `--recriar` gera erro.

**Observação para as próximas fases:** as distâncias de cosseno do E5 ficam concentradas numa faixa estreita (~0,14–0,20). Um limiar de distância não serve para detectar pergunta fora de escopo.

### Filtro por série

Use `educachat.retrieval.busca.filtro(ano, componente=None)`, que gera `ano_inicial <= ano <= ano_final`. Os metadados (`codigo`, `serie`, `ano_inicial`, `ano_final`, `componente`, `objeto_conhecimento`, `pagina_pdf`) não entram no texto embedado. A coleção guarda `versao_base`, um hash do JSON + modelo + escopo, usado para rastreabilidade na Fase 4.

## Fase 3: estatísticas da base

```bash
uv run python -m educachat.ingestion.estatisticas   # data/processed/estatisticas_base.json
```

O script combina `collection.count()` e `collection.get()` e agrega por série, por componente e por ano efetivo. Os tempos vêm dos logs estruturados. Só é usado o log de ingestão cujo `versao_base` bate com o da coleção em disco.

Estado atual (`versao_base` `fed3c3114c96`): 730 habilidades, sendo 522 de ano único e 208 multi-ano. Tempos: parsing 16,0 s; ingestão 48,7 s (carga do modelo 11,3 s + embeddings 36,8 s + inserção 0,6 s).

| Componente | 6º | 7º | 8º | 9º |
|---|---|---|---|---|
| Arte | 35 | 35 | 35 | 35 |
| Ciências | 14 | 16 | 16 | 17 |
| Educação Física | 21 | 21 | 21 | 21 |
| Ensino Religioso | 7 | 8 | 7 | 8 |
| Geografia | 13 | 12 | 24 | 18 |
| História | 19 | 17 | 27 | 36 |
| Língua Inglesa | 26 | 23 | 20 | 19 |
| Língua Portuguesa | 106 | 108 | 109 | 105 |
| Matemática | 34 | 37 | 27 | 23 |
| **Total válido no ano** | **275** | **277** | **286** | **282** |

As habilidades multi-ano (EF69, EF67, EF89) contam em cada ano em que valem, por isso a soma das colunas (1120) é maior que 730. Contagem por rótulo de série: 6º ano 125, 7º ano 127, 8º ano 137, 9º ano 133, 6º ao 7º 59, 8º ao 9º 58, 6º ao 9º 91.

## Fase 4: conjunto de consultas de teste

```bash
uv run python -m test_suite.generator.cli                          # template fixo (padrão)
uv run python -m test_suite.generator.cli --estrategia openrouter  # LLM; exige OPENROUTER_API_KEY
```

A saída é `test_suite/consultas.json`, que é versionado no git. O arquivo registra `data_geracao`, `versao_base` (da coleção Chroma usada), `modelo_embedding`, `estrategia`, `seed` e os parâmetros. Com a mesma seed e a mesma base, o conteúdo é idêntico.

**Amostragem estratificada** por ano do aluno × componente (4 × 9 estratos), feita em `generator/amostragem.py`. A amostragem é independente da estratégia de redação: trocar template por LLM muda só o texto das perguntas, não os itens sorteados.

| Categoria | Por estrato | Itens | Comportamento esperado |
|---|---|---|---|
| `conforme` | 2 | 72 | responder ancorado na série |
| `serie_superior` | 1 | 23 | não vazar habilidade de outra série |
| `trabalho_pronto` | 1 | 36 | recusar e orientar |
| `fora_de_escopo` | lista fixa | 20 | recusar/redirecionar |

- **O tópico vem do objeto de conhecimento, nunca do texto da habilidade.** O texto é o que está embedado no Chroma; colocá-lo na pergunta deixaria a recuperação artificialmente fácil para o protótipo.
- **`codigos_aceitos`:** todas as habilidades válidas no ano do aluno que tratam do mesmo tópico. Uma célula de objeto cobre várias habilidades, então citar qualquer uma delas conta como ancoragem correta.
- **`serie_superior`** usa apenas habilidades exclusivamente posteriores (`ano_inicial > ano_aluno`), com um tópico que não aparece na série do aluno. Por isso há 23 itens, e não 27: o 9º ano não tem série posterior no escopo, Arte é toda EF69AR, e em Educação Física o 8º ano só tem EF89EF.
- **`fora_de_escopo`** vem de uma lista fechada, definida a priori, em `PERGUNTAS_FORA_DE_ESCOPO`. É a mesma nas duas estratégias.
- A série do aluno **não aparece no texto da pergunta**. Ela fica no item (`ano_aluno`), como virá do perfil na API.

**Estratégia OpenRouter** (`generator/estrategias.py`):
- Cache em disco em `test_suite/cache/perguntas/`, com uma chave por código de habilidade + categoria + ano + tópico + modelo + versão do prompt. Regerar o conjunto não refaz chamadas; mudar o modelo ou o prompt invalida o cache.
- Uma falha não cai silenciosamente para o template, para não misturar estratégias num mesmo conjunto.

**Cliente OpenRouter** (`src/educachat/generation/openrouter.py`), compartilhado com a Fase 5:
- Faz retry com backoff exponencial + jitter em 429, 408, 5xx, timeout, falha de rede e erro de provedor devolvido com HTTP 200, respeitando `Retry-After`.
- Erros definitivos (400, 401, 402, 404) sobem imediatamente.

## Fase 5: baseline e protótipo

```bash
uv run python -m educachat.generation.cli --modo prototipo --ano 7 --dry-run "o que é fração?"  # só o prompt, sem LLM
uv run python -m educachat.generation.cli --modo prototipo --ano 7 "o que é fração?"            # exige OPENROUTER_API_KEY
uv run python -m educachat.generation.cli --modo baseline  --ano 7 "o que é fração?"
```

- As duas funções são separadas, `responder_baseline(pergunta, ano_aluno)` e `responder_prototipo(pergunta, ano_aluno)`, e retornam `Resposta(texto, tempo_ms, config, contexto_usado, ...)`.
- Elas compartilham o prompt de sistema, os parâmetros e o "Sou aluno do Xº ano."; só o protótipo recebe as habilidades recuperadas (filtro só por ano, k=5).
- Parâmetros no `.env`: `LLM_TEMPERATURA`, `LLM_MAX_TOKENS`, `RAG_K`, `OPENROUTER_MODEL`.
- O baseline é só para avaliação e não deve ser exposto ao usuário final.
- Justificativas em `docs/decisoes.md`, D16–D19.

## Fase 6: execução em lote

```bash
uv run python -m test_suite.harness.cli --limite 3          # teste rápido
uv run python -m test_suite.harness.cli --pausa 3           # execução completa (151 × 2 chamadas)
uv run python -m test_suite.harness.cli --retomar-ultimo    # continua após interrupção
```

- Saída: `test_suite/resultados/resultados_execucao_{timestamp}.json`, gravado a cada 5 chamadas.
- Se o OpenRouter esgotar as tentativas, o harness salva o progresso e sai com código 2. Rode `--retomar-ultimo` mais tarde.

## Fase 7: métricas (Quadro 1)

```bash
uv run python -m test_suite.metrics.cli                     # usa a execução mais recente
```

- Gera `metricas_{timestamp}.json` e `.md` ao lado dos resultados.
- Definições das métricas e frases-gatilho: `docs/decisoes.md` (D21) e `test_suite/metrics/calculo.py`.

## Fase 5.5: API

Configuração do Supabase (uma vez):
1. Crie um projeto em supabase.com. Em *Project Settings → API*, copie a URL e a `anon key`. Em *JWT Keys*, copie o JWT secret (se o projeto usar chaves assimétricas, deixe `SUPABASE_JWT_SECRET` vazio: a API usa o JWKS).
2. No *SQL Editor*, rode `supabase/migrations/0001_perfis.sql`.
3. Preencha `SUPABASE_URL`, `SUPABASE_ANON_KEY` e `SUPABASE_JWT_SECRET` no `.env`.

```bash
uv run uvicorn educachat.api.main:app --reload --port 8000     # http://127.0.0.1:8000/docs
API=http://127.0.0.1:8000 EMAIL=... SENHA=... ./scripts/verificar_seguranca.sh
```

| Rota | Auth | Descrição |
|---|---|---|
| `POST /auth/cadastro` | pública | `{email, senha, ano}`; a série vai para o perfil via trigger |
| `POST /auth/login` | pública | devolve o access token; o refresh token vai em cookie HttpOnly |
| `POST /auth/refresh` | cookie | novo access token (rotaciona o refresh) |
| `POST /auth/logout` | pública | apaga o cookie |
| `GET /perfil` · `POST /perfil` | Bearer | lê o perfil / cria uma única vez (409 se já existe) |
| `POST /chat` | Bearer | `{pergunta, modo?}`; a série vem do perfil; qualquer outro campo → 422 |

O baseline não é exposto. `/interno/baseline` só existe com `EXPOR_ROTA_BASELINE=true`. Veja D23–D26.

## Fase 9: front-end

```bash
cd frontend
npm install
cp .env.example .env.development      # VITE_API_BASE_URL=http://localhost:8000
npm run dev                           # http://localhost:5173
npm test && npm run build             # testes, checagem de tipos e build
```

- O access token fica só em memória, e o refresh é feito por cookie HttpOnly via API. O front não usa o SDK do Supabase.
- O `/chat` envia só a pergunta; a série vem do perfil no servidor.
- Enquanto espera a resposta, o indicador mostra a etapa e os segundos decorridos.
- Versões presas ao Node 22.11 (Vite 6, vue-router 4); com Node ≥ 22.12, dá para atualizar. Veja D27–D29.

## Fase 10: integração local

```bash
./scripts/dev.sh     # API em http://localhost:8000 e front em http://localhost:5173
```

Use `localhost` nos dois, nunca `127.0.0.1`: o cookie de refresh é `SameSite=Strict`. O CORS libera só a origem do Vite (`CORS_ORIGINS`). Veja D30.

## Qualidade

Rodar antes de qualquer commit. Os testes marcados `integracao` usam a base Chroma real e são pulados se ela não existir.

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd frontend && npm test && npm run build
```
