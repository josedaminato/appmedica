# AppMedica - Script de inicio (Windows)
# Uso: .\start.ps1
# Opciones:
#   .\start.ps1 -DockerAll     # db + backend + frontend en Docker
#   .\start.ps1 -LocalFrontend # db + backend Docker, frontend con npm local

param(
    [switch]$DockerAll,
    [switch]$LocalFrontend
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=== AppMedica ===" -ForegroundColor Cyan

# 1. Verificar Docker
$dockerOk = $false
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $dockerOk = $true }
} catch {}

if (-not $dockerOk) {
    Write-Host "Docker no esta corriendo. Iniciando Docker Desktop..." -ForegroundColor Yellow
    $dockerExe = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerExe) {
        Start-Process $dockerExe
        $i = 0
        while ($i -lt 36) {
            Start-Sleep -Seconds 5
            docker info 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { $dockerOk = $true; break }
            $i++
            Write-Host "  Esperando Docker... ($i)"
        }
    }
}

if (-not $dockerOk) {
    Write-Host "ERROR: Inicia Docker Desktop manualmente y vuelve a ejecutar este script." -ForegroundColor Red
    exit 1
}

# 2. .env
if (-not (Test-Path "$root\.env")) {
    Copy-Item "$root\.env.example" "$root\.env"
    Write-Host "Creado .env desde .env.example"
}
if (-not (Test-Path "$root\frontend\.env")) {
    Copy-Item "$root\frontend\.env.example" "$root\frontend\.env"
    Write-Host "Creado frontend/.env desde .env.example"
}

Set-Location $root

if ($DockerAll) {
    Write-Host "Levantando db + backend + frontend (Docker)..." -ForegroundColor Green
    docker compose up -d --build
} else {
    Write-Host "Levantando db + backend (Docker)..." -ForegroundColor Green
    docker compose up db backend -d --build
}

Write-Host "Esperando API..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host "ERROR: El backend no respondio. Revisa: docker compose logs backend --tail=50" -ForegroundColor Red
    exit 1
}
Write-Host "Backend listo." -ForegroundColor Green

if ($DockerAll) {
    Write-Host "Esperando frontend Docker..." -ForegroundColor Yellow
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { break }
        } catch {}
        Start-Sleep -Seconds 2
    }
} elseif (-not $LocalFrontend) {
    Write-Host "Iniciando frontend local (npm)..." -ForegroundColor Green
    if (-not (Test-Path "$root\frontend\node_modules")) {
        Push-Location "$root\frontend"
        npm install
        Pop-Location
    }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
    Start-Sleep -Seconds 4
}

Write-Host ""
Write-Host "Listo! Abri en el navegador:" -ForegroundColor Green
Write-Host "  App:      http://localhost:5173  (o http://127.0.0.1:5173)" -ForegroundColor White
Write-Host "  API:      http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Cuenta demo (tests y pruebas):" -ForegroundColor Cyan
Write-Host "  Email:    demo@consultorio.com" -ForegroundColor White
Write-Host "  Password: demo12345" -ForegroundColor White
Write-Host ""
Write-Host "Validar flujo: docker compose exec backend python scripts/test_core_flow.py" -ForegroundColor Cyan
