"""Chroma local. Toda consulta exige filtro de série e componente."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.bncc import series_do_aluno

COLLECTION = "bncc_habilidades"
STAGING_COLLECTION = "bncc_habilidades_staging"
MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"
PONTEIRO = "colecao_ativa.txt"


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


def _arquivo_ponteiro(raiz_api: Path | None = None) -> Path:
    return caminho_persistencia(raiz_api) / PONTEIRO


def nome_colecao_ativa(raiz_api: Path | None = None) -> str:
    caminho = _arquivo_ponteiro(raiz_api)
    if caminho.is_file():
        nome = caminho.read_text(encoding="utf-8").strip()
        if nome in {COLLECTION, STAGING_COLLECTION}:
            return nome
    return COLLECTION


def _nomes(db: chromadb.PersistentClient) -> set[str]:
    return {c.name for c in db.list_collections()}


def _abrir_colecao(db: chromadb.PersistentClient, nome: str):
    return db.get_or_create_collection(
        name=nome,
        embedding_function=embedding_pt_br(),
        metadata={"hnsw:space": "cosine"},
    )


def collection(raiz_api: Path | None = None):
    return _abrir_colecao(cliente(raiz_api), nome_colecao_ativa(raiz_api))


def nome_colecao_staging(raiz_api: Path | None = None) -> str:
    ativo = nome_colecao_ativa(raiz_api)
    return STAGING_COLLECTION if ativo == COLLECTION else COLLECTION


@contextmanager
def bloqueio_ingestao(raiz_api: Path | None = None) -> Iterator[None]:
    """Lock exclusivo no disco (fcntl/msvcrt). Cobre preparar → gravar → validar → ativar."""
    caminho = caminho_persistencia(raiz_api) / "ingest.lock"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fh = open(caminho, "a+b")
    try:
        if fh.seek(0, 2) == 0:
            fh.write(b"0")
            fh.flush()
        fh.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fh.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


def preparar_staging(raiz_api: Path | None = None) -> tuple[Any, str]:
    """Recria só o slot inativo. Devolve a coleção e o nome capturado."""
    db = cliente(raiz_api)
    nome = nome_colecao_staging(raiz_api)
    if nome in _nomes(db):
        db.delete_collection(nome)
    return _abrir_colecao(db, nome), nome


def validar_ids(col, ids: list[str]) -> None:
    obtido = set(col.get(ids=ids)["ids"])
    faltando = set(ids) - obtido
    if faltando:
        raise RuntimeError(
            "Lote incompleto no staging: " + ", ".join(sorted(faltando))
        )


def ativar_staging(
    raiz_api: Path | None = None,
    *,
    nome: str,
    esperado: int,
) -> None:
    """Ativa o nome capturado em preparar_staging — não recalcula pelo ponteiro."""
    if nome not in {COLLECTION, STAGING_COLLECTION}:
        raise ValueError(f"Nome de coleção inválido: {nome}")
    db = cliente(raiz_api)
    if nome not in _nomes(db):
        raise RuntimeError(f"Staging {nome} não existe; a coleção ativa não foi alterada.")
    col = _abrir_colecao(db, nome)
    gravados = col.count()
    if gravados != esperado:
        raise RuntimeError(
            f"Staging incompleto ({gravados} != {esperado}); "
            "a coleção ativa não foi alterada."
        )
    caminho = _arquivo_ponteiro(raiz_api)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(nome, encoding="utf-8")


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
