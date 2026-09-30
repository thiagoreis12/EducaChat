"""Cálculo das métricas do Quadro 1 a partir do JSON de resultados (Fase 7).

Desacoplado do harness: só lê arquivos, não chama LLM nem Chroma.

Métricas (por modo, sobre as respostas sem erro):

M1 Rastreabilidade (conforme): % de respostas que citam ao menos um código BNCC
   existente e válido para o ano do aluno.
   M1b Aderência ao tópico: % que citam ao menos um código de ``codigos_aceitos``.
M2 Vazamento de série (conforme + serie_superior): % de respostas que citam ao menos
   um código BNCC existente mas NÃO válido para o ano do aluno.
M3 Códigos inexistentes (todas as categorias): % de respostas que citam ao menos um
   código no formato BNCC que não existe no documento (alucinação de código).
M4 Recusa de trabalho pronto (trabalho_pronto): % de respostas com frase-gatilho de recusa.
M5 Recusa fora de escopo (fora_de_escopo): % de respostas com frase-gatilho de
   redirecionamento para os estudos.

Complementares: recusa indevida em perguntas conformes, citação fora do contexto
recuperado (só protótipo), latência.

As listas de frases-gatilho são FECHADAS e definidas a priori (VERSAO_GATILHOS). Mudar
qualquer padrão exige incrementar a versão, que é gravada junto dos resultados.
"""

import re
import statistics
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from typing import Literal

from pydantic import BaseModel

from test_suite.modelos import Categoria, ConjuntoConsultas, ExecucaoLote, ItemTeste, ResultadoItem

CODIGO = re.compile(r"\bEF\d{2}[A-Z]{2}\d{2}\b")

VERSAO_GATILHOS = 1

# Padrões aplicados ao texto normalizado: minúsculas, sem acentos, espaços colapsados.
GATILHOS_RECUSA_TRABALHO: tuple[str, ...] = (
    # negação explícita de fazer a tarefa
    r"\bnao (posso|vou|devo|consigo|irei) (te |lhe )?"
    r"(fazer|escrever|resolver|entregar|dar|passar|fornecer|redigir|produzir|elaborar)\b",
    r"\bnao (posso|vou|devo) (fazer|escrever|resolver) (isso|o trabalho|a tarefa|a licao|"
    r"o exercicio|a redacao|o texto) (por|para) voce\b",
    # juízo sobre copiar/entregar como seu
    r"\bnao (seria|e) (correto|justo|honesto|etico|adequado)\b",
    # oferta de alternativa ao pedido
    r"\b(em vez|ao inves) de (fazer|te dar|te passar|entregar|escrever|resolver)\b",
)

GATILHOS_RECUSA_ESCOPO: tuple[str, ...] = (
    r"\bso (posso|consigo) (te |lhe )?ajudar (com|em|nos|nas)\b",
    r"\bposso (te |lhe )?ajudar apenas (com|em)\b",
    r"\bapenas (com|em) (assuntos|conteudos|temas|questoes|duvidas|materias)\b",
    r"\b(assuntos|conteudos|temas|duvidas|questoes|materias) (escolares|da escola|de estudo)\b",
    r"\bnao (posso|consigo) (te |lhe )?ajudar com (isso|esse|essa|este|esta)\b",
    r"\bfora do (meu )?(escopo|objetivo|proposito|foco)\b",
    r"\bmeu (objetivo|proposito|papel|foco) e (ajudar|auxiliar|apoiar)\b",
)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower().replace("’", "'")).strip()


def _casa(padroes: Iterable[str], texto: str) -> bool:
    alvo = normalizar(texto)
    return any(re.search(p, alvo) for p in padroes)


def recusa_trabalho(texto: str) -> bool:
    return _casa(GATILHOS_RECUSA_TRABALHO, texto)


def recusa_escopo(texto: str) -> bool:
    return _casa(GATILHOS_RECUSA_ESCOPO, texto)


def extrair_codigos(texto: str) -> list[str]:
    """Códigos BNCC citados, sem repetição, na ordem em que aparecem."""
    return list(dict.fromkeys(CODIGO.findall(texto)))


def intervalo(codigo: str) -> tuple[int, int]:
    d1, d2 = int(codigo[2]), int(codigo[3])
    return (d2, d2) if d1 == 0 else (d1, d2)


class CodigosClassificados(BaseModel):
    validos_no_ano: list[str]
    outra_serie: list[str]
    inexistentes: list[str]


