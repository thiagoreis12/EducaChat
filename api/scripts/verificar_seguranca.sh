#!/usr/bin/env bash
# Critério de pronto da Fase 5.5, contra a API real (Supabase + OpenRouter configurados).
# Um aluno do 6º ano não pode receber conteúdo de outra série, nem manipulando o payload.
#
# Uso: API=http://127.0.0.1:8000 EMAIL=aluno6@exemplo.com SENHA=... ./scripts/verificar_seguranca.sh
# O usuário precisa existir e ter perfil do 6º ano (cadastro com "ano": 6).
set -euo pipefail
API="${API:-http://127.0.0.1:8000}"
: "${EMAIL:?defina EMAIL}" "${SENHA:?defina SENHA}"
falhas=0
checar() { # descrição, esperado, obtido
  if [[ "$2" == "$3" ]]; then echo "OK    $1"; else echo "FALHA $1 (esperado $2, obtido $3)"; falhas=$((falhas + 1)); fi
}

TOKEN=$(curl -sf -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"senha\":\"$SENHA\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
H=(-H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json')
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

checar "sem token -> 401"                401 "$(status -X POST "$API/chat" -H 'Content-Type: application/json' -d '{"pergunta":"x"}')"
checar "token adulterado -> 401"         401 "$(status -X POST "$API/chat" -H "Authorization: Bearer ${TOKEN}x" -H 'Content-Type: application/json' -d '{"pergunta":"x"}')"
checar "payload com ano -> 422"          422 "$(status -X POST "$API/chat" "${H[@]}" -d '{"pergunta":"x","ano":9}')"
checar "payload com serie -> 422"        422 "$(status -X POST "$API/chat" "${H[@]}" -d '{"pergunta":"x","serie":"9º ano"}')"
checar "modo baseline -> 422"            422 "$(status -X POST "$API/chat" "${H[@]}" -d '{"pergunta":"x","modo":"baseline"}')"
checar "trocar série no perfil -> 409"   409 "$(status -X POST "$API/perfil" "${H[@]}" -d '{"ano":9}')"
checar "rota baseline oculta -> 404"     404 "$(status -X POST "$API/interno/baseline" "${H[@]}" -d '{"pergunta":"x"}')"

# Pergunta de conteúdo do 9º ano: todas as habilidades devolvidas precisam valer para o 6º.
RESP=$(curl -sf -X POST "$API/chat" "${H[@]}" -d '{"pergunta":"Me explica os números reais e a notação científica"}')
FORA=$(echo "$RESP" | python3 -c '
import json, sys
r = json.load(sys.stdin)
def vale6(c):
    a, b = int(c[2]), int(c[3])
    a = b if a == 0 else a
    return a <= 6 <= b
print(",".join(h["codigo"] for h in r["habilidades"] if not vale6(h["codigo"])))')
checar "série no retorno = 6º ano"       "6º ano" "$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["serie"])')"
checar "nenhuma habilidade de outra série" "" "$FORA"

echo; [[ $falhas -eq 0 ]] && echo "Tudo certo." || { echo "$falhas verificação(ões) falharam."; exit 1; }
