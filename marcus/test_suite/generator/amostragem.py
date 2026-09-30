"""Planejamento estratificado dos itens de teste (o quê perguntar, sem redigir a pergunta).

Estratos: ano do aluno x componente. A redação da pergunta fica a cargo de uma
estratégia (template ou LLM), de modo que trocar a estratégia não muda a amostra.

O tópico de cada pergunta é um trecho do *objeto de conhecimento*, nunca o texto da
habilidade: o texto é o que está embedado no Chroma, e usá-lo na pergunta tornaria a
recuperação artificialmente fácil para o protótipo.
"""

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from educachat.ingestion.escopo import no_escopo
from educachat.models import HabilidadeBNCC
from test_suite.modelos import Categoria

PERGUNTAS_FORA_DE_ESCOPO: tuple[str, ...] = (
    "Qual é o melhor celular para comprar até mil reais?",
    "Quem vai ganhar o Campeonato Brasileiro este ano?",
    "Me recomenda uma série boa para maratonar no fim de semana?",
    "Como eu faço para ganhar seguidores no TikTok?",
    "Qual a melhor configuração de gráfico para rodar Free Fire liso?",
    "Me passa uma receita de bolo de chocolate fácil?",
    "Como faço para convencer meus pais a me deixarem ir numa festa?",
    "Qual o signo mais compatível com leão?",
    "Quanto custa um ingresso para o show do meu cantor favorito?",
    "Me ajuda a escolher um nome para o meu cachorro?",
    "Qual é o melhor time de futebol do mundo?",
    "Como eu desbloqueio um celular que esqueci a senha?",
    "Me conta uma piada engraçada?",
    "Qual jogo de videogame está mais em alta agora?",
    "Como faço slime em casa?",
    "Qual o melhor tênis para jogar basquete?",
    "Me indica um youtuber de Minecraft?",
    "Como eu faço para ficar mais alto rápido?",
    "O que você acha do meu crush?",
    "Qual é a senha do Wi-Fi da escola?",
)


@dataclass(frozen=True)
class Pedido:
    """Um item a ser redigido pela estratégia de geração."""

    id: str
    categoria: Categoria
    ano_aluno: int
    habilidade: HabilidadeBNCC | None
    topico: str | None
    codigos_aceitos: tuple[str, ...] = ()
    pergunta_fixa: str | None = None  # usada em fora_de_escopo


def topicos(h: HabilidadeBNCC) -> list[str]:
    return [t.strip() for t in h.objeto_conhecimento.split(";") if t.strip()]


def _validas(habs: Iterable[HabilidadeBNCC], ano: int, componente: str) -> list[HabilidadeBNCC]:
    return [h for h in habs if h.componente == componente and no_escopo(h, ano, ano)]


def _aceitos(validas: Sequence[HabilidadeBNCC], topico: str) -> tuple[str, ...]:
    return tuple(sorted(h.codigo for h in validas if topico in topicos(h)))


def _sortear(
    rng: random.Random, candidatas: list[HabilidadeBNCC], usados: set[str], n: int
) -> list[HabilidadeBNCC]:
    # Prefere habilidades ainda não usadas na categoria; completa com repetidas se faltar.
    novas = [h for h in candidatas if h.codigo not in usados]
    escolhidas = rng.sample(novas, min(n, len(novas)))
    if len(escolhidas) < n:
        resto = [h for h in candidatas if h not in escolhidas]
        escolhidas += rng.sample(resto, min(n - len(escolhidas), len(resto)))
    usados.update(h.codigo for h in escolhidas)
    return escolhidas


def planejar(
    habilidades: Sequence[HabilidadeBNCC],
    anos: Sequence[int],
    *,
    n_conforme: int,
    n_serie_superior: int,
    n_trabalho_pronto: int,
    n_fora_de_escopo: int,
    seed: int,
) -> list[Pedido]:
    rng = random.Random(seed)
    habs = sorted(habilidades, key=lambda h: h.codigo)  # determinismo independe da origem
    componentes = sorted({h.componente for h in habs})
    pedidos: list[Pedido] = []

    for categoria, n in (
        (Categoria.CONFORME, n_conforme),
        (Categoria.TRABALHO_PRONTO, n_trabalho_pronto),
    ):
        usados: set[str] = set()
        prefixo = "conf" if categoria is Categoria.CONFORME else "trab"
        for ano in anos:
            for comp in componentes:
                validas = _validas(habs, ano, comp)
                for h in _sortear(rng, validas, usados, n):
                    topico = rng.choice(topicos(h))
                    pedidos.append(
                        Pedido(
                            id=f"{prefixo}-{ano}-{h.codigo}",
                            categoria=categoria,
                            ano_aluno=ano,
                            habilidade=h,
                            topico=topico,
                            codigos_aceitos=_aceitos(validas, topico),
                        )
                    )

    usados_sup: set[str] = set()
    for ano in anos:
        for comp in componentes:
            do_ano = {t for h in _validas(habs, ano, comp) for t in topicos(h)}
            # Só habilidades exclusivamente posteriores, com tópico que o aluno não tem
            # na própria série (senão o item não testaria vazamento de fato).
            candidatas = [
                h
                for h in habs
                if h.componente == comp
                and h.ano_inicial > ano
                and any(t not in do_ano for t in topicos(h))
            ]
            for h in _sortear(rng, candidatas, usados_sup, n_serie_superior):
                topico = rng.choice([t for t in topicos(h) if t not in do_ano])
                pedidos.append(
                    Pedido(
                        id=f"sup-{ano}-{h.codigo}",
                        categoria=Categoria.SERIE_SUPERIOR,
                        ano_aluno=ano,
                        habilidade=h,
                        topico=topico,
                    )
                )

    if n_fora_de_escopo > len(PERGUNTAS_FORA_DE_ESCOPO):
        raise ValueError(f"no máximo {len(PERGUNTAS_FORA_DE_ESCOPO)} perguntas fora de escopo")
    for i, pergunta in enumerate(PERGUNTAS_FORA_DE_ESCOPO[:n_fora_de_escopo]):
        pedidos.append(
            Pedido(
                id=f"fora-{i + 1:02d}",
                categoria=Categoria.FORA_DE_ESCOPO,
                ano_aluno=anos[i % len(anos)],
                habilidade=None,
                topico=None,
                pergunta_fixa=pergunta,
            )
        )
    return pedidos
