#!/usr/bin/env bash
# Configuración operativa en el VPS: SMTP, backup y cron.
# Ejecutar en el servidor:
#   cd /opt/appmedica && bash scripts/setup-prod-ops.sh
#
# Para setear la contraseña SMTP sin editar a mano (una sola vez):
#   SMTP_PASSWORD='tu-password-correo' bash scripts/setup-prod-ops.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/appmedica}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="backend/.env.prod"
CRON_BACKUP='0 3 * * * cd /opt/appmedica && bash scripts/backup-db.sh >> /var/log/appmedica-backup.log 2>&1'
CRON_REMINDERS='*/5 * * * * cd /opt/appmedica && docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T backend python scripts/process_reminders.py >> /var/log/appmedica-reminders.log 2>&1'
CRON_DIGEST='0 0 * * * cd /opt/appmedica && docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T backend python scripts/send_daily_agenda.py >> /var/log/appmedica-digest.log 2>&1'
CRON_SERIES='0 4 * * * cd /opt/appmedica && docker compose -f docker-compose.prod.yml --env-file backend/.env.prod exec -T backend python scripts/extend_indefinite_series.py >> /var/log/appmedica-series.log 2>&1'

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: No existe ${ENV_FILE}"
  exit 1
fi

echo "=========================================="
echo " AppMédica — setup operativo (prod)"
echo "=========================================="

# --- 0. URLs públicas (CORS + links en emails) ---
echo ""
echo "[0/5] Verificando CORS_ORIGINS, PUBLIC_APP_URL y VITE_API_URL..."

ensure_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    if ! grep -q "^${key}=${value}$" "${ENV_FILE}"; then
      sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
      NEEDS_BACKEND_RESTART=1
      echo "  ${key} actualizado."
    fi
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
    NEEDS_BACKEND_RESTART=1
    echo "  ${key} agregado."
  fi
}

NEEDS_BACKEND_RESTART=0
ensure_env "CORS_ORIGINS" "https://daminatoweb.com,https://www.daminatoweb.com"
ensure_env "PUBLIC_APP_URL" "https://daminatoweb.com"
ensure_env "VITE_API_URL" "/api/v1"

# --- 1. SMTP ---
echo ""
echo "[1/5] Verificando SMTP..."

if [[ -n "${SMTP_PASSWORD:-}" ]]; then
  if grep -q '^SMTP_PASSWORD=' "${ENV_FILE}"; then
    sed -i "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=${SMTP_PASSWORD}|" "${ENV_FILE}"
    echo "  SMTP_PASSWORD actualizado desde variable de entorno."
  else
    echo "SMTP_PASSWORD=${SMTP_PASSWORD}" >> "${ENV_FILE}"
    echo "  SMTP_PASSWORD agregado al .env.prod."
  fi
  NEEDS_BACKEND_RESTART=1
fi

# Alinear usuario/remitente con contacto@ (soporte oficial del producto)
if grep -q '^SMTP_USER=' "${ENV_FILE}"; then
  sed -i 's|^SMTP_USER=.*|SMTP_USER=contacto@daminatoweb.com|' "${ENV_FILE}"
else
  echo "SMTP_USER=contacto@daminatoweb.com" >> "${ENV_FILE}"
fi
if grep -q '^SMTP_FROM_EMAIL=' "${ENV_FILE}"; then
  sed -i 's|^SMTP_FROM_EMAIL=.*|SMTP_FROM_EMAIL=contacto@daminatoweb.com|' "${ENV_FILE}"
else
  echo "SMTP_FROM_EMAIL=contacto@daminatoweb.com" >> "${ENV_FILE}"
fi

if ! grep -q '^EMAIL_PROVIDER=smtp' "${ENV_FILE}"; then
  echo "  Configurando EMAIL_PROVIDER=smtp..."
  if grep -q '^EMAIL_PROVIDER=' "${ENV_FILE}"; then
    sed -i 's|^EMAIL_PROVIDER=.*|EMAIL_PROVIDER=smtp|' "${ENV_FILE}"
  else
    echo "EMAIL_PROVIDER=smtp" >> "${ENV_FILE}"
  fi
fi

for var in SMTP_HOST SMTP_PORT SMTP_USER SMTP_FROM_EMAIL; do
  if ! grep -q "^${var}=" "${ENV_FILE}"; then
    case "${var}" in
      SMTP_HOST) echo "SMTP_HOST=smtp.hostinger.com" >> "${ENV_FILE}" ;;
      SMTP_PORT) echo "SMTP_PORT=587" >> "${ENV_FILE}" ;;
      SMTP_USER) echo "SMTP_USER=contacto@daminatoweb.com" >> "${ENV_FILE}" ;;
      SMTP_FROM_EMAIL) echo "SMTP_FROM_EMAIL=contacto@daminatoweb.com" >> "${ENV_FILE}" ;;
    esac
    echo "  Agregado ${var} por defecto."
  fi
