"""CLI da Fase 2: bncc_estruturada.json -> coleção persistente no ChromaDB.

Uso: python -m educachat.ingestion.cli [--recriar]
"""

import argparse
import hashlib
import logging
import time
from datetime import UTC, datetime

import chromadb

from educachat.config import get_settings
from educachat.ingestion.embeddings import carregar, classe_embedding_chroma, codificar
from educachat.ingestion.escopo import filtrar_escopo
from educachat.ingestion.indexar import indexar
from educachat.logging_config import setup_logging
from educachat.models import BaseBNCC

logger = logging.getLogger("educachat.ingestion")


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recriar", action="store_true", help="apaga a coleção antes de indexar")
    args = parser.parse_args(argv)
    setup_logging("ingestion", settings.log_dir, settings.log_level)

    t_total = time.perf_counter()
    bruto = settings.bncc_json_path.read_bytes()
    base = BaseBNCC.model_validate_json(bruto)
    habs = filtrar_escopo(base.habilidades, settings.escopo_ano_min, settings.escopo_ano_max)
    json_sha = hashlib.sha256(bruto).hexdigest()
    escopo = f"{settings.escopo_ano_min}-{settings.escopo_ano_max}"
    # Identifica o estado da base indexada; a Fase 4 grava isso em consultas.json.
    versao_base = hashlib.sha256(
        f"{json_sha}|{settings.embedding_model}|{escopo}".encode()
    ).hexdigest()[:12]
    logger.info(
        "escopo_selecionado",
        extra={"habilidades": len(habs), "total_base": base.total, "escopo": escopo},
    )

    t0 = time.perf_counter()
    carregar(settings.embedding_model)
    carga_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    vetores = codificar(settings.embedding_model, [h.texto for h in habs], "documento")
    embeddings_s = time.perf_counter() - t0
    logger.info(
        "embeddings_gerados",
        extra={
            "modelo": settings.embedding_model,
            "dimensao": int(vetores.shape[1]),
            "duracao_s": round(embeddings_s, 3),
        },
    )

    t0 = time.perf_counter()
    cliente = chromadb.PersistentClient(path=str(settings.chroma_dir))
    if args.recriar and settings.chroma_collection in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(settings.chroma_collection)
        logger.info("colecao_apagada", extra={"colecao": settings.chroma_collection})
    colecao = cliente.get_or_create_collection(
        settings.chroma_collection,
        embedding_function=classe_embedding_chroma()(settings.embedding_model),
        configuration={"hnsw": {"space": "cosine"}},
    )
    colecao.modify(
        metadata={
            "versao_base": versao_base,
            "json_sha256": json_sha,
            "fonte_pdf_sha256": base.fonte_sha256,
            "modelo_embedding": settings.embedding_model,
            "escopo_anos": escopo,
            "indexado_em": datetime.now(tz=UTC).isoformat(),
        }
    )
    indexar(colecao, habs, vetores)
    insercao_s = time.perf_counter() - t0

    logger.info(
        "fase2_concluida",
        extra={
            "colecao": settings.chroma_collection,
            "documentos": colecao.count(),
            "versao_base": versao_base,
            "carga_modelo_s": round(carga_s, 3),
            "embeddings_s": round(embeddings_s, 3),
            "insercao_s": round(insercao_s, 3),
            "duracao_s": round(time.perf_counter() - t_total, 3),
        },
    )


if __name__ == "__main__":
    main()
