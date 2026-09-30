from educachat.config import Settings


def validar_ano(ano_aluno: int, settings: Settings) -> None:
    if not settings.escopo_ano_min <= ano_aluno <= settings.escopo_ano_max:
        raise ValueError(
            f"ano {ano_aluno} fora do escopo {settings.escopo_ano_min}º-{settings.escopo_ano_max}º"
        )
