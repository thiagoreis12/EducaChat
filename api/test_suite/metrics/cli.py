"""Fase 7: calcula o Quadro 1 a partir de um arquivo de resultados do harness.

Uso:
    python -m test_suite.metrics.cli                       # execução mais recente
    python -m test_suite.metrics.cli ARQUIVO_RESULTADOS

Saída (ao lado do arquivo de resultados): metricas_{timestamp}.json e .md
"""

import argparse
import sys
from pathlib import Path

from educachat.config import PROJECT_ROOT, get_settings
from educachat.models import BaseBNCC
from test_suite.harness.executor import carregar
from test_suite.metrics.calculo import calcular, quadro_markdown
from test_suite.modelos import ConjuntoConsultas

DIR_RESULTADOS = PROJECT_ROOT / "test_suite/resultados"


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resultados", type=Path, nargs="?", default=None)
    args = parser.parse_args(argv)

    caminho: Path | None = args.resultados
    if caminho is None:
        existentes = sorted(DIR_RESULTADOS.glob("resultados_execucao_*.json"))
        if not existentes:
            sys.stderr.write("nenhum arquivo de resultados em test_suite/resultados/\n")
            return 1
        caminho = existentes[-1]

    execucao = carregar(caminho)
    conjunto = ConjuntoConsultas.model_validate_json(
        (PROJECT_ROOT / execucao.consultas_arquivo).read_text(encoding="utf-8")
    )
    # Códigos de TODO o Fundamental (1º-9º): citar EF05.. para um aluno do 6º é vazamento,
    # não código inexistente.
    base = BaseBNCC.model_validate_json(settings.bncc_json_path.read_text(encoding="utf-8"))
    existentes_bncc = {h.codigo for h in base.habilidades}

    try:
        rotulo = str(caminho.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        rotulo = str(caminho)
    quadro = calcular(execucao, conjunto, existentes_bncc, arquivo_resultados=rotulo)
    sufixo = caminho.stem.removeprefix("resultados_execucao_")
    destino = caminho.parent / f"metricas_{sufixo}"
    destino.with_suffix(".json").write_text(quadro.model_dump_json(indent=2), encoding="utf-8")
    markdown = quadro_markdown(quadro)
    destino.with_suffix(".md").write_text(markdown, encoding="utf-8")
    sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
