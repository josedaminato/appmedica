#!/usr/bin/env bash
# Backup PostgreSQL de AppMedica (producción)
# Uso en el VPS:
#   cd /opt/appmedica && bash scripts/backup-db.sh
# Cron diario (ej. 3:00 AM):
#   0 3 * * * cd /opt/appmedica && bash scripts/backup-db.sh >> /var/log/appmedica-backup.log 2>&1

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/appmedica}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="backend/.env.prod"
BACKUP_DIR="${BACKUP_DIR:-/opt/appmedica/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: No existe ${ENV_FILE}"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

POSTGRES_USER="${POSTGRES_USER:-appmedica}"
POSTGRES_DB="${POSTGRES_DB:-appmedica}"

mkdir -p "${BACKUP_DIR}"

STAMP="$(date +%F_%H%M%S)"
OUT="${BACKUP_DIR}/appmedica-${STAMP}.sql"

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T db \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "${OUT}"

gzip -f "${OUT}"
echo "Backup: ${OUT}.gz ($(du -h "${OUT}.gz" | cut -f1))"

find "${BACKUP_DIR}" -name 'appmedica-*.sql.gz' -mtime +"${KEEP_DAYS}" -delete 2>/dev/null || true
