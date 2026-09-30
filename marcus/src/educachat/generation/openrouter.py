"""Cliente mínimo da API de chat do OpenRouter, com retry e backoff exponencial.

No plano gratuito o OpenRouter devolve 429 com frequência (limite por minuto e por
dia). Execuções longas (gerador da Fase 4, harness da Fase 6) não podem morrer no
primeiro 429, então erros transitórios (429, 408, 5xx, timeout, falha de rede) são
repetidos com backoff exponencial + jitter, respeitando ``Retry-After`` quando
presente. Erros definitivos (400, 401, 402, 404...) sobem na hora.
"""

import logging
import random
import time
from collections.abc import Callable, Sequence
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from educachat.config import Settings, get_settings

logger = logging.getLogger(__name__)

URL_CHAT = "https://openrouter.ai/api/v1/chat/completions"
STATUS_TRANSITORIOS = frozenset({408, 429, 500, 502, 503, 504})


class Mensagem(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class RespostaLLM(BaseModel):
    texto: str
    modelo: str
    tempo_ms: float
    tentativas: int
    tokens_prompt: int | None = None
    tokens_resposta: int | None = None


class ErroOpenRouter(RuntimeError):
    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status


class TentativasEsgotadas(ErroOpenRouter):
    """Erro transitório persistiu após todas as tentativas (ex.: limite diário)."""


class _Transitorio(Exception):
    def __init__(self, motivo: str, status: int | None, retry_after: float | None) -> None:
        super().__init__(motivo)
        self.status = status
        self.retry_after = retry_after


def _retry_after(resposta: httpx.Response) -> float | None:
    valor = resposta.headers.get("retry-after")
    try:
        return float(valor) if valor is not None else None
    except ValueError:
        return None


class ClienteOpenRouter:
    def __init__(
        self,
        api_key: str,
        modelo: str,
        *,
        max_tentativas: int = 6,
        backoff_base_s: float = 2.0,
        backoff_max_s: float = 90.0,
        timeout_s: float = 90.0,
        http: httpx.Client | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY não configurada (veja .env.example)")
        self.modelo = modelo
        self.max_tentativas = max_tentativas
        self.backoff_base_s = backoff_base_s
        self.backoff_max_s = backoff_max_s
        self._dormir = dormir
        self._http = http or httpx.Client(timeout=timeout_s)
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "EducaChat",
        }

    @classmethod
    def from_settings(cls, settings: Settings | None = None, **kwargs: Any) -> "ClienteOpenRouter":
        settings = settings or get_settings()
        chave = (
            settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ""
        )
        return cls(chave, settings.openrouter_model, **kwargs)

    def _espera(self, tentativa: int, retry_after: float | None) -> float:
        exponencial = self.backoff_base_s * float(2 ** (tentativa - 1))
        espera = min(self.backoff_max_s, exponencial) + random.uniform(0, self.backoff_base_s)
        if retry_after is not None:
            espera = max(espera, min(retry_after, self.backoff_max_s))
        return espera

    def _uma_chamada(self, corpo: dict[str, Any]) -> dict[str, Any]:
        try:
            resposta = self._http.post(URL_CHAT, headers=self._headers, json=corpo)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _Transitorio(f"falha de rede: {exc!r}", None, None) from exc

        if resposta.status_code in STATUS_TRANSITORIOS:
            raise _Transitorio(
                f"HTTP {resposta.status_code}: {resposta.text[:200]}",
                resposta.status_code,
                _retry_after(resposta),
            )
        if resposta.status_code >= 400:
            raise ErroOpenRouter(
                f"HTTP {resposta.status_code}: {resposta.text[:500]}", resposta.status_code
            )

        dados: dict[str, Any] = resposta.json()
        # O OpenRouter às vezes devolve 200 com erro do provedor no corpo.
        if "error" in dados:
            erro = dados["error"] or {}
            codigo = erro.get("code")
            status = codigo if isinstance(codigo, int) else None
            if status is None or status in STATUS_TRANSITORIOS:
                raise _Transitorio(f"erro do provedor: {erro}", status, None)
            raise ErroOpenRouter(f"erro do provedor: {erro}", status)
        if not dados.get("choices"):
            raise _Transitorio("resposta sem choices", None, None)
        return dados

    def completar(
        self,
        mensagens: Sequence[Mensagem],
        *,
        temperatura: float = 0.7,
        max_tokens: int | None = None,
        modelo: str | None = None,
    ) -> RespostaLLM:
        corpo: dict[str, Any] = {
            "model": modelo or self.modelo,
            "messages": [m.model_dump() for m in mensagens],
            "temperature": temperatura,
        }
        if max_tokens is not None:
            corpo["max_tokens"] = max_tokens

        inicio = time.perf_counter()
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                dados = self._uma_chamada(corpo)
            except _Transitorio as exc:
                if tentativa == self.max_tentativas:
                    raise TentativasEsgotadas(
                        f"{self.max_tentativas} tentativas esgotadas; último erro: {exc}",
                        exc.status,
                    ) from exc
                espera = self._espera(tentativa, exc.retry_after)
                logger.warning(
                    "openrouter_retry",
                    extra={
                        "tentativa": tentativa,
                        "status": exc.status,
                        "espera_s": round(espera, 1),
                        "motivo": str(exc)[:200],
                    },
                )
                self._dormir(espera)
                continue

            uso = dados.get("usage") or {}
            return RespostaLLM(
                texto=(dados["choices"][0]["message"].get("content") or "").strip(),
                modelo=str(dados.get("model", corpo["model"])),
                tempo_ms=round((time.perf_counter() - inicio) * 1000, 1),
                tentativas=tentativa,
                tokens_prompt=uso.get("prompt_tokens"),
                tokens_resposta=uso.get("completion_tokens"),
            )
        raise AssertionError("inalcançável")
