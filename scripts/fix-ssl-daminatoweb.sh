#!/usr/bin/env bash
# Renueva / emite SSL para daminatoweb.com + www
# Uso: cd /opt/appmedica && sudo bash scripts/fix-ssl-daminatoweb.sh

set -euo pipefail

echo "=== AppMedica — arreglar SSL daminatoweb.com ==="

# Solo daminatoweb.com (no app.daminatoweb.com)
sudo rm -f /etc/nginx/sites-enabled/app.daminatoweb.com.conf
sudo cp /opt/appmedica/nginx/daminatoweb.com.conf /etc/nginx/sites-available/daminatoweb.com.conf
sudo ln -sf /etc/nginx/sites-available/daminatoweb.com.conf /etc/nginx/sites-enabled/daminatoweb.com.conf

echo ""
echo "Certificados actuales:"
sudo certbot certificates || true

echo ""
echo "Emitiendo / reinstalando certificado (Let's Encrypt)..."
if [[ "${1:-}" == "--force-renewal" ]]; then
  sudo certbot --nginx -d daminatoweb.com -d www.daminatoweb.com --force-renewal --non-interactive --redirect
else
  # Tras copiar nginx del repo (solo HTTP), re-aplica el cert existente sin forzar renovación.
  sudo certbot --nginx -d daminatoweb.com -d www.daminatoweb.com --non-interactive --redirect
fi

echo ""
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "Probando HTTPS..."
curl -sI https://daminatoweb.com | head -3 || true
echo ""
echo "Listo. Abrí: https://daminatoweb.com"
