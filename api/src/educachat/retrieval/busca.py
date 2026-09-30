"""Busca semântica na base BNCC com filtro obrigatório por ano (e opcional por componente).

A série do aluno é um inteiro (6..9). Como habilidades multi-ano (EF69LP.., EF67EF..)
valem para vários anos, o filtro é por intervalo:
``ano_inicial <= ano <= ano_final``. Um filtro por igualdade de ``serie`` perderia
essas habilidades.
"""

from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from pydantic import BaseModel

from educachat.config import Settings, get_settings
from educachat.ingestion.embeddings import classe_embedding_chroma


class HabilidadeRecuperada(BaseModel):
    codigo: str
    serie: str
    componente: str
    objeto_conhecimento: str
    texto: str
    distancia: float


def filtro(ano: int, componente: str | None = None) -> dict[str, Any]:
    """Cláusula ``where`` do Chroma para habilidades válidas no ``ano`` informado."""
    if not 1 <= ano <= 9:
        raise ValueError(f"ano fora do Ensino Fundamental: {ano}")
    condicoes: list[dict[str, Any]] = [
        {"ano_inicial": {"$lte": ano}},
        {"ano_final": {"$gte": ano}},
    ]
    if componente is not None:
        condicoes.append({"componente": {"$eq": componente}})
    return {"$and": condicoes}


def abrir_colecao(settings: Settings | None = None) -> Collection:
    """Abre a coleção persistida (criada pela Fase 2) com a mesma função de embedding."""
    settings = settings or get_settings()
    cliente = chromadb.PersistentClient(path=str(settings.chroma_dir))
    ef = classe_embedding_chroma()(settings.embedding_model)
    return cliente.get_collection(settings.chroma_collection, embedding_function=ef)


def buscar(
    colecao: Collection,
    pergunta: str,
    ano: int,
    componente: str | None = None,
    k: int = 5,
) -> list[HabilidadeRecuperada]:
    res = colecao.query(
        query_texts=[pergunta],
        n_results=k,
        where=filtro(ano, componente),
        include=["documents", "metadatas", "distances"],
    )
    documentos = (res["documents"] or [[]])[0]
    metadados = (res["metadatas"] or [[]])[0]
    distancias = (res["distances"] or [[]])[0]
    return [
        HabilidadeRecuperada(
            codigo=str(m["codigo"]),
            serie=str(m["serie"]),
            componente=str(m["componente"]),
            objeto_conhecimento=str(m["objeto_conhecimento"]),
            texto=doc,
            distancia=float(dist),
        )
        for doc, m, dist in zip(documentos, metadados, distancias, strict=True)
    ]
