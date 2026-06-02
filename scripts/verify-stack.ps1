# Verificación de estabilidad AppMedica
# Uso: .\scripts\verify-stack.ps1

$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host "`n=== docker compose ps ===" -ForegroundColor Cyan
docker compose ps

Write-Host "`n=== backend logs (tail 30) ===" -ForegroundColor Cyan
docker compose logs backend --tail=30

Write-Host "`n=== frontend logs (tail 30) ===" -ForegroundColor Cyan
docker compose logs frontend --tail=30

Write-Host "`n=== alembic current ===" -ForegroundColor Cyan
docker compose exec -T backend alembic current

Write-Host "`n=== alembic upgrade head ===" -ForegroundColor Cyan
docker compose exec -T backend alembic upgrade head

Write-Host "`n=== seed demo ===" -ForegroundColor Cyan
docker compose exec -T backend python scripts/seed_demo.py

Write-Host "`n=== health check ===" -ForegroundColor Cyan
$apiPort = 8000
if (Test-Path "$root\.env") {
    $m = Select-String -Path "$root\.env" -Pattern "^BACKEND_HOST_PORT=(\d+)" | Select-Object -First 1
    if ($m) { $apiPort = [int]$m.Matches.Groups[1].Value }
}
$healthUrl = "http://127.0.0.1:$apiPort/api/v1/health"
Write-Host "API port: $apiPort" -ForegroundColor Gray
try {
    $h = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10
    Write-Host "OK $($h | ConvertTo-Json -Compress)"
} catch {
    Write-Host "FAIL health: $($_.Exception.Message)" -ForegroundColor Red
}
$env:API_BASE_URL = "http://127.0.0.1:$apiPort/api/v1"

Write-Host "`n=== test_core_flow.py ===" -ForegroundColor Cyan
docker compose exec -T backend python scripts/test_core_flow.py
$code = $LASTEXITCODE
Write-Host "`nExit code: $code" -ForegroundColor $(if ($code -eq 0) { "Green" } else { "Red" })
exit $code
