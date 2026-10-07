# Briefing para Marcus Paulo Pereira de Oliveira

Ciência da Computação — dupla com Thiago Reis (ADS / ETEP). Atualizado em 30/09/2026.

## O que é

**EducaChat** é um protótipo de assistente de estudos para alunos do 6º ao 9º ano, ancorado na BNCC. A série vem do perfil do aluno, a busca no currículo é filtrada por ela, e o assistente recusa trabalho pronto. Ainda **não há escola parceira**.

## Onde está o código

- Repositório da dupla: https://github.com/thiagoreis12/EducaChat
- Seu repositório ([MarcusSant0s/educachat](https://github.com/MarcusSant0s/educachat)) entra inteiro na pasta `api/` do repositório da dupla, com o seu histórico preservado (subtree). A integração mais recente é o commit `4cde3e4` (Supabase Auth, front Vue 3 e integração local).
- Você pode continuar trabalhando no seu repositório. Para trazer as novidades, o Thiago roda:

```powershell
git fetch marcus
git merge -X subtree=api marcus/master
```

- O esqueleto antigo do Thiago (`web/` e a primeira ingestão com MiniLM) foi removido: o seu pipeline e o seu front substituíram os dois.

## Ajuste local na máquina do Thiago

A porta 8000 lá é de um nginx. A API sobe na 8001 e o front aponta para ela por um `api/frontend/.env.development.local`, fora do Git. Nenhum arquivo seu foi alterado.

## Estado

- 162 testes do back-end passando (`pytest -m "not integracao"`), 18 do front (Vitest) e `vue-tsc` sem erros.
- Pendentes que dependem da dupla, os mesmos do seu README:
  1. Criar o projeto Supabase, aplicar `supabase/migrations/0001_perfis.sql` e preencher o `.env`.
  2. Fluxo manual: cadastro → login → pergunta → resposta com habilidades → recarregar → sair.
  3. `scripts/verificar_seguranca.sh` contra o Supabase real.
  4. Harness (151 × 2 chamadas) e métricas com o OpenRouter.
  5. Conferência da amostra de 20 habilidades (D06) e das definições das métricas (D21).
  6. SUS com o produto integrado.

## Diferenças em relação ao artigo da Fase 1

O artigo planejou três modos (dúvida, trabalho e exercício) com condução socrática, e só Matemática, Português, Ciências e conhecimentos gerais. O código tem um modo único, cobre os 9 componentes e filtra só por ano (D17). A 2.1 do artigo registra isso como ajuste do planejado. Se a dupla quiser os três modos, eles entram como trabalho novo no prompt e no `/chat`.

## Contato do recorte

Thiago Reis (ADS) e Marcus Paulo Pereira de Oliveira (Ciência da Computação).
