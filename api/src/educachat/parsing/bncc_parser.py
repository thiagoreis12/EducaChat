"""Extração das habilidades do Ensino Fundamental do PDF da BNCC.

Layout do PDF (versão "site", 600 páginas): cada tabela de habilidades ocupa um
par de páginas espelhadas.

* página da esquerda: colunas "UNIDADES TEMÁTICAS" (ou "PRÁTICAS DE LINGUAGEM")
  e "OBJETOS DE CONHECIMENTO";
* página da direita: coluna "HABILIDADES", com cada habilidade iniciada por
  ``(EFxxYYnn)``.

As linhas da tabela são traços horizontais desenhados nas mesmas coordenadas y
nas duas páginas. A habilidade é associada ao objeto de conhecimento da faixa
(entre dois traços) da página da esquerda que contém o topo da habilidade.
Quando a faixa não tem texto na coluna de objetos (célula mesclada que continua
da página anterior), reaproveita-se o último objeto visto e isso é logado.
"""

import logging
import re
from bisect import bisect_right
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from pydantic import ValidationError

from educachat.models import HabilidadeBNCC

logger = logging.getLogger(__name__)

# Código no início de uma linha: marca o começo de uma habilidade.
INICIO_HABILIDADE = re.compile(r"(?m)^\s*\((EF\d{2}[A-Z]{2}\d{2})\)\s*")
# Qualquer menção parecida com código (inclusive malformada), para auditoria.
CODIGO_SOLTO = re.compile(r"\(\s*(EF\s*\d{2}\s*[A-Z]{2}\s*\d{2})\s*\)")
ROTULO_ANOS = re.compile(r"^(\s*\d+º\s+ANOS?\s*)+$", re.IGNORECASE)
CABECALHO_OBJETOS = "OBJETOS DE CONHECIMENTO"

RODAPE_Y = 795.0  # abaixo disso: número de página
TOLERANCIA_Y = 2.0


@dataclass
class _Bloco:
    x0: float
    y0: float
    x1: float
    y1: float
    texto: str


@dataclass
class _HabilidadeBruta:
    codigo: str
    partes: list[str]
    x0: float
    x1: float
    y0: float
    pagina: int  # índice 0-based da página das habilidades
    objeto: str = ""
    avisos: list[str] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return normalizar(" ".join(self.partes))


def normalizar(texto: str) -> str:
    texto = texto.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    return re.sub(r"\s+", " ", texto).strip()


def _blocos(page: pymupdf.Page) -> list[_Bloco]:
    out = []
    for x0, y0, x1, y1, texto, _n, tipo in page.get_text("blocks"):
        if tipo != 0 or not texto.strip() or y0 >= RODAPE_Y:
            continue
        out.append(_Bloco(x0, y0, x1, y1, texto))
    return sorted(out, key=lambda b: (round(b.y0), b.x0))


def _linhas_horizontais(page: pymupdf.Page, x_min: float, x_max: float) -> list[float]:
    """Coordenadas y das divisões de linha da tabela que cruzam o intervalo [x_min, x_max].

    Duas fontes: traços horizontais finos e as bordas superior/inferior de retângulos
    preenchidos (as faixas cinzas de "CAMPO ..." no LP separam linhas sem traço).
    """
    candidatos: list[float] = []
    for desenho in page.get_drawings():
        r = desenho["rect"]
        if r.width < 20 or r.x1 < x_min or r.x0 > x_max:
            continue
        if r.height <= TOLERANCIA_Y:
            candidatos.append((r.y0 + r.y1) / 2)
        elif desenho.get("fill") is not None:
            candidatos.extend((r.y0, r.y1))
    ys: list[float] = []
    for y in sorted(candidatos):
        if not ys or y - ys[-1] > TOLERANCIA_Y:
            ys.append(y)
    return ys


def _cabecalho(page: pymupdf.Page, rotulo: str) -> pymupdf.Rect | None:
    """Retângulo do cabeçalho de coluna ``rotulo`` (maiúsculas, primeira ocorrência).

    ``search_for`` ignora caixa, então "habilidades" no corpo do texto também casaria;
    por isso conferimos o texto exato dentro do retângulo.
    """
    achados = [r for r in page.search_for(rotulo) if page.get_textbox(r).strip() == rotulo]
    return min(achados, key=lambda r: r.y0) if achados else None


