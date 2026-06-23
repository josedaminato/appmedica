# Despliega AppMedica en el VPS (app.daminatoweb.com)
# Uso: .\scripts\deploy-remote.ps1
# Requiere: SSH a root@72.60.166.24 (contraseña en hPanel -> VPS -> SSH)

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

if (-not (Test-Path $EnvLocal)) {
    Write-Host "ERROR: No existe $EnvLocal" -ForegroundColor Red
    Write-Host "Copiá: cp backend/.env.prod.example backend/.env.prod y completá los valores." -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Deploy AppMedica -> $AppUrl ===" -ForegroundColor Cyan
Write-Host "Te pedirá la contraseña SSH del VPS (hPanel -> VPS -> SSH)." -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "[1/6] Subiendo backend/.env.prod al VPS..." -ForegroundColor White
    & scp $EnvLocal "${VpsUser}@${VpsHost}:/opt/appmedica/backend/.env.prod"
    if ($LASTEXITCODE -ne 0) { throw "scp falló (código $LASTEXITCODE)." }

    Write-Host "[2/6] git pull..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && git pull origin main"

    Write-Host "[3/6] deploy (build + migraciones)..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && bash scripts/deploy.sh"

    Write-Host "[4/6] nginx (app.daminatoweb.com)..." -ForegroundColor White
    Invoke-Vps "sudo cp /opt/appmedica/nginx/app.daminatoweb.com.conf /etc/nginx/sites-available/app.daminatoweb.com.conf"
    Invoke-Vps "sudo ln -sf /etc/nginx/sites-available/app.daminatoweb.com.conf /etc/nginx/sites-enabled/app.daminatoweb.com.conf"
    Invoke-Vps "sudo nginx -t && sudo systemctl reload nginx"

    Write-Host "[5/6] setup operativo (SMTP, backup, cron)..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && bash scripts/setup-prod-ops.sh"

    Write-Host "[6/6] smoke test..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && BASE_URL=$AppUrl bash scripts/prod-smoke-test.sh"

    Write-Host ""
    Write-Host "Deploy listo. Abrí: $AppUrl" -ForegroundColor Green
    Write-Host "Health: $AppUrl/api/v1/health" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Fallo: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Si dice Permission denied: usá la contraseña del VPS (no la del correo)." -ForegroundColor Yellow
    exit 1
}
