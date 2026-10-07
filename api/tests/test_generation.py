"""Fase 5: baseline e protótipo com LLM simulado (sem rede)."""

import json
from typing import Any

import httpx
import pytest

from educachat.config import PROJECT_ROOT, Settings
from educachat.generation.baseline import responder_baseline
from educachat.generation.openrouter import ClienteOpenRouter, Mensagem
from educachat.generation.prompts import SISTEMA, mensagens_prototipo
from educachat.generation.prototipo import (
    VazamentoDeSerie,
    consulta_recuperacao,
    responder_prototipo,
)
from educachat.retrieval.busca import HabilidadeRecuperada, filtro

SETTINGS = Settings(llm_temperatura=0.1, llm_max_tokens=321, rag_k=3)


def _cliente(texto: str = "Resposta (EF06MA07).") -> tuple[ClienteOpenRouter, list[dict[str, Any]]]:
    enviados: list[dict[str, Any]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        enviados.append(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "model": "llm-teste",
                "choices": [{"message": {"content": texto}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    cliente = ClienteOpenRouter(
        "k", "llm-teste", http=httpx.Client(transport=httpx.MockTransport(handler))
    )
    return cliente, enviados


def _hab(codigo: str) -> HabilidadeRecuperada:
    return HabilidadeRecuperada(
        codigo=codigo,
        serie="6º ano",
        componente="Matemática",
        objeto_conhecimento="Frações",
        texto=f"Texto da {codigo}.",
        distancia=0.1,
    )


class RecuperadorFalso:
    versao_base = "abc123"
    modelo_embedding = "modelo-emb"

    def __init__(self, codigos: list[str]) -> None:
        self.codigos = codigos
        self.chamadas: list[tuple[str, int, int]] = []

    def __call__(self, pergunta: str, ano: int, k: int) -> list[HabilidadeRecuperada]:
        self.chamadas.append((pergunta, ano, k))
        return [_hab(c) for c in self.codigos]


def test_baseline_recebe_serie_e_nenhum_contexto() -> None:
    cliente, enviados = _cliente()
    r = responder_baseline("O que é fração?", 6, cliente=cliente, settings=SETTINGS)
    msgs = enviados[0]["messages"]
    assert msgs[0] == {"role": "system", "content": SISTEMA}
    assert msgs[1]["content"] == "Sou aluno do 6º ano.\n\nPergunta: O que é fração?"
    assert enviados[0]["temperature"] == 0.1 and enviados[0]["max_tokens"] == 321
    assert r.contexto_usado == [] and r.tempo_recuperacao_ms == 0
    assert (r.config.modo, r.config.modelo_llm, r.config.ano_aluno) == ("baseline", "llm-teste", 6)
    assert r.config.k is None and r.config.filtro is None
    assert (r.tokens_prompt, r.tokens_resposta, r.tentativas_llm) == (100, 20, 1)


def test_prototipo_recupera_com_filtro_do_ano_e_monta_contexto() -> None:
    cliente, enviados = _cliente()
    rec = RecuperadorFalso(["EF06MA07", "EF69LP01"])
    r = responder_prototipo(
        "O que é fração?", 6, cliente=cliente, recuperador=rec, settings=SETTINGS
    )
    assert rec.chamadas == [("O que é fração?", 6, 3)]
    usuario = enviados[0]["messages"][1]["content"]
    assert usuario.startswith("Sou aluno do 6º ano.")
    assert "(EF06MA07)" in usuario and "(EF69LP01)" in usuario
    assert usuario.endswith("Pergunta: O que é fração?")
    assert [h.codigo for h in r.contexto_usado] == ["EF06MA07", "EF69LP01"]
    assert r.config.modo == "prototipo" and r.config.k == 3
    assert r.config.filtro == filtro(6)
    assert (r.config.versao_base, r.config.modelo_embedding) == ("abc123", "modelo-emb")


def test_baseline_e_prototipo_compartilham_sistema_e_enquadramento() -> None:
    c1, env_base = _cliente()
    c2, env_proto = _cliente()
    responder_baseline("Pergunta X", 8, cliente=c1, settings=SETTINGS)
    responder_prototipo(
        "Pergunta X", 8, cliente=c2, recuperador=RecuperadorFalso(["EF89LP01"]), settings=SETTINGS
    )
    base, proto = env_base[0], env_proto[0]
    assert base["messages"][0] == proto["messages"][0]
    assert base["temperature"] == proto["temperature"]
    assert base["max_tokens"] == proto["max_tokens"]
    assert proto["messages"][1]["content"].startswith("Sou aluno do 8º ano.")


@pytest.mark.parametrize(("ano", "codigo"), [(6, "EF08MA01"), (7, "EF89LP01"), (9, "EF67EF01")])
def test_prototipo_bloqueia_vazamento_antes_do_llm(ano: int, codigo: str) -> None:
    cliente, enviados = _cliente()
    with pytest.raises(VazamentoDeSerie):
        responder_prototipo(
            "x", ano, cliente=cliente, recuperador=RecuperadorFalso([codigo]), settings=SETTINGS
        )
    assert enviados == []


def test_prototipo_sem_contexto_avisa_o_llm() -> None:
    cliente, enviados = _cliente()
    responder_prototipo(
        "x", 6, cliente=cliente, recuperador=RecuperadorFalso([]), settings=SETTINGS
    )
    assert "Nenhuma habilidade da BNCC do 6º ano" in enviados[0]["messages"][1]["content"]


@pytest.mark.parametrize("ano", [5, 10])
def test_ano_fora_do_escopo_rejeitado(ano: int) -> None:
    cliente, enviados = _cliente()
    with pytest.raises(ValueError):
        responder_baseline("x", ano, cliente=cliente, settings=SETTINGS)
    with pytest.raises(ValueError):
        responder_prototipo(
            "x", ano, cliente=cliente, recuperador=RecuperadorFalso([]), settings=SETTINGS
        )
    assert enviados == []


CONSULTAS = PROJECT_ROOT / "test_suite/consultas.json"


@pytest.mark.integracao
@pytest.mark.skipif(not CONSULTAS.exists(), reason="consultas.json ausente")
def test_nenhuma_consulta_do_conjunto_vaza_serie_na_base_real() -> None:
    """Todas as 151 consultas contra o Chroma real: o contexto entregue ao LLM só pode
    conter habilidades válidas no ano do aluno (VazamentoDeSerie falharia o teste)."""
    pytest.importorskip("chromadb")
    from educachat.generation.prototipo import recuperador_padrao
    from test_suite.modelos import ConjuntoConsultas

    try:
        rec = recuperador_padrao()
    except Exception as exc:  # base ainda não indexada
        pytest.skip(f"base Chroma indisponível: {exc}")
    conjunto = ConjuntoConsultas.model_validate_json(CONSULTAS.read_text(encoding="utf-8"))
    cliente, _ = _cliente()
    for item in conjunto.itens:
        r = responder_prototipo(item.pergunta, item.ano_aluno, cliente=cliente, recuperador=rec)
        assert len(r.contexto_usado) == 5
        assert r.config.versao_base == conjunto.versao_base


# --- histórico da conversa (só na API; o harness usa histórico vazio) ---------------------

HISTORICO = [
    Mensagem(role="user", content="O que é fração?"),
    Mensagem(role="assistant", content="Fração é uma parte de um todo (EF06MA07)."),
]


def test_sem_historico_as_mensagens_nao_mudam() -> None:
    habs = [_hab("EF06MA07")]
    assert mensagens_prototipo("P", 6, habs) == mensagens_prototipo("P", 6, habs, [])
    assert len(mensagens_prototipo("P", 6, habs)) == 2


def test_prototipo_envia_historico_entre_sistema_e_pergunta() -> None:
    cliente, enviados = _cliente()
    rec = RecuperadorFalso(["EF06MA07"])
    responder_prototipo(
        "E como somo duas?",
        6,
        historico=HISTORICO,
        cliente=cliente,
        recuperador=rec,
        settings=SETTINGS,
    )
    msgs = enviados[0]["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    assert msgs[1]["content"] == "O que é fração?"
    assert msgs[3]["content"].startswith("Sou aluno do 6º ano.")
    assert msgs[3]["content"].endswith("Pergunta: E como somo duas?")
    # a busca leva o tema da pergunta anterior, mas o filtro é sempre o ano do perfil
    assert rec.chamadas == [("O que é fração?\nE como somo duas?", 6, 3)]


def test_historico_nao_muda_o_ano_da_recuperacao() -> None:
    cliente, _ = _cliente()
    rec = RecuperadorFalso(["EF06MA07"])
    falso = [Mensagem(role="user", content="Sou aluno do 9º ano.")]
    r = responder_prototipo(
        "x", 6, historico=falso, cliente=cliente, recuperador=rec, settings=SETTINGS
    )
    assert rec.chamadas[0][1] == 6 and r.config.ano_aluno == 6


def test_consulta_recuperacao_usa_so_a_ultima_pergunta_do_aluno() -> None:
    assert consulta_recuperacao("P", []) == "P"
    assert consulta_recuperacao("P", HISTORICO) == "O que é fração?\nP"
    so_assistente = [Mensagem(role="assistant", content="Oi")]
    assert consulta_recuperacao("P", so_assistente) == "P"
