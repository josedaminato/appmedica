#!/usr/bin/env bash
# Actualizacion rapida en el VPS (git pull + build + migraciones)
# Uso en terminal del VPS: cd /opt/appmedica && bash scripts/vps-update.sh

set -euo pipefail
cd /opt/appmedica
git pull origin main
bash scripts/deploy.sh
curl -fsS https://daminatoweb.com/api/v1/health && echo ""
