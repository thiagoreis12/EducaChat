"""Sorteia habilidades para conferência manual contra o PDF (critério de pronto da Fase 1).

Uso:
    python -m educachat.parsing.amostra --n 20 --seed 42 --imagens data/processed/amostra
Com ``--imagens``, renderiza o par de páginas (objetos | habilidades) de cada item em PNG.
"""

import argparse
import random
import sys
from pathlib import Path

import pymupdf

from educachat.config import get_settings
from educachat.models import BaseBNCC


def renderizar_par(doc: pymupdf.Document, pagina_pdf: int, destino: Path) -> None:
    esq, dir_ = doc[pagina_pdf - 2], doc[pagina_pdf - 1]
    w, h = dir_.rect.width, dir_.rect.height
    saida = pymupdf.open()
    page = saida.new_page(width=2 * w, height=h)
    page.show_pdf_page(pymupdf.Rect(0, 0, w, h), doc, esq.number)
    page.show_pdf_page(pymupdf.Rect(w, 0, 2 * w, h), doc, dir_.number)
    page.get_pixmap(dpi=100).save(destino)


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--json", type=Path, default=settings.bncc_json_path)
    parser.add_argument("--imagens", type=Path, default=None)
    args = parser.parse_args(argv)

    base = BaseBNCC.model_validate_json(args.json.read_text(encoding="utf-8"))
    amostra = random.Random(args.seed).sample(base.habilidades, args.n)
    doc = pymupdf.open(settings.bncc_pdf_path) if args.imagens else None
    if args.imagens:
        args.imagens.mkdir(parents=True, exist_ok=True)

    out = sys.stdout
    for i, h in enumerate(sorted(amostra, key=lambda h: h.pagina_pdf), 1):
        out.write(
            f"\n[{i:02d}] {h.codigo} | {h.serie} | {h.componente} | PDF p. {h.pagina_pdf}\n"
            f"     objeto: {h.objeto_conhecimento}\n"
            f"     texto : {h.texto}\n"
        )
        if doc is not None and args.imagens is not None:
            renderizar_par(doc, h.pagina_pdf, args.imagens / f"{i:02d}_{h.codigo}.png")


if __name__ == "__main__":
    main()
