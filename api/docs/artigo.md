# Material para o artigo

Números e descrições de método prontos para citar. Cada número indica o arquivo que o gerou, para que possa ser conferido ou atualizado.

> **Estado de referência:** `versao_base` **fed3c3114c96**, modelo `intfloat/multilingual-e5-base`, escopo 6º–9º ano, fonte `BNCC_EI_EF_110518_versaofinal_site.pdf`. Se a base for reindexada, rode de novo `python -m educachat.ingestion.estatisticas` e atualize esta página.

## 1. Base de conhecimento (seção 3.1, fecha os [pendente] de contagem)

Fonte: `data/processed/estatisticas_base.json` e `data/processed/bncc_estruturada.json`.

- Habilidades extraídas do Ensino Fundamental (1º–9º): **1.304**.
- Habilidades indexadas (Ensino Fundamental II): **730**.
  - 522 são de um único ano;
  - 208 valem para vários anos (91 do 6º ao 9º, 59 do 6º ao 7º e 58 do 8º ao 9º).
- Por rótulo de série: 6º ano 125 · 7º ano 127 · 8º ano 137 · 9º ano 133 · 6º ao 7º 59 · 8º ao 9º 58 · 6º ao 9º 91.
- Habilidades disponíveis para o aluno de cada ano, com as multi-ano contadas em todos os anos em que valem:

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
| **Total** | **275** | **277** | **286** | **282** |

> Atenção ao citar: a soma das colunas (1.120) é maior que 730 porque cada habilidade multi-ano aparece em mais de um ano.

## 2. Tempos de processamento

Fonte: logs estruturados em `logs/*.jsonl` (eventos `fase1_concluida` e `fase2_concluida`), consolidados em `estatisticas_base.json`. Hardware: CPU, 16 núcleos, sem GPU.

| Etapa | Tempo |
|---|---|
| Extração do PDF (600 páginas, 1.304 habilidades) | 16,0 s |
| Carga do modelo de embedding | 11,3 s |
| Geração dos embeddings (730 habilidades) | 36,8 s |
| Inserção no ChromaDB | 0,6 s |
| **Ingestão total (Fase 2)** | **48,7 s** |
| Latência de embedding de uma consulta | ~44–57 ms |

## 3. Escolha do modelo de embedding

Fonte: `data/processed/comparacao_embeddings.json`. A tabela completa e a justificativa estão em `docs/decisoes.md`, D10.

Síntese para o texto:
- Foram comparados três modelos multilíngues executáveis localmente: paraphrase-multilingual-mpnet-base-v2, paraphrase-multilingual-MiniLM-L12-v2 e multilingual-e5-base.
- Critérios: dimensão do vetor, custo de inferência em CPU, limite de tokens e uma tarefa proxy de recuperação.
- Escolhido o **multilingual-e5-base** (768 dimensões, 278M parâmetros, limite de 512 tokens). Foi o único que não truncou nenhuma habilidade; os outros dois, limitados a 128 tokens, truncariam 5,2% (38 habilidades, até 387 tokens). Também teve o melhor desempenho no proxy (hit@5 = 0,802; MRR@10 = 0,682), com custo de inferência da mesma ordem do mpnet.

## 4. Extração e validação dos dados

Descrição de método:
- **Extração:** as habilidades foram extraídas do PDF oficial pela geometria da página (blocos de texto e divisórias vetoriais da tabela).
- **Associação com o objeto de conhecimento:** cada habilidade foi ligada ao objeto da mesma linha da tabela, na página espelhada.
- **Validação:** a completude foi verificada por dois critérios independentes:
  - todo código visível nas tabelas corresponde a um registro extraído;
  - a numeração de cada prefixo (ex.: EF06MA01…EF06MA34) é contígua, sem lacunas, nos 70 prefixos.
- **Conferência manual:** a associação habilidade ↔ objeto foi conferida contra as páginas renderizadas do PDF (8 casos fixados em teste automatizado + amostra aleatória de 20 registros). ⏳ *Só cite a amostra de 20 depois de registrar o resultado da sua conferência em `docs/decisoes.md` (D06).*

Evidência de rigor, que pode ser útil na banca:
- A validação encontrou e corrigiu dois erros silenciosos antes da indexação:
  - 15 habilidades omitidas por um falso cabeçalho;
  - 58 habilidades com objeto de conhecimento fundido com o da linha vizinha.
- Nenhum dos dois quebrava a execução; ambos só apareceram nas verificações.

## 5. Conjunto de consultas de teste

Fonte: `test_suite/consultas.json` (seed 42, estratégia `template`, `versao_base` fed3c3114c96).

| Categoria | Itens | Comportamento esperado |
|---|---|---|
| Conforme | 72 | responder ancorado em habilidade da série do aluno |
| Série superior | 23 | não recuperar/citar habilidade de outra série |
| Trabalho pronto | 36 | recusar fazer a tarefa e orientar o estudo |
| Fora de escopo | 20 | recusar/redirecionar |
| **Total** | **151** | |

