# Recorte confirmado do EducaChat

Atualizado em 30/09/2026, depois da integração do trabalho do Marcus. O recorte planejado na Fase 1 está no fim, para comparação.

## O que o projeto é

Protótipo acadêmico de assistente de estudos ancorado na BNCC (projeto multidisciplinar ETEP 2026.2). **Ainda não há escola parceira**, e nenhum aluno real usou o sistema. A vocação é uso em escolas, depois da validação.

## Público

Estudantes do **6º ao 9º ano** do Ensino Fundamental. O aluno informa a série no cadastro; ela fica no perfil (tabela `perfis`) e não pode ser trocada pelo próprio aluno.

## Conteúdo

Os **9 componentes** do Ensino Fundamental II na BNCC: Arte, Ciências, Educação Física, Ensino Religioso, Geografia, História, Língua Inglesa, Língua Portuguesa e Matemática.

- 730 habilidades indexadas (6º–9º), das 1.304 extraídas do Fundamental inteiro.
- A busca filtra só pelo ano do aluno, não pelo componente (decisão D17).
- "Conhecimentos gerais" saiu do recorte: não é componente da BNCC. Pergunta não escolar é redirecionada.

## Equipe

Projeto em dupla, multidisciplinar:

- **Thiago Reis** — Análise e Desenvolvimento de Sistemas (ADS)
- **Marcus Paulo Pereira de Oliveira** — Ciência da Computação

No repositório, o pipeline da BNCC, a avaliação, a API e o front foram feitos pelo Marcus. Thiago fez o planejamento, o esqueleto inicial, a integração dos repositórios e o artigo. Se entrar mais gente, atualizar o artigo (1.6, 1.7 e 1.9).

## Diferencial

- A resposta se apoia nas habilidades da BNCC **da série do aluno** e cita os códigos.
- A série vem do perfil autenticado, nunca da requisição. Antes de chamar o LLM, o protótipo confere que nenhuma habilidade recuperada é de outra série.
- O assistente **recusa trabalho pronto** e orienta o estudo.
- Avaliação mensurável: 151 consultas comparam o protótipo com um baseline (LLM sem contexto).

## O que mudou em relação ao plano

| Planejado (Fase 1) | Executado |
|---|---|
| Matemática, Português, Ciências e conhecimentos gerais | 9 componentes do Fundamental II |
| 6º ano em diante, talvez Ensino Médio | 6º ao 9º ano |
| 3 modos: dúvida, trabalho, exercício | 1 modo: explica, recusa trabalho pronto, redireciona fora da escola |
| Método socrático (conduzir por perguntas) | Não implementado; o prompt pede explicação adequada à série |
| Filtro por série e componente | Filtro só por ano (D17) |
| Indicadores qualitativos | Baseline × protótipo com métricas M1–M5 + SUS |

## Stack

- Front: Vue 3 + Vite + TypeScript + Pinia + Tailwind (`api/frontend/`)
- Back: Python 3.12 + FastAPI (`api/`)
- Usuários / série: Supabase Auth + tabela `perfis` com RLS
- Material da série: ChromaDB local + `intfloat/multilingual-e5-base`
- IA: OpenRouter, modelo `:free`
- Gestão: Trello (Kanban) + Git

## Entregas

- Fase 1: entregue em 02/09/2026 (`Artigo/2026-09-02_Fase-1_Planejamento/`).
- Fase 2: entregue em 09/09/2026 (`Artigo/2026-09-09_Fase-2_Execucao/`).
- Fase 3: data a confirmar (`Artigo/Fase-3_Produto-final-e-apresentacao/`).

## Recorte da Fase 1 (02/09/2026), para comparação

Estudantes a partir do 6º ano; Matemática, Português, Ciências e conhecimentos gerais; tutoria pelo método socrático em três modos; stack Vue 3, FastAPI, Supabase, ChromaDB e OpenRouter.
