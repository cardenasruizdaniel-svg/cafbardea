# Build CafBarDLA Windows Installer using Inno Setup
# Este script compila el instalador .exe desde el script .iss

param(
    [string]$InnoSetupPath = "C:\Program Files (x86)\Inno Setup 6"
)

Write-Host "🔨 Construyendo instalador CafBarDLA..." -ForegroundColor Cyan

# Validar que Inno Setup esté instalado
if (-not (Test-Path "$InnoSetupPath\ISCC.exe")) {
    Write-Host "❌ Error: Inno Setup no encontrado en: $InnoSetupPath" -ForegroundColor Red
    Write-Host "Descarga desde: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 1
}

# Path del proyecto
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$InstallerScript = "$ProjectRoot\installer\CafBarDLA.iss"
$OutputDir = "$ProjectRoot\installer\Output"

# Crear directorio de salida
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Opciones para compilar en modo producción
$BuildOptions = @(
    "/O`"$OutputDir`"",  # Output directory
    "/F`"CafBarDLA-Setup`"",  # Output filename (sin .exe)
    "/DAppName=CafBarDLA POS",
    "/DAppVersion=0.1.0",
    "/DAppPublisher=DLA Tecnología"
)

Write-Host "📋 Configuración:" -ForegroundColor Green
Write-Host "  Script: $InstallerScript"
Write-Host "  Salida: $OutputDir"
Write-Host ""

# Advertencia: requiere dist\CafBarDLA\CafBarDLA.exe
$ExePath = "$ProjectRoot\dist\CafBarDLA\CafBarDLA.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "⚠️  ADVERTENCIA: Ejecutable no encontrado en $ExePath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Opciones para generar el ejecutable:" -ForegroundColor Cyan
    Write-Host "1️⃣  Usar PyInstaller (requiere Python sin memoria limitada):"
    Write-Host "   python -m PyInstaller launcher.py --onefile --windowed --name CafBarDLA"
    Write-Host ""
    Write-Host "2️⃣  Usar servidor FastAPI directamente (sin instalador):"
    Write-Host "   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
    Write-Host ""
    Write-Host "¿Deseas continuar igualmente? (s/n)"
    $continue = Read-Host
    if ($continue -ne "s") { exit 0 }
}

Write-Host "🚀 Compilando instalador..." -ForegroundColor Cyan
Write-Host ""

# Compilar el instalador
& "$InnoSetupPath\ISCC.exe" $BuildOptions $InstallerScript

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Instalador compilado exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 Ubicación: $OutputDir\CafBarDLA-Setup.exe" -ForegroundColor Green
    Write-Host ""
    Write-Host "Puedes distribuir este archivo .exe a los usuarios." -ForegroundColor Yellow
    
    # Mostrar información del archivo
    $SetupExe = "$OutputDir\CafBarDLA-Setup.exe"
    if (Test-Path $SetupExe) {
        $FileInfo = Get-Item $SetupExe
        Write-Host "Tamaño: $([math]::Round($FileInfo.Length / 1MB, 2)) MB" -ForegroundColor Gray
        Write-Host "Fecha: $($FileInfo.LastWriteTime)" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "❌ Error compilando instalador (código: $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
