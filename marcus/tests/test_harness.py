"""Fase 6: harness resumível, com respostas simuladas."""

from pathlib import Path

import pytest

from educachat.generation.modelos import ConfigGeracao, Resposta
from educachat.generation.openrouter import TentativasEsgotadas
from test_suite.harness.executor import InterrompidoPorLimite, agora, carregar, executar
from test_suite.modelos import (
    COMPORTAMENTO_ESPERADO,
    Categoria,
    ConjuntoConsultas,
    ExecucaoLote,
    ItemTeste,
)


def _item(i: int) -> ItemTeste:
    return ItemTeste(
        id=f"fora-{i:02d}",
        categoria=Categoria.FORA_DE_ESCOPO,
        pergunta=f"Pergunta número {i}?",
        ano_aluno=6,
        serie="6º ano",
        componente=None,
        codigo=None,
        serie_habilidade=None,
        topico=None,
        comportamento_esperado=COMPORTAMENTO_ESPERADO[Categoria.FORA_DE_ESCOPO],
        estrategia="template",
    )


CONJUNTO = ConjuntoConsultas(
    data_geracao="x",
    versao_base="vb",
    modelo_embedding="m",
    escopo_anos="6-9",
    estrategia="template",
    seed=1,
    parametros={},
    contagem={"fora_de_escopo": 4},
    itens=[_item(i) for i in range(4)],
)


def _execucao() -> ExecucaoLote:
    return ExecucaoLote(
        iniciado_em=agora(),
        atualizado_em=agora(),
        consultas_arquivo="c.json",
        consultas_sha256="sha",
        versao_base="vb",
        modelo_llm="m",
        parametros={},
        modos=["baseline", "prototipo"],
    )


def _resposta(modo: str, pergunta: str) -> Resposta:
    return Resposta(
        texto=f"{modo}: {pergunta}",
        tempo_ms=1,
        tempo_llm_ms=1,
        tentativas_llm=1,
        config=ConfigGeracao(
            modo=modo, modelo_llm="m", temperatura=0, max_tokens=1, versao_prompt=1, ano_aluno=6
        ),
    )


class Falso:
    """Responder simulado; falha nas chamadas listadas em ``falhas`` (1-indexadas)."""

    def __init__(self, modo: str, falhas: dict[int, Exception] | None = None) -> None:
        self.modo, self.falhas, self.chamadas = modo, falhas or {}, 0

    def __call__(self, pergunta: str, ano: int) -> Resposta:
        self.chamadas += 1
        if self.chamadas in self.falhas:
            raise self.falhas[self.chamadas]
        return _resposta(self.modo, pergunta)


def test_executa_todos_os_pares_e_marca_concluido(tmp_path: Path) -> None:
    arq = tmp_path / "r.json"
    ex = executar(
        CONJUNTO, _execucao(), {"baseline": Falso("baseline"), "prototipo": Falso("prototipo")}, arq
    )
    assert ex.concluido and len(ex.resultados) == 8
    salvo = carregar(arq)
    assert salvo.concluido and salvo.chaves_ok() == ex.chaves_ok()
    assert not list(tmp_path.glob("*.tmp"))


def test_erro_de_item_nao_derruba_e_e_repetido_ao_retomar(tmp_path: Path) -> None:
    arq = tmp_path / "r.json"
    base = Falso("baseline", {2: RuntimeError("falhou")})
    ex = executar(CONJUNTO, _execucao(), {"baseline": base, "prototipo": Falso("prototipo")}, arq)
    assert not ex.concluido
    erros = [r for r in ex.resultados if not r.ok]
    assert [(r.item_id, r.modo) for r in erros] == [("fora-01", "baseline")]
    assert "RuntimeError: falhou" in (erros[0].erro or "")

    # Retomada: só o par que falhou é executado de novo.
    base2, proto2 = Falso("baseline"), Falso("prototipo")
    ex2 = executar(CONJUNTO, carregar(arq), {"baseline": base2, "prototipo": proto2}, arq)
    assert (base2.chamadas, proto2.chamadas) == (1, 0)
    assert ex2.concluido and len(ex2.resultados) == 8 and all(r.ok for r in ex2.resultados)


def test_limite_de_taxa_salva_progresso_e_interrompe(tmp_path: Path) -> None:
    arq = tmp_path / "r.json"
    base = Falso("baseline", {3: TentativasEsgotadas("429 persistente", 429)})
    proto = Falso("prototipo")
    with pytest.raises(InterrompidoPorLimite):
        executar(
            CONJUNTO, _execucao(), {"baseline": base, "prototipo": proto}, arq, checkpoint_cada=100
        )
    salvo = carregar(arq)  # salvo mesmo com checkpoint_cada alto
    assert len(salvo.chaves_ok()) == 4  # itens 0 e 1, dois modos
    assert not salvo.concluido
    assert proto.chamadas == 2  # parou na hora, não seguiu para o protótipo do item 2

    ex = executar(CONJUNTO, salvo, {"baseline": Falso("baseline"), "prototipo": proto}, arq)
    assert ex.concluido and len(ex.resultados) == 8


def test_checkpoint_periodico(tmp_path: Path) -> None:
    arq = tmp_path / "r.json"
    gravacoes: list[int] = []

    class Espiao(Falso):
        def __call__(self, pergunta: str, ano: int) -> Resposta:
            if arq.exists():
                gravacoes.append(len(carregar(arq).resultados))
            return super().__call__(pergunta, ano)

    executar(
        CONJUNTO,
        _execucao(),
        {"baseline": Espiao("baseline"), "prototipo": Espiao("prototipo")},
        arq,
        checkpoint_cada=3,
    )
    assert gravacoes[:4] == [3, 3, 3, 6]


def test_limite_de_itens_e_pausa(tmp_path: Path) -> None:
    pausas: list[float] = []
    ex = executar(
        CONJUNTO,
        _execucao(),
        {"baseline": Falso("baseline"), "prototipo": Falso("prototipo")},
        tmp_path / "r.json",
        limite_itens=2,
        pausa_s=1.5,
        dormir=pausas.append,
    )
    assert len(ex.resultados) == 4 and not ex.concluido  # execução parcial nunca é "concluída"
    assert pausas == [1.5, 1.5, 1.5]
