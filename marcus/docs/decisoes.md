# Registro de decisões

Cada decisão registra o contexto, o que foi escolhido, as alternativas descartadas e onde está no código. Decisões novas entram no fim; decisões revistas são marcadas como **substituída por Dxx**, sem apagar o registro original.

Status: ✅ vigente · ⏳ pendente · ♻️ substituída

---

## Infraestrutura

### D01 ✅ Código como pacote `src/educachat/`
- **Contexto:** o plano previa `src/parsing/`, `src/ingestion/` etc. soltos em `src/`.
- **Decisão:** as mesmas subpastas ficam dentro de um pacote instalável, `src/educachat/`. `test_suite/` também é um pacote.
- **Por quê:** imports absolutos e estáveis (`from educachat.models import ...`) em scripts, testes e, mais tarde, na API, sem mexer em `sys.path`.
- **Onde:** `pyproject.toml` (`[tool.hatch.build.targets.wheel]`).

### D02 ✅ Ferramentas: uv, ruff, mypy strict, pytest
- **Decisão:** dependências gerenciadas com `uv` (`uv.lock` versionado); ruff para lint e formatação, com `print` proibido (regra T20); mypy em modo `strict`; pytest.
- **Exceções documentadas no `pyproject.toml`:**
  - chamadas ao PyMuPDF, que é só parcialmente tipado;
  - regra N818, porque as exceções têm nome em português (`ErroOpenRouter`);
  - RUF001–003, porque `º` e `–` são legítimos em PT-BR.
- **Python ≥ 3.12:** os stubs do numpy usam sintaxe de 3.12.

### D03 ✅ PyTorch somente CPU
- **Contexto:** a máquina de desenvolvimento não tem GPU e tem cerca de 9 GB de RAM.
- **Decisão:** `torch` vem do índice `pytorch-cpu` (`[tool.uv.sources]`). Isso evita cerca de 2 GB de bibliotecas CUDA sem uso.
- **Consequência:** todos os tempos reportados são medidos em CPU (16 núcleos).

### D04 ✅ Configuração via `.env` e logging estruturado
- **Decisão:**
  - segredos (OpenRouter, Supabase) ficam só no `.env`, lido por `pydantic-settings` e guardado como `SecretStr`; `.env` está no `.gitignore` e `.env.example` documenta as variáveis;
  - todos os scripts registram logs em JSON Lines em `logs/<etapa>_<timestamp>.jsonl`.
- **Por quê:** os tempos do artigo (seção 3.1) saem dos próprios logs (`fase1_concluida`, `fase2_concluida`), sem cronometragem manual.
- **Onde:** `src/educachat/config.py`, `src/educachat/logging_config.py`.

---

## Fase 1: parser da BNCC

### D05 ✅ Extração geométrica por página espelhada
- **Contexto:** no PDF (`BNCC_EI_EF_110518_versaofinal_site.pdf`, 600 páginas) cada tabela ocupa duas páginas. A da esquerda tem unidades temáticas e objetos de conhecimento; a da direita tem as habilidades. As linhas da tabela são traços horizontais nas mesmas coordenadas y das duas páginas.
- **Decisão:** usar o PyMuPDF para ler blocos de texto e desenhos vetoriais.
  - Uma habilidade começa em `(EFxxYYnn)` no início de uma linha.
  - Ela é associada à faixa da tabela (entre duas divisórias) da página da esquerda que contém o seu topo.
  - As divisórias são os traços finos **e** as bordas dos retângulos preenchidos. As faixas cinzas "CAMPO …" de LP separam linhas sem nenhum traço.
- **Alternativas descartadas:** extração de tabelas genérica (pdfplumber/camelot), porque o PDF não tem estrutura de tabela e as células mescladas quebram essas ferramentas; texto corrido com regex, porque perde a associação habilidade ↔ objeto.
- **Onde:** `src/educachat/parsing/bncc_parser.py`.

