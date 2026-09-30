"""Fase 4: gera test_suite/consultas.json a partir da base indexada no Chroma.

Uso:
    python -m test_suite.generator.cli                          # template fixo (padrão)
    python -m test_suite.generator.cli --estrategia openrouter  # LLM, com cache em disco
"""

import argparse
import logging
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from educachat.config import PROJECT_ROOT, get_settings
from educachat.generation.openrouter import ClienteOpenRouter
from educachat.logging_config import setup_logging
from educachat.models import HabilidadeBNCC, rotulo_serie
from educachat.retrieval.busca import abrir_colecao
from test_suite.generator.amostragem import planejar
from test_suite.generator.estrategias import (
    EstrategiaOpenRouter,
    EstrategiaPergunta,
    EstrategiaTemplate,
)
from test_suite.modelos import COMPORTAMENTO_ESPERADO, ConjuntoConsultas, ItemTeste

logger = logging.getLogger("test_suite.generator")


def habilidades_da_colecao() -> tuple[list[HabilidadeBNCC], dict[str, str]]:
    colecao = abrir_colecao()
    dados = colecao.get(include=["documents", "metadatas"])
    habs = [
        HabilidadeBNCC.from_codigo(
            codigo=str(m["codigo"]),
            texto=doc,
            objeto_conhecimento=str(m["objeto_conhecimento"]),
            pagina_pdf=int(str(m["pagina_pdf"])),
        )
        for doc, m in zip(dados["documents"] or [], dados["metadatas"] or [], strict=True)
    ]
    return habs, {k: str(v) for k, v in (colecao.metadata or {}).items()}


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estrategia", choices=["template", "openrouter"], default="template")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--conforme", type=int, default=2, help="itens por ano x componente")
    parser.add_argument("--serie-superior", type=int, default=1, help="itens por ano x componente")
    parser.add_argument("--trabalho-pronto", type=int, default=1, help="itens por ano x componente")
    parser.add_argument("--fora-de-escopo", type=int, default=20, help="total de itens")
    parser.add_argument("--modelo", default=None, help="modelo OpenRouter (padrão: .env)")
    parser.add_argument("--saida", type=Path, default=PROJECT_ROOT / "test_suite/consultas.json")
    parser.add_argument(
        "--cache-dir", type=Path, default=PROJECT_ROOT / "test_suite/cache/perguntas"
    )
    args = parser.parse_args(argv)
    setup_logging("generator", settings.log_dir, settings.log_level)
    inicio = time.perf_counter()

    habs, meta = habilidades_da_colecao()
    anos = list(range(settings.escopo_ano_min, settings.escopo_ano_max + 1))
    pedidos = planejar(
        habs,
        anos,
        n_conforme=args.conforme,
        n_serie_superior=args.serie_superior,
        n_trabalho_pronto=args.trabalho_pronto,
        n_fora_de_escopo=args.fora_de_escopo,
        seed=args.seed,
    )

    estrategia: EstrategiaPergunta
    if args.estrategia == "openrouter":
        cliente = ClienteOpenRouter.from_settings(settings)
        if args.modelo:
            cliente.modelo = args.modelo
        estrategia = EstrategiaOpenRouter(cliente, args.cache_dir)
    else:
        estrategia = EstrategiaTemplate(args.seed)

    itens = []
    for p in pedidos:
        h = p.habilidade
        itens.append(
            ItemTeste(
                id=p.id,
                categoria=p.categoria,
                pergunta=estrategia.redigir(p),
                ano_aluno=p.ano_aluno,
                serie=rotulo_serie(p.ano_aluno, p.ano_aluno),
                componente=h.componente if h else None,
                codigo=h.codigo if h else None,
                serie_habilidade=h.serie if h else None,
                topico=p.topico,
                codigos_aceitos=list(p.codigos_aceitos),
                comportamento_esperado=COMPORTAMENTO_ESPERADO[p.categoria],
                estrategia=estrategia.nome,
            )
        )

    conjunto = ConjuntoConsultas(
        data_geracao=datetime.now(tz=UTC).isoformat(),
        versao_base=meta["versao_base"],
        modelo_embedding=meta["modelo_embedding"],
        escopo_anos=meta["escopo_anos"],
        estrategia=estrategia.nome,
        seed=args.seed,
        parametros={
            "conforme_por_estrato": args.conforme,
            "serie_superior_por_estrato": args.serie_superior,
            "trabalho_pronto_por_estrato": args.trabalho_pronto,
            "fora_de_escopo_total": args.fora_de_escopo,
            "estratos": "ano_aluno x componente",
        },
        contagem=dict(sorted(Counter(i.categoria.value for i in itens).items())),
        itens=itens,
    )
    args.saida.write_text(conjunto.model_dump_json(indent=2), encoding="utf-8")
    logger.info(
        "fase4_concluida",
        extra={
            "saida": str(args.saida),
            "itens": len(itens),
            "contagem": conjunto.contagem,
            "versao_base": conjunto.versao_base,
            "estrategia": conjunto.estrategia,
            "duracao_s": round(time.perf_counter() - inicio, 3),
        },
    )


if __name__ == "__main__":
    main()
