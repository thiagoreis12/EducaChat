"""API do EducaChat (Fase 5.5).

Rodar: ``uv run uvicorn educachat.api.main:app --reload`` (ou ``educachat-api``).

Regra central de segurança: a série usada no /chat é SEMPRE lida do perfil do usuário
autenticado (tabela ``perfis``, via token). O corpo do /chat só aceita
``{pergunta, modo}``; qualquer campo extra (``ano``, ``serie``...) é rejeitado com 422.
"""

import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from educachat.config import Settings, get_settings
from educachat.generation.baseline import responder_baseline
from educachat.generation.modelos import Resposta
from educachat.generation.openrouter import ErroOpenRouter, TentativasEsgotadas
from educachat.generation.prototipo import VazamentoDeSerie, responder_prototipo
from educachat.models import rotulo_serie

from .seguranca import AutenticacaoMiddleware, UsuarioAutenticado, VerificadorJWT
from .supabase import (
    ErroAuth,
    PerfilJaExiste,
    ProvedorAuth,
    RepositorioPerfis,
    Sessao,
    SupabaseAuth,
    SupabasePerfis,
)

logger = logging.getLogger(__name__)

COOKIE_REFRESH = "educachat_refresh"
Responder = Callable[[str, int], Resposta]


@dataclass
class Servicos:
    auth: ProvedorAuth
    perfis: RepositorioPerfis
    verificador: VerificadorJWT
    responder: Responder
    responder_baseline: Responder


# ---------------------------------------------------------------------------- esquemas


class Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CadastroEntrada(Estrito):
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)
    ano: int = Field(ge=6, le=9)


class LoginEntrada(Estrito):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class PerfilEntrada(Estrito):
    ano: int = Field(ge=6, le=9)


class ChatEntrada(Estrito):
    pergunta: str = Field(min_length=1, max_length=2000)
    # O baseline nunca é exposto ao usuário final: o único modo aceito é o protótipo.
    modo: Literal["prototipo"] = "prototipo"


class Perfil(BaseModel):
    ano: int
    serie: str


class SessaoSaida(BaseModel):
    access_token: str
    expires_in: int
    usuario_id: str
    email: str | None
    perfil: Perfil | None


class CadastroSaida(BaseModel):
    confirmacao_pendente: bool
    sessao: SessaoSaida | None = None


class HabilidadeSaida(BaseModel):
    codigo: str
    serie: str
    componente: str
    objeto_conhecimento: str
    texto: str


class ChatSaida(BaseModel):
    resposta: str
    serie: str
    habilidades: list[HabilidadeSaida]
    tempo_ms: float


# ---------------------------------------------------------------------------- app


def _perfil(ano: int | None) -> Perfil | None:
    return Perfil(ano=ano, serie=rotulo_serie(ano, ano)) if ano is not None else None


def servicos_padrao(settings: Settings) -> Servicos:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_ANON_KEY são obrigatórios (veja .env.example)")
    anon = settings.supabase_anon_key.get_secret_value()
    secret = (
        settings.supabase_jwt_secret.get_secret_value() if settings.supabase_jwt_secret else None
    )
    return Servicos(
        auth=SupabaseAuth(settings.supabase_url, anon),
        perfis=SupabasePerfis(settings.supabase_url, anon),
        verificador=VerificadorJWT(settings.supabase_url, secret),
        responder=lambda p, a: responder_prototipo(p, a, settings=settings),
        responder_baseline=lambda p, a: responder_baseline(p, a, settings=settings),
    )


