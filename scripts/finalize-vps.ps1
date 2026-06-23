# UN SOLO PASO: sube .env.prod y reinstala todo en el VPS
# Uso: .\scripts\finalize-vps.ps1
# Te pide la contraseña SSH del VPS (hPanel -> VPS -> SSH)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$Vps = "root@72.60.166.24"
$EnvLocal = Join-Path $root "backend\.env.prod"
$SshKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"

if (-not (Test-Path $EnvLocal)) {
    Write-Host "ERROR: No existe backend\.env.prod" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AppMedica - Finalizar VPS (1 comando)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Esto va a:" -ForegroundColor White
Write-Host "  1. Subir tu .env.prod" -ForegroundColor Gray
Write-Host "  2. Recrear la base de datos (password correcta)" -ForegroundColor Gray
Write-Host "  3. Build + deploy completo" -ForegroundColor Gray
Write-Host "  4. Configurar nginx en daminatoweb.com" -ForegroundColor Gray
Write-Host ""
Write-Host "Contraseña: hPanel -> VPS -> SSH (usuario root)" -ForegroundColor Yellow
Write-Host ""

$scpArgs = @()
$sshArgs = @()
if (Test-Path $SshKey) {
    $scpArgs += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
    $sshArgs += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
}
$scpArgs += @("-P", "22", $EnvLocal, "${Vps}:/opt/appmedica/backend/.env.prod")

Write-Host "[1/2] Subiendo .env.prod..." -ForegroundColor White
& scp @scpArgs
if ($LASTEXITCODE -ne 0) { throw "scp fallo" }

$remote = @'
cd /opt/appmedica && git pull origin main && chmod +x scripts/vps-finish-install.sh && bash scripts/vps-finish-install.sh
'@

Write-Host "[2/2] Instalacion completa en el VPS (5-10 min)..." -ForegroundColor White
& ssh @sshArgs $Vps $remote
if ($LASTEXITCODE -ne 0) { throw "Instalacion fallo" }

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Listo. Proba en el navegador:" -ForegroundColor Green
Write-Host " https://daminatoweb.com" -ForegroundColor Green
Write-Host " https://daminatoweb.com/register" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
