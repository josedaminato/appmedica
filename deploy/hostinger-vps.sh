#!/usr/bin/env bash
# Despliegue en Hostinger VPS (Ubuntu/Debian con Docker)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no instalado. En Hostinger VPS: hPanel → VPS → Docker, o:"
  echo "  curl -fsSL https://get.docker.com | sh"
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.production.example .env
  echo "Creado .env — EDITÁ JWT_SECRET, POSTGRES_PASSWORD y PUBLIC_URL antes de continuar."
  exit 1
fi

echo "=== AppMedica — build y deploy producción ==="
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "Listo. Verificá:"
echo "  curl -s http://127.0.0.1/api/v1/health"
echo ""
echo "Abrí en el navegador: \${PUBLIC_URL:-http://TU-IP}"
echo "Swagger (si APP_ENV != production): /docs"
