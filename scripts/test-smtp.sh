#!/usr/bin/env bash
# Prueba envío SMTP desde el backend en producción
# Uso: cd /opt/appmedica && bash scripts/test-smtp.sh daminatojp@gmail.com

set -euo pipefail

TO_EMAIL="${1:-}"
if [[ -z "${TO_EMAIL}" ]]; then
  echo "Uso: bash scripts/test-smtp.sh email@destino.com"
  exit 1
fi

cd /opt/appmedica
COMPOSE="docker compose -f docker-compose.prod.yml --env-file backend/.env.prod"

echo "=== Config SMTP (sin mostrar password) ==="
grep -E '^(EMAIL_PROVIDER|SMTP_HOST|SMTP_PORT|SMTP_USER|SMTP_FROM)' backend/.env.prod || true
if grep -q '^SMTP_PASSWORD=.' backend/.env.prod; then
  echo "SMTP_PASSWORD=***configurado***"
else
  echo "SMTP_PASSWORD=FALTA"
  exit 1
fi

echo ""
echo "=== Enviando email de prueba a ${TO_EMAIL} ==="
$COMPOSE exec -T backend python - <<PY
import asyncio
import sys
from app.core.config import get_settings
from app.integrations.reminders.base import ReminderPayload
from app.integrations.reminders.email_adapter import EmailReminderProvider

to_email = "${TO_EMAIL}"
settings = get_settings()
print(f"provider={settings.email_provider} host={settings.smtp_host} port={settings.smtp_port}")
print(f"user={settings.smtp_user} from={settings.smtp_from_email}")
print(f"password_len={len(settings.smtp_password or '')}")

async def main():
    payload = ReminderPayload(
        patient_name="Prueba",
        message="Si recibís este correo, SMTP de AppMedica funciona correctamente.",
        email=to_email,
        subject="AppMedica — prueba SMTP",
    )
    await EmailReminderProvider(settings).send(payload)

try:
    asyncio.run(main())
    print("OK: email enviado (revisá bandeja y spam)")
except Exception as e:
    print(f"ERROR SMTP: {e}", file=sys.stderr)
    sys.exit(1)
PY

echo ""
echo "=== Últimos logs de email en backend ==="
$COMPOSE logs backend --tail=30 2>&1 | grep -iE 'email|smtp|reset' || echo "(sin líneas recientes)"
