"""Execução em lote de baseline e protótipo sobre o conjunto de consultas (Fase 6).

Resumível: o arquivo de resultados é regravado de forma atômica a cada N chamadas.
Ao retomar, pares (item, modo) já respondidos são pulados e os que falharam são
tentados de novo. Se o OpenRouter esgotar as tentativas (ex.: limite diário do plano
gratuito), a execução salva o progresso e para, em vez de marcar todo o resto como erro.
"""

import logging
import os
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from educachat.generation.modelos import Resposta
from educachat.generation.openrouter import TentativasEsgotadas
from test_suite.modelos import ConjuntoConsultas, ExecucaoLote, Modo, ResultadoItem

logger = logging.getLogger(__name__)

Responder = Callable[[str, int], Resposta]


class InterrompidoPorLimite(RuntimeError):
    """Limite de taxa persistente; progresso salvo, retome mais tarde."""


def agora() -> str:
    return datetime.now(tz=UTC).isoformat()


def salvar(execucao: ExecucaoLote, caminho: Path) -> None:
    execucao.atualizado_em = agora()
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(execucao.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporario, caminho)  # atômico: um kill no meio não corrompe o arquivo


def carregar(caminho: Path) -> ExecucaoLote:
    return ExecucaoLote.model_validate_json(caminho.read_text(encoding="utf-8"))


def executar(
    conjunto: ConjuntoConsultas,
    execucao: ExecucaoLote,
    responders: Mapping[Modo, Responder],
    caminho: Path,
    *,
    checkpoint_cada: int = 5,
    pausa_s: float = 0.0,
    limite_itens: int | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> ExecucaoLote:
    itens = conjunto.itens[:limite_itens] if limite_itens else conjunto.itens
    feitos = execucao.chaves_ok()
    pendentes = [(i, m) for i in itens for m in execucao.modos if (i.id, m) not in feitos]
    logger.info(
        "harness_inicio",
        extra={"pendentes": len(pendentes), "ja_feitos": len(feitos), "arquivo": str(caminho)},
    )

    desde_checkpoint = 0
    for n, (item, modo) in enumerate(pendentes, 1):
        # Remove tentativa anterior com erro do mesmo par, se houver.
        execucao.resultados = [
            r for r in execucao.resultados if (r.item_id, r.modo) != (item.id, modo)
        ]
        base = {
            "item_id": item.id,
            "modo": modo,
            "categoria": item.categoria,
            "ano_aluno": item.ano_aluno,
        }
        try:
            resposta = responders[modo](item.pergunta, item.ano_aluno)
            execucao.resultados.append(
                ResultadoItem(**base, resposta=resposta, executado_em=agora())
            )
        except TentativasEsgotadas as exc:
            execucao.resultados.append(
                ResultadoItem(**base, erro=f"{type(exc).__name__}: {exc}", executado_em=agora())
            )
            salvar(execucao, caminho)
            logger.warning("harness_interrompido_limite", extra={"item_id": item.id, "modo": modo})
            raise InterrompidoPorLimite(
                f"limite de taxa persistente em {item.id}/{modo}; progresso salvo em {caminho}"
            ) from exc
        except Exception as exc:  # erro de um item não derruba o lote
            logger.exception("harness_erro_item", extra={"item_id": item.id, "modo": modo})
            execucao.resultados.append(
                ResultadoItem(**base, erro=f"{type(exc).__name__}: {exc}", executado_em=agora())
            )

        desde_checkpoint += 1
        if desde_checkpoint >= checkpoint_cada:
            salvar(execucao, caminho)
            desde_checkpoint = 0
            logger.info("harness_checkpoint", extra={"feitos": n, "total": len(pendentes)})
        if pausa_s and n < len(pendentes):
            dormir(pausa_s)

    esperados = {(i.id, m) for i in itens for m in execucao.modos}
    execucao.concluido = limite_itens is None and esperados <= execucao.chaves_ok()
    salvar(execucao, caminho)
    erros = sum(1 for r in execucao.resultados if not r.ok)
    logger.info(
        "fase6_concluida" if execucao.concluido else "harness_parcial",
        extra={"resultados": len(execucao.resultados), "erros": erros, "arquivo": str(caminho)},
    )
    return execucao
