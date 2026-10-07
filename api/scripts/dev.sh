#!/usr/bin/env bash
# Fase 10: sobe API (FastAPI) e front (Vite) juntos, localmente.
# Front: http://localhost:5173   API: http://localhost:8000 (docs em /docs)
#
# Os dois usam o host "localhost" de propósito: o cookie de refresh é SameSite=Strict e o
# navegador trata localhost e 127.0.0.1 como sites diferentes.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

[[ -f "$RAIZ/.env" ]] || { echo "Falta $RAIZ/.env (copie de .env.example)"; exit 1; }
[[ -d "$RAIZ/frontend/node_modules" ]] || (cd "$RAIZ/frontend" && npm install)
[[ -f "$RAIZ/frontend/.env.development" ]] || cp "$RAIZ/frontend/.env.example" "$RAIZ/frontend/.env.development"

trap 'kill 0' EXIT INT TERM
(cd "$RAIZ" && uv run uvicorn educachat.api.main:app --host localhost --port 8000 --reload --reload-dir src) &
(cd "$RAIZ/frontend" && npm run dev) &
wait
