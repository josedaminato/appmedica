# Valida backend/.env.prod antes de subir al VPS
# Uso: .\scripts\validate-env-prod.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root "backend\.env.prod"

if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: No existe backend\.env.prod" -ForegroundColor Red
    Write-Host "Copiá: Copy-Item backend\.env.prod.example backend\.env.prod" -ForegroundColor Yellow
    exit 1
}

$content = Get-Content $envFile -Raw
$vars = @{}
foreach ($line in (Get-Content $envFile)) {
    if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
    if ($line -match '^([^=]+)=(.*)$') {
        $vars[$Matches[1].Trim()] = $Matches[2].Trim()
    }
}

$errors = @()
$warnings = @()

function Require-Var([string]$name) {
    if (-not $vars.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($vars[$name])) {
        $script:errors += "Falta $name"
    }
}

function Warn-If([string]$name, [scriptblock]$check) {
    if ($vars.ContainsKey($name) -and (& $check $vars[$name])) {
        $script:warnings += "$name tiene valor por revisar: $($vars[$name])"
    }
}

Require-Var "POSTGRES_PASSWORD"
Require-Var "DATABASE_URL"
Require-Var "JWT_SECRET"
Require-Var "CORS_ORIGINS"
Require-Var "PUBLIC_APP_URL"
Require-Var "VITE_API_URL"
Require-Var "APP_ENV"

Warn-If "POSTGRES_PASSWORD" { param($v) $v -match 'CAMBIAR' }
Warn-If "JWT_SECRET" { param($v) $v.Length -lt 32 -or $v -match 'CAMBIAR' }
Warn-If "SMTP_PASSWORD" { param($v) $v -match 'CAMBIAR' -or [string]::IsNullOrWhiteSpace($v) }
Warn-If "CORS_ORIGINS" { param($v) $v -notmatch 'app\.daminatoweb\.com' }
Warn-If "PUBLIC_APP_URL" { param($v) $v -ne 'https://app.daminatoweb.com' }
Warn-If "VITE_API_URL" { param($v) $v -ne '/api/v1' }
Warn-If "APP_ENV" { param($v) $v -ne 'production' }
Warn-If "SEED_DEMO" { param($v) $v -eq '1' }
Warn-If "REMINDER_BACKGROUND_LOOP" { param($v) $v -ne 'false' }

Write-Host "=== Validacion backend/.env.prod ===" -ForegroundColor Cyan

if ($errors.Count -gt 0) {
    foreach ($e in $errors) { Write-Host "ERROR: $e" -ForegroundColor Red }
}
if ($warnings.Count -gt 0) {
    foreach ($w in $warnings) { Write-Host "AVISO: $w" -ForegroundColor Yellow }
}

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "OK - listo para subir al VPS." -ForegroundColor Green
    exit 0
}

if ($errors.Count -eq 0) {
    Write-Host ""
    Write-Host "Sin errores bloqueantes. Revisa los avisos antes de vender." -ForegroundColor Yellow
    exit 0
}

exit 1
