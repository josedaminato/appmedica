# Checklist operativo en el VPS (SMTP + backup + deploy + smoke test)
# Uso:
#   .\scripts\run-prod-checklist.ps1
#   .\scripts\run-prod-checklist.ps1 -SmtpPassword 'tu-password-correo'
#
# Requiere SSH interactivo a root@72.60.166.24 (contraseña hPanel -> VPS -> SSH)

param(
    [string]$SmtpPassword = ""
)

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

Write-Host "=== Checklist produccion AppMedica ===" -ForegroundColor Cyan
Write-Host "1. Deploy (git pull + build)" -ForegroundColor White
Write-Host "2. SMTP + backup manual + cron" -ForegroundColor White
Write-Host "3. Smoke test API" -ForegroundColor White
Write-Host ""
if (-not $SmtpPassword) {
    Write-Host "Sin -SmtpPassword: el script avisara si falta la contraseña SMTP." -ForegroundColor Yellow
    Write-Host "Ejemplo: .\scripts\run-prod-checklist.ps1 -SmtpPassword 'tu-password'" -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "Conectando a ${VpsUser}@${VpsHost}..." -ForegroundColor Cyan
Write-Host "Password: la del VPS (hPanel -> VPS -> SSH), no la del correo." -ForegroundColor Yellow
Write-Host ""

try {
    Invoke-Vps "cd /opt/appmedica && git pull origin main"
    Invoke-Vps "cd /opt/appmedica && bash scripts/deploy.sh"

    if ($SmtpPassword) {
        $escaped = $SmtpPassword.Replace("'", "'\''")
        Invoke-Vps "cd /opt/appmedica && SMTP_PASSWORD='$escaped' bash scripts/setup-prod-ops.sh"
    } else {
        Invoke-Vps "cd /opt/appmedica && bash scripts/setup-prod-ops.sh"
    }

    Invoke-Vps "cd /opt/appmedica && bash scripts/prod-smoke-test.sh"

    Write-Host ""
    Write-Host "Listo. Proba en el navegador:" -ForegroundColor Green
    Write-Host "  https://daminatoweb.com/forgot-password (email real de un usuario)" -ForegroundColor Green
    Write-Host "  Checklist: registro -> OS -> paciente -> turno -> cierre -> cobro -> export" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Fallo: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Si SSH dice Permission denied, la clave es la del VPS en Hostinger (no la del correo)." -ForegroundColor Yellow
    exit 1
}
