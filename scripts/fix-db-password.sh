#!/usr/bin/env bash
# Sincroniza la contraseña de PostgreSQL con backend/.env.prod
#
# Uso en el VPS:
#   cd /opt/appmedica && bash scripts/fix-db-password.sh
#
# Si falla, recrear volumen (borra datos):
#   RESET_DB_VOLUME=1 bash scripts/fix-db-password.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/appmedica}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="backend/.env.prod"
DEFAULT_OLD_PASSWORD="appmedica_secret"

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: No existe ${ENV_FILE}"
  exit 1
fi

POSTGRES_USER="$(grep '^POSTGRES_USER=' "${ENV_FILE}" | cut -d= -f2- | tr -d '\r')"
POSTGRES_PASSWORD="$(grep '^POSTGRES_PASSWORD=' "${ENV_FILE}" | cut -d= -f2- | tr -d '\r')"
POSTGRES_DB="$(grep '^POSTGRES_DB=' "${ENV_FILE}" | cut -d= -f2- | tr -d '\r')"

if [[ -z "${POSTGRES_USER}" || -z "${POSTGRES_PASSWORD}" || -z "${POSTGRES_DB}" ]]; then
  echo "ERROR: POSTGRES_USER, POSTGRES_PASSWORD o POSTGRES_DB vacíos en ${ENV_FILE}"
  exit 1
fi

reset_volume() {
  echo ""
  echo "=== Recreando volumen PostgreSQL (datos anteriores se pierden) ==="
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" down
  docker volume rm -f appmedica_postgres_data 2>/dev/null || true
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d db
  echo "Esperando PostgreSQL..."
  sleep 8
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build backend
  sleep 15
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T backend alembic upgrade head
}

align_database_url() {
  local new_url="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
  if grep -q '^DATABASE_URL=' "${ENV_FILE}"; then
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${new_url}|" "${ENV_FILE}"
  else
    echo "DATABASE_URL=${new_url}" >> "${ENV_FILE}"
  fi
}

try_alter_password() {
  local try_password="${1:-}"
  if [[ -n "${try_password}" ]]; then
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T \
      -e PGPASSWORD="${try_password}" db \
      psql -h 127.0.0.1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 \
      -c "ALTER USER \"${POSTGRES_USER}\" WITH PASSWORD '${POSTGRES_PASSWORD}';"
  else
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T db \
      psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 \
      -c "ALTER USER \"${POSTGRES_USER}\" WITH PASSWORD '${POSTGRES_PASSWORD}';"
  fi
}

health_ok() {
  local health
  health="$(curl -sf http://127.0.0.1:8000/api/v1/health 2>/dev/null || echo FAIL)"
  echo "${health}"
  echo "${health}" | grep -q '"database":"ok"'
}

if [[ "${RESET_DB_VOLUME:-0}" == "1" ]]; then
  reset_volume
  align_database_url
  if health_ok; then
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d frontend
    echo "OK — base nueva creada."
    exit 0
  fi
  echo "ERROR tras reset. Ver logs del backend."
  exit 1
fi

echo "=== AppMedica — sincronizar password PostgreSQL ==="
echo "Usuario: ${POSTGRES_USER}"
echo "Base:    ${POSTGRES_DB}"
echo ""

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d db
sleep 3

echo "[1/3] Intentando ALTER USER (socket local)..."
if try_alter_password ""; then
  echo "  OK con socket local."
else
  echo "  Falló socket local. Probando password por defecto (${DEFAULT_OLD_PASSWORD})..."
  if ! try_alter_password "${DEFAULT_OLD_PASSWORD}"; then
    echo ""
    echo "No se pudo cambiar la password. Opciones:"
    echo "  1) Recrear volumen (sin datos importantes): RESET_DB_VOLUME=1 bash scripts/fix-db-password.sh"
    echo "  2) Si recordás la password vieja: PGPASSWORD='vieja' docker compose ... exec db psql ..."
    exit 1
  fi
  echo "  OK con password anterior por defecto."
fi

align_database_url

echo "[2/3] Recrear backend..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --force-recreate backend
sleep 12

echo "[3/3] Migraciones..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T backend alembic upgrade head

echo ""
HEALTH="$(health_ok && curl -sf http://127.0.0.1:8000/api/v1/health || echo FAIL)"
echo "Health: ${HEALTH}"

if echo "${HEALTH}" | grep -q '"database":"ok"'; then
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d frontend
  echo "OK — base de datos conectada."
  exit 0
fi

echo ""
echo "Sigue fallando. Si no hay clientes reales en la DB, ejecutá:"
echo "  RESET_DB_VOLUME=1 bash scripts/fix-db-password.sh"
exit 1
