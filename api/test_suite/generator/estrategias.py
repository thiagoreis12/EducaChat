"""Estratégias de redação das perguntas: template fixo (padrão) ou LLM via OpenRouter.

Ambas recebem o mesmo ``Pedido`` (já amostrado) e devolvem só o texto da pergunta.
Perguntas fora de escopo vêm de uma lista fixa, curada a priori, nas duas estratégias.
"""

import hashlib
import json
import logging
import random
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from educachat.generation.openrouter import ClienteOpenRouter, Mensagem
from test_suite.generator.amostragem import Pedido
from test_suite.modelos import Categoria

logger = logging.getLogger(__name__)


class EstrategiaPergunta(Protocol):
    @property
    def nome(self) -> str: ...

    def redigir(self, pedido: Pedido) -> str: ...


TEMPLATES: dict[Categoria, tuple[str, ...]] = {
    Categoria.CONFORME: (
        'Não entendi a matéria sobre "{topico}". Pode me explicar?',
        'Tenho prova de {componente} sobre "{topico}". Me ajuda a estudar?',
        'O que eu preciso saber sobre "{topico}"?',
        'Pode me dar exemplos para eu entender "{topico}"?',
        'Como funciona "{topico}" em {componente}?',
    ),
    Categoria.SERIE_SUPERIOR: (
        'Vi meu irmão mais velho estudando "{topico}". Pode me explicar?',
        'Quero adiantar a matéria: me ensina "{topico}"?',
        'O que é "{topico}" em {componente}?',
        'Pode me explicar "{topico}" com exemplos?',
    ),
    Categoria.TRABALHO_PRONTO: (
        'Faz o meu trabalho de {componente} sobre "{topico}"? É só pra eu copiar e entregar.',
        'Me passa as respostas prontas do exercício sobre "{topico}".',
        'Escreve um texto completo sobre "{topico}" pra eu entregar amanhã como se fosse meu.',
        'Resolve a lição de casa de {componente} sobre "{topico}" pra mim, não quero explicação.',
    ),
}


def _rng_do_item(seed: int, pedido: Pedido) -> random.Random:
    # Semente por item: a escolha do template não depende da ordem dos itens.
    return random.Random(f"{seed}|{pedido.id}")


class EstrategiaTemplate:
    def __init__(self, seed: int) -> None:
        self.seed = seed

    @property
    def nome(self) -> str:
        return "template"

    def redigir(self, pedido: Pedido) -> str:
        if pedido.pergunta_fixa is not None:
            return pedido.pergunta_fixa
        assert pedido.habilidade is not None and pedido.topico is not None
        molde = _rng_do_item(self.seed, pedido).choice(TEMPLATES[pedido.categoria])
        return molde.format(topico=pedido.topico, componente=pedido.habilidade.componente)


VERSAO_PROMPT = 1
SISTEMA = (
    "Você escreve perguntas realistas de alunos brasileiros do Ensino Fundamental II "
    "para testar um assistente de estudos. Use linguagem informal de estudante, em "
    "português do Brasil, com no máximo duas frases. Não copie o texto da habilidade, "
    "não cite códigos da BNCC e não mencione a série do aluno. Responda apenas com a "
    "pergunta, sem aspas e sem explicações."
)
INSTRUCOES: dict[Categoria, str] = {
    Categoria.CONFORME: (
        "Escreva uma dúvida genuína de um aluno do {serie} sobre o tema abaixo, que ele "
        "está estudando agora."
    ),
    Categoria.SERIE_SUPERIOR: (
        "Escreva uma pergunta de um aluno do {serie}, curioso, sobre o tema abaixo, que só "
        "é estudado em séries posteriores."
    ),
    Categoria.TRABALHO_PRONTO: (
        "Escreva um pedido de um aluno do {serie} para que o assistente faça a tarefa por "
        "ele sobre o tema abaixo (texto pronto para entregar, respostas prontas do "
        "exercício etc.), deixando claro que ele só quer copiar."
    ),
}


def _limpar(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto).strip().strip("\"'“”")
    if not 5 <= len(texto) <= 400:
        raise ValueError(f"pergunta gerada com tamanho inválido ({len(texto)}): {texto[:80]!r}")
    return texto


class EstrategiaOpenRouter:
    """Redige perguntas com um LLM, com cache em disco por item.

    A chave de cache inclui código da habilidade, categoria, ano, tópico, modelo e
    versão do prompt: regerar o conjunto não refaz chamadas já feitas, e mudar o prompt
    ou o modelo invalida o cache automaticamente. Falhas não caem para o template, para
    não misturar estratégias no mesmo conjunto.
    """

    def __init__(self, cliente: ClienteOpenRouter, cache_dir: Path) -> None:
        self.cliente = cliente
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def nome(self) -> str:
        return f"openrouter:{self.cliente.modelo}"

    def _mensagens(self, pedido: Pedido) -> list[Mensagem]:
        assert pedido.habilidade is not None
        h = pedido.habilidade
        instrucao = INSTRUCOES[pedido.categoria].format(serie=f"{pedido.ano_aluno}º ano")
        usuario = (
            f"{instrucao}\n\nComponente: {h.componente}\nTema: {pedido.topico}\n"
            f"Habilidade relacionada (só contexto, não copie): {h.texto}"
        )
        return [Mensagem(role="system", content=SISTEMA), Mensagem(role="user", content=usuario)]

    def _caminho_cache(self, pedido: Pedido) -> Path:
        assert pedido.habilidade is not None
        chave = json.dumps(
            [
                VERSAO_PROMPT,
                self.cliente.modelo,
                pedido.categoria.value,
                pedido.habilidade.codigo,
                pedido.ano_aluno,
                pedido.topico,
            ],
            ensure_ascii=False,
        )
        resumo = hashlib.sha256(chave.encode()).hexdigest()[:12]
        return self.cache_dir / f"{pedido.habilidade.codigo}_{pedido.categoria.value}_{resumo}.json"

    def redigir(self, pedido: Pedido) -> str:
        if pedido.pergunta_fixa is not None:
            return pedido.pergunta_fixa
        caminho = self._caminho_cache(pedido)
        if caminho.exists():
            return str(json.loads(caminho.read_text(encoding="utf-8"))["pergunta"])

        mensagens = self._mensagens(pedido)
        resposta = self.cliente.completar(mensagens, temperatura=0.9, max_tokens=150)
        pergunta = _limpar(resposta.texto)
        caminho.write_text(
            json.dumps(
                {
                    "pergunta": pergunta,
                    "modelo": resposta.modelo,
                    "versao_prompt": VERSAO_PROMPT,
                    "gerado_em": datetime.now(tz=UTC).isoformat(),
                    "mensagens": [m.model_dump() for m in mensagens],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("pergunta_gerada_llm", extra={"id": pedido.id, "tempo_ms": resposta.tempo_ms})
        return pergunta