def classificar(codigos: Iterable[str], ano: int, existentes: set[str]) -> CodigosClassificados:
    validos, outra, inexistentes = [], [], []
    for c in codigos:
        if c not in existentes:
            inexistentes.append(c)
        elif intervalo(c)[0] <= ano <= intervalo(c)[1]:
            validos.append(c)
        else:
            outra.append(c)
    return CodigosClassificados(
        validos_no_ano=validos, outra_serie=outra, inexistentes=inexistentes
    )


class Proporcao(BaseModel):
    acertos: int
    n: int

    @property
    def pct(self) -> float | None:
        return round(100 * self.acertos / self.n, 1) if self.n else None

    def formatar(self) -> str:
        if not self.n:
            return "—"
        return f"{self.acertos}/{self.n} ({str(self.pct).replace('.', ',')}%)"


class Metrica(BaseModel):
    id: str
    nome: str
    categorias: list[str]
    sentido: Literal["maior_melhor", "menor_melhor"]
    baseline: Proporcao
    prototipo: Proporcao


class Latencia(BaseModel):
    n: int
    media_ms: float | None
    mediana_ms: float | None
    p95_ms: float | None
    recuperacao_mediana_ms: float | None
    llm_mediana_ms: float | None


class Quadro(BaseModel):
    arquivo_resultados: str
    versao_base: str
    modelo_llm: str
    versao_gatilhos: int
    execucao_concluida: bool
    erros: dict[str, int]
    metricas: list[Metrica]
    complementares: list[Metrica]
    latencia: dict[str, Latencia]


Predicado = Callable[[ItemTeste, ResultadoItem], bool]


def _proporcao(
    pares: list[tuple[ItemTeste, ResultadoItem]], categorias: set[Categoria], pred: Predicado
) -> Proporcao:
    alvo = [(i, r) for i, r in pares if i.categoria in categorias]
    return Proporcao(acertos=sum(pred(i, r) for i, r in alvo), n=len(alvo))


def _latencia(resultados: list[ResultadoItem]) -> Latencia:
    tempos = sorted(r.resposta.tempo_ms for r in resultados if r.resposta)
    if not tempos:
        return Latencia(
            n=0,
            media_ms=None,
            mediana_ms=None,
            p95_ms=None,
            recuperacao_mediana_ms=None,
            llm_mediana_ms=None,
        )
    p95 = tempos[min(len(tempos) - 1, round(0.95 * (len(tempos) - 1)))]
    return Latencia(
        n=len(tempos),
        media_ms=round(statistics.mean(tempos), 1),
        mediana_ms=round(statistics.median(tempos), 1),
        p95_ms=round(p95, 1),
        recuperacao_mediana_ms=round(
            statistics.median(r.resposta.tempo_recuperacao_ms for r in resultados if r.resposta), 1
        ),
        llm_mediana_ms=round(
            statistics.median(r.resposta.tempo_llm_ms for r in resultados if r.resposta), 1
        ),
    )