### D06 ✅ Validação do parser em camadas
- **Contexto:** um erro no parser não quebra nada; ele só contamina os dados. É o maior risco silencioso do projeto.
- **Decisão:** quatro verificações independentes.
  1. **Auditoria de códigos:** todo `(EF..)` visível nas páginas de habilidades precisa virar um registro. Diferenças são registradas no log (`codigos_nao_extraidos`).
  2. **Numeração contígua:** dentro de cada prefixo (ex.: EF06MA), os números vão de 01 a N sem saltos. Os 70 prefixos passam (`tests/test_parsing.py`).
  3. **Conferência visual durante o desenvolvimento:** 5 pares de páginas renderizados (p. 101, 171, 229, 343 e 425: LP 1º–2º, LP 6º–7º, Educação Física 1º–2º, Ciências 5º e História 7º) comparados com a extração; 8 casos foram fixados como teste automatizado.
  4. **Conferência manual pelo autor:** amostra de 20 registros sorteados (seed 2026) em `data/processed/amostra_fase1/`, com PNG das páginas de cada um. ⏳ *A conferência ainda não foi registrada; ao concluí-la, anote aqui a data e o resultado (quantos batem e quais divergências).* `python -m educachat.parsing.amostra --seed <n>` gera novas amostras.
- **Bugs que a validação encontrou** (ambos silenciosos):
  - O `search_for` do PyMuPDF ignora maiúsculas e minúsculas. Um "habilidades" no corpo do texto era confundido com o cabeçalho da coluna, e 15 habilidades eram descartadas sem erro. A auditoria de códigos detectou.
  - As faixas cinzas "CAMPO …" não tinham traço, e os objetos de linhas vizinhas eram fundidos (ex.: EF67LP26 recebia "Textualização; Relação entre textos"). A conferência visual detectou; a correção mudou o objeto de 58 habilidades.
- **Descartes legítimos:** 10 parágrafos introdutórios dos campos de atuação de LP 6º–9º, que não são habilidades. Ficam registrados no log (`bloco_descartado`).

### D07 ✅ Série de habilidades multi-ano
- **Contexto:** códigos como EF69LP01 (6º–9º), EF67EF01 (6º–7º) e EF89LP01 (8º–9º) valem para vários anos.
- **Decisão:** cada registro tem `ano_inicial` e `ano_final` (inteiros) e `serie` (rótulo legível, ex. "6º ao 9º ano"). **Todo filtro usa o intervalo** `ano_inicial ≤ ano ≤ ano_final`.
- **Alternativa descartada:** `where={"serie": "6º ano"}`, como no plano original. Deixaria de fora as 150 habilidades multi-ano válidas no 6º ano (91 EF69 + 59 EF67).
- **Onde:** `src/educachat/models.py` (`anos_do_codigo`), `src/educachat/retrieval/busca.py` (`filtro`).

### D08 ✅ Objeto de conhecimento = célula inteira
- **Contexto:** na BNCC, uma célula de objetos cobre várias habilidades e pode conter vários objetos (ex.: EF05CI10–13 têm 4 objetos em comum).
- **Decisão:** `objeto_conhecimento` guarda todos os objetos da célula, separados por `"; "`; os marcadores "•" de História são convertidos no mesmo separador.
- **Consequência:** a relação habilidade ↔ objeto é por linha da tabela, não 1:1. Isso afeta os `codigos_aceitos` da Fase 4 (D14).

### D09 ✅ Escopo: extrair todo o Fundamental, indexar só o Fundamental II
- **Decisão (confirmada pelo autor em 2026-09-30):** o parser extrai o Ensino Fundamental inteiro (1.304 habilidades). A ingestão indexa as habilidades cujo intervalo de anos intersecta 6–9, ou seja, 730.
- **Por quê:** o JSON completo continua útil e permite mudar o recorte (`ESCOPO_ANO_MIN` / `ESCOPO_ANO_MAX`) sem refazer o parsing.

---

## Fase 2: ingestão

### D10 ✅ Modelo de embedding: `intfloat/multilingual-e5-base`
- **Comparação empírica** entre três modelos multilíngues, nas 730 habilidades, em CPU (`python -m educachat.ingestion.comparar_modelos`, que gera `data/processed/comparacao_embeddings.json`):

| | mpnet-base-v2 | MiniLM-L12-v2 | **e5-base** |
|---|---|---|---|
| Dimensão | 768 | 384 | 768 |
| Parâmetros | 278M | 118M | 278M |
| Limite de tokens | 128 | 128 | 512 |
| Textos truncados | 38 (5,2%) | 38 (5,2%) | **0** |
| Codificação (730 docs) | ~30–33 s | ~8–11 s | ~36–45 s |
| Latência por consulta | ~50 ms | ~21 ms | ~44–57 ms |
| Proxy hit@5 / MRR@10 | 0,791 / 0,651 | 0,743 / 0,613 | **0,802 / 0,682** |

