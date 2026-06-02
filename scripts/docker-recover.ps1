# Recuperar Docker cuando appmedica-backend queda trabado
# Uso: .\scripts\docker-recover.ps1

$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

function Test-BackendPort([int]$Port) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/v1/health" -UseBasicParsing -TimeoutSec 3
        return $r.StatusCode -eq 200
    } catch { return $false }
}

Write-Host "=== AppMedica — recuperación Docker ===" -ForegroundColor Cyan

Write-Host "`nContenedores:" -ForegroundColor Yellow
docker ps -a --filter "name=appmedica" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"

$zombie = docker ps -q --filter "name=appmedica-backend" 2>$null
if ($zombie) {
    Write-Host "`nIntentando eliminar contenedor zombie..." -ForegroundColor Yellow
    docker rm -f appmedica-backend 2>$null
    docker rm -f $zombie 2>$null
}

docker compose down --remove-orphans 2>&1 | Out-Host

$envFile = Join-Path $root ".env"
$envContent = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
if (-not $envContent) { Copy-Item (Join-Path $root ".env.example") $envFile; $envContent = Get-Content $envFile -Raw }

$usePort = 8000
if ($zombie -or -not (Test-BackendPort 8000)) {
    # Puerto 8000 ocupado o zombie: levantar en 8001
    $usePort = 8001
    Write-Host "`nPuerto 8000 no disponible. Usando puerto $usePort ..." -ForegroundColor Yellow
    $envContent = $envContent -replace "(?m)^BACKEND_HOST_PORT=.*", "BACKEND_HOST_PORT=$usePort"
    if ($envContent -notmatch "BACKEND_HOST_PORT=") { $envContent += "`nBACKEND_HOST_PORT=$usePort`n" }
    $envContent = $envContent -replace "(?m)^VITE_API_URL=.*", "VITE_API_URL=http://localhost:$usePort/api/v1"
    if ($envContent -notmatch "VITE_API_URL=") { $envContent += "`nVITE_API_URL=http://localhost:$usePort/api/v1`n" }
    Set-Content -Path $envFile -Value $envContent.TrimEnd() -NoNewline
    Add-Content -Path $envFile -Value ""
    $feEnv = Join-Path $root "frontend\.env"
    if (-not (Test-Path $feEnv)) { Copy-Item (Join-Path $root "frontend\.env.example") $feEnv }
    Set-Content -Path $feEnv -Value "VITE_API_URL=http://localhost:$usePort/api/v1"
}

Write-Host "`nLevantando stack (puerto API: $usePort)..." -ForegroundColor Green
docker compose up -d --build 2>&1 | Out-Host

Write-Host "`nEsperando API..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    if (Test-BackendPort $usePort) { $ready = $true; break }
    Start-Sleep -Seconds 2
}

docker compose ps

if ($ready) {
    Write-Host "`nOK API en http://127.0.0.1:$usePort/docs" -ForegroundColor Green
    Write-Host "App: http://127.0.0.1:5173" -ForegroundColor Green
    if ($usePort -ne 8000) {
        Write-Host "`nNota: API en puerto $usePort porque 8000 está bloqueado." -ForegroundColor Yellow
        Write-Host "Para liberar 8000: Quit Docker Desktop -> Reiniciar PC -> docker rm -f appmedica-backend" -ForegroundColor Yellow
    }
    Write-Host "`nSiguiente paso: .\scripts\verify-stack.ps1" -ForegroundColor Cyan
    exit 0
}

Write-Host "`nERROR: API no respondió. Logs:" -ForegroundColor Red
docker compose logs backend --tail=40
Write-Host "`nProbá: reiniciar la PC, luego docker rm -f appmedica-backend" -ForegroundColor Yellow
exit 1
