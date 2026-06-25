# Sube .env.prod y lanza instalacion en el VPS (sobrevive cortes de SSH)
# Uso: .\scripts\finalize-vps.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$Vps = "root@72.60.166.24"
$EnvLocal = Join-Path $root "backend\.env.prod"
$SshKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$LogFile = "/var/log/appmedica-install.log"

$sshBase = @(
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=120",
    "-o", "TCPKeepAlive=yes"
)
$scpBase = @("-P", "22")

if (Test-Path $SshKey) {
    $sshBase += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
    $scpBase += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
}

function Invoke-Ssh([string]$Command) {
    & ssh @sshBase $Vps $Command
    if ($LASTEXITCODE -ne 0) { throw "SSH fallo (codigo $LASTEXITCODE)" }
}

if (-not (Test-Path $EnvLocal)) {
    Write-Host "ERROR: No existe backend\.env.prod" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AppMedica - Finalizar VPS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Contraseña SSH: hPanel -> VPS -> SSH (usuario root)" -ForegroundColor Yellow
Write-Host ""

Write-Host "[1/3] Subiendo .env.prod..." -ForegroundColor White
& scp @scpBase $EnvLocal "${Vps}:/opt/appmedica/backend/.env.prod"
if ($LASTEXITCODE -ne 0) { throw "scp fallo" }
Write-Host "  OK" -ForegroundColor Green

Write-Host "[2/3] Iniciando instalacion en segundo plano (5-10 min)..." -ForegroundColor White
$startCmd = @"
cd /opt/appmedica && git pull origin main && chmod +x scripts/vps-finish-install.sh && nohup bash scripts/vps-finish-install.sh > $LogFile 2>&1 & echo PID:\$!
"@
Invoke-Ssh $startCmd

Write-Host "[3/3] Esperando resultado (mostrando log)..." -ForegroundColor White
Write-Host ""

$waitCmd = @'
for i in $(seq 1 90); do
  if grep -q 'LISTO PARA VENDER' /var/log/appmedica-install.log 2>/dev/null; then
    tail -30 /var/log/appmedica-install.log
    exit 0
  fi
  if grep -q 'ERROR — revisar logs' /var/log/appmedica-install.log 2>/dev/null; then
    tail -40 /var/log/appmedica-install.log
    exit 1
  fi
  sleep 10
done
echo 'TIMEOUT — ultimas lineas del log:'
tail -40 /var/log/appmedica-install.log
exit 2
'@
& ssh @sshBase $Vps $waitCmd
$code = $LASTEXITCODE

Write-Host ""
if ($code -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " LISTO. Proba:" -ForegroundColor Green
    Write-Host " https://daminatoweb.com" -ForegroundColor Green
    Write-Host " https://daminatoweb.com/register" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    exit 0
}

Write-Host "No termino OK. Conectate al VPS y ejecuta:" -ForegroundColor Yellow
Write-Host "  tail -50 $LogFile" -ForegroundColor Gray
Write-Host "  cd /opt/appmedica && bash scripts/vps-finish-install.sh" -ForegroundColor Gray
exit 1