- **Justificativa:**
  - Os dois modelos `paraphrase` leem só 128 tokens e cortariam o fim das 38 habilidades mais longas (até 387 tokens).
  - O e5-base tem a mesma dimensão e o mesmo porte do mpnet, sem esse corte, e com custo da mesma ordem. A latência (<60 ms) é desprezível perto da chamada ao LLM.
  - Com 730 vetores (~2,2 MB), o armazenamento não pesa. Por isso a dimensão menor do MiniLM não compensa sua qualidade inferior.
- **Proxy de qualidade:** cada objeto de conhecimento (componente + texto) vira uma consulta, e as habilidades daquela linha da tabela são as relevantes. É um indicativo comparativo, sem rotulagem manual e com diferenças pequenas; não mede o sistema final.
- **Limitação observada:** as distâncias de cosseno do E5 ficam concentradas (~0,14–0,20), então um limiar de distância não separa bem pergunta relevante de irrelevante.

### D11 ✅ Só o texto da habilidade é embedado; o resto é metadado
- **Decisão:** o documento é apenas `texto`. `codigo`, `serie`, `ano_inicial`, `ano_final`, `componente`, `objeto_conhecimento` e `pagina_pdf` ficam como metadados filtráveis.
- **Detalhes:**
  - distância de cosseno;
  - `PersistentClient` em `data/chroma/`;
  - upsert com `id = codigo`, então reindexar é idempotente.
- **Função de embedding registrada no Chroma** (`EmbeddingBNCC`):
  - aplica os prefixos do E5 (`passage:` / `query:`);
  - é serializada junto da coleção, então reabrir a base com outro modelo gera erro em vez de misturar vetores incompatíveis.
- **Rastreabilidade:** a coleção guarda `versao_base = sha256(JSON + modelo + escopo)[:12]` (atual: `fed3c3114c96`).

---

## Fase 3: estatísticas

### D12 ✅ Contagem por "ano efetivo" e tempos casados por `versao_base`
- **Decisão:**
  - além da contagem por rótulo de série, o script conta as habilidades **válidas em cada ano** (uma EF69 conta no 6º, 7º, 8º e 9º), que é o que o aluno daquele ano pode receber;
  - o tempo da Fase 2 vem do log `fase2_concluida` cujo `versao_base` é igual ao da coleção em disco, para nunca citar o tempo de uma indexação antiga.
- **Onde:** `src/educachat/ingestion/estatisticas.py`, que gera `data/processed/estatisticas_base.json`.

---

## Fase 4: conjunto de consultas

### D13 ✅ Perguntas por template agora, OpenRouter plugável depois
- **Decisão (autor, 2026-09-30):** a estratégia padrão é o template fixo.
- **Estratégia OpenRouter:**
  - já está implementada; basta `--estrategia openrouter` e a chave no `.env`;
  - usa cache em disco por habilidade + categoria + ano + tópico + modelo + versão do prompt;
  - uma falha não cai para o template, para não misturar estratégias num conjunto.
- **Separação amostragem × redação:** a escolha dos itens (`amostragem.py`) não depende da estratégia. Trocar template por LLM, com a mesma seed, muda só o texto das perguntas, o que permite comparar as duas.

### D14 ✅ Desenho do conjunto de teste
- **Estratos:** ano do aluno (6–9) × componente (9); seed 42.
- **Tópico a partir do objeto de conhecimento, nunca do texto da habilidade:** o texto é o que está embedado; usá-lo na pergunta tornaria a recuperação artificialmente fácil e inflaria o resultado do protótipo.
- **`codigos_aceitos`:** todas as habilidades válidas no ano do aluno que tratam do mesmo tópico (consequência de D08).
- **Série superior:**
  - usa só habilidades exclusivamente posteriores (`ano_inicial > ano_aluno`), com tópico ausente da série do aluno;
  - dá 23 itens, e não 27, porque o 9º ano não tem série posterior no escopo, Arte é toda EF69AR, e Educação Física no 8º só tem EF89EF.
- **Fora de escopo:** lista fechada de 20 perguntas, definida a priori (`PERGUNTAS_FORA_DE_ESCOPO`).
- **A série não aparece no texto da pergunta:** ela fica em `ano_aluno`, como virá do perfil autenticado na API.
- **Resultado:** 151 itens (72 conforme, 23 série superior, 36 trabalho pronto, 20 fora de escopo). Regenerar com a mesma seed e a mesma base produz um arquivo idêntico.

