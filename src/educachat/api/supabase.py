"""Integração com o Supabase: Auth (GoTrue) e tabela ``perfis`` (PostgREST).

Cadastro, login e refresh são delegados ao Supabase Auth: a API nunca vê nem guarda
hash de senha. O acesso a ``perfis`` usa o token do próprio usuário, então as policies
de RLS valem também para a API (defesa em profundidade: nem um bug na API permite ler
o perfil de outro aluno).
"""

from typing import Any, Protocol

import httpx
from pydantic import BaseModel


class ErroAuth(Exception):
    def __init__(self, status: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


class PerfilJaExiste(Exception):
    pass


class ErroPerfis(Exception):
    """Falha ao acessar ``perfis`` (tabela ausente, Supabase fora do ar, timeout...).

    Diferente de "perfil não existe", que é ``obter_ano`` devolvendo ``None``.
    """


class Sessao(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str
    email: str | None = None


class ProvedorAuth(Protocol):
    def cadastrar(self, email: str, senha: str, ano: int) -> Sessao | None: ...
    def entrar(self, email: str, senha: str) -> Sessao: ...
    def renovar(self, refresh_token: str) -> Sessao: ...
    def sair(self, access_token: str) -> None: ...


class RepositorioPerfis(Protocol):
    def obter_ano(self, user_id: str, token: str) -> int | None: ...
    def criar(self, user_id: str, ano: int, token: str) -> None: ...


def _mensagem(resposta: httpx.Response) -> str:
    try:
        dados = resposta.json()
    except ValueError:
        return resposta.text[:200]
    for chave in ("msg", "error_description", "message", "error"):
        if isinstance(dados, dict) and dados.get(chave):
            return str(dados[chave])
    return resposta.text[:200]


class SupabaseAuth:
    def __init__(self, url: str, anon_key: str, http: httpx.Client | None = None) -> None:
        self.base = url.rstrip("/") + "/auth/v1"
        self.anon_key = anon_key
        self.http = http or httpx.Client(timeout=15)

    def _headers(self, token: str | None = None) -> dict[str, str]:
        # As chaves novas do Supabase (sb_publishable_...) não são JWT e não podem ir em
        # Authorization; o cabeçalho apikey basta e também funciona com a anon key legada.
        cabecalhos = {"apikey": self.anon_key}
        if token:
            cabecalhos["Authorization"] = f"Bearer {token}"
        return cabecalhos

    def _sessao(self, dados: dict[str, Any]) -> Sessao:
        usuario = dados.get("user") or {}
        return Sessao(
            access_token=dados["access_token"],
            refresh_token=dados["refresh_token"],
            expires_in=int(dados.get("expires_in", 3600)),
            user_id=str(usuario.get("id", "")),
            email=usuario.get("email"),
        )

    def _post(self, caminho: str, corpo: dict[str, Any], token: str | None = None) -> Any:
        r = self.http.post(self.base + caminho, json=corpo, headers=self._headers(token))
        if r.status_code >= 400:
            raise ErroAuth(r.status_code, _mensagem(r))
        return r.json() if r.content else None

    def cadastrar(self, email: str, senha: str, ano: int) -> Sessao | None:
        # A série vai em user_metadata; o trigger do banco cria o perfil (0001_perfis.sql).
        dados = self._post("/signup", {"email": email, "password": senha, "data": {"ano": ano}})
        # Com confirmação de e-mail ativa, o Supabase não devolve sessão no cadastro.
        return self._sessao(dados) if dados and dados.get("access_token") else None

    def entrar(self, email: str, senha: str) -> Sessao:
        return self._sessao(
            self._post("/token?grant_type=password", {"email": email, "password": senha})
        )

    def renovar(self, refresh_token: str) -> Sessao:
        return self._sessao(
            self._post("/token?grant_type=refresh_token", {"refresh_token": refresh_token})
        )

    def sair(self, access_token: str) -> None:
        self._post("/logout", {}, token=access_token)


class SupabasePerfis:
    def __init__(self, url: str, anon_key: str, http: httpx.Client | None = None) -> None:
        self.base = url.rstrip("/") + "/rest/v1/perfis"
        self.anon_key = anon_key
        self.http = http or httpx.Client(timeout=15)

    def _headers(self, token: str) -> dict[str, str]:
        return {"apikey": self.anon_key, "Authorization": f"Bearer {token}"}

    def obter_ano(self, user_id: str, token: str) -> int | None:
        try:
            r = self.http.get(
                self.base,
                params={"user_id": f"eq.{user_id}", "select": "ano"},
                headers=self._headers(token),
            )
            r.raise_for_status()
            linhas = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ErroPerfis(str(exc)) from exc
        return int(linhas[0]["ano"]) if linhas else None

    def criar(self, user_id: str, ano: int, token: str) -> None:
        try:
            r = self.http.post(
                self.base,
                json={"user_id": user_id, "ano": ano},
                headers={**self._headers(token), "Prefer": "return=minimal"},
            )
        except httpx.HTTPError as exc:
            raise ErroPerfis(str(exc)) from exc
        if r.status_code == 409:
            raise PerfilJaExiste(user_id)
        if r.is_error:
            raise ErroPerfis(f"HTTP {r.status_code}: {_mensagem(r)}")
