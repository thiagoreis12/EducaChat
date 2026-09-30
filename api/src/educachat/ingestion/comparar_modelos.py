"""Compara os modelos de embedding candidatos sobre as habilidades do escopo.

Mede, por modelo: dimensão do vetor, nº de parâmetros, limite de tokens e taxa de
truncamento dos textos da BNCC, tempo de carga, tempo de codificação da base
inteira e latência de uma consulta isolada (CPU).

Qualidade de recuperação é estimada por uma tarefa *proxy*, sem rotulagem manual:
cada objeto de conhecimento (componente + texto do objeto) vira uma consulta, e são
relevantes as habilidades daquela linha da tabela. A busca é restrita ao mesmo
componente, como no protótipo. Reporta-se hit@5 e MRR@10. É um indicativo
comparativo entre modelos, não uma medida da qualidade final do sistema.

Uso: python -m educachat.ingestion.comparar_modelos [--saida arquivo.json]
"""

import argparse
import gc
import json
import logging
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from educachat.config import PROJECT_ROOT, get_settings
from educachat.ingestion.embeddings import MODELOS, carregar, codificar
from educachat.ingestion.escopo import filtrar_escopo
from educachat.logging_config import setup_logging
from educachat.models import BaseBNCC, HabilidadeBNCC

logger = logging.getLogger("educachat.ingestion.comparar")


def _consultas_proxy(habs: list[HabilidadeBNCC]) -> dict[tuple[str, str], set[int]]:
    grupos: dict[tuple[str, str], set[int]] = defaultdict(set)
    for i, h in enumerate(habs):
        grupos[(h.componente, h.objeto_conhecimento)].add(i)
    return grupos


def avaliar_modelo(nome: str, habs: list[HabilidadeBNCC]) -> dict[str, Any]:
    textos = [h.texto for h in habs]
    t0 = time.perf_counter()
    modelo = carregar(nome)
    carga_s = time.perf_counter() - t0

    tokenizer = modelo.tokenizer
    if modelo.max_seq_length is None:
        raise ValueError(f"{nome}: modelo sem max_seq_length definido")
    limite = int(modelo.max_seq_length)
    prefixo = MODELOS[nome].prefixo_documento
    n_tokens = [len(tokenizer(prefixo + t)["input_ids"]) for t in textos]
    truncados = sum(n > limite for n in n_tokens)

    t0 = time.perf_counter()
    docs = codificar(nome, textos, "documento")
    codificacao_s = time.perf_counter() - t0

    latencias = []
    for consulta in ["fração", "revolução industrial", "gêneros textuais argumentativos"] * 7:
        t0 = time.perf_counter()
        codificar(nome, [consulta], "consulta")
        latencias.append((time.perf_counter() - t0) * 1000)

    grupos = _consultas_proxy(habs)
    chaves = list(grupos)
    consultas = codificar(nome, [objeto for _comp, objeto in chaves], "consulta")
    componentes = np.array([h.componente for h in habs])
    hits, rr = [], []
    for (comp, _obj), q in zip(chaves, consultas, strict=True):
        scores = docs @ q
        scores[componentes != comp] = -np.inf
        ranking = np.argsort(-scores)[:10]
        relevantes = grupos[(comp, _obj)]
        hits.append(any(int(i) in relevantes for i in ranking[:5]))
        pos = next((k for k, i in enumerate(ranking, 1) if int(i) in relevantes), None)
        rr.append(1 / pos if pos else 0.0)

    resultado = {
        "modelo": nome,
        "hf_id": MODELOS[nome].hf_id,
        "dimensao": int(docs.shape[1]),
        "parametros_milhoes": round(sum(p.numel() for p in modelo.parameters()) / 1e6, 1),
        "max_tokens": limite,
        "tokens_mediana": int(statistics.median(n_tokens)),
        "tokens_max": max(n_tokens),
        "textos_truncados": truncados,
        "textos_truncados_pct": round(100 * truncados / len(textos), 1),
        "carga_s": round(carga_s, 2),
        "codificacao_base_s": round(codificacao_s, 2),
        "ms_por_documento": round(1000 * codificacao_s / len(textos), 2),
        "latencia_consulta_ms_mediana": round(statistics.median(latencias), 1),
        "bytes_por_vetor_float32": int(docs.shape[1]) * 4,
        "proxy_consultas": len(chaves),
        "proxy_hit_at_5": round(float(np.mean(hits)), 3),
        "proxy_mrr_at_10": round(float(np.mean(rr)), 3),
    }
    logger.info("modelo_avaliado", extra=resultado)
    return resultado


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--saida", type=Path, default=PROJECT_ROOT / "data/processed/comparacao_embeddings.json"
    )
    parser.add_argument("--modelos", nargs="*", default=list(MODELOS))
    args = parser.parse_args(argv)
    setup_logging("comparar_modelos", settings.log_dir, settings.log_level)

    base = BaseBNCC.model_validate_json(settings.bncc_json_path.read_text(encoding="utf-8"))
    habs = filtrar_escopo(base.habilidades, settings.escopo_ano_min, settings.escopo_ano_max)
    logger.info("escopo", extra={"habilidades": len(habs)})

    resultados = []
    for nome in args.modelos:
        resultados.append(avaliar_modelo(nome, habs))
        carregar.cache_clear()
        gc.collect()

    saida = {
        "escopo_anos": [settings.escopo_ano_min, settings.escopo_ano_max],
        "habilidades": len(habs),
        "hardware": "CPU",
        "resultados": resultados,
    }
    args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
