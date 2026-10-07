"""Prompts da Fase 5.

Baseline e protótipo usam o MESMO prompt de sistema e o MESMO enquadramento da série
("Sou aluno do Xº ano."). A única diferença é o bloco de habilidades recuperadas no
protótipo. Assim a comparação isola o efeito da recuperação (decisões D16 e D18).
"""

from collections.abc import Sequence

from educachat.generation.openrouter import Mensagem
from educachat.retrieval.busca import HabilidadeRecuperada

VERSAO_PROMPT = 1

SISTEMA = (
    "Você é o EducaChat, um assistente de estudos para alunos do Ensino Fundamental II "
    "no Brasil. Explique com linguagem clara e adequada à série do aluno, com exemplos "
    "quando ajudar.\n"
    "Regras:\n"
    "1. Não faça tarefas, redações, trabalhos ou exercícios prontos para o aluno "
    "entregar. Nesses casos, recuse com gentileza e ofereça orientação para que ele "
    "faça sozinho.\n"
    "2. Se a pergunta não for sobre conteúdo escolar, diga que você só pode ajudar com "
    "os estudos.\n"
    "3. Quando sua explicação se apoiar em uma habilidade da BNCC, cite o código entre "
    "parênteses, por exemplo (EF06MA07)."
)

INSTRUCAO_CONTEXTO = (
    "Use apenas as habilidades acima como referência curricular e cite o código das que "
    "usar. Se a pergunta tratar de um conteúdo que não aparece nelas, avise que esse "
    "conteúdo não é da sua série e oriente o aluno a partir do que é da série dele. Não "
    "cite códigos que não estejam na lista."
)


def enquadramento(ano_aluno: int) -> str:
    return f"Sou aluno do {ano_aluno}º ano."


def formatar_contexto(ano_aluno: int, habilidades: list[HabilidadeRecuperada]) -> str:
    if not habilidades:
        return f"Nenhuma habilidade da BNCC do {ano_aluno}º ano foi encontrada para esta pergunta."
    linhas = [f"Habilidades da BNCC válidas para o {ano_aluno}º ano relacionadas à pergunta:"]
    for h in habilidades:
        linhas.append(
            f"- ({h.codigo}) [{h.componente} · {h.serie} · {h.objeto_conhecimento}] {h.texto}"
        )
    return "\n".join(linhas)


def mensagens_baseline(pergunta: str, ano_aluno: int) -> list[Mensagem]:
    return [
        Mensagem(role="system", content=SISTEMA),
        Mensagem(role="user", content=f"{enquadramento(ano_aluno)}\n\nPergunta: {pergunta}"),
    ]


def mensagens_prototipo(
    pergunta: str,
    ano_aluno: int,
    habilidades: list[HabilidadeRecuperada],
    historico: Sequence[Mensagem] = (),
) -> list[Mensagem]:
    """``historico`` (turnos anteriores, só na API) entra entre o sistema e a pergunta.

    Vazio por padrão: o harness da Fase 6 gera exatamente as mesmas mensagens de antes.
    """
    usuario = (
        f"{enquadramento(ano_aluno)}\n\n"
        f"{formatar_contexto(ano_aluno, habilidades)}\n\n"
        f"{INSTRUCAO_CONTEXTO}\n\n"
        f"Pergunta: {pergunta}"
    )
    return [
        Mensagem(role="system", content=SISTEMA),
        *historico,
        Mensagem(role="user", content=usuario),
    ]
