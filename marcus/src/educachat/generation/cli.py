"""Teste manual da Fase 5.

Uso:
    python -m educachat.generation.cli --modo prototipo --ano 6 "o que é fração?"
    python -m educachat.generation.cli --modo baseline --ano 6 "o que é fração?"
    python -m educachat.generation.cli --modo prototipo --ano 6 --dry-run "..."   # sem LLM
"""

import argparse
import sys

from educachat.config import get_settings
from educachat.generation.baseline import responder_baseline
from educachat.generation.prompts import mensagens_baseline, mensagens_prototipo
from educachat.generation.prototipo import recuperador_padrao, responder_prototipo
from educachat.logging_config import setup_logging


def main(argv: list[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pergunta")
    parser.add_argument("--modo", choices=["baseline", "prototipo"], default="prototipo")
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true", help="só mostra o prompt")
    args = parser.parse_args(argv)
    setup_logging("generation", settings.log_dir, settings.log_level)
    out = sys.stdout

    if args.dry_run:
        if args.modo == "baseline":
            mensagens = mensagens_baseline(args.pergunta, args.ano)
        else:
            contexto = recuperador_padrao()(args.pergunta, args.ano, settings.rag_k)
            mensagens = mensagens_prototipo(args.pergunta, args.ano, contexto)
        for m in mensagens:
            out.write(f"--- {m.role} ---\n{m.content}\n\n")
        return

    if args.modo == "baseline":
        resposta = responder_baseline(args.pergunta, args.ano)
    else:
        resposta = responder_prototipo(args.pergunta, args.ano)
    out.write(resposta.texto + "\n\n")
    out.write(
        f"[{resposta.config.modo} | {resposta.config.modelo_llm} | "
        f"total {resposta.tempo_ms:.0f} ms (recuperação {resposta.tempo_recuperacao_ms:.0f} ms, "
        f"LLM {resposta.tempo_llm_ms:.0f} ms) | tentativas {resposta.tentativas_llm} | "
        f"contexto {[h.codigo for h in resposta.contexto_usado]}]\n"
    )


if __name__ == "__main__":
    main()
