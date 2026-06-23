#!/usr/bin/env bash
# Instalación / reparación completa en el VPS — una sola ejecución
# Uso: cd /opt/appmedica && bash scripts/vps-finish-install.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/appmedica}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="backend/.env.prod"

cd "${APP_DIR}"

echo "=========================================="
echo " AppMedica — instalación completa VPS"
echo "=========================================="

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Falta ${ENV_FILE}"
  echo "Copiá desde tu PC: scp backend/.env.prod root@VPS:/opt/appmedica/backend/.env.prod"
  exit 1
fi

echo ""
echo "[1/8] git pull..."
git pull origin main

echo ""
echo "[2/8] Recrear PostgreSQL (password alineada con .env.prod)..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" down || true
docker volume rm -f appmedica_postgres_data 2>/dev/null || true

POSTGRES_USER="$(grep '^POSTGRES_USER=' "${ENV_FILE}" | cut -d= -f2- | tr -d '\r')"
POSTGRES_PASSWORD="$(grep '^POSTGRES_PASSWORD=' "${ENV_FILE}" | cut -d= -f2- | tr -d '\r')"
POSTGRES_DB="$(grep '^POSTGRES_DB=' "${ENV_FILE}" | cut -d= -f2- | tr -d '\r')"
NEW_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
if grep -q '^DATABASE_URL=' "${ENV_FILE}"; then
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${NEW_URL}|" "${ENV_FILE}"
fi

# URLs producción — landing + AppMedica en daminatoweb.com
set_env() {
  local k="$1" v="$2"
  if grep -q "^${k}=" "${ENV_FILE}"; then
    sed -i "s|^${k}=.*|${k}=${v}|" "${ENV_FILE}"
  else
    echo "${k}=${v}" >> "${ENV_FILE}"
  fi
}
set_env "CORS_ORIGINS" "https://daminatoweb.com,https://www.daminatoweb.com"
set_env "PUBLIC_APP_URL" "https://daminatoweb.com"
set_env "VITE_API_URL" "/api/v1"
set_env "APP_ENV" "production"
set_env "REMINDER_BACKGROUND_LOOP" "false"
set_env "SEED_DEMO" "0"

echo ""
echo "[3/8] Build y levantar servicios..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build
echo "Esperando backend..."
sleep 25

echo ""
echo "[4/8] Migraciones..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T backend alembic upgrade head

echo ""
echo "[5/8] Nginx (solo daminatoweb.com)..."
sudo rm -f /etc/nginx/sites-enabled/app.daminatoweb.com.conf
sudo cp nginx/daminatoweb.com.conf /etc/nginx/sites-available/daminatoweb.com.conf
sudo ln -sf /etc/nginx/sites-available/daminatoweb.com.conf /etc/nginx/sites-enabled/daminatoweb.com.conf
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "[6/8] Cron + backup + SMTP check..."
bash scripts/setup-prod-ops.sh || true

echo ""
echo "[7/8] Health check..."
HEALTH="$(curl -sf http://127.0.0.1:8000/api/v1/health || echo FAIL)"
echo "${HEALTH}"

echo ""
echo "[8/8] Estado contenedores..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps

echo ""
echo "=========================================="
if echo "${HEALTH}" | grep -q '"database":"ok"'; then
  echo " LISTO PARA VENDER"
  echo " https://daminatoweb.com"
  echo " https://daminatoweb.com/register"
  echo ""
  echo " Si HTTPS falla, ejecutá una vez:"
  echo "   sudo certbot --nginx -d daminatoweb.com -d www.daminatoweb.com"
else
  echo " ERROR — revisar logs:"
  echo "   docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE} logs backend --tail=40"
  exit 1
fi
echo "=========================================="
