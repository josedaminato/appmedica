#!/usr/bin/env bash
# Smoke test rápido en producción (correr en VPS o contra URL pública).
# Uso en VPS:
#   cd /opt/appmedica && bash scripts/prod-smoke-test.sh
# Contra prod desde tu PC (solo health + forgot-password genérico):
#   BASE_URL=https://daminatoweb.com bash scripts/prod-smoke-test.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API="${BASE_URL}/api/v1"

echo "=== Smoke test AppMédica ==="
echo "API: ${API}"
echo ""

echo -n "[health] "
curl -sf "${API}/health"
echo ""

echo -n "[forgot-password] "
RESP="$(curl -sf -X POST "${API}/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke-test@example.com"}')"
echo "${RESP}"

if echo "${RESP}" | grep -qi 'enviado\|instrucciones\|message'; then
  echo "  OK: endpoint responde."
else
  echo "  Revisar respuesta del endpoint."
fi

echo ""
echo "Checklist manual en el navegador (§8 docs/deploy-daminatoweb-vps.md):"
echo "  1. https://daminatoweb.com/register — registro con términos"
echo "  2. /insurances — obra social"
echo "  3. /patients — paciente o import Excel"
echo "  4. /agenda/new — turno"
echo "  5. Agenda — cierre + cobro"
echo "  6. /payments — export deuda"
echo "  7. /forgot-password — email real (requiere SMTP)"
