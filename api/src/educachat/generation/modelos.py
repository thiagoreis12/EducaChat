"""Modelos de saída da geração (Fase 5)."""

from typing import Literal

from pydantic import BaseModel, Field

from educachat.retrieval.busca import HabilidadeRecuperada


class ConfigGeracao(BaseModel):
    """Tudo o que é preciso para reproduzir uma resposta."""

    modo: Literal["baseline", "prototipo"]
    modelo_llm: str
    temperatura: float
    max_tokens: int
    versao_prompt: int
    ano_aluno: int
    # Só no protótipo:
    k: int | None = None
    filtro: dict[str, object] | None = None
    modelo_embedding: str | None = None
    versao_base: str | None = None


class Resposta(BaseModel):
    texto: str
    tempo_ms: float = Field(description="Tempo total: recuperação + LLM")
    tempo_recuperacao_ms: float = 0.0
    tempo_llm_ms: float
    tentativas_llm: int
    tokens_prompt: int | None = None
    tokens_resposta: int | None = None
    config: ConfigGeracao
    contexto_usado: list[HabilidadeRecuperada] = Field(
        default_factory=list,
        description="Habilidades entregues ao LLM (vazio no baseline). Permite calcular "
        "rastreabilidade e vazamento de série sem re-executar.",
    )
