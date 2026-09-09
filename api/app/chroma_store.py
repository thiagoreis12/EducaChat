"""Chroma local. Toda consulta exige filtro de série e componente."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.bncc import series_do_aluno

COLLECTION = "bncc_habilidades"
MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"


def embedding_pt_br() -> SentenceTransformerEmbeddingFunction:
    # O default do Chroma é all-MiniLM em inglês; para pt-BR a similaridade cai.
    return SentenceTransformerEmbeddingFunction(model_name=MODELO_EMBEDDING)


def caminho_persistencia(raiz_api: Path | None = None) -> Path:
    base = raiz_api if raiz_api is not None else Path(__file__).resolve().parent.parent
    return base / "data" / "chroma"


def cliente(raiz_api: Path | None = None) -> chromadb.PersistentClient:
    # PersistentClient grava em pasta local — banco embutido, sem servidor
    # (parecido com um H2/SQLite, não com um PostgreSQL remoto).
    path = caminho_persistencia(raiz_api)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def collection(raiz_api: Path | None = None, *, reset: bool = False):
    db = cliente(raiz_api)
    if reset and COLLECTION in {c.name for c in db.list_collections()}:
        db.delete_collection(COLLECTION)
    return db.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embedding_pt_br(),
        metadata={"hnsw:space": "cosine"},
    )


def consultar(
    pergunta: str,
    *,
    serie: int | None,
    componente: str | None,
    n_results: int = 4,
    raiz_api: Path | None = None,
) -> dict[str, Any]:
    if serie is None or componente is None or not str(componente).strip():
        raise ValueError(
            "Consulta ao Chroma sem filtro de série e componente é proibida."
        )

    blocos = series_do_aluno(int(serie))
    if not blocos:
        raise ValueError(f"Série {serie} está fora do recorte (6º ano em diante).")

    col = collection(raiz_api)
    return col.query(
        query_texts=[pergunta],
        n_results=n_results,
        where={
            "$and": [
                {"serie": {"$in": blocos}},
                {"componente": componente.strip().upper()},
            ]
        },
    )
