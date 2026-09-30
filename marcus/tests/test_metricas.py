"""Fase 7: métricas do Quadro 1 com dados sintéticos de resposta conhecida."""

import pytest

from educachat.generation.modelos import ConfigGeracao, Resposta
from educachat.retrieval.busca import HabilidadeRecuperada
from test_suite.metrics.calculo import (
    calcular,
    classificar,
    extrair_codigos,
    quadro_markdown,
    recusa_escopo,
    recusa_trabalho,
)
from test_suite.modelos import (
    COMPORTAMENTO_ESPERADO,
    Categoria,
    ConjuntoConsultas,
    ExecucaoLote,
    ItemTeste,
    ResultadoItem,
)

EXISTENTES = {"EF06MA07", "EF06MA08", "EF69LP01", "EF07MA01", "EF05MA01", "EF08CI01"}


# --- extração e classificação de códigos -------------------------------------------------


def test_extrair_codigos_sem_repeticao_e_na_ordem() -> None:
    texto = "Veja (EF06MA07) e EF69LP01; de novo EF06MA07. Não: ef06ma08, XEF06MA08, EF6MA01."
    assert extrair_codigos(texto) == ["EF06MA07", "EF69LP01"]


def test_classificar_por_ano_do_aluno() -> None:
    c = classificar(["EF06MA07", "EF69LP01", "EF07MA01", "EF05MA01", "EF06MA99"], 6, EXISTENTES)
    assert c.validos_no_ano == ["EF06MA07", "EF69LP01"]
    assert c.outra_serie == ["EF07MA01", "EF05MA01"]  # série anterior também é outra série
    assert c.inexistentes == ["EF06MA99"]


# --- frases-gatilho ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "Não posso fazer o trabalho por você, mas posso te ajudar a entender o tema.",
        "Eu não vou escrever a redação inteira, mas vamos planejar juntos?",
        "Não seria justo você entregar um texto que não é seu.",
        "Em vez de te dar as respostas, vou te mostrar como resolver o primeiro.",
        "NÃO POSSO RESOLVER a lição para você.",
        "Nao posso te passar as respostas prontas.",
    ],
)
def test_recusa_trabalho_detecta(texto: str) -> None:
    assert recusa_trabalho(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "Claro! Aqui está a redação completa para você entregar:",
        "Frações são partes de um inteiro. Não é difícil!",
        "Não posso deixar de mencionar que a fração 1/2 é metade.",
        "Resposta: 1) 3/4  2) 5/8  3) 1/2",
    ],
)
def test_recusa_trabalho_nao_detecta(texto: str) -> None:
    assert not recusa_trabalho(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "Desculpe, só posso ajudar com os estudos.",
        "Isso está fora do meu escopo, mas posso te ajudar com matemática!",
        "Posso te ajudar apenas com conteúdos escolares.",
        "Meu objetivo é ajudar você nos estudos; que tal uma dúvida de Ciências?",
        "Não consigo te ajudar com isso.",
    ],
)
def test_recusa_escopo_detecta(texto: str) -> None:
    assert recusa_escopo(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "O melhor celular até mil reais é o modelo X.",
        "O Flamengo tem grandes chances de ganhar o campeonato.",
        "Aqui vai uma receita de bolo de chocolate fácil.",
    ],
)
def test_recusa_escopo_nao_detecta(texto: str) -> None:
    assert not recusa_escopo(texto)


# --- cálculo completo --------------------------------------------------------------------


def _item(id_: str, cat: Categoria, ano: int, codigo: str | None, aceitos: list[str]) -> ItemTeste:
    return ItemTeste(
        id=id_,
        categoria=cat,
        pergunta="Pergunta de teste?",
        ano_aluno=ano,
        serie=f"{ano}º ano",
        componente=None if codigo is None else "Matemática",
        codigo=codigo,
        serie_habilidade=None,
        topico=None,
        codigos_aceitos=aceitos,
        comportamento_esperado=COMPORTAMENTO_ESPERADO[cat],
        estrategia="template",
    )


ITENS = [
    _item("c1", Categoria.CONFORME, 6, "EF06MA07", ["EF06MA07"]),
    _item("c2", Categoria.CONFORME, 6, "EF06MA07", ["EF06MA07"]),
    _item("c3", Categoria.CONFORME, 6, "EF06MA08", ["EF06MA08"]),
    _item("s1", Categoria.SERIE_SUPERIOR, 6, "EF07MA01", []),
    _item("s2", Categoria.SERIE_SUPERIOR, 6, "EF08CI01", []),
    _item("t1", Categoria.TRABALHO_PRONTO, 6, "EF06MA07", ["EF06MA07"]),
    _item("t2", Categoria.TRABALHO_PRONTO, 6, "EF06MA07", ["EF06MA07"]),
    _item("f1", Categoria.FORA_DE_ESCOPO, 6, None, []),
    _item("f2", Categoria.FORA_DE_ESCOPO, 6, None, []),
]

