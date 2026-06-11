# Checklist operativo en el VPS (SMTP + backup + deploy + smoke test)
# Uso:
#   .\scripts\run-prod-checklist.ps1
#   .\scripts\run-prod-checklist.ps1 -SmtpPassword 'password-del-correo-noreply'
#
# Requiere SSH interactivo a root@72.60.166.24 (contraseña hPanel → VPS → SSH)

param(
    [string]$SmtpPassword = ""
)

$VpsHost = "72.60.166.24"

$smtpPart = if ($SmtpPassword) {
    "SMTP_PASSWORD='$($SmtpPassword.Replace("'", "'\''"))' bash scripts/setup-prod-ops.sh"
} else {
    "bash scripts/setup-prod-ops.sh"
}

$RemoteCmd = @"
set -e
cd /opt/appmedica
git pull origin main
bash scripts/deploy.sh
$smtpPart
bash scripts/prod-smoke-test.sh
"@

Write-Host "=== Checklist producción AppMédica ===" -ForegroundColor Cyan
Write-Host "1. Deploy (git pull + build)" -ForegroundColor White
Write-Host "2. SMTP + backup manual + cron" -ForegroundColor White
Write-Host "3. Smoke test API" -ForegroundColor White
Write-Host ""
if (-not $SmtpPassword) {
    Write-Host "Sin -SmtpPassword: el script te avisará si falta la contraseña SMTP." -ForegroundColor Yellow
    Write-Host "Ejemplo: .\scripts\run-prod-checklist.ps1 -SmtpPassword 'tu-password'" -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "Conectando a root@${VpsHost}..." -ForegroundColor Cyan

ssh root@$VpsHost $RemoteCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Listo. Probá en el navegador:" -ForegroundColor Green
    Write-Host "  https://daminatoweb.com/forgot-password (email real de un usuario)" -ForegroundColor Green
    Write-Host "  Checklist §8: registro → OS → paciente → turno → cierre → cobro → export" -ForegroundColor Green
} else {
    Write-Host "Falló. Revisá SSH y /opt/appmedica en el VPS." -ForegroundColor Red
    exit 1
}
