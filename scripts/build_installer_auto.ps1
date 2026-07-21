# Script para compilar instalador CafBarDLA .exe
# Requiere: Inno Setup (se instala automáticamente si no existe)

param(
    [switch]$SkipInnoSetup = $false
)

$ErrorActionPreference = "Stop"

# Paths
$InnoSetupUrl = "https://jrsoftware.org/files/is/6/innosetup-6.2.2.exe"
$InnoSetupPath = "$env:ProgramFiles (x86)\Inno Setup 6"
$IsccExe = "$InnoSetupPath\ISCC.exe"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$IssScript = "$ProjectRoot\installer\CafBarDLA.iss"
$OutputDir = "$ProjectRoot\installer\Output"

Write-Host "`n" + ("="*60) -ForegroundColor Cyan
Write-Host "🔨 Constructor de Instalador CafBarDLA" -ForegroundColor Cyan
Write-Host ("="*60) -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# PASO 1: Verificar/Instalar Inno Setup
# ============================================================================

Write-Host "[PASO 1/3] Verificar Inno Setup..." -ForegroundColor Yellow

if (Test-Path $IsccExe) {
    Write-Host "✓ Inno Setup encontrado en: $InnoSetupPath`n" -ForegroundColor Green
} else {
    if ($SkipInnoSetup) {
        Write-Host "❌ ERROR: Inno Setup no encontrado`n" -ForegroundColor Red
        Write-Host "Descargue desde: https://jrsoftware.org/isdl.php`n" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "⚠ Inno Setup no encontrado" -ForegroundColor Yellow
    Write-Host "Descargando Inno Setup 6.2.2..." -ForegroundColor Cyan
    
    $DownloadPath = "$env:TEMP\innosetup-installer.exe"
    
    try {
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri $InnoSetupUrl -OutFile $DownloadPath -ErrorAction Stop
        Write-Host "✓ Descarga completada`n" -ForegroundColor Green
        
        Write-Host "Instalando Inno Setup..." -ForegroundColor Cyan
        & $DownloadPath /VERYSILENT /NORESTART | Out-Null
        
        Start-Sleep -Seconds 3
        
        if (Test-Path $IsccExe) {
            Write-Host "✓ Inno Setup instalado exitosamente`n" -ForegroundColor Green
        } else {
            Write-Host "❌ La instalación de Inno Setup falló`n" -ForegroundColor Red
            exit 1
        }
    }
    catch {
        Write-Host "❌ Error descargando Inno Setup: $_`n" -ForegroundColor Red
        Write-Host "Descargue manualmente desde: https://jrsoftware.org/isdl.php`n" -ForegroundColor Yellow
        exit 1
    }
}

# ============================================================================
# PASO 2: Preparar archivos para empaquetar
# ============================================================================

Write-Host "[PASO 2/3] Preparar archivos..." -ForegroundColor Yellow

# Verificar archivo .iss
if (-not (Test-Path $IssScript)) {
    Write-Host "❌ ERROR: Script Inno Setup no encontrado: $IssScript`n" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Script Inno Setup encontrado`n" -ForegroundColor Green

# Crear directorio de salida
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "✓ Directorio de salida creado`n" -ForegroundColor Green
}

# ============================================================================
# PASO 3: Compilar Instalador
# ============================================================================

Write-Host "[PASO 3/3] Compilar instalador..." -ForegroundColor Yellow
Write-Host ""

$CompileArgs = @(
    "/O`"$OutputDir`""
    "/F`"CafBarDLA-Setup`""
    "/DAppName=CafBarDLA POS"
    "/DAppVersion=0.1.0"
    "/DAppPublisher=DLA Tecnología"
    $IssScript
)

Write-Host "Ejecutando ISCC.exe..." -ForegroundColor Cyan
Write-Host "Script: $IssScript" -ForegroundColor Gray
Write-Host "Salida: $OutputDir" -ForegroundColor Gray
Write-Host ""

$CompileOutput = & $IsccExe $CompileArgs 2>&1
Write-Host $CompileOutput

Write-Host ""

# Verificar resultado
$SetupExe = "$OutputDir\CafBarDLA-Setup.exe"

if (Test-Path $SetupExe) {
    $FileSize = (Get-Item $SetupExe).Length / (1MB)
    $CreationTime = (Get-Item $SetupExe).CreationTime
    
    Write-Host ("="*60) -ForegroundColor Green
    Write-Host "✅ ¡INSTALADOR COMPILADO EXITOSAMENTE!" -ForegroundColor Green
    Write-Host ("="*60) -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 Información del archivo:" -ForegroundColor Cyan
    Write-Host "   Nombre: CafBarDLA-Setup.exe" -ForegroundColor White
    Write-Host "   Ubicación: $SetupExe" -ForegroundColor White
    Write-Host "   Tamaño: $([math]::Round($FileSize, 2)) MB" -ForegroundColor White
    Write-Host "   Creado: $CreationTime" -ForegroundColor White
    Write-Host ""
    
    Write-Host "📋 Próximos pasos:" -ForegroundColor Cyan
    Write-Host "   1. Distribuir: CafBarDLA-Setup.exe" -ForegroundColor White
    Write-Host "   2. Los usuarios ejecutan el instalador" -ForegroundColor White
    Write-Host "   3. La aplicación se instala en Program Files\CafBarDLA" -ForegroundColor White
    Write-Host "   4. Se crea acceso directo en el escritorio" -ForegroundColor White
    Write-Host ""
    
    Write-Host "🚀 Prueba local:" -ForegroundColor Cyan
    Write-Host "   & '$SetupExe'" -ForegroundColor Gray
    Write-Host ""
    
} else {
    Write-Host ("="*60) -ForegroundColor Red
    Write-Host "❌ ERROR: Falló la compilación del instalador" -ForegroundColor Red
    Write-Host ("="*60) -ForegroundColor Red
    Write-Host ""
    Write-Host "Verificar:" -ForegroundColor Yellow
    Write-Host "  1. Inno Setup está instalado correctamente" -ForegroundColor Gray
    Write-Host "  2. El script CafBarDLA.iss es válido" -ForegroundColor Gray
    Write-Host "  3. Los archivos fuente existen (dist\CafBarDLA\CafBarDLA.exe)" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""