Descrição de método:
- **Estratificação:** amostragem estratificada por ano do aluno (6º–9º) × componente curricular (9), com semente fixa. O conjunto é reprodutível a partir da base indexada.
- **Formulação:** as perguntas foram redigidas por templates fixos a partir do **objeto de conhecimento**, e não do texto da habilidade. Assim se evita favorecer a recuperação semântica do protótipo, já que o texto da habilidade é justamente o conteúdo indexado.
- **Série do aluno:** não aparece na pergunta; ela é informada separadamente, como no sistema real, em que vem do perfil do usuário.
- **Série superior:** foram usadas apenas habilidades exclusivamente de séries posteriores, com tópicos ausentes da série do aluno. O 9º ano não gera itens nessa categoria, por ser a última série do escopo.
- **Fora de escopo:** as 20 perguntas vêm de uma lista fechada, definida a priori.

## 6. Baseline e protótipo (condições experimentais)

Descrição de método (código em `src/educachat/generation/`; decisões D16–D19):
- **O que as duas condições compartilham:**
  - o mesmo LLM (via OpenRouter);
  - os mesmos parâmetros (temperatura 0,3; máximo de 800 tokens);
  - o mesmo prompt de sistema;
  - a mesma informação sobre o aluno ("Sou aluno do Xº ano.").
- **O que muda no protótipo:** ele recupera as 5 habilidades mais similares à pergunta, **restritas às válidas no ano do aluno** (filtro de metadados `ano_inicial ≤ ano ≤ ano_final`), e as inclui no prompt com a instrução de usá-las como referência e citar seus códigos.
- **Consequência:** a diferença entre as condições é só o contexto recuperado.
- **O que é registrado:** para cada resposta, o texto, os tempos (total, recuperação e LLM), a configuração completa e as habilidades entregues ao modelo. As métricas são calculadas depois, sem nova execução.
- **Salvaguarda de série:** antes de chamar o LLM, o protótipo verifica que todas as habilidades recuperadas valem para o ano do aluno. Nas 151 consultas do conjunto de teste, contra a base real, nenhuma habilidade de outra série foi recuperada.
- **Latência da recuperação:** cerca de 85 ms por consulta (mediana de 30 consultas, CPU), sem contar a carga única do modelo de embedding na inicialização.

## 7. Execução e métricas (Quadro 1)

> ⏳ Os valores do Quadro 1 só existem depois da execução real (Fase 6 com `OPENROUTER_API_KEY`). O Quadro é gerado em `test_suite/resultados/metricas_{timestamp}.md`; copie a tabela de lá.

Descrição de método (decisões D20–D21; ⚠️ confira se as definições batem com as do artigo):
- **Execução:** cada uma das 151 consultas foi submetida às duas condições. Registraram-se a resposta, os tempos, a configuração e as habilidades entregues ao modelo.
- **Cálculo posterior:** as métricas foram calculadas depois, por um script independente, sem nova chamada ao modelo.
- **Códigos citados:** foram identificados pela expressão regular `EF\d{2}[A-Z]{2}\d{2}` e classificados contra a base completa do Ensino Fundamental em três grupos: válido para o ano do aluno, de outra série, ou inexistente.
- **Recusas:** foram detectadas por listas fechadas de frases-gatilho, definidas a priori e versionadas (v1), aplicadas ao texto normalizado (minúsculas, sem acentos).
- **Métricas:**
  - rastreabilidade (M1) e aderência ao tópico (M1b), nas perguntas conformes;
  - vazamento de série (M2), nas conformes e de série superior;
  - códigos inexistentes (M3), em todas;
  - recusa de trabalho pronto (M4);
  - redirecionamento fora de escopo (M5);
  - latência total, de recuperação e do LLM.
- **Denominadores:** excluem respostas com erro de execução, que são reportadas à parte.

## 8. Limitações a declarar

- **Proxy de recuperação:** o proxy da comparação de embeddings é derivado da própria estrutura da BNCC (objeto → habilidades). Ele serve para comparar modelos entre si, não para medir a qualidade final do sistema.
- **Naturalidade das perguntas:** perguntas por template são menos naturais que perguntas reais de alunos. A estratégia com LLM está implementada e pode ser usada para comparação.
- **Distâncias concentradas:** no modelo escolhido, as distâncias de cosseno ficam numa faixa estreita. Por isso a detecção de fora de escopo não pode depender de um limiar de similaridade.
- **Códigos no baseline:** o baseline também é instruído a citar códigos BNCC (mesmo prompt de sistema), então pode inventar códigos. Isso é medido, não corrigido.
- **Contexto de outro componente:** o filtro é só por série; o contexto pode trazer habilidades de outro componente, sempre da série correta.
- **Frases-gatilho:** a detecção de recusa depende de uma lista fechada de padrões. Recusas formuladas de outro jeito não são contadas (falso negativo), e o valor medido é um limite inferior. Uma amostra das respostas pode ser conferida manualmente para estimar esse erro.
- **Fidelidade ao PDF:** o texto das habilidades é reproduzido como está no PDF. Ex.: EF67LP27 não termina com ponto final no original.
