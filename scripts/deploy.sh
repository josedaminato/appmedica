#!/usr/bin/env bash
# AppMedica — deploy / actualización en el VPS
# Ejecutar desde /opt/appmedica: bash scripts/deploy.sh

set -euo pipefail

APP_DIR="/opt/appmedica"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="backend/.env.prod"
GIT_BRANCH="${GIT_BRANCH:-main}"

echo "=========================================="
echo " AppMedica — deploy"
echo "=========================================="

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: No existe ${ENV_FILE}"
  echo "Copiá backend/.env.prod.example y completá los valores."
  exit 1
fi

if [[ -d .git ]]; then
  echo "[1/5] git pull origin ${GIT_BRANCH}..."
  git fetch origin "${GIT_BRANCH}"
  git pull origin "${GIT_BRANCH}"
else
  echo "[1/5] Sin repositorio git — omitiendo pull."
fi

echo ""
echo "[2/5] Build de imágenes (sin caché)..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" build --no-cache

echo ""
echo "[3/5] Levantando contenedores..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

echo ""
echo "[4/5] Migraciones Alembic..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T backend alembic upgrade head

echo ""
echo "[5/5] Estado de contenedores:"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps

echo ""
echo "=========================================="
echo " Deploy finalizado."
echo " Verificá: curl -s https://app.daminatoweb.com/api/v1/health"
echo "=========================================="
