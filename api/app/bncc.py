"""Leitura da BNCC: um chunk por habilidade, metadata sai do código."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pymupdf

# EF06MA01, EF67LP08, EF08CI03 — o formato oficial do PDF.
CODIGO_RE = re.compile(r"EF(\d{2})([A-Z]{2})(\d{2})")

# Só o que vale a partir do 6º ano (produto do EducaChat).
ANOS_FINAIS = frozenset({"06", "07", "08", "09", "67", "69", "89"})

# Tabela do próprio PDF (página da composição do código), não inventada:
# 06=6º, 67=6º e 7º, 69=6º ao 9º, 89=8º e 9º.
BLOCO_PARA_ANOS: dict[str, tuple[int, ...]] = {
    "06": (6,),
    "07": (7,),
    "08": (8,),
    "09": (9,),
    "67": (6, 7),
    "69": (6, 7, 8, 9),
    "89": (8, 9),
}

RUIDO_LEGENDA = (
    "primeiro par de letras",
    "último par de números",
    "posição da habilidade",
    "refere-se à primeira habilidade",
)

# Cabeçalhos de página/tabela que o PDF cola depois do enunciado.
CORTES_CABECALHO = (
    "BASE NACIONAL COMUM CURRICULAR",
    "PRÁTICAS DE LINGUAGEM",
    "UNIDADES TEMÁTICAS",
    "OBJETOS DE CONHECIMENTO",
)


def _limpar_enunciado(texto: str) -> str:
    # Normaliza quebra de linha do PDF antes de cortar cabeçalho.
    texto = " ".join(texto.lstrip(") \t\r\n").split())
    for marcador in CORTES_CABECALHO:
        idx = texto.find(marcador)
        if idx != -1:
            texto = texto[:idx]
    return texto.rstrip("( ").strip()


@dataclass(frozen=True)
class Habilidade:
    codigo: str
    serie: str
    componente: str
    texto: str


def parse_codigo(codigo: str) -> tuple[str, str, str] | None:
    """Devolve (codigo, serie, componente) ou None se não for EF de anos finais."""
    match = CODIGO_RE.fullmatch(codigo)
    if match is None:
        return None
    serie, componente, _seq = match.groups()
    if serie not in ANOS_FINAIS:
        return None
    return codigo, serie, componente


def series_do_aluno(ano: int) -> list[str]:
    """Blocos da BNCC que incluem o ano do aluno. 6 → 06, 67, 69."""
    return [bloco for bloco, anos in BLOCO_PARA_ANOS.items() if ano in anos]


def _parece_habilidade(texto: str) -> bool:
    normalizado = " ".join(texto.split())
    if len(normalizado) < 40:
        return False
    baixo = normalizado.lower()
    return not any(ruido in baixo for ruido in RUIDO_LEGENDA)


def extrair_habilidades(pdf_path: Path) -> list[Habilidade]:
    if not pdf_path.is_file():
        raise FileNotFoundError(
            f"PDF da BNCC não encontrado em {pdf_path}. "
            "Coloque o arquivo oficial em api/data/bncc.pdf."
        )

    doc = pymupdf.open(pdf_path)
    try:
        paginas = [page.get_text() for page in doc]
    finally:
        doc.close()

    texto = "\n".join(paginas)
    matches = list(CODIGO_RE.finditer(texto))
    por_codigo: dict[str, str] = {}

    for i, match in enumerate(matches):
        codigo = match.group(0)
        parsed = parse_codigo(codigo)
        if parsed is None:
            continue
        inicio = match.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        enunciado = _limpar_enunciado(texto[inicio:fim])
        if not _parece_habilidade(enunciado):
            continue
        anterior = por_codigo.get(codigo)
        if anterior is None or len(enunciado) > len(anterior):
            por_codigo[codigo] = enunciado

    habilidades: list[Habilidade] = []
    for codigo, enunciado in por_codigo.items():
        parsed = parse_codigo(codigo)
        if parsed is None:
            continue
        _, serie, componente = parsed
        habilidades.append(
            Habilidade(
                codigo=codigo,
                serie=serie,
                componente=componente,
                texto=f"({codigo}) {enunciado}",
            )
        )
    habilidades.sort(key=lambda h: h.codigo)
    return habilidades


def contar_por_serie(habilidades: list[Habilidade]) -> dict[str, int]:
    contagem: dict[str, int] = defaultdict(int)
    for h in habilidades:
        contagem[h.serie] += 1
    return dict(sorted(contagem.items()))


def contar_por_componente(habilidades: list[Habilidade]) -> dict[str, int]:
    contagem: dict[str, int] = defaultdict(int)
    for h in habilidades:
        contagem[h.componente] += 1
    return dict(sorted(contagem.items()))
