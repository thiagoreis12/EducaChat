"""Modelos de dados compartilhados entre as fases do pipeline."""

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CODIGO_REGEX = re.compile(r"^EF\d{2}[A-Z]{2}\d{2}$")

COMPONENTES: dict[str, str] = {
    "LP": "Língua Portuguesa",
    "AR": "Arte",
    "EF": "Educação Física",
    "LI": "Língua Inglesa",
    "MA": "Matemática",
    "CI": "Ciências",
    "GE": "Geografia",
    "HI": "História",
    "ER": "Ensino Religioso",
}


def anos_do_codigo(codigo: str) -> tuple[int, int]:
    """Extrai o intervalo de anos do código BNCC.

    ``EF06MA01`` -> (6, 6); ``EF69LP01`` -> (6, 9); ``EF15AR01`` -> (1, 5).
    Códigos com dois dígitos distintos designam habilidades comuns a um bloco de anos.
    """
    d1, d2 = int(codigo[2]), int(codigo[3])
    if d1 == 0:
        return d2, d2
    return d1, d2


def rotulo_serie(ano_inicial: int, ano_final: int) -> str:
    if ano_inicial == ano_final:
        return f"{ano_inicial}º ano"
    return f"{ano_inicial}º ao {ano_final}º ano"


class HabilidadeBNCC(BaseModel):
    """Uma habilidade do Ensino Fundamental extraída da BNCC.

    ``serie`` é o rótulo legível ("6º ano" ou "6º ao 9º ano"). Para filtragem use
    ``ano_inicial``/``ano_final``: uma habilidade EF69LP.. vale para o 6º ano, mas
    ``serie == "6º ano"`` não a encontraria.
    """

    model_config = ConfigDict(frozen=True)

    codigo: str
    serie: str
    ano_inicial: int = Field(ge=1, le=9)
    ano_final: int = Field(ge=1, le=9)
    componente: str
    objeto_conhecimento: str = Field(min_length=1)
    texto: str = Field(min_length=10)
    pagina_pdf: int = Field(ge=1, description="Página (numeração do leitor de PDF) da habilidade")

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str) -> str:
        if not CODIGO_REGEX.match(v):
            raise ValueError(f"código fora do padrão EF\\d{{2}}[A-Z]{{2}}\\d{{2}}: {v!r}")
        if v[4:6] not in COMPONENTES:
            raise ValueError(f"sigla de componente desconhecida em {v!r}")
        return v

    @model_validator(mode="after")
    def _consistencia(self) -> Self:
        ini, fim = anos_do_codigo(self.codigo)
        if (self.ano_inicial, self.ano_final) != (ini, fim):
            raise ValueError(f"{self.codigo}: anos {self.ano_inicial}-{self.ano_final} != código")
        if self.serie != rotulo_serie(ini, fim):
            raise ValueError(f"{self.codigo}: série {self.serie!r} inconsistente com o código")
        if self.componente != COMPONENTES[self.codigo[4:6]]:
            raise ValueError(f"{self.codigo}: componente {self.componente!r} inconsistente")
        return self

    @property
    def anos(self) -> list[int]:
        return list(range(self.ano_inicial, self.ano_final + 1))

    @classmethod
    def from_codigo(
        cls, codigo: str, texto: str, objeto_conhecimento: str, pagina_pdf: int
    ) -> "HabilidadeBNCC":
        ini, fim = anos_do_codigo(codigo)
        return cls(
            codigo=codigo,
            serie=rotulo_serie(ini, fim),
            ano_inicial=ini,
            ano_final=fim,
            componente=COMPONENTES.get(codigo[4:6], codigo[4:6]),
            objeto_conhecimento=objeto_conhecimento,
            texto=texto,
            pagina_pdf=pagina_pdf,
        )


class BaseBNCC(BaseModel):
    """Arquivo data/processed/bncc_estruturada.json."""

    fonte_pdf: str
    fonte_sha256: str
    gerado_em: str
    total: int
    habilidades: list[HabilidadeBNCC]