done

SMTP_PASS="$(grep '^SMTP_PASSWORD=' "${ENV_FILE}" | cut -d= -f2- | sed 's/^"//;s/"$//;s/^'\''//;s/'\''$//' || true)"
if [[ -z "${SMTP_PASS}" || "${SMTP_PASS}" == *"CAMBIAR"* ]]; then
  echo ""
  echo "  ATENCIÓN: SMTP_PASSWORD no está configurado."
  echo "  Configurá SMTP_PASSWORD (correo contacto@daminatoweb.com en Hostinger) y ejecutá:"
  echo "    SMTP_PASSWORD='tu-password' bash scripts/setup-prod-ops.sh"
  echo "  O editá: nano backend/.env.prod"
  SMTP_OK=0
else
  SMTP_OK=1
  echo "  SMTP_PASSWORD: configurado."
fi

if [[ "${SMTP_OK}" -eq 1 ]]; then
  NEEDS_BACKEND_RESTART=1
fi

echo ""
echo "[1b/5] Verificando REMINDER_BACKGROUND_LOOP..."

if grep -q '^REMINDER_BACKGROUND_LOOP=' "${ENV_FILE}"; then
  if ! grep -q '^REMINDER_BACKGROUND_LOOP=false' "${ENV_FILE}"; then
    NEEDS_BACKEND_RESTART=1
  fi
  sed -i 's|^REMINDER_BACKGROUND_LOOP=.*|REMINDER_BACKGROUND_LOOP=false|' "${ENV_FILE}"
else
  echo "REMINDER_BACKGROUND_LOOP=false" >> "${ENV_FILE}"
  NEEDS_BACKEND_RESTART=1
fi
echo "  REMINDER_BACKGROUND_LOOP=false (cron procesa recordatorios)."

if [[ "${NEEDS_BACKEND_RESTART}" -eq 1 ]]; then
  echo "  Reiniciando backend para aplicar cambios de entorno..."
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --force-recreate backend
  sleep 8
  echo "  Backend reiniciado."
fi

if [[ "${SMTP_OK}" -eq 1 ]]; then
  echo "  Probando login SMTP contra Hostinger..."
  if docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T backend python -c "
from app.core.config import get_settings
from app.integrations.reminders.email_adapter import EmailReminderProvider
EmailReminderProvider(get_settings()).verify_connection()
print('SMTP login OK')
"; then
    echo "  SMTP login OK."
  else
    echo "  ATENCIÓN: login SMTP falló. Revisá usuario/contraseña del correo en Hostinger."
    echo "  Probá: bash scripts/test-smtp.sh tu-email@gmail.com"
    SMTP_OK=0
  fi
fi

# --- 2. Backup manual ---
echo ""
echo "[2/5] Backup manual de PostgreSQL..."
bash scripts/backup-db.sh

# --- 3. Cron diario ---
echo ""
echo "[3/5] Programando cron de backup (3:00 AM)..."
if crontab -l 2>/dev/null | grep -qF 'scripts/backup-db.sh'; then
  echo "  Cron de backup ya existe."
else
  (crontab -l 2>/dev/null || true; echo "${CRON_BACKUP}") | crontab -
  echo "  Cron agregado: ${CRON_BACKUP}"
fi

# --- 3b. Cron recordatorios y resumen diario ---
echo ""
echo "[3b/5] Programando cron de recordatorios y resumen diario..."
if crontab -l 2>/dev/null | grep -qF 'process_reminders.py'; then
  echo "  Cron de recordatorios ya existe."
else
  (crontab -l 2>/dev/null || true; echo "${CRON_REMINDERS}") | crontab -
  echo "  Cron agregado: ${CRON_REMINDERS}"
fi
if crontab -l 2>/dev/null | grep -qF 'send_daily_agenda.py'; then
  echo "  Cron de resumen diario ya existe."
else
  (crontab -l 2>/dev/null || true; echo "${CRON_DIGEST}") | crontab -
  echo "  Cron agregado: ${CRON_DIGEST}"
fi
if crontab -l 2>/dev/null | grep -qF 'extend_indefinite_series.py'; then
  echo "  Cron de turnos fijos continuos ya existe."
else
  (crontab -l 2>/dev/null || true; echo "${CRON_SERIES}") | crontab -
  echo "  Cron agregado: ${CRON_SERIES}"
fi

# --- 4. Health ---
echo ""
echo "[4/5] Health check..."
curl -sf http://127.0.0.1:8000/api/v1/health | head -c 200
echo ""

echo ""
echo "=========================================="
if [[ "${SMTP_OK}" -eq 1 ]]; then
  echo " Listo. Probá: https://app.daminatoweb.com/forgot-password"
else
  echo " Backup y cron OK. Falta SMTP_PASSWORD para forgot-password."
fi
echo "=========================================="
