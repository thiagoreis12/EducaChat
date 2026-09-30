"""Cliente OpenRouter: retry/backoff testados com transporte HTTP simulado (sem rede)."""

import json
from collections.abc import Callable

import httpx
import pytest

from educachat.generation.openrouter import (
    ClienteOpenRouter,
    ErroOpenRouter,
    Mensagem,
    TentativasEsgotadas,
)

OK = {
    "model": "modelo-x",
    "choices": [{"message": {"content": "  resposta  "}}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 3},
}
MSGS = [Mensagem(role="user", content="oi")]


def _cliente(
    respostas: list[httpx.Response | Exception], esperas: list[float]
) -> tuple[ClienteOpenRouter, list[dict[str, object]]]:
    enviados: list[dict[str, object]] = []
    fila = list(respostas)

    def handler(req: httpx.Request) -> httpx.Response:
        enviados.append(json.loads(req.content))
        assert req.headers["authorization"] == "Bearer chave-teste"
        item = fila.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    http = httpx.Client(transport=httpx.MockTransport(handler))
    dormir: Callable[[float], None] = esperas.append
    cliente = ClienteOpenRouter(
        "chave-teste", "modelo-x", max_tentativas=4, backoff_base_s=1, http=http, dormir=dormir
    )
    return cliente, enviados


def test_sucesso_direto() -> None:
    esperas: list[float] = []
    cliente, enviados = _cliente([httpx.Response(200, json=OK)], esperas)
    r = cliente.completar(MSGS, temperatura=0.2, max_tokens=50)
    assert (r.texto, r.tentativas, r.tokens_prompt, r.tokens_resposta) == ("resposta", 1, 10, 3)
    assert enviados[0] == {
        "model": "modelo-x",
        "messages": [{"role": "user", "content": "oi"}],
        "temperature": 0.2,
        "max_tokens": 50,
    }
    assert esperas == []


def test_429_e_5xx_sao_repetidos_com_backoff_crescente() -> None:
    esperas: list[float] = []
    cliente, _ = _cliente(
        [httpx.Response(429), httpx.Response(503), httpx.Response(200, json=OK)], esperas
    )
    r = cliente.completar(MSGS)
    assert r.tentativas == 3
    assert len(esperas) == 2
    assert 1 <= esperas[0] <= 2 and 2 <= esperas[1] <= 3  # base*2^(n-1) + jitter [0, base]


def test_retry_after_e_respeitado() -> None:
    esperas: list[float] = []
    cliente, _ = _cliente(
        [httpx.Response(429, headers={"Retry-After": "30"}), httpx.Response(200, json=OK)],
        esperas,
    )
    cliente.completar(MSGS)
    assert esperas[0] >= 30


def test_falha_de_rede_e_repetida() -> None:
    esperas: list[float] = []
    cliente, _ = _cliente([httpx.ConnectTimeout("t"), httpx.Response(200, json=OK)], esperas)
    assert cliente.completar(MSGS).tentativas == 2


def test_erro_do_provedor_no_corpo_200() -> None:
    esperas: list[float] = []
    erro = {"error": {"code": 429, "message": "rate limited upstream"}}
    cliente, _ = _cliente([httpx.Response(200, json=erro), httpx.Response(200, json=OK)], esperas)
    assert cliente.completar(MSGS).tentativas == 2


@pytest.mark.parametrize("status", [400, 401, 402, 404])
def test_erro_definitivo_nao_e_repetido(status: int) -> None:
    esperas: list[float] = []
    cliente, enviados = _cliente([httpx.Response(status, text="nao")], esperas)
    with pytest.raises(ErroOpenRouter) as exc:
        cliente.completar(MSGS)
    assert exc.value.status == status
    assert len(enviados) == 1 and esperas == []


def test_tentativas_esgotadas() -> None:
    esperas: list[float] = []
    cliente, enviados = _cliente([httpx.Response(429)] * 4, esperas)
    with pytest.raises(TentativasEsgotadas):
        cliente.completar(MSGS)
    assert len(enviados) == 4 and len(esperas) == 3


def test_sem_chave_falha_cedo() -> None:
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        ClienteOpenRouter("", "modelo-x")