def _eh_pagina_de_habilidades(doc: pymupdf.Document, idx: int) -> bool:
    if idx == 0:
        return False
    if not INICIO_HABILIDADE.search(doc[idx].get_text()):
        return False
    return CABECALHO_OBJETOS in doc[idx - 1].get_text()


class _ColunaObjetos:
    """Coluna "OBJETOS DE CONHECIMENTO" da página da esquerda, fatiada por faixas."""

    def __init__(self, page: pymupdf.Page) -> None:
        cab = _cabecalho(page, CABECALHO_OBJETOS)
        if cab is None:
            raise ValueError(f"página {page.number + 1}: cabeçalho de objetos não encontrado")
        self.x0 = cab.x0 - 3
        self.y_topo = cab.y1
        self.cortes = [
            y for y in _linhas_horizontais(page, self.x0, page.rect.width) if y > self.y_topo
        ]
        # (y_centro, bloco, texto) de cada linha de texto que começa dentro da coluna.
        # Linhas que começam à esquerda (unidade temática, ou parágrafos introdutórios
        # que atravessam a página inteira no LP 6º-9º) são ignoradas por completo.
        self._linhas: list[tuple[float, int, str]] = []
        agrupado: dict[tuple[int, int], list[tuple[float, float, str]]] = {}
        for x0, y0, _x1, y1, palavra, bloco, linha, _w in page.get_text("words"):
            if y0 < self.y_topo or y0 >= RODAPE_Y:
                continue
            agrupado.setdefault((bloco, linha), []).append((x0, (y0 + y1) / 2, palavra))
        for (bloco, _linha), palavras in sorted(
            agrupado.items(), key=lambda kv: (min(p[1] for p in kv[1]), kv[0])
        ):
            if min(p[0] for p in palavras) < self.x0:
                continue
            palavras.sort()
            yc = sum(p[1] for p in palavras) / len(palavras)
            self._linhas.append((yc, bloco, " ".join(p[2] for p in palavras)))

    def faixa(self, y: float) -> tuple[float, float]:
        i = bisect_right(self.cortes, y + TOLERANCIA_Y)
        inicio = self.cortes[i - 1] if i > 0 else self.y_topo
        fim = self.cortes[i] if i < len(self.cortes) else RODAPE_Y
        return inicio, fim

    def texto_na_faixa(self, y: float) -> str:
        inicio, fim = self.faixa(y)
        partes: list[str] = []
        bloco_atual: int | None = None
        for yc, bloco, texto in self._linhas:
            if not (inicio <= yc < fim):
                continue
            # blocos diferentes dentro da mesma célula = objetos distintos
            sep = " " if bloco == bloco_atual or bloco_atual is None else "; "
            partes.append((sep if partes else "") + texto)
            bloco_atual = bloco
        # Marcadores "•" (História) também separam objetos distintos.
        texto = re.sub(r"\s*•\s*", "; ", "".join(partes))
        texto = re.sub(r"(;\s*)+", "; ", texto)
        return normalizar(texto).strip("; ")


def _extrair_pagina(doc: pymupdf.Document, idx: int) -> Iterator[tuple[_Bloco, str | None, str]]:
    """Itera (bloco, código|None, trecho) na página de habilidades ``idx``."""
    page = doc[idx]
    cab = _cabecalho(page, "HABILIDADES")
    y_min = cab.y1 if cab is not None else 100.0
    for bloco in _blocos(page):
        if bloco.y0 < y_min - TOLERANCIA_Y:
            continue
        texto = bloco.texto
        if texto.strip().upper() == "HABILIDADES" or ROTULO_ANOS.match(texto.strip()):
            continue
        matches = list(INICIO_HABILIDADE.finditer(texto))
        if not matches:
            yield bloco, None, texto
            continue
        prefixo = texto[: matches[0].start()]
        if prefixo.strip():
            yield bloco, None, prefixo
        for i, m in enumerate(matches):
            fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
            yield bloco, m.group(1), texto[m.end() : fim]