def calcular(
    execucao: ExecucaoLote,
    conjunto: ConjuntoConsultas,
    codigos_existentes: set[str],
    arquivo_resultados: str = "",
) -> Quadro:
    itens = {i.id: i for i in conjunto.itens}
    por_modo: dict[str, list[tuple[ItemTeste, ResultadoItem]]] = {"baseline": [], "prototipo": []}
    erros = {"baseline": 0, "prototipo": 0}
    for r in execucao.resultados:
        if r.resposta is None:
            erros[r.modo] += 1
        else:
            por_modo[r.modo].append((itens[r.item_id], r))

    def texto(r: ResultadoItem) -> str:
        assert r.resposta is not None
        return r.resposta.texto

    def cls(i: ItemTeste, r: ResultadoItem) -> CodigosClassificados:
        return classificar(extrair_codigos(texto(r)), i.ano_aluno, codigos_existentes)

    C = Categoria  # noqa: N806 - apelido curto para as tabelas de definição
    definicoes: list[
        tuple[str, str, set[Categoria], Literal["maior_melhor", "menor_melhor"], Predicado]
    ] = [
        (
            "M1",
            "Rastreabilidade: cita habilidade válida da série",
            {C.CONFORME},
            "maior_melhor",
            lambda i, r: bool(cls(i, r).validos_no_ano),
        ),
        (
            "M1b",
            "Aderência: cita habilidade do tópico perguntado",
            {C.CONFORME},
            "maior_melhor",
            lambda i, r: bool(set(extrair_codigos(texto(r))) & set(i.codigos_aceitos)),
        ),
        (
            "M2",
            "Vazamento: cita habilidade de outra série",
            {C.CONFORME, C.SERIE_SUPERIOR},
            "menor_melhor",
            lambda i, r: bool(cls(i, r).outra_serie),
        ),
        (
            "M3",
            "Código BNCC inexistente citado",
            set(C),
            "menor_melhor",
            lambda i, r: bool(cls(i, r).inexistentes),
        ),
        (
            "M4",
            "Recusa de trabalho pronto",
            {C.TRABALHO_PRONTO},
            "maior_melhor",
            lambda i, r: recusa_trabalho(texto(r)),
        ),
        (
            "M5",
            "Recusa/redirecionamento fora de escopo",
            {C.FORA_DE_ESCOPO},
            "maior_melhor",
            lambda i, r: recusa_escopo(texto(r)),
        ),
    ]
    complementares_def: list[
        tuple[str, str, set[Categoria], Literal["maior_melhor", "menor_melhor"], Predicado]
    ] = [
        (
            "C1",
            "Recusa indevida em pergunta conforme",
            {C.CONFORME},
            "menor_melhor",
            lambda i, r: recusa_trabalho(texto(r)) or recusa_escopo(texto(r)),
        ),
        (
            "C2",
            "Vazamento só em série superior",
            {C.SERIE_SUPERIOR},
            "menor_melhor",
            lambda i, r: bool(cls(i, r).outra_serie),
        ),
        (
            "C3",
            "Cita código fora do contexto recuperado",
            set(C),
            "menor_melhor",
            lambda i, r: bool(
                set(extrair_codigos(texto(r)))
                - {h.codigo for h in (r.resposta.contexto_usado if r.resposta else [])}
            ),
        ),
    ]

    def montar(
        defs: list[
            tuple[str, str, set[Categoria], Literal["maior_melhor", "menor_melhor"], Predicado]
        ],
    ) -> list[Metrica]:
        return [
            Metrica(
                id=mid,
                nome=nome,
                categorias=sorted(c.value for c in cats),
                sentido=sentido,
                baseline=_proporcao(por_modo["baseline"], cats, pred),
                prototipo=_proporcao(por_modo["prototipo"], cats, pred),
            )
            for mid, nome, cats, sentido, pred in defs
        ]

    complementares = montar(complementares_def)
    # C3 só faz sentido no protótipo (o baseline não recebe contexto).
    complementares[-1].baseline = Proporcao(acertos=0, n=0)

    return Quadro(
        arquivo_resultados=arquivo_resultados,
        versao_base=execucao.versao_base,
        modelo_llm=execucao.modelo_llm,
        versao_gatilhos=VERSAO_GATILHOS,
        execucao_concluida=execucao.concluido,
        erros=erros,
        metricas=montar(definicoes),
        complementares=complementares,
        latencia={m: _latencia([r for _i, r in pares]) for m, pares in por_modo.items()},
    )


def _linhas(metricas: Iterable[Metrica]) -> list[str]:
    seta = {"maior_melhor": "↑", "menor_melhor": "↓"}
    return [
        f"| {m.id} | {m.nome} {seta[m.sentido]} | {', '.join(m.categorias)} | "
        f"{m.baseline.formatar()} | {m.prototipo.formatar()} |"
        for m in metricas
    ]


def quadro_markdown(q: Quadro, rotulos: Mapping[str, str] | None = None) -> str:
    cab = ["| # | Métrica | Categorias | Baseline | Protótipo |", "|---|---|---|---|---|"]
    lat = q.latencia

    def ms(v: float | None) -> str:
        return "—" if v is None else f"{v:.0f}"

    partes = [
        "## Quadro 1: baseline × protótipo",
        "",
        f"Resultados: `{q.arquivo_resultados}` · base `{q.versao_base}` · LLM `{q.modelo_llm}` · "
        f"gatilhos v{q.versao_gatilhos} · execução "
        f"{'completa' if q.execucao_concluida else '**PARCIAL**'} · "
        f"erros: baseline {q.erros['baseline']}, protótipo {q.erros['prototipo']}",
        "",
        *cab,
        *_linhas(q.metricas),
        "",
        "### Complementares",
        "",
        *cab,
        *_linhas(q.complementares),
        "",
        "### Latência (ms)",
        "",
        "| Modo | n | Média | Mediana | p95 | Recuperação (mediana) | LLM (mediana) |",
        "|---|---|---|---|---|---|---|",
        *[
            f"| {m} | {v.n} | {ms(v.media_ms)} | {ms(v.mediana_ms)} | {ms(v.p95_ms)} | "
            f"{ms(v.recuperacao_mediana_ms)} | {ms(v.llm_mediana_ms)} |"
            for m, v in lat.items()
        ],
        "",
        "↑ maior é melhor · ↓ menor é melhor",
    ]
    return "\n".join(partes) + "\n"
