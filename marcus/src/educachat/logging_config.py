"""Logging estruturado (JSON Lines) para stderr e para arquivo em logs/.

Cada linha de log é um objeto JSON; campos extras passados via ``extra={...}``
são incluídos no objeto. Isso permite, por exemplo, somar tempos de ingestão
a partir de ``logs/*.jsonl`` na Fase 3.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(run_name: str, log_dir: Path, level: str = "INFO") -> Path:
    """Configura o logger raiz; retorna o caminho do arquivo .jsonl desta execução."""
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"{run_name}_{stamp}.jsonl"

    formatter = JsonFormatter()
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    # Bibliotecas ruidosas (downloads do Hugging Face, telemetria do Chroma).
    for nome in ("httpx", "httpcore", "urllib3", "huggingface_hub", "chromadb"):
        logging.getLogger(nome).setLevel(logging.WARNING)
    return log_path
