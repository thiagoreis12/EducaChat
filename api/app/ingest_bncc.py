"""Ingere a BNCC no Chroma: um documento por código de habilidade."""

from __future__ import annotations

import sys
from pathlib import Path

from app.bncc import (
    contar_por_componente,
    contar_por_serie,
    extrair_habilidades,
)
from app.chroma_store import collection, consultar

RAIZ = Path(__file__).resolve().parent.parent
PDF = RAIZ / "data" / "bncc.pdf"
LOTE = 64


def _imprimir_contagens(habilidades) -> None:
    print("=== Chunks por série (token do código) ===")
    for serie, n in contar_por_serie(habilidades).items():
        print(f"  {serie}: {n}")
    print(f"  total: {len(habilidades)}")

    print("=== Chunks por componente ===")
    for componente, n in contar_por_componente(habilidades).items():
        print(f"  {componente}: {n}")


def _gravar(habilidades) -> None:
    col = collection(RAIZ, reset=True)
    for inicio in range(0, len(habilidades), LOTE):
        lote = habilidades[inicio : inicio + LOTE]
        col.add(
            ids=[h.codigo for h in lote],
            documents=[h.texto for h in lote],
            metadatas=[
                {
                    "codigo": h.codigo,
                    "serie": h.serie,
                    "componente": h.componente,
                }
                for h in lote
            ],
        )
        print(f"  gravados {min(inicio + LOTE, len(habilidades))}/{len(habilidades)}")


def _mostrar_consulta(titulo: str, pergunta: str, serie: int, componente: str) -> None:
    print(f"=== Consulta: {titulo} ===")
    print(f"  filtro: serie={serie} componente={componente}")
    print(f"  pergunta: {pergunta}")
    resultado = consultar(
        pergunta,
        serie=serie,
        componente=componente,
        n_results=3,
        raiz_api=RAIZ,
    )
    ids = resultado["ids"][0]
    docs = resultado["documents"][0]
    metas = resultado["metadatas"][0]
    if not ids:
        print("  (nenhum trecho recuperado)")
        return
    for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas), start=1):
        trecho = doc if len(doc) <= 360 else doc[:357] + "..."
        print(f"  [{i}] {doc_id}  serie={meta['serie']} componente={meta['componente']}")
        print(f"      {trecho}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Lendo {PDF}")
    habilidades = extrair_habilidades(PDF)
    if not habilidades:
        print("Nenhuma habilidade de 6º ano em diante foi extraída. Pare e revise o PDF.")
        return 1

    _imprimir_contagens(habilidades)
    print("Gravando no Chroma (baixa o modelo de embedding na primeira vez)...")
    _gravar(habilidades)

    _mostrar_consulta(
        "6º ano / Matemática",
        "comparar números naturais e racionais na reta numérica",
        serie=6,
        componente="MA",
    )
    _mostrar_consulta(
        "7º ano / Português",
        "coesão referencial com sinônimos e pronomes anafóricos",
        serie=7,
        componente="LP",
    )
    _mostrar_consulta(
        "8º ano / Ciências",
        "estrutura da Terra camadas e dinâmica interna",
        serie=8,
        componente="CI",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
