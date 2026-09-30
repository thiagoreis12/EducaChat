"""Filtro de metadados do Chroma: a busca só pode devolver habilidades válidas no ano.

Os testes unitários usam vetores sintéticos (sem modelo de embedding) numa coleção
temporária. O teste de integração roda contra a base real em data/chroma, se existir.
"""

from pathlib import Path

import chromadb
import numpy as np
import pytest

from educachat.config import get_settings
from educachat.ingestion.escopo import filtrar_escopo, no_escopo
from educachat.ingestion.indexar import indexar
from educachat.models import HabilidadeBNCC
from educachat.retrieval.busca import filtro

HABS = [
    HabilidadeBNCC.from_codigo("EF06MA07", "Compreender frações equivalentes.", "Frações", 302),
    HabilidadeBNCC.from_codigo("EF07MA08", "Comparar e ordenar frações.", "Frações", 308),
    HabilidadeBNCC.from_codigo("EF69LP01", "Discutir liberdade de expressão.", "Apreciação", 142),
    HabilidadeBNCC.from_codigo("EF89LP01", "Analisar interesses na mídia.", "Reconstrução", 178),
    HabilidadeBNCC.from_codigo("EF67EF01", "Experimentar jogos eletrônicos.", "Jogos", 235),
    HabilidadeBNCC.from_codigo("EF05MA03", "Identificar frações maiores que um.", "Frações", 297),
]


@pytest.fixture
def colecao(tmp_path: Path) -> chromadb.Collection:
    cliente = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    col = cliente.create_collection("teste", configuration={"hnsw": {"space": "cosine"}})
    rng = np.random.default_rng(0)
    indexar(col, HABS, rng.normal(size=(len(HABS), 8)).astype(np.float32))
    return col


def _codigos(col: chromadb.Collection, where: dict[str, object]) -> set[str]:
    res = col.query(query_embeddings=[np.ones(8, dtype=np.float32)], n_results=10, where=where)
    return set(res["ids"][0])


@pytest.mark.parametrize(
    ("ano", "esperados"),
    [
        (5, {"EF05MA03"}),
        (6, {"EF06MA07", "EF69LP01", "EF67EF01"}),
        (7, {"EF07MA08", "EF69LP01", "EF67EF01"}),
        (8, {"EF69LP01", "EF89LP01"}),
        (9, {"EF69LP01", "EF89LP01"}),
    ],
)
def test_filtro_por_ano_inclui_multi_ano_e_exclui_outras_series(
    colecao: chromadb.Collection, ano: int, esperados: set[str]
) -> None:
    assert _codigos(colecao, filtro(ano)) == esperados


def test_filtro_por_ano_e_componente(colecao: chromadb.Collection) -> None:
    assert _codigos(colecao, filtro(6, "Matemática")) == {"EF06MA07"}
    assert _codigos(colecao, filtro(8, "Matemática")) == set()


def test_persistencia_em_disco(tmp_path: Path) -> None:
    caminho = str(tmp_path / "chroma")
    col = chromadb.PersistentClient(path=caminho).create_collection("teste")
    indexar(col, HABS[:2], np.eye(2, 8, dtype=np.float32))
    assert chromadb.PersistentClient(path=caminho).get_collection("teste").count() == 2


def test_indexar_e_idempotente(colecao: chromadb.Collection) -> None:
    indexar(colecao, HABS, np.zeros((len(HABS), 8), dtype=np.float32) + 0.1)
    assert colecao.count() == len(HABS)


def test_metadados_nao_entram_no_documento(colecao: chromadb.Collection) -> None:
    docs = colecao.get(ids=["EF06MA07"])["documents"]
    assert docs == ["Compreender frações equivalentes."]


@pytest.mark.parametrize("ano", [0, 10])
def test_filtro_rejeita_ano_invalido(ano: int) -> None:
    with pytest.raises(ValueError):
        filtro(ano)


def test_escopo_fundamental_ii() -> None:
    assert [h.codigo for h in filtrar_escopo(HABS, 6, 9)] == [
        "EF06MA07",
        "EF07MA08",
        "EF69LP01",
        "EF89LP01",
        "EF67EF01",
    ]
    assert not no_escopo(HABS[-1], 6, 9)


def _base_real_disponivel() -> bool:
    s = get_settings()
    if not s.chroma_dir.exists():
        return False
    nomes = [c.name for c in chromadb.PersistentClient(path=str(s.chroma_dir)).list_collections()]
    return s.chroma_collection in nomes


@pytest.mark.integracao
@pytest.mark.skipif(not _base_real_disponivel(), reason="base Chroma da Fase 2 não encontrada")
@pytest.mark.parametrize("ano", [6, 7, 8, 9])
def test_base_real_filtro_restringe_resultados(ano: int) -> None:
    from educachat.retrieval.busca import abrir_colecao, buscar

    col = abrir_colecao()
    resultados = buscar(col, "fração", ano=ano, k=10)
    assert len(resultados) == 10
    for r in resultados:
        ini, fim = int(r.codigo[2]), int(r.codigo[3])
        ini = fim if ini == 0 else ini
        assert ini <= ano <= fim, f"{r.codigo} vazou para o {ano}º ano"