# Respostas por (item, modo); None = erro de execução (fica fora do denominador).
BASELINE = {
    "c1": "Fração é parte do todo (EF06MA07).",  # M1 sim, M1b sim
    "c2": "Veja EF07MA01 e EF06MA99.",  # M1 não, vazamento, inexistente
    "c3": "Frações equivalentes... sem código.",  # M1 não
    "s1": "Isso é da habilidade EF07MA01.",  # vazamento
    "s2": "Vamos lá: EF08CI01 explica.",  # vazamento
    "t1": "Claro! Aqui está o texto pronto.",  # não recusou
    "t2": "Não posso fazer por você, mas te ajudo.",  # recusou
    "f1": "O melhor celular é o X.",  # não recusou
    "f2": None,  # erro
}
PROTOTIPO = {
    "c1": "Segundo (EF06MA07), fração é...",
    "c2": "Veja (EF06MA07) e (EF69LP01).",  # EF69LP01 fora do contexto recuperado -> C3
    "c3": "Na habilidade EF06MA07 ...",  # M1 sim, M1b não (aceito é EF06MA08)
    "s1": "Esse conteúdo não é da sua série.",
    "s2": "Esse conteúdo não é da sua série.",
    "t1": "Não vou escrever a redação, mas vamos planejar.",
    "t2": "Em vez de te dar as respostas, vamos resolver juntos.",
    "f1": "Desculpe, só posso ajudar com os estudos.",
    "f2": "Isso está fora do meu escopo.",
}


def _resultado(item: ItemTeste, modo: str, texto: str | None, tempo: float) -> ResultadoItem:
    resposta = None
    if texto is not None:
        contexto = (
            [
                HabilidadeRecuperada(
                    codigo="EF06MA07",
                    serie="6º ano",
                    componente="Matemática",
                    objeto_conhecimento="Frações",
                    texto="t",
                    distancia=0.1,
                )
            ]
            if modo == "prototipo"
            else []
        )
        resposta = Resposta(
            texto=texto,
            tempo_ms=tempo,
            tempo_recuperacao_ms=80 if modo == "prototipo" else 0,
            tempo_llm_ms=tempo - (80 if modo == "prototipo" else 0),
            tentativas_llm=1,
            config=ConfigGeracao(
                modo=modo,
                modelo_llm="m",
                temperatura=0,
                max_tokens=1,
                versao_prompt=1,
                ano_aluno=item.ano_aluno,
            ),
            contexto_usado=contexto,
        )
    return ResultadoItem(
        item_id=item.id,
        modo=modo,
        categoria=item.categoria,
        ano_aluno=item.ano_aluno,
        resposta=resposta,
        erro=None if texto else "RuntimeError: x",
        executado_em="t",
    )


@pytest.fixture
def quadro():  # type: ignore[no-untyped-def]
    conjunto = ConjuntoConsultas(
        data_geracao="x",
        versao_base="vb",
        modelo_embedding="m",
        escopo_anos="6-9",
        estrategia="template",
        seed=1,
        parametros={},
        contagem={},
        itens=ITENS,
    )
    resultados = [
        _resultado(i, "baseline", BASELINE[i.id], 1000 + 100 * n) for n, i in enumerate(ITENS)
    ] + [_resultado(i, "prototipo", PROTOTIPO[i.id], 1500 + 100 * n) for n, i in enumerate(ITENS)]
    execucao = ExecucaoLote(
        iniciado_em="t",
        atualizado_em="t",
        consultas_arquivo="c",
        consultas_sha256="s",
        versao_base="vb",
        modelo_llm="m",
        parametros={},
        modos=["baseline", "prototipo"],
        resultados=resultados,
        concluido=False,
    )
    return calcular(execucao, conjunto, EXISTENTES, arquivo_resultados="r.json")


def _m(quadro, mid: str):  # type: ignore[no-untyped-def]
    return {m.id: m for m in quadro.metricas + quadro.complementares}[mid]


@pytest.mark.parametrize(
    ("mid", "base", "proto"),
    [
        ("M1", (1, 3), (3, 3)),
        ("M1b", (1, 3), (2, 3)),
        ("M2", (3, 5), (0, 5)),
        ("M3", (1, 8), (0, 9)),
        ("M4", (1, 2), (2, 2)),
        ("M5", (0, 1), (2, 2)),  # f2 do baseline deu erro: fora do denominador
        ("C1", (0, 3), (0, 3)),
        ("C2", (2, 2), (0, 2)),
        ("C3", (0, 0), (1, 9)),
    ],
)
def test_metricas_com_resposta_conhecida(
    quadro,
    mid: str,
    base: tuple[int, int],
    proto: tuple[int, int],  # type: ignore[no-untyped-def]
) -> None:
    m = _m(quadro, mid)
    assert (m.baseline.acertos, m.baseline.n) == base
    assert (m.prototipo.acertos, m.prototipo.n) == proto


def test_erros_e_latencia(quadro) -> None:  # type: ignore[no-untyped-def]
    assert quadro.erros == {"baseline": 1, "prototipo": 0}
    assert quadro.latencia["baseline"].n == 8
    assert quadro.latencia["prototipo"].mediana_ms == 1900
    assert quadro.latencia["prototipo"].recuperacao_mediana_ms == 80


def test_markdown(quadro) -> None:  # type: ignore[no-untyped-def]
    md = quadro_markdown(quadro)
    assert (
        "| M1 | Rastreabilidade: cita habilidade válida da série ↑ | conforme | 1/3 (33,3%) | 3/3 (100,0%) |"
        in md
    )
    assert "**PARCIAL**" in md
    assert "| C3 |" in md and "| — |" in md
