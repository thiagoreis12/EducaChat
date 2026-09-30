"""Fase 6: roda baseline e protótipo para cada item de test_suite/consultas.json.

Uso:
    python -m test_suite.harness.cli                     # nova execução
    python -m test_suite.harness.cli --retomar-ultimo    # continua a execução mais recente
    python -m test_suite.harness.cli --retomar ARQUIVO   # continua uma execução específica
    python -m test_suite.harness.cli --limite 3          # teste rápido com 3 itens

Saída: test_suite/resultados/resultados_execucao_{timestamp}.json
"""

import argparse
import hashlib
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

from educachat.config import PROJECT_ROOT, get_settings
from educachat.generation.baseline import responder_baseline
from educachat.generation.openrouter import ClienteOpenRouter
from educachat.generation.prototipo import recuperador_padrao, responder_prototipo
from educachat.logging_config import setup_logging
from test_suite.harness.executor import InterrompidoPorLimite, agora, carregar, executar
from test_suite.modelos import ConjuntoConsultas, ExecucaoLote, Modo

logger = logging.getLogger("test_suite.harness")
DIR_RESULTADOS = PROJECT_ROOT / "test_suite/resultados"


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--consultas", type=Path, default=PROJECT_ROOT / "test_suite/consultas.json"
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--retomar", type=Path, default=None)
    grupo.add_argument("--retomar-ultimo", action="store_true")
    parser.add_argument(
        "--modos", nargs="+", choices=list(get_args(Modo)), default=list(get_args(Modo))
    )
    parser.add_argument("--limite", type=int, default=None, help="só os N primeiros itens")
    parser.add_argument("--checkpoint", type=int, default=5, help="salvar a cada N chamadas")
    parser.add_argument("--pausa", type=float, default=0.0, help="segundos entre chamadas")
    parser.add_argument("--ignorar-versao-base", action="store_true")
    args = parser.parse_args(argv)
    setup_logging("harness", settings.log_dir, settings.log_level)

    bruto = args.consultas.read_bytes()
    conjunto = ConjuntoConsultas.model_validate_json(bruto)
    sha = hashlib.sha256(bruto).hexdigest()

    recuperador = recuperador_padrao()
    if recuperador.versao_base != conjunto.versao_base and not args.ignorar_versao_base:
        logger.error(
            "versao_base_divergente",
            extra={"consultas": conjunto.versao_base, "colecao": recuperador.versao_base},
        )
        sys.stderr.write(
            f"consultas.json foi gerado para a base {conjunto.versao_base}, mas a coleção atual "
            f"é {recuperador.versao_base}. Regere as consultas ou use --ignorar-versao-base.\n"
        )
        return 1

    caminho: Path | None = args.retomar
    if args.retomar_ultimo:
        existentes = sorted(DIR_RESULTADOS.glob("resultados_execucao_*.json"))
        if not existentes:
            sys.stderr.write("nenhuma execução anterior para retomar\n")
            return 1
        caminho = existentes[-1]

    if caminho is not None:
        execucao = carregar(caminho)
        if execucao.consultas_sha256 != sha:
            sys.stderr.write("consultas.json mudou desde o início desta execução; abortando\n")
            return 1
    else:
        DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        caminho = DIR_RESULTADOS / f"resultados_execucao_{stamp}.json"
        execucao = ExecucaoLote(
            iniciado_em=agora(),
            atualizado_em=agora(),
            consultas_arquivo=str(args.consultas.relative_to(PROJECT_ROOT)),
            consultas_sha256=sha,
            versao_base=conjunto.versao_base,
            modelo_llm=settings.openrouter_model,
            parametros={
                "temperatura": settings.llm_temperatura,
                "max_tokens": settings.llm_max_tokens,
                "k": settings.rag_k,
            },
            modos=args.modos,
        )

    cliente = ClienteOpenRouter.from_settings(settings)
    responders = {
        "baseline": lambda p, a: responder_baseline(p, a, cliente=cliente, settings=settings),
        "prototipo": lambda p, a: responder_prototipo(
            p, a, cliente=cliente, recuperador=recuperador, settings=settings
        ),
    }
    try:
        executar(
            conjunto,
            execucao,
            responders,  # type: ignore[arg-type]
            caminho,
            checkpoint_cada=args.checkpoint,
            pausa_s=args.pausa,
            limite_itens=args.limite,
        )
    except InterrompidoPorLimite as exc:
        sys.stderr.write(
            f"{exc}\nRetome com: python -m test_suite.harness.cli --retomar {caminho}\n"
        )
        return 2
    sys.stdout.write(f"Resultados em {caminho}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
