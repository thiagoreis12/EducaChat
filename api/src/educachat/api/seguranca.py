"""Validação do JWT do Supabase e middleware de autenticação (nega por padrão)."""

import logging
from collections.abc import Awaitable, Callable

import jwt
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

AUDIENCIA = "authenticated"


class UsuarioAutenticado(BaseModel):
    id: str
    email: str | None = None
    token: str


class TokenInvalido(Exception):
    pass


class VerificadorJWT:
    """Aceita HS256 (JWT secret do projeto) ou chaves assimétricas via JWKS."""

    def __init__(self, supabase_url: str, jwt_secret: str | None = None) -> None:
        self.emissor = supabase_url.rstrip("/") + "/auth/v1"
        self.secret = jwt_secret
        self._jwks = (
            None if jwt_secret else jwt.PyJWKClient(self.emissor + "/.well-known/jwks.json")
        )

    def verificar(self, token: str) -> UsuarioAutenticado:
        try:
            if self.secret:
                chave: object = self.secret
                algoritmos = ["HS256"]
            else:
                assert self._jwks is not None
                chave = self._jwks.get_signing_key_from_jwt(token).key
                algoritmos = ["ES256", "RS256"]
            dados = jwt.decode(
                token,
                chave,  # type: ignore[arg-type]
                algorithms=algoritmos,
                audience=AUDIENCIA,
                issuer=self.emissor,
                options={"require": ["exp", "sub", "aud", "iss"]},
                leeway=10,
            )
        except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
            raise TokenInvalido(str(exc)) from exc
        if dados.get("role") != "authenticated":
            raise TokenInvalido("papel do token não é 'authenticated'")
        return UsuarioAutenticado(id=str(dados["sub"]), email=dados.get("email"), token=token)


ROTAS_PUBLICAS = frozenset(
    {
        "/health",
        "/auth/cadastro",
        "/auth/login",
        "/auth/refresh",
        "/auth/logout",
        "/docs",
        "/openapi.json",
    }
)


class AutenticacaoMiddleware(BaseHTTPMiddleware):
    """Exige Bearer válido em TODA rota fora de ``ROTAS_PUBLICAS``, inclusive rotas que
    ainda não existem: uma rota nova nasce protegida."""

    def __init__(
        self, app: ASGIApp, verificador: VerificadorJWT, publicas: frozenset[str] = ROTAS_PUBLICAS
    ) -> None:
        super().__init__(app)
        self.verificador = verificador
        self.publicas = publicas

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "OPTIONS" or request.url.path in self.publicas:
            return await call_next(request)
        cabecalho = request.headers.get("authorization", "")
        esquema, _, token = cabecalho.partition(" ")
        if esquema.lower() != "bearer" or not token:
            return _nao_autorizado("token ausente")
        try:
            request.state.usuario = self.verificador.verificar(token)
        except TokenInvalido as exc:
            logger.info("token_invalido", extra={"motivo": str(exc), "rota": request.url.path})
            return _nao_autorizado("token inválido ou expirado")
        return await call_next(request)


def _nao_autorizado(detalhe: str) -> JSONResponse:
    return JSONResponse(
        {"detail": detalhe}, status_code=401, headers={"WWW-Authenticate": "Bearer"}
    )