### D15 ✅ Cliente OpenRouter com retry e backoff
- **Retry** (backoff exponencial + jitter, até 6 tentativas, respeitando `Retry-After`) em:
  - 429, 408 e 5xx;
  - timeout e falha de rede;
  - erro do provedor devolvido dentro de uma resposta HTTP 200.
- **Sem retry:** erros definitivos (400, 401, 402, 404) sobem imediatamente.
- **Por quê:** o plano gratuito tem limite por minuto e por dia; sem isso, execuções longas (Fase 6) morreriam no meio.
- **Onde:** `src/educachat/generation/openrouter.py`; testado com HTTP simulado em `tests/test_openrouter.py`.

---

---

## Fase 5: baseline e protótipo

### D16 ✅ O baseline recebe a série do aluno (antes P1)
- **Decisão (autor, 2026-09-30):** as duas funções recebem a pergunta prefixada com "Sou aluno do Xº ano.".
- **Por quê:** isola o efeito da recuperação. Sem a série, o baseline perderia também por não saber o nível do aluno, e a comparação misturaria duas causas.

### D17 ✅ O protótipo filtra só por ano (antes P2)
- **Decisão (autor, 2026-09-30):** a busca usa `filtro(ano)`, sem restringir por componente.
- **Por quê:** a API (`POST /chat {pergunta, modo}`) não recebe componente, e o filtro por ano é a garantia de segurança.
- **Consequência conhecida:** às vezes o contexto traz habilidades de outro componente, ainda que sempre da série certa.

### D18 ✅ Mesmo prompt de sistema e mesmos parâmetros nos dois modos
- **Decisão:** baseline e protótipo usam o mesmo `SISTEMA`, a mesma temperatura (0,3) e o mesmo `max_tokens` (800). O prompt de sistema:
  - pede linguagem adequada à série;
  - manda recusar trabalho pronto e orientar;
  - manda redirecionar perguntas não escolares;
  - pede que códigos BNCC sejam citados.
- **A única diferença:** o protótipo recebe o bloco com as k=5 habilidades recuperadas e a instrução de usar só essas, citar os códigos usados e avisar quando o conteúdo não é da série.
- **Por quê:** mesmo raciocínio de D16. As diferenças medidas na Fase 7 passam a ser atribuíveis ao contexto recuperado, e não a instruções diferentes.
- **Consequência a declarar:** como o baseline também é instruído a citar códigos, ele pode inventar códigos. A Fase 7 mede isso (código citado inexistente ou de outra série), o que por si só é um resultado.
- **Alternativa descartada:** um baseline "cru", sem prompt de sistema. Mediria o prompt e a recuperação juntos.
- **Onde:** `src/educachat/generation/prompts.py` (`VERSAO_PROMPT = 1`).

### D19 ✅ Duas funções separadas e um objeto `Resposta` completo
- **Duas funções separadas, sem `if modo` espalhado:**
  - `responder_baseline(pergunta, ano_aluno)` em `generation/baseline.py`;
  - `responder_prototipo(pergunta, ano_aluno)` em `generation/prototipo.py`.
- **`Resposta` guarda:**
  - `texto`;
  - tempos (`tempo_ms` total, `tempo_recuperacao_ms`, `tempo_llm_ms`);
  - tentativas e tokens;
  - `config`: modo, modelo do LLM, temperatura, max_tokens, versão do prompt, ano, k, filtro aplicado, modelo de embedding e `versao_base`;
  - `contexto_usado`: as habilidades entregues ao LLM.
- **Por quê:** a Fase 7 calcula rastreabilidade e vazamento só a partir do JSON salvo, sem executar nada de novo.
- **Defesa em profundidade:** o protótipo confere se todo código recuperado vale para o ano do aluno antes de chamar o LLM. Se não valer, levanta `VazamentoDeSerie` e o LLM não é chamado. O teste de integração roda as 151 consultas contra a base real sem nenhum vazamento.
- **O ano vem de parâmetro:** na Fase 5.5 ele virá do perfil autenticado, nunca do corpo da requisição.
- **Rate limit:** tratado pelo cliente (D15).

---

## Fase 6: harness