def extrair_habilidades(pdf_path: Path) -> list[HabilidadeBNCC]:
    """Extrai e valida todas as habilidades EF do PDF da BNCC."""
    doc = pymupdf.open(pdf_path)
    paginas = [i for i in range(doc.page_count) if _eh_pagina_de_habilidades(doc, i)]
    logger.info("paginas_de_habilidades", extra={"total": len(paginas), "pdf": pdf_path.name})

    brutas: list[_HabilidadeBruta] = []
    descartes = 0
    ultimo_objeto = ""
    for idx in paginas:
        coluna = _ColunaObjetos(doc[idx - 1])
        da_pagina: list[_HabilidadeBruta] = []
        for bloco, codigo, trecho in _extrair_pagina(doc, idx):
            if codigo is not None:
                hab = _HabilidadeBruta(codigo, [trecho], bloco.x0, bloco.x1, bloco.y0, idx)
                objeto = coluna.texto_na_faixa(bloco.y0)
                if not objeto:
                    objeto = ultimo_objeto
                    hab.avisos.append("objeto_herdado_da_faixa_anterior")
                ultimo_objeto = objeto
                hab.objeto = objeto
                da_pagina.append(hab)
                brutas.append(hab)
                continue
            # Texto sem código: continuação da habilidade imediatamente acima na mesma coluna.
            dono = _dono_da_continuacao(da_pagina, bloco)
            if dono is None and not da_pagina and brutas and not _terminada(brutas[-1].texto):
                dono = brutas[-1]  # habilidade que quebrou na virada de página
                dono.avisos.append("continuacao_na_pagina_seguinte")
            if dono is None:
                descartes += 1
                logger.warning(
                    "bloco_descartado",
                    extra={"pagina_pdf": idx + 1, "y0": round(bloco.y0), "texto": trecho[:120]},
                )
                continue
            dono.partes.append(trecho)

    habilidades: list[HabilidadeBNCC] = []
    vistos: set[str] = set()
    for hab in brutas:
        if hab.codigo in vistos:
            logger.warning(
                "codigo_duplicado", extra={"codigo": hab.codigo, "pagina_pdf": hab.pagina + 1}
            )
            descartes += 1
            continue
        if hab.avisos:
            logger.info(
                "habilidade_com_aviso",
                extra={"codigo": hab.codigo, "avisos": hab.avisos, "pagina_pdf": hab.pagina + 1},
            )
        try:
            h = HabilidadeBNCC.from_codigo(
                codigo=hab.codigo,
                texto=hab.texto,
                objeto_conhecimento=hab.objeto,
                pagina_pdf=hab.pagina + 1,
            )
        except ValidationError as exc:
            descartes += 1
            logger.warning(
                "habilidade_invalida",
                extra={"codigo": hab.codigo, "pagina_pdf": hab.pagina + 1, "erros": exc.errors()},
            )
            continue
        vistos.add(h.codigo)
        habilidades.append(h)

    _auditar_codigos(doc, paginas, vistos)
    logger.info(
        "extracao_concluida", extra={"habilidades": len(habilidades), "descartes": descartes}
    )
    return habilidades


def _terminada(texto: str) -> bool:
    return texto.rstrip().endswith((".", ";", ")", "!", "?"))


def _dono_da_continuacao(
    candidatas: list[_HabilidadeBruta], bloco: _Bloco
) -> _HabilidadeBruta | None:
    acima = [
        h
        for h in candidatas
        if h.y0 <= bloco.y0 + TOLERANCIA_Y and h.x0 < bloco.x1 and bloco.x0 < h.x1 + 5
    ]
    return max(acima, key=lambda h: h.y0) if acima else None


def _auditar_codigos(doc: pymupdf.Document, paginas: list[int], extraidos: set[str]) -> None:
    """Confere se todo código visível nas páginas de habilidades virou registro."""
    visiveis: set[str] = set()
    for idx in paginas:
        for m in CODIGO_SOLTO.finditer(doc[idx].get_text()):
            visiveis.add(re.sub(r"\s+", "", m.group(1)))
    faltando = sorted(visiveis - extraidos)
    if faltando:
        logger.warning("codigos_nao_extraidos", extra={"total": len(faltando), "codigos": faltando})
