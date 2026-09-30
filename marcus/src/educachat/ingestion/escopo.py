"""Seleção das habilidades que entram na base indexada (recorte do artigo)."""

from educachat.models import HabilidadeBNCC


def no_escopo(h: HabilidadeBNCC, ano_min: int, ano_max: int) -> bool:
    """Verdadeiro se o intervalo de anos da habilidade intersecta [ano_min, ano_max]."""
    return h.ano_inicial <= ano_max and h.ano_final >= ano_min


def filtrar_escopo(
    habilidades: list[HabilidadeBNCC], ano_min: int, ano_max: int
) -> list[HabilidadeBNCC]:
    return [h for h in habilidades if no_escopo(h, ano_min, ano_max)]
