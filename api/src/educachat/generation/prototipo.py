"""Protótipo: recupera habilidades da série do aluno no Chroma e responde com esse contexto."""

import logging
import time
from functools import lru_cache
from typing import Protocol

from chromadb.api.models.Collection import Collection

from educachat.config import Settings, get_settings
from educachat.generation.modelos import ConfigGeracao, Resposta
from educachat.generation.openrouter import ClienteOpenRouter
from educachat.generation.prompts import VERSAO_PROMPT, mensagens_prototipo
from educachat.generation.validacao import validar_ano
from educachat.retrieval.busca import HabilidadeRecuperada, abrir_colecao, buscar, filtro

logger = logging.getLogger(__name__)


class VazamentoDeSerie(RuntimeError):
    """A recuperação devolveu habilidade que não vale para o ano do aluno."""


class Recuperador(Protocol):
    versao_base: str | None
    modelo_embedding: str | None

    def __call__(self, pergunta: str, ano: int, k: int) -> list[HabilidadeRecuperada]: ...


class RecuperadorChroma:
    def __init__(self, colecao: Collection) -> None:
        self.colecao = colecao
        meta = colecao.metadata or {}
        self.versao_base = str(meta["versao_base"]) if "versao_base" in meta else None
        self.modelo_embedding = (
            str(meta["modelo_embedding"]) if "modelo_embedding" in meta else None
        )

    def __call__(self, pergunta: str, ano: int, k: int) -> list[HabilidadeRecuperada]:
        # P2/D17: filtro somente por ano; o componente não restringe a busca.
        return buscar(self.colecao, pergunta, ano=ano, k=k)


@lru_cache(maxsize=1)
def recuperador_padrao() -> RecuperadorChroma:
    return RecuperadorChroma(abrir_colecao())


def _valida_no_ano(codigo: str, ano: int) -> bool:
    d1, d2 = int(codigo[2]), int(codigo[3])
    inicio, fim = (d2, d2) if d1 == 0 else (d1, d2)
    return inicio <= ano <= fim


def responder_prototipo(
    pergunta: str,
    ano_aluno: int,
    *,
    cliente: ClienteOpenRouter | None = None,
    recuperador: Recuperador | None = None,
    settings: Settings | None = None,
) -> Resposta:
    """Responde ancorado nas habilidades da BNCC válidas para ``ano_aluno``.

    ``ano_aluno`` deve vir do perfil autenticado, nunca do corpo da requisição (Fase 5.5).
    """
    settings = settings or get_settings()
    validar_ano(ano_aluno, settings)
    cliente = cliente or ClienteOpenRouter.from_settings(settings)
    recuperador = recuperador or recuperador_padrao()

    inicio = time.perf_counter()
    contexto = recuperador(pergunta, ano_aluno, settings.rag_k)
    tempo_recuperacao_ms = round((time.perf_counter() - inicio) * 1000, 1)

    # Defesa em profundidade: o filtro do Chroma já garante isso; se falhar, não
    # entregamos ao LLM conteúdo de outra série.
    fora = [h.codigo for h in contexto if not _valida_no_ano(h.codigo, ano_aluno)]
    if fora:
        logger.error("vazamento_de_serie", extra={"ano_aluno": ano_aluno, "codigos": fora})
        raise VazamentoDeSerie(f"recuperação devolveu {fora} para o {ano_aluno}º ano")

    llm = cliente.completar(
        mensagens_prototipo(pergunta, ano_aluno, contexto),
        temperatura=settings.llm_temperatura,
        max_tokens=settings.llm_max_tokens,
    )
    return Resposta(
        texto=llm.texto,
        tempo_ms=round((time.perf_counter() - inicio) * 1000, 1),
        tempo_recuperacao_ms=tempo_recuperacao_ms,
        tempo_llm_ms=llm.tempo_ms,
        tentativas_llm=llm.tentativas,
        tokens_prompt=llm.tokens_prompt,
        tokens_resposta=llm.tokens_resposta,
        config=ConfigGeracao(
            modo="prototipo",
            modelo_llm=llm.modelo,
            temperatura=settings.llm_temperatura,
            max_tokens=settings.llm_max_tokens,
            versao_prompt=VERSAO_PROMPT,
            ano_aluno=ano_aluno,
            k=settings.rag_k,
            filtro=filtro(ano_aluno),
            modelo_embedding=recuperador.modelo_embedding,
            versao_base=recuperador.versao_base,
        ),
        contexto_usado=contexto,
    )