### D20 ✅ Execução em lote resumível e atômica
- **Saída:** `test_suite/resultados/resultados_execucao_{timestamp}.json` (`ExecucaoLote`). Cada entrada é um par (item, modo) com a `Resposta` completa ou o erro.
- **Checkpoint:** o arquivo é salvo a cada N chamadas (`--checkpoint`, padrão 5), gravando num `.tmp` e depois renomeando (`os.replace`). Um kill no meio da gravação não corrompe o arquivo.
- **Retomada:** `--retomar ARQUIVO` ou `--retomar-ultimo`. Pares já respondidos são pulados; pares com erro são tentados de novo.
- **Limite de taxa persistente** (`TentativasEsgotadas`, ex.: limite diário do plano gratuito): o harness salva e **para**, com código de saída 2 e a instrução de retomada, em vez de marcar todo o resto como erro.
- **Outros erros:** um erro isolado fica registrado no item e o lote segue.
- **Rastreabilidade:**
  - o arquivo guarda `consultas_sha256`, `versao_base`, modelo do LLM e parâmetros;
  - o harness se recusa a rodar se a `versao_base` das consultas for diferente da coleção atual;
  - ao retomar, recusa se `consultas.json` mudou.
- **`--pausa`:** segundos entre chamadas, para respeitar o limite por minuto sem depender só do backoff.
- **`--limite N`:** execução de teste com N itens; ela nunca é marcada como concluída.

---

## Fase 7: métricas

### D21 ✅ Métricas do Quadro 1 (⚠️ conferir com as definições do artigo)
- **Contexto:** o plano fala em "5 métricas já definidas no artigo", mas as definições não estavam disponíveis durante a implementação. As métricas abaixo seguem o que o plano descreve: regex de código, rastreabilidade, vazamento de série e frases-gatilho para trabalho pronto.
- **Métricas principais:**

| # | Métrica | Denominador | Sentido |
|---|---|---|---|
| M1 | Rastreabilidade: cita ≥1 código BNCC existente e válido no ano do aluno | conforme | ↑ |
| M1b | Aderência: cita ≥1 código de `codigos_aceitos` (o tópico perguntado) | conforme | ↑ |
| M2 | Vazamento: cita ≥1 código existente de **outra** série | conforme + série superior | ↓ |
| M3 | Código inexistente: cita código no formato BNCC que não existe | todas | ↓ |
| M4 | Recusa de trabalho pronto (frase-gatilho) | trabalho pronto | ↑ |
| M5 | Recusa/redirecionamento fora de escopo (frase-gatilho) | fora de escopo | ↑ |

- **Complementares:**
  - C1: recusa indevida em pergunta conforme;
  - C2: vazamento só na categoria série superior;
  - C3: código citado fora do contexto recuperado (só protótipo);
  - latência: média, mediana, p95, e mediana de recuperação e de LLM.
- **Regras de cálculo:**
  - denominador = respostas sem erro de execução; os erros são reportados à parte;
  - "existente" = qualquer código do Fundamental (1º–9º), extraído do `bncc_estruturada.json`. Citar EF05.. para um aluno do 6º conta como vazamento, não como código inexistente.
- **Extração de código:** regex `\bEF\d{2}[A-Z]{2}\d{2}\b`, case-sensitive, sem repetição.
- **Frases-gatilho:**
  - são listas **fechadas, definidas a priori**, em `test_suite/metrics/calculo.py`: `GATILHOS_RECUSA_TRABALHO` e `GATILHOS_RECUSA_ESCOPO`;
  - são aplicadas ao texto em minúsculas, sem acentos;
  - qualquer mudança exige incrementar `VERSAO_GATILHOS`, que é gravada no Quadro.
- **Independência:** o script é separado do harness e só lê arquivos (resultados + consultas + base). Saída: `metricas_{timestamp}.json` e `.md`.
- **Se o artigo definir diferente:** as definições ficam numa tabela no começo de `calcular()` e mudar uma é local. Os testes de `tests/test_metricas.py` precisam ser atualizados junto.

---

## Fase 8: testes

### D22 ✅ Testes escritos junto de cada fase
- **Parser:** duplicidade, campos vazios, regex, cobertura de anos, numeração contígua e casos conferidos no PDF.
- **Filtro do Chroma:** coleção temporária com vetores sintéticos, mais integração na base real.
- **Cliente OpenRouter:** HTTP simulado, cobrindo 429, 5xx, `Retry-After`, erro no corpo 200 e erros definitivos.
- **Harness:** retomada, retry de erro, parada em limite de taxa e checkpoint.
- **Métricas:** cada métrica sobre um conjunto sintético de 9 itens × 2 modos, com resultado calculado à mão; mais casos positivos e negativos das frases-gatilho.
- **Segurança da série:** as 151 consultas contra a base real, sem nenhum vazamento.
- **Marcador `integracao`:** usa a base real e o modelo; é pulado se a base não existir.

## Pendentes

Nenhuma no momento.
