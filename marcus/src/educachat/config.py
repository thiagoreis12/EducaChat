"""Configuração central lida de variáveis de ambiente / arquivo .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    bncc_pdf_path: Path = PROJECT_ROOT / "data/raw/BNCC_EI_EF_110518_versaofinal_site.pdf"
    bncc_json_path: Path = PROJECT_ROOT / "data/processed/bncc_estruturada.json"
    chroma_dir: Path = PROJECT_ROOT / "data/chroma"
    log_dir: Path = PROJECT_ROOT / "logs"
    log_level: str = "INFO"

    # Recorte do artigo: Ensino Fundamental II. Habilidades cujo intervalo de anos
    # intersecta [ano_min, ano_max] entram na base indexada.
    escopo_ano_min: int = 6
    escopo_ano_max: int = 9
    embedding_model: str = "multilingual-e5-base"  # justificativa: README, Fase 2
    chroma_collection: str = "bncc_habilidades"

    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Geração (Fase 5). Mesmos parâmetros para baseline e protótipo.
    llm_temperatura: float = 0.3
    llm_max_tokens: int = 800
    rag_k: int = 5

    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    # Tokens do Supabase Auth: HS256 com o JWT secret (projetos legados) ou, se o secret
    # não for informado, chaves assimétricas publicadas no JWKS do projeto.
    supabase_jwt_secret: SecretStr | None = None

    # API (Fase 5.5)
    cors_origins: list[str] = ["http://localhost:5173"]
    cookie_secure: bool = False  # True em produção (HTTPS)
    cookie_samesite: Literal["lax", "strict", "none"] = "strict"
    expor_rota_baseline: bool = False  # só para testes internos; nunca em produção


@lru_cache
def get_settings() -> Settings:
    return Settings()
