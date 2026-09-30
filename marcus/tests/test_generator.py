import json
from pathlib import Path

import httpx
import pytest

from educachat.config import PROJECT_ROOT
from educachat.generation.openrouter import ClienteOpenRouter
from educachat.ingestion.escopo import no_escopo
from educachat.models import HabilidadeBNCC
from test_suite.generator.amostragem import PERGUNTAS_FORA_DE_ESCOPO, planejar, topicos
from test_suite.generator.estrategias import EstrategiaOpenRouter, EstrategiaTemplate
from test_suite.modelos import Categoria, ConjuntoConsultas


def _h(codigo: str, objeto: str) -> HabilidadeBNCC:
    return HabilidadeBNCC.from_codigo(codigo, f"Texto da habilidade {codigo}.", objeto, 1)


HABS = [
    _h("EF06MA01", "Frações; Números naturais"),
    _h("EF06MA02", "Frações"),
    _h("EF07MA01", "Frações; Números inteiros"),
    _h("EF08MA01", "Potenciação"),
    _h("EF09MA01", "Números reais"),
    _h("EF69LP01", "Apreciação e réplica"),
    _h("EF89LP01", "Argumentação"),
    _h("EF06LP01", "Leitura"),
    _h("EF07LP01", "Leitura"),
]
ANOS = [6, 7, 8, 9]


def _plano(seed: int = 1, **kw: int) -> list:  # type: ignore[type-arg]
    params = {
        "n_conforme": 1,
        "n_serie_superior": 1,
        "n_trabalho_pronto": 1,
        "n_fora_de_escopo": 5,
    } | kw
    return planejar(HABS, ANOS, seed=seed, **params)


def test_plano_e_deterministico_e_ids_unicos() -> None:
    a, b = _plano(seed=7), _plano(seed=7)
    assert a == b
    assert len({p.id for p in a}) == len(a)


def test_conforme_e_trabalho_usam_habilidades_validas_no_ano() -> None:
    for p in _plano():
        if p.categoria in (Categoria.CONFORME, Categoria.TRABALHO_PRONTO):
            assert no_escopo(p.habilidade, p.ano_aluno, p.ano_aluno)
            assert p.topico in topicos(p.habilidade)
            assert p.habilidade.codigo in p.codigos_aceitos
            aceitas = {h.codigo: h for h in HABS if h.codigo in p.codigos_aceitos}
            assert all(no_escopo(h, p.ano_aluno, p.ano_aluno) for h in aceitas.values())


def test_codigos_aceitos_incluem_outras_habilidades_do_mesmo_topico() -> None:
    fracoes_6 = [
        p
        for p in _plano(n_conforme=2)
        if p.categoria is Categoria.CONFORME and p.ano_aluno == 6 and p.topico == "Frações"
    ]
    assert fracoes_6
    assert set(fracoes_6[0].codigos_aceitos) == {"EF06MA01", "EF06MA02"}


def test_serie_superior_so_usa_conteudo_posterior_e_inedito() -> None:
    sup = [p for p in _plano() if p.categoria is Categoria.SERIE_SUPERIOR]
    assert sup
    for p in sup:
        assert p.habilidade.ano_inicial > p.ano_aluno
        do_ano = {
            t
            for h in HABS
            if h.componente == p.habilidade.componente and no_escopo(h, p.ano_aluno, p.ano_aluno)
            for t in topicos(h)
        }
        assert p.topico not in do_ano
        assert p.codigos_aceitos == ()
    # 7º ano de Matemática: "Frações" do 7º não conta (o aluno já tem); 9º não tem posterior
    assert not any(p.ano_aluno == 9 for p in sup)


def test_fora_de_escopo_lista_fixa() -> None:
    fora = [p for p in _plano() if p.categoria is Categoria.FORA_DE_ESCOPO]
    assert [p.pergunta_fixa for p in fora] == list(PERGUNTAS_FORA_DE_ESCOPO[:5])
    assert all(p.habilidade is None for p in fora)
    with pytest.raises(ValueError):
        _plano(n_fora_de_escopo=len(PERGUNTAS_FORA_DE_ESCOPO) + 1)


def test_template_nao_copia_texto_da_habilidade() -> None:
    estrategia = EstrategiaTemplate(seed=1)
    for p in _plano():
        pergunta = estrategia.redigir(p)
        if p.habilidade is not None:
            assert p.habilidade.texto not in pergunta
            assert p.topico in pergunta
            assert p.habilidade.codigo not in pergunta
    assert [estrategia.redigir(p) for p in _plano()] == [estrategia.redigir(p) for p in _plano()]


def test_openrouter_usa_cache_em_disco(tmp_path: Path) -> None:
    chamadas: list[dict[str, object]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        chamadas.append(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '"Oi, o que é?"'}}]})

    cliente = ClienteOpenRouter(
        "k", "m", http=httpx.Client(transport=httpx.MockTransport(handler)), dormir=lambda _: None
    )
    estrategia = EstrategiaOpenRouter(cliente, tmp_path)
    pedido = next(p for p in _plano() if p.categoria is Categoria.CONFORME)
    assert estrategia.redigir(pedido) == "Oi, o que é?"
    assert estrategia.redigir(pedido) == "Oi, o que é?"
    assert len(chamadas) == 1
    assert len(list(tmp_path.glob(f"{pedido.habilidade.codigo}_conforme_*.json"))) == 1

    # Outro modelo invalida o cache.
    cliente.modelo = "outro"
    estrategia.redigir(pedido)
    assert len(chamadas) == 2


def test_openrouter_nao_grava_cache_de_resposta_invalida(tmp_path: Path) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]})

    cliente = ClienteOpenRouter(
        "k", "m", http=httpx.Client(transport=httpx.MockTransport(handler)), dormir=lambda _: None
    )
    pedido = next(p for p in _plano() if p.categoria is Categoria.CONFORME)
    with pytest.raises(ValueError):
        EstrategiaOpenRouter(cliente, tmp_path).redigir(pedido)
    assert list(tmp_path.iterdir()) == []


CONSULTAS = PROJECT_ROOT / "test_suite/consultas.json"


@pytest.mark.skipif(not CONSULTAS.exists(), reason="consultas.json ainda não gerado")
def test_consultas_json_valido() -> None:
    conjunto = ConjuntoConsultas.model_validate_json(CONSULTAS.read_text(encoding="utf-8"))
    assert conjunto.versao_base and conjunto.data_geracao
    assert sum(conjunto.contagem.values()) == len(conjunto.itens)
    assert set(conjunto.contagem) == {c.value for c in Categoria}