def criar_app(servicos: Servicos, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="EducaChat API", version="0.1.0")
    app.state.servicos = servicos

    # Ordem importa: o último middleware adicionado é o mais externo. O CORS precisa
    # envolver a autenticação para responder ao preflight (OPTIONS) e anexar os cabeçalhos
    # CORS até nas respostas 401.
    app.add_middleware(AutenticacaoMiddleware, verificador=servicos.verificador)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,  # necessário para o cookie de refresh
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def usuario(request: Request) -> UsuarioAutenticado:
        u: UsuarioAutenticado | None = getattr(request.state, "usuario", None)
        if u is None:  # não deveria acontecer: o middleware já barrou
            raise HTTPException(401, "não autenticado")
        return u

    Usuario = Annotated[UsuarioAutenticado, Depends(usuario)]  # noqa: N806

    def gravar_cookie(resposta: Response, sessao: Sessao) -> None:
        resposta.set_cookie(
            COOKIE_REFRESH,
            sessao.refresh_token,
            httponly=True,  # inacessível ao JavaScript: mitiga roubo por XSS
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            path="/auth",  # só é enviado para as rotas de auth
            max_age=60 * 60 * 24 * 30,
        )

    def saida_sessao(sessao: Sessao) -> SessaoSaida:
        ano = servicos.perfis.obter_ano(sessao.user_id, sessao.access_token)
        return SessaoSaida(
            access_token=sessao.access_token,
            expires_in=sessao.expires_in,
            usuario_id=sessao.user_id,
            email=sessao.email,
            perfil=_perfil(ano),
        )

    def erro_auth(exc: ErroAuth) -> HTTPException:
        status = exc.status if exc.status in (400, 401, 403, 409, 422, 429) else 502
        return HTTPException(status, exc.mensagem)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/auth/cadastro", status_code=201)
    def cadastro(entrada: CadastroEntrada, resposta: Response) -> CadastroSaida:
        try:
            sessao = servicos.auth.cadastrar(entrada.email, entrada.senha, entrada.ano)
        except ErroAuth as exc:
            raise erro_auth(exc) from exc
        if sessao is None:
            return CadastroSaida(confirmacao_pendente=True)
        gravar_cookie(resposta, sessao)
        return CadastroSaida(confirmacao_pendente=False, sessao=saida_sessao(sessao))

    @app.post("/auth/login")
    def login(entrada: LoginEntrada, resposta: Response) -> SessaoSaida:
        try:
            sessao = servicos.auth.entrar(entrada.email, entrada.senha)
        except ErroAuth as exc:
            raise erro_auth(exc) from exc
        gravar_cookie(resposta, sessao)
        return saida_sessao(sessao)

    @app.post("/auth/refresh")
    def refresh(request: Request, resposta: Response) -> SessaoSaida:
        token = request.cookies.get(COOKIE_REFRESH)
        if not token:
            raise HTTPException(401, "sem sessão")
        try:
            sessao = servicos.auth.renovar(token)
        except ErroAuth as exc:
            resposta.delete_cookie(COOKIE_REFRESH, path="/auth")
            raise HTTPException(401, "sessão expirada") from exc
        gravar_cookie(resposta, sessao)  # o Supabase rotaciona o refresh token
        return saida_sessao(sessao)

    @app.post("/auth/logout", status_code=204)
    def logout(request: Request) -> Response:
        cabecalho = request.headers.get("authorization", "")
        if cabecalho.lower().startswith("bearer "):
            with contextlib.suppress(ErroAuth):  # o cookie é apagado de qualquer forma
                servicos.auth.sair(cabecalho[7:])
        resposta = Response(status_code=204)
        resposta.delete_cookie(COOKIE_REFRESH, path="/auth")
        return resposta

    @app.get("/perfil")
    def obter_perfil(u: Usuario) -> Perfil:
        perfil = _perfil(servicos.perfis.obter_ano(u.id, u.token))
        if perfil is None:
            raise HTTPException(404, "perfil_incompleto")
        return perfil

    @app.post("/perfil", status_code=201)
    def criar_perfil(entrada: PerfilEntrada, u: Usuario) -> Perfil:
        # user_id vem do token, nunca do corpo. A série só pode ser definida uma vez.
        try:
            servicos.perfis.criar(u.id, entrada.ano, u.token)
        except PerfilJaExiste as exc:
            raise HTTPException(409, "perfil já existe; a série não pode ser alterada") from exc
        return Perfil(ano=entrada.ano, serie=rotulo_serie(entrada.ano, entrada.ano))

    def _responder(responder: Responder, pergunta: str, ano: int) -> Resposta:
        try:
            return responder(pergunta, ano)
        except TentativasEsgotadas as exc:
            raise HTTPException(503, "assistente ocupado, tente de novo em instantes") from exc
        except ErroOpenRouter as exc:
            logger.exception("erro_llm")
            raise HTTPException(502, "falha ao consultar o modelo de linguagem") from exc
        except VazamentoDeSerie as exc:
            logger.exception("vazamento_bloqueado")
            raise HTTPException(500, "erro interno") from exc

    def ano_do_perfil(u: UsuarioAutenticado) -> int:
        ano = servicos.perfis.obter_ano(u.id, u.token)
        if ano is None:
            raise HTTPException(409, "perfil_incompleto")
        return ano

    @app.post("/chat")
    def chat(entrada: ChatEntrada, u: Usuario) -> ChatSaida:
        ano = ano_do_perfil(u)  # ÚNICA fonte da série
        r = _responder(servicos.responder, entrada.pergunta, ano)
        return ChatSaida(
            resposta=r.texto,
            serie=rotulo_serie(ano, ano),
            habilidades=[
                HabilidadeSaida(**h.model_dump(exclude={"distancia"})) for h in r.contexto_usado
            ],
            tempo_ms=r.tempo_ms,
        )

    if settings.expor_rota_baseline:
        logger.warning("rota_baseline_exposta")

        @app.post("/interno/baseline")
        def baseline(entrada: ChatEntrada, u: Usuario) -> ChatSaida:
            ano = ano_do_perfil(u)
            r = _responder(servicos.responder_baseline, entrada.pergunta, ano)
            return ChatSaida(
                resposta=r.texto, serie=rotulo_serie(ano, ano), habilidades=[], tempo_ms=r.tempo_ms
            )

    return app


def _app_padrao() -> FastAPI:
    settings = get_settings()
    return criar_app(servicos_padrao(settings), settings)


def __getattr__(nome: str) -> FastAPI:
    # ``educachat.api.main:app`` é criado sob demanda, para que importar o módulo (ex.:
    # nos testes) não exija credenciais do Supabase.
    if nome == "app":
        return _app_padrao()
    raise AttributeError(nome)


def run() -> None:
    import uvicorn

    uvicorn.run("educachat.api.main:app", host="127.0.0.1", port=8000, reload=False)
