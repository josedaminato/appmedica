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
echo "Emitiendo certificado nuevo (Let's Encrypt)..."
sudo certbot --nginx -d daminatoweb.com -d www.daminatoweb.com --force-renewal

echo ""
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "Probando HTTPS..."
curl -sI https://daminatoweb.com | head -3 || true
echo ""
echo "Listo. Abrí: https://daminatoweb.com"
