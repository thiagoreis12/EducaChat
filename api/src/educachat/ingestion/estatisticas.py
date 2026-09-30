"""Fase 3: estatísticas da base indexada (fecha os [pendente] de contagem do artigo).

Lê a coleção do Chroma (``count`` + ``get``) e agrega em Python. Os tempos vêm dos
logs estruturados da Fase 1 (``fase1_concluida``) e da Fase 2 (``fase2_concluida``).
Só vale o log de ingestão cujo ``versao_base`` coincide com o da coleção atual, para
não citar o tempo de uma indexação que não é a que está em disco.

Uso: python -m educachat.ingestion.estatisticas [--saida arquivo.json]
"""

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from educachat.config import PROJECT_ROOT, get_settings
from educachat.retrieval.busca import abrir_colecao


def agregar(metadados: Sequence[Mapping[str, Any]], anos: range) -> dict[str, Any]:
    """Contagens por rótulo de série, por componente e por ano efetivo.

    "Por ano efetivo" conta cada habilidade em todos os anos em que vale (EF69LP01
    conta no 6º, 7º, 8º e 9º). É o que um aluno de cada ano pode receber, e por isso
    a soma dessa tabela é maior que o total de documentos.
    """
    por_serie = Counter(str(m["serie"]) for m in metadados)
    por_componente = Counter(str(m["componente"]) for m in metadados)
    por_ano: dict[int, int] = {}
    por_ano_componente: dict[int, dict[str, int]] = {}
    for ano in anos:
        validas = [m for m in metadados if int(m["ano_inicial"]) <= ano <= int(m["ano_final"])]
        por_ano[ano] = len(validas)
        por_ano_componente[ano] = dict(
            sorted(Counter(str(m["componente"]) for m in validas).items())
        )
    exclusivas = sum(1 for m in metadados if m["ano_inicial"] == m["ano_final"])
    return {
        "total_documentos": len(metadados),
        "habilidades_ano_unico": exclusivas,
        "habilidades_multi_ano": len(metadados) - exclusivas,
        "por_serie": dict(sorted(por_serie.items())),
        "por_componente": dict(sorted(por_componente.items())),
        "por_ano_efetivo": por_ano,
        "por_ano_efetivo_e_componente": por_ano_componente,
    }


def ultimo_evento(
    log_dir: Path, prefixo: str, evento: str, filtro: Mapping[str, Any] | None = None
) -> dict[str, Any] | None:
    """Último registro ``evento`` nos logs ``{prefixo}_*.jsonl`` que casa com ``filtro``."""
    encontrado: dict[str, Any] | None = None
    for caminho in sorted(log_dir.glob(f"{prefixo}_*.jsonl")):
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            try:
                registro = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if registro.get("event") != evento:
                continue
            if filtro and any(registro.get(k) != v for k, v in filtro.items()):
                continue
            if encontrado is None or registro["ts"] > encontrado["ts"]:
                encontrado = registro
    return encontrado


def _tabela(stats: dict[str, Any]) -> str:
    anos = list(stats["por_ano_efetivo_e_componente"])
    componentes = sorted(stats["por_componente"])
    largura = max(len(c) for c in componentes) + 2
    linhas = ["Componente".ljust(largura) + "".join(f"{a}º ano".rjust(9) for a in anos)]
    for c in componentes:
        valores = "".join(
            str(stats["por_ano_efetivo_e_componente"][a].get(c, 0)).rjust(9) for a in anos
        )
        linhas.append(c.ljust(largura) + valores)
    linhas.append(
        "Total".ljust(largura) + "".join(str(stats["por_ano_efetivo"][a]).rjust(9) for a in anos)
    )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--saida", type=Path, default=PROJECT_ROOT / "data/processed/estatisticas_base.json"
    )
    args = parser.parse_args(argv)

    colecao = abrir_colecao(settings)
    meta_colecao = dict(colecao.metadata or {})
    registros = colecao.get(include=["metadatas"])["metadatas"] or []
    total = colecao.count()
    if total != len(registros):
        raise RuntimeError(f"count()={total} difere de get()={len(registros)}")

    stats = agregar(registros, range(settings.escopo_ano_min, settings.escopo_ano_max + 1))
    ingestao = ultimo_evento(
        settings.log_dir,
        "ingestion",
        "fase2_concluida",
        {"versao_base": meta_colecao.get("versao_base")},
    )
    parsing = ultimo_evento(settings.log_dir, "parsing", "fase1_concluida")
    tempos = {
        "fase1_parsing_s": parsing["duracao_s"] if parsing else None,
        "fase2_total_s": ingestao["duracao_s"] if ingestao else None,
        "fase2_carga_modelo_s": ingestao["carga_modelo_s"] if ingestao else None,
        "fase2_embeddings_s": ingestao["embeddings_s"] if ingestao else None,
        "fase2_insercao_s": ingestao["insercao_s"] if ingestao else None,
        "fase2_log_ts": ingestao["ts"] if ingestao else None,
    }
    saida = {"colecao": colecao.name, "metadados_colecao": meta_colecao, **stats, "tempos": tempos}
    args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    out = sys.stdout
    out.write(
        f"Coleção {colecao.name!r} | versao_base {meta_colecao.get('versao_base')} | "
        f"modelo {meta_colecao.get('modelo_embedding')}\n"
        f"Documentos: {stats['total_documentos']} "
        f"({stats['habilidades_ano_unico']} de ano único, "
        f"{stats['habilidades_multi_ano']} multi-ano)\n\n"
        "Por rótulo de série:\n"
        + "".join(f"  {s:<16}{n:>5}\n" for s, n in stats["por_serie"].items())
        + "\nHabilidades válidas por ano (multi-ano contam em cada ano):\n"
        + _tabela(stats)
        + "\n\nTempos:\n"
        + "".join(f"  {k:<24}{v}\n" for k, v in tempos.items())
    )
    if ingestao is None:
        out.write("  AVISO: nenhum log de ingestão com o versao_base atual.\n")
    out.write(f"\nJSON salvo em {args.saida}\n")


if __name__ == "__main__":
    main()
