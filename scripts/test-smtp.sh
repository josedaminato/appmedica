#!/usr/bin/env bash
# Prueba SMTP desde el backend en producción (login + envío opcional).
# Uso:
#   cd /opt/appmedica && bash scripts/test-smtp.sh
#   cd /opt/appmedica && bash scripts/test-smtp.sh daminatojp@gmail.com

set -euo pipefail

TO_EMAIL="${1:-}"

cd /opt/appmedica
COMPOSE="docker compose -f docker-compose.prod.yml --env-file backend/.env.prod"

echo "=== Config SMTP (sin mostrar password) ==="
grep -E '^(EMAIL_PROVIDER|SMTP_HOST|SMTP_PORT|SMTP_USER|SMTP_FROM|SMTP_USE)' backend/.env.prod || true
if grep -qE '^SMTP_PASSWORD=.+' backend/.env.prod; then
  echo "SMTP_PASSWORD=***configurado***"
else
  echo "SMTP_PASSWORD=FALTA"
  exit 1
fi

echo ""
echo "=== Verificando login SMTP ==="
$COMPOSE exec -T backend python - <<'PY'
import sys
from app.core.config import get_settings
from app.integrations.reminders.email_adapter import EmailReminderProvider

settings = get_settings()
print(f"provider={settings.email_provider} host={settings.smtp_host} port={settings.smtp_port}")
print(f"user={settings.smtp_user} from={settings.smtp_from_email}")
print(f"password_len={len(settings.smtp_password or '')} use_ssl={settings.smtp_use_ssl} use_tls={settings.smtp_use_tls}")
try:
    EmailReminderProvider(settings).verify_connection()
    print("OK: login SMTP correcto")
except Exception as e:
    print(f"ERROR SMTP login: {e}", file=sys.stderr)
    sys.exit(1)
PY

if [[ -n "${TO_EMAIL}" ]]; then
  echo ""
  echo "=== Enviando email de prueba a ${TO_EMAIL} ==="
  $COMPOSE exec -T backend python - <<PY
import sys
from app.core.config import get_settings
from app.integrations.reminders.base import ReminderPayload
from app.integrations.reminders.email_adapter import EmailReminderProvider

to_email = "${TO_EMAIL}"
settings = get_settings()
payload = ReminderPayload(
    patient_name="Prueba",
    message="Si recibís este correo, SMTP de AppMédica funciona correctamente.\\n\\n— AppMédica",
    email=to_email,
    subject="AppMédica — prueba SMTP",
)
try:
    EmailReminderProvider(settings).send_sync(payload)
    print("OK: email enviado (revisá bandeja y spam)")
except Exception as e:
    print(f"ERROR SMTP send: {e}", file=sys.stderr)
    sys.exit(1)
PY
fi

echo ""
echo "=== Últimos logs de email en backend ==="
$COMPOSE logs backend --tail=40 2>&1 | grep -iE 'email|smtp|reset' || echo "(sin líneas recientes)"
