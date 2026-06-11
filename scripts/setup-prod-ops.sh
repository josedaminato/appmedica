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
CRON_LINE='0 3 * * * cd /opt/appmedica && bash scripts/backup-db.sh >> /var/log/appmedica-backup.log 2>&1'

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: No existe ${ENV_FILE}"
  exit 1
fi

echo "=========================================="
echo " AppMédica — setup operativo (prod)"
echo "=========================================="

# --- 1. SMTP ---
echo ""
echo "[1/4] Verificando SMTP..."

if [[ -n "${SMTP_PASSWORD:-}" ]]; then
  if grep -q '^SMTP_PASSWORD=' "${ENV_FILE}"; then
    sed -i "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=${SMTP_PASSWORD}|" "${ENV_FILE}"
    echo "  SMTP_PASSWORD actualizado desde variable de entorno."
  else
    echo "SMTP_PASSWORD=${SMTP_PASSWORD}" >> "${ENV_FILE}"
    echo "  SMTP_PASSWORD agregado al .env.prod."
  fi
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
      SMTP_USER) echo "SMTP_USER=noreply@daminatoweb.com" >> "${ENV_FILE}" ;;
      SMTP_FROM_EMAIL) echo "SMTP_FROM_EMAIL=noreply@daminatoweb.com" >> "${ENV_FILE}" ;;
    esac
    echo "  Agregado ${var} por defecto."
  fi
done

SMTP_PASS="$(grep '^SMTP_PASSWORD=' "${ENV_FILE}" | cut -d= -f2- || true)"
if [[ -z "${SMTP_PASS}" || "${SMTP_PASS}" == *"CAMBIAR"* ]]; then
  echo ""
  echo "  ATENCIÓN: SMTP_PASSWORD no está configurado."
  echo "  Creá el correo noreply@daminatoweb.com en Hostinger y ejecutá:"
  echo "    SMTP_PASSWORD='tu-password' bash scripts/setup-prod-ops.sh"
  echo "  O editá: nano backend/.env.prod"
  SMTP_OK=0
else
  SMTP_OK=1
  echo "  SMTP_PASSWORD: configurado."
fi

if [[ "${SMTP_OK}" -eq 1 ]]; then
  echo "  Reiniciando backend para aplicar SMTP..."
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --force-recreate backend
  sleep 3
  echo "  Backend reiniciado."
fi

# --- 2. Backup manual ---
echo ""
echo "[2/4] Backup manual de PostgreSQL..."
bash scripts/backup-db.sh

# --- 3. Cron diario ---
echo ""
echo "[3/4] Programando cron de backup (3:00 AM)..."
if crontab -l 2>/dev/null | grep -qF 'scripts/backup-db.sh'; then
  echo "  Cron de backup ya existe."
else
  (crontab -l 2>/dev/null || true; echo "${CRON_LINE}") | crontab -
  echo "  Cron agregado: ${CRON_LINE}"
fi

# --- 4. Health ---
echo ""
echo "[4/4] Health check..."
curl -sf http://127.0.0.1:8000/api/v1/health | head -c 200
echo ""

echo ""
echo "=========================================="
if [[ "${SMTP_OK}" -eq 1 ]]; then
  echo " Listo. Probá: https://daminatoweb.com/forgot-password"
else
  echo " Backup y cron OK. Falta SMTP_PASSWORD para forgot-password."
fi
echo "=========================================="
