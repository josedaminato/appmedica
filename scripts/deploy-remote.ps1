# Despliega AppMedica en el VPS Hostinger (daminatoweb.com)
# Uso: .\scripts\deploy-remote.ps1

$ErrorActionPreference = "Stop"
$VpsHost = "72.60.166.24"
$VpsUser = "root"

function Invoke-Vps([string]$BashCommand) {
    Write-Host ">> $BashCommand" -ForegroundColor DarkGray
    & ssh "${VpsUser}@${VpsHost}" $BashCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Comando remoto falló (código $LASTEXITCODE)."
    }
}

Write-Host "Conectando a ${VpsUser}@${VpsHost}..." -ForegroundColor Cyan
Write-Host "Password: hPanel -> VPS -> SSH (no la del hosting PHP)." -ForegroundColor Yellow

try {
    Invoke-Vps "cd /opt/appmedica && git pull origin main"
    Invoke-Vps "cd /opt/appmedica && bash scripts/deploy.sh"
    Invoke-Vps "cd /opt/appmedica && bash scripts/setup-prod-ops.sh"
    Invoke-Vps "sudo cp /opt/appmedica/nginx/daminatoweb.com.conf /etc/nginx/sites-available/daminatoweb.com.conf"
    Invoke-Vps "sudo nginx -t && sudo systemctl reload nginx"
    Invoke-Vps "cd /opt/appmedica && bash scripts/prod-smoke-test.sh"
    Write-Host "`nListo. Proba: https://daminatoweb.com" -ForegroundColor Green
}
catch {
    Write-Host "`nFallo: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
