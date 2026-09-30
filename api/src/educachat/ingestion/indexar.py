"""Inserção das habilidades no Chroma (sem dependência do modelo de embedding)."""

from collections.abc import Sequence
from typing import Any

import numpy as np
from chromadb.api.models.Collection import Collection
from numpy.typing import NDArray

from educachat.models import HabilidadeBNCC


def metadados(h: HabilidadeBNCC) -> dict[str, Any]:
    """Metadados filtráveis. Nada disso entra no texto embedado."""
    return {
        "codigo": h.codigo,
        "serie": h.serie,
        "ano_inicial": h.ano_inicial,
        "ano_final": h.ano_final,
        "componente": h.componente,
        "objeto_conhecimento": h.objeto_conhecimento,
        "pagina_pdf": h.pagina_pdf,
    }


def indexar(
    colecao: Collection,
    habilidades: Sequence[HabilidadeBNCC],
    embeddings: NDArray[np.float32],
    lote: int = 500,
) -> None:
    """Upsert idempotente: o id é o código da habilidade."""
    if len(habilidades) != len(embeddings):
        raise ValueError("habilidades e embeddings com tamanhos diferentes")
    for i in range(0, len(habilidades), lote):
        parte = habilidades[i : i + lote]
        colecao.upsert(
            ids=[h.codigo for h in parte],
            documents=[h.texto for h in parte],
            embeddings=embeddings[i : i + lote],
            metadatas=[metadados(h) for h in parte],
        )
