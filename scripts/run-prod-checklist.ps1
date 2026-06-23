# Checklist operativo en el VPS (env + deploy + SMTP + smoke test)
# Uso:
#   .\scripts\run-prod-checklist.ps1
#   .\scripts\run-prod-checklist.ps1 -SmtpPassword 'tu-password-correo'
#
# Requiere SSH interactivo a root@72.60.166.24 (contraseña hPanel -> VPS -> SSH)

param(
    [string]$SmtpPassword = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$VpsHost = "72.60.166.24"
$VpsUser = "root"
$AppUrl = "https://app.daminatoweb.com"
$EnvLocal = Join-Path $root "backend\.env.prod"

function Invoke-Vps([string]$BashCommand) {
    Write-Host ">> $BashCommand" -ForegroundColor DarkGray
    & ssh "${VpsUser}@${VpsHost}" $BashCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Comando remoto falló (código $LASTEXITCODE)."
    }
}

Write-Host "=== Checklist produccion AppMedica ===" -ForegroundColor Cyan
Write-Host "URL: $AppUrl" -ForegroundColor White
Write-Host ""
if (-not $SmtpPassword) {
    Write-Host "Sin -SmtpPassword: el script avisara si falta la contraseña SMTP." -ForegroundColor Yellow
    Write-Host "Ejemplo: .\scripts\run-prod-checklist.ps1 -SmtpPassword 'tu-password'" -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "Te pedirá la contraseña SSH del VPS." -ForegroundColor Yellow
Write-Host ""

if (-not (Test-Path $EnvLocal)) {
    Write-Host "ERROR: No existe $EnvLocal" -ForegroundColor Red
    exit 1
}

try {
    Write-Host "[1/5] Subiendo backend/.env.prod..." -ForegroundColor White
    & scp $EnvLocal "${VpsUser}@${VpsHost}:/opt/appmedica/backend/.env.prod"
    if ($LASTEXITCODE -ne 0) { throw "scp falló." }

    Write-Host "[2/5] git pull + deploy..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && git pull origin main"
    Invoke-Vps "cd /opt/appmedica && bash scripts/deploy.sh"

    Write-Host "[3/5] setup operativo..." -ForegroundColor White
    if ($SmtpPassword) {
        $escaped = $SmtpPassword.Replace("'", "'\''")
        Invoke-Vps "cd /opt/appmedica && SMTP_PASSWORD='$escaped' bash scripts/setup-prod-ops.sh"
    } else {
        Invoke-Vps "cd /opt/appmedica && bash scripts/setup-prod-ops.sh"
    }

    Write-Host "[4/5] smoke test..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && BASE_URL=$AppUrl bash scripts/prod-smoke-test.sh"

    Write-Host ""
    Write-Host "Listo. Proba en el navegador:" -ForegroundColor Green
    Write-Host "  $AppUrl/register" -ForegroundColor Green
    Write-Host "  $AppUrl/forgot-password (email real; requiere SMTP_PASSWORD)" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Fallo: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Si SSH dice Permission denied, la clave es la del VPS en Hostinger (no la del correo)." -ForegroundColor Yellow
    exit 1
}
