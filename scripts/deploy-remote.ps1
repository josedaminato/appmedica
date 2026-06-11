# Despliega AppMedica en el VPS Hostinger (daminatoweb.com)
# Uso: .\scripts\deploy-remote.ps1
# Requiere: SSH a root@72.60.166.24 (clave "PC José" o contraseña de hPanel → VPS)

$VpsHost = "72.60.166.24"
$RemoteCmd = @"
set -e
cd /opt/appmedica
git pull origin main
bash scripts/deploy.sh
bash scripts/setup-prod-ops.sh
sudo cp nginx/daminatoweb.com.conf /etc/nginx/sites-available/daminatoweb.com.conf
sudo nginx -t && sudo systemctl reload nginx
bash scripts/prod-smoke-test.sh
"@

Write-Host "Conectando a root@${VpsHost}..." -ForegroundColor Cyan
Write-Host "Si pedis contraseña, usá la de hPanel -> VPS -> SSH (no la del hosting PHP)." -ForegroundColor Yellow
ssh root@$VpsHost $RemoteCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nListo. Probá: https://daminatoweb.com" -ForegroundColor Green
} else {
    Write-Host "`nFalló SSH o el deploy. Revisá credenciales y que exista /opt/appmedica en el VPS." -ForegroundColor Red
    exit 1
}
