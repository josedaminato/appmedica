# Prueba conexion SSH al VPS Hostinger
# Uso: .\scripts\ssh-test.ps1

$ErrorActionPreference = "Continue"
$VpsHost = "72.60.166.24"
$VpsUser = "root"
$VpsPort = 22
$KeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519"

Write-Host "=== Diagnostico SSH AppMedica ===" -ForegroundColor Cyan
Write-Host "Servidor: ${VpsUser}@${VpsHost}:${VpsPort}" -ForegroundColor White
Write-Host ""

Write-Host "[1] Puerto $VpsPort alcanzable..." -ForegroundColor White
$tcp = Test-NetConnection -ComputerName $VpsHost -Port $VpsPort -WarningAction SilentlyContinue
if ($tcp.TcpTestSucceeded) {
    Write-Host "  OK - el puerto responde." -ForegroundColor Green
} else {
    Write-Host "  FALLO - no hay conexion al puerto $VpsPort." -ForegroundColor Red
    Write-Host "  Revisa firewall en hPanel -> VPS -> Firewall (puerto 22 abierto)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2] Clave SSH local (id_ed25519)..." -ForegroundColor White
if (Test-Path $KeyPath) {
    Write-Host "  Encontrada: $KeyPath" -ForegroundColor Green
    $pub = Get-Content "$KeyPath.pub" -ErrorAction SilentlyContinue
    if ($pub) {
        Write-Host "  Huella: $pub" -ForegroundColor DarkGray
    }
    Write-Host "  Probando login por clave (sin contrasena)..." -ForegroundColor Gray
    & ssh -o BatchMode=yes -o ConnectTimeout=10 -i $KeyPath -o IdentitiesOnly=yes -p $VpsPort "${VpsUser}@${VpsHost}" "echo CLAVE_OK"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK - la clave SSH funciona. Podes usar deploy-remote.ps1 sin contrasena." -ForegroundColor Green
        exit 0
    }
    Write-Host "  La clave NO esta autorizada en el VPS." -ForegroundColor Yellow
} else {
    Write-Host "  No hay clave en $KeyPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3] Login interactivo (contrasena)..." -ForegroundColor White
Write-Host "  IMPORTANTE: usa la contrasena del VPS, NO la del hosting ni del correo." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Donde encontrarla:" -ForegroundColor White
Write-Host "    hPanel -> VPS -> Overview (servidor 1035833) -> Root password / SSH access" -ForegroundColor Gray
Write-Host "    NO uses: hPanel -> Dominios -> SSH (usuario u906481625, puerto 65002)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Si la contrasena falla, reseteala:" -ForegroundColor White
Write-Host "    hPanel -> VPS -> Settings -> Reset root password" -ForegroundColor Gray
Write-Host ""
Write-Host "  Conectando ahora (escribi la contrasena cuando pida Password:)..." -ForegroundColor Cyan
Write-Host ""

& ssh -p $VpsPort "${VpsUser}@${VpsHost}"
$code = $LASTEXITCODE

Write-Host ""
if ($code -eq 0) {
    Write-Host "SSH OK." -ForegroundColor Green
} else {
    Write-Host "SSH fallo (codigo $code)." -ForegroundColor Red
    Write-Host ""
    Write-Host "=== Solucion recomendada: agregar clave SSH en Hostinger ===" -ForegroundColor Cyan
    if (Test-Path "$KeyPath.pub") {
        Write-Host ""
        Write-Host "1. hPanel -> VPS -> SSH keys -> Add SSH key" -ForegroundColor White
        Write-Host "2. Pega esta clave publica:" -ForegroundColor White
        Write-Host ""
        Get-Content "$KeyPath.pub"
        Write-Host ""
        Write-Host "3. Volve a correr: .\scripts\ssh-test.ps1" -ForegroundColor White
        Write-Host ""
        Write-Host "Alternativa sin SSH desde PC: hPanel -> VPS -> Browser terminal" -ForegroundColor Yellow
        Write-Host "  (terminal web en el servidor, sin contrasena desde Windows)" -ForegroundColor Yellow
    }
}

exit $code
