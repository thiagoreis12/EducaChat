"""CLI da Fase 1: PDF da BNCC -> data/processed/bncc_estruturada.json."""

import argparse
import hashlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from educachat.config import get_settings
from educachat.logging_config import setup_logging
from educachat.models import BaseBNCC
from educachat.parsing.bncc_parser import extrair_habilidades

logger = logging.getLogger("educachat.parsing")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=settings.bncc_pdf_path)
    parser.add_argument("--saida", type=Path, default=settings.bncc_json_path)
    args = parser.parse_args(argv)

    setup_logging("parsing", settings.log_dir, settings.log_level)
    inicio = time.perf_counter()
    habilidades = extrair_habilidades(args.pdf)
    base = BaseBNCC(
        fonte_pdf=args.pdf.name,
        fonte_sha256=_sha256(args.pdf),
        gerado_em=datetime.now(tz=UTC).isoformat(),
        total=len(habilidades),
        habilidades=habilidades,
    )
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(base.model_dump_json(indent=2), encoding="utf-8")
    logger.info(
        "fase1_concluida",
        extra={
            "saida": str(args.saida),
            "total": len(habilidades),
            "duracao_s": round(time.perf_counter() - inicio, 3),
        },
    )


if __name__ == "__main__":
    main()
