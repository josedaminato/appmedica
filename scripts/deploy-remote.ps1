# Despliega AppMedica en el VPS (app.daminatoweb.com)
# Uso: .\scripts\deploy-remote.ps1
# Requiere: SSH a root@72.60.166.24 (contraseña en hPanel -> VPS -> SSH)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$VpsHost = "72.60.166.24"
$VpsUser = "root"
$VpsPort = 22
$AppUrl = "https://daminatoweb.com"
$EnvLocal = Join-Path $root "backend\.env.prod"
$SshKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"

function Get-SshArgs() {
    $args = @("-p", "$VpsPort")
    if (Test-Path $SshKey) {
        $args += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
    }
    return $args
}

function Invoke-Vps([string]$BashCommand) {
    Write-Host ">> $BashCommand" -ForegroundColor DarkGray
    $sshArgs = Get-SshArgs
    & ssh @sshArgs "${VpsUser}@${VpsHost}" $BashCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Comando remoto falló (código $LASTEXITCODE)."
    }
}

function Invoke-Scp([string]$Local, [string]$Remote) {
    $scpArgs = @()
    if (Test-Path $SshKey) {
        $scpArgs += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
    }
    $scpArgs += @("-P", "$VpsPort", $Local, "${VpsUser}@${VpsHost}:$Remote")
    & scp @scpArgs
    if ($LASTEXITCODE -ne 0) {
        throw "scp falló (código $LASTEXITCODE)."
    }
}

if (-not (Test-Path $EnvLocal)) {
    Write-Host "ERROR: No existe $EnvLocal" -ForegroundColor Red
    Write-Host "Copiá: cp backend/.env.prod.example backend/.env.prod y completá los valores." -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Deploy AppMedica -> $AppUrl ===" -ForegroundColor Cyan
Write-Host "Te pedirá la contraseña SSH del VPS (hPanel -> VPS -> SSH)." -ForegroundColor Yellow
Write-Host "Si falla la contraseña, corré primero: .\scripts\ssh-test.ps1" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "[1/6] Subiendo backend/.env.prod al VPS..." -ForegroundColor White
    Invoke-Scp $EnvLocal "/opt/appmedica/backend/.env.prod"

    Write-Host "[2/6] git pull..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && git pull origin main"

    Write-Host "[3/6] deploy (build + migraciones)..." -ForegroundColor White
    Invoke-Vps "cd /opt/appmedica && bash scripts/deploy.sh"

    Write-Host "[4/6] nginx (daminatoweb.com - landing + AppMedica)..." -ForegroundColor White
    Invoke-Vps "sudo rm -f /etc/nginx/sites-enabled/app.daminatoweb.com.conf"
    Invoke-Vps "sudo cp /opt/appmedica/nginx/daminatoweb.com.conf /etc/nginx/sites-available/daminatoweb.com.conf"
    Invoke-Vps "sudo ln -sf /etc/nginx/sites-available/daminatoweb.com.conf /etc/nginx/sites-enabled/daminatoweb.com.conf"
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
