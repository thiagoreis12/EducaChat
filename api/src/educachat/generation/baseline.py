"""Baseline: chamada direta ao LLM, sem recuperação."""

import time

from educachat.config import Settings, get_settings
from educachat.generation.modelos import ConfigGeracao, Resposta
from educachat.generation.openrouter import ClienteOpenRouter
from educachat.generation.prompts import VERSAO_PROMPT, mensagens_baseline
from educachat.generation.validacao import validar_ano


def responder_baseline(
    pergunta: str,
    ano_aluno: int,
    *,
    cliente: ClienteOpenRouter | None = None,
    settings: Settings | None = None,
) -> Resposta:
    """Responde sem contexto da BNCC. Recebe a série (decisão D16) para isolar o efeito
    da recuperação na comparação com o protótipo.

    Uso interno de avaliação: não deve ser exposto ao usuário final (Fase 5.5).
    """
    settings = settings or get_settings()
    validar_ano(ano_aluno, settings)
    cliente = cliente or ClienteOpenRouter.from_settings(settings)

    inicio = time.perf_counter()
    llm = cliente.completar(
        mensagens_baseline(pergunta, ano_aluno),
        temperatura=settings.llm_temperatura,
        max_tokens=settings.llm_max_tokens,
    )
    return Resposta(
        texto=llm.texto,
        tempo_ms=round((time.perf_counter() - inicio) * 1000, 1),
        tempo_llm_ms=llm.tempo_ms,
        tentativas_llm=llm.tentativas,
        tokens_prompt=llm.tokens_prompt,
        tokens_resposta=llm.tokens_resposta,
        config=ConfigGeracao(
            modo="baseline",
            modelo_llm=llm.modelo,
            temperatura=settings.llm_temperatura,
            max_tokens=settings.llm_max_tokens,
            versao_prompt=VERSAO_PROMPT,
            ano_aluno=ano_aluno,
        ),
    )
