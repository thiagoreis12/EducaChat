import pytest

from educachat.config import get_settings
from educachat.models import BaseBNCC, HabilidadeBNCC
from educachat.parsing.bncc_parser import extrair_habilidades


@pytest.fixture(scope="session")
def habilidades() -> list[HabilidadeBNCC]:
    """Usa o JSON gerado pela Fase 1 se existir; senão, roda o parser no PDF."""
    settings = get_settings()
    if settings.bncc_json_path.exists():
        base = BaseBNCC.model_validate_json(settings.bncc_json_path.read_text(encoding="utf-8"))
        return base.habilidades
    if not settings.bncc_pdf_path.exists():
        pytest.skip("PDF da BNCC ausente em data/raw/")
    return extrair_habilidades(settings.bncc_pdf_path)
