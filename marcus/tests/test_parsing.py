import re
from collections import Counter

import pytest
from pydantic import ValidationError

from educachat.models import COMPONENTES, HabilidadeBNCC, anos_do_codigo, rotulo_serie

CODIGO = re.compile(r"^EF\d{2}[A-Z]{2}\d{2}$")

# Total extraído do PDF BNCC_EI_EF_110518_versaofinal_site.pdf, com auditoria de
# códigos sem pendências. Se mudar, investigue antes de atualizar o número.
TOTAL_ESPERADO = 1304


def test_total_de_habilidades(habilidades: list[HabilidadeBNCC]) -> None:
    assert len(habilidades) == TOTAL_ESPERADO


def test_nenhum_codigo_duplicado(habilidades: list[HabilidadeBNCC]) -> None:
    repetidos = [c for c, n in Counter(h.codigo for h in habilidades).items() if n > 1]
    assert repetidos == []


def test_nenhum_campo_vazio(habilidades: list[HabilidadeBNCC]) -> None:
    for h in habilidades:
        for campo, valor in h.model_dump().items():
            if isinstance(valor, str):
                assert valor.strip(), f"{h.codigo}: campo {campo} vazio"


def test_codigos_no_padrao(habilidades: list[HabilidadeBNCC]) -> None:
    assert all(CODIGO.match(h.codigo) for h in habilidades)


def test_todos_os_anos_do_fundamental_cobertos(habilidades: list[HabilidadeBNCC]) -> None:
    cobertos = {ano for h in habilidades for ano in h.anos}
    assert cobertos == set(range(1, 10))


@pytest.mark.parametrize("ano", [6, 7, 8, 9])
def test_fundamental_ii_tem_todos_os_componentes(
    habilidades: list[HabilidadeBNCC], ano: int
) -> None:
    componentes = {h.componente for h in habilidades if ano in h.anos}
    assert componentes == set(COMPONENTES.values())


def test_numeracao_contigua_por_prefixo(habilidades: list[HabilidadeBNCC]) -> None:
    # Dentro de cada prefixo (ex.: EF06MA) a BNCC numera 01..N sem saltos; uma lacuna
    # indica habilidade perdida na extração mesmo que a contagem total pareça plausível.
    numeros: dict[str, set[int]] = {}
    for h in habilidades:
        numeros.setdefault(h.codigo[:6], set()).add(int(h.codigo[6:]))
    lacunas = {p: sorted(set(range(1, max(n) + 1)) - n) for p, n in numeros.items()}
    assert {p: faltam for p, faltam in lacunas.items() if faltam} == {}


def test_texto_nao_contem_outro_codigo_no_inicio(habilidades: list[HabilidadeBNCC]) -> None:
    # Sinal de duas habilidades fundidas num registro só.
    fundidas = [h.codigo for h in habilidades if re.search(r"\(EF\d{2}[A-Z]{2}\d{2}\)", h.texto)]
    assert fundidas == []


# Casos conferidos visualmente contra o PDF (páginas renderizadas).
@pytest.mark.parametrize(
    ("codigo", "objeto", "inicio_texto"),
    [
        ("EF06MA01", None, "Comparar, ordenar, ler e escrever números naturais"),
        ("EF01LP01", "Protocolos de leitura", "Reconhecer que textos são lidos"),
        ("EF12LP03", None, "Copiar textos breves"),
        ("EF02LP01", "Construção do sistema alfabético/ Convenções da escrita", "Utilizar,"),
        ("EF67LP26", "Textualização", "Reconhecer a estrutura de hipertexto"),
        ("EF67LP27", "Relação entre textos", "Analisar, entre os textos literários"),
        ("EF07HI06", "As descobertas científicas e a expansão marítima", "Comparar as navegações"),
        ("EF07HI17", "A emergência do capitalismo", "Discutir as razões"),
    ],
)
def test_casos_conferidos_no_pdf(
    habilidades: list[HabilidadeBNCC], codigo: str, objeto: str | None, inicio_texto: str
) -> None:
    h = {x.codigo: x for x in habilidades}[codigo]
    assert h.texto.startswith(inicio_texto)
    if objeto is not None:
        assert h.objeto_conhecimento == objeto


def test_habilidade_multi_ano() -> None:
    assert anos_do_codigo("EF69LP01") == (6, 9)
    assert anos_do_codigo("EF06MA01") == (6, 6)
    assert anos_do_codigo("EF15AR01") == (1, 5)
    assert rotulo_serie(6, 9) == "6º ao 9º ano"
    h = HabilidadeBNCC.from_codigo("EF69LP01", "Texto de teste válido.", "Objeto", 142)
    assert h.anos == [6, 7, 8, 9]


@pytest.mark.parametrize("codigo", ["EF6MA01", "EF06ma01", "EI06MA01", "EF06XX01", "EF06MA1"])
def test_codigo_invalido_rejeitado(codigo: str) -> None:
    with pytest.raises(ValidationError):
        HabilidadeBNCC(
            codigo=codigo,
            serie="6º ano",
            ano_inicial=6,
            ano_final=6,
            componente="Matemática",
            objeto_conhecimento="x",
            texto="Texto de teste válido.",
            pagina_pdf=1,
        )


def test_serie_inconsistente_rejeitada() -> None:
    with pytest.raises(ValidationError):
        HabilidadeBNCC(
            codigo="EF06MA01",
            serie="7º ano",
            ano_inicial=6,
            ano_final=6,
            componente="Matemática",
            objeto_conhecimento="x",
            texto="Texto de teste válido.",
            pagina_pdf=1,
        )
