"""Modelos de embedding candidatos e a função de embedding usada pelo Chroma.

Documentos e consultas passam pela mesma função; modelos da família E5 exigem
prefixos diferentes ("passage: " / "query: "), por isso o prefixo é aplicado aqui
e não espalhado pelo código de ingestão e busca.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


@dataclass(frozen=True)
class ModeloEmbedding:
    nome: str
    hf_id: str
    prefixo_documento: str = ""
    prefixo_consulta: str = ""


MODELOS: dict[str, ModeloEmbedding] = {
    m.nome: m
    for m in (
        ModeloEmbedding(
            "paraphrase-multilingual-mpnet-base-v2",
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        ),
        ModeloEmbedding(
            "paraphrase-multilingual-MiniLM-L12-v2",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ),
        ModeloEmbedding(
            "multilingual-e5-base",
            "intfloat/multilingual-e5-base",
            prefixo_documento="passage: ",
            prefixo_consulta="query: ",
        ),
    )
}


@lru_cache(maxsize=1)
def carregar(nome: str) -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELOS[nome].hf_id, device="cpu")


def codificar(
    nome: str,
    textos: list[str],
    tipo: Literal["documento", "consulta"],
    batch_size: int = 32,
) -> NDArray[np.float32]:
    """Embeddings L2-normalizados (similaridade de cosseno = produto interno)."""
    modelo = MODELOS[nome]
    prefixo = modelo.prefixo_documento if tipo == "documento" else modelo.prefixo_consulta
    vetores = carregar(nome).encode(
        [prefixo + t for t in textos],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vetores, dtype=np.float32)


def _registrar() -> type:
    from chromadb.api.types import Documents, EmbeddingFunction, Embeddings, Space
    from chromadb.utils.embedding_functions import register_embedding_function

    @register_embedding_function
    class EmbeddingBNCC(EmbeddingFunction[Documents]):
        """Adapta ``codificar`` ao protocolo do Chroma (inclui prefixo de consulta do E5).

        Registrada e serializável: o Chroma persiste ``get_config`` junto da coleção,
        então reabrir a base com outro modelo é detectado em vez de gerar vetores
        incompatíveis em silêncio.
        """

        def __init__(self, modelo: str) -> None:
            if modelo not in MODELOS:
                raise ValueError(f"modelo de embedding desconhecido: {modelo}")
            self.modelo = modelo

        def __call__(self, input: Documents) -> Embeddings:
            return list(codificar(self.modelo, list(input), "documento"))

        def embed_query(self, input: Documents) -> Embeddings:
            return list(codificar(self.modelo, list(input), "consulta"))

        @staticmethod
        def name() -> str:
            return "educachat-bncc"

        def default_space(self) -> Space:
            return "cosine"

        def supported_spaces(self) -> list[Space]:
            return ["cosine"]

        def get_config(self) -> dict[str, str]:
            return {"modelo": self.modelo}

        @staticmethod
        def build_from_config(config: dict[str, str]) -> "EmbeddingBNCC":
            return EmbeddingBNCC(config["modelo"])

        def validate_config_update(
            self, old_config: dict[str, str], new_config: dict[str, str]
        ) -> None:
            if old_config.get("modelo") != new_config.get("modelo"):
                raise ValueError("trocar o modelo exige reindexar a coleção (--recriar)")

    return EmbeddingBNCC


@lru_cache(maxsize=1)
def classe_embedding_chroma() -> type:
    return _registrar()
