import json
from pathlib import Path

from educachat.ingestion.estatisticas import agregar, ultimo_evento
from educachat.ingestion.indexar import metadados
from educachat.models import HabilidadeBNCC

HABS = [
    HabilidadeBNCC.from_codigo("EF06MA01", "Texto de teste válido.", "Objeto", 1),
    HabilidadeBNCC.from_codigo("EF06MA02", "Texto de teste válido.", "Objeto", 1),
    HabilidadeBNCC.from_codigo("EF07CI01", "Texto de teste válido.", "Objeto", 1),
    HabilidadeBNCC.from_codigo("EF69LP01", "Texto de teste válido.", "Objeto", 1),
    HabilidadeBNCC.from_codigo("EF89EF01", "Texto de teste válido.", "Objeto", 1),
]


def test_agregar_conta_multi_ano_em_cada_ano() -> None:
    stats = agregar([metadados(h) for h in HABS], range(6, 10))
    assert stats["total_documentos"] == 5
    assert stats["habilidades_ano_unico"] == 3
    assert stats["habilidades_multi_ano"] == 2
    assert stats["por_serie"] == {
        "6º ano": 2,
        "6º ao 9º ano": 1,
        "7º ano": 1,
        "8º ao 9º ano": 1,
    }
    assert stats["por_ano_efetivo"] == {6: 3, 7: 2, 8: 2, 9: 2}
    assert stats["por_ano_efetivo_e_componente"][6] == {"Língua Portuguesa": 1, "Matemática": 2}
    assert stats["por_ano_efetivo_e_componente"][9] == {
        "Educação Física": 1,
        "Língua Portuguesa": 1,
    }


def _log(caminho: Path, registros: list[dict[str, object]]) -> None:
    caminho.write_text("\n".join(json.dumps(r) for r in registros) + "\nlixo\n", encoding="utf-8")


def test_ultimo_evento_respeita_versao_base(tmp_path: Path) -> None:
    _log(
        tmp_path / "ingestion_20260101T000000Z.jsonl",
        [
            {
                "ts": "2026-01-01T00:00:00",
                "event": "fase2_concluida",
                "versao_base": "aaa",
                "duracao_s": 10,
            },
            {"ts": "2026-01-01T00:00:01", "event": "outro"},
        ],
    )
    _log(
        tmp_path / "ingestion_20260102T000000Z.jsonl",
        [
            {
                "ts": "2026-01-02T00:00:00",
                "event": "fase2_concluida",
                "versao_base": "bbb",
                "duracao_s": 20,
            }
        ],
    )
    assert ultimo_evento(tmp_path, "ingestion", "fase2_concluida")["duracao_s"] == 20  # type: ignore[index]
    achado = ultimo_evento(tmp_path, "ingestion", "fase2_concluida", {"versao_base": "aaa"})
    assert achado is not None and achado["duracao_s"] == 10
    assert ultimo_evento(tmp_path, "ingestion", "fase2_concluida", {"versao_base": "zzz"}) is None
