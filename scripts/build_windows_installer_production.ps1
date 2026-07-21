# ============================================================================
# build_windows_installer_production.ps1
# Compilar CafBarDLA en ejecutable Windows con PyInstaller + NSIS
# Requerimientos: PyInstaller, NSIS instalados
# ============================================================================

param(
    [string]$Version = "1.0.0",
    [string]$BuildDir = ".\build_production",
    [string]$DistDir = ".\dist_production"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CafBarDLA - Windows Installer Build" -ForegroundColor Cyan
Write-Host "Versión: $Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verificar dependencias
Write-Host "`n[1/5] Verificando dependencias..." -ForegroundColor Green

$deps = @{
    "pyinstaller" = "pyinstaller --version"
    "nsis" = "& 'C:\Program Files (x86)\NSIS\makensis.exe' /VERSION"
}

foreach ($dep in $deps.GetEnumerator()) {
    try {
        $result = Invoke-Expression $dep.Value 2>&1
        Write-Host "  ✓ $($dep.Key): Instalado" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $($dep.Key): NO ENCONTRADO" -ForegroundColor Red
        Write-Host "    Descargar de: https://pyinstaller.org/ o https://nsis.sourceforge.io/" -ForegroundColor Yellow
        exit 1
    }
}

# Limpiar directorios anteriores
Write-Host "`n[2/5] Preparando directorios..." -ForegroundColor Green
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
if (Test-Path $DistDir) { Remove-Item $DistDir -Recurse -Force }
New-Item -ItemType Directory -Path $BuildDir, $DistDir -Force | Out-Null
Write-Host "  ✓ Directorios preparados" -ForegroundColor Green

# Ejecutar PyInstaller
Write-Host "`n[3/5] Compilando con PyInstaller..." -ForegroundColor Green
$pyinstallerArgs = @(
    "launcher.py",
    "--onefile",
    "--windowed",
    "--icon=app/static/icon.ico",
    "--name=CafBarDLA",
    "--distpath=$DistDir",
    "--buildpath=$BuildDir",
    "--specpath=$BuildDir",
    "--add-data=app/templates:app/templates",
    "--add-data=app/static:app/static",
    "--add-data=alembic:alembic",
    "--add-data=.env.production:.env.production",
    "--hidden-import=sqlalchemy.ext.compiler",
    "--hidden-import=alembic",
    "--collect-all=fastapi",
    "--collect-all=starlette"
)

try {
    & pyinstaller $pyinstallerArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Error durante compilación PyInstaller" -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Ejecutable compilado: CafBarDLA.exe" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Crear script NSIS
Write-Host "`n[4/5] Configurando instalador NSIS..." -ForegroundColor Green

$nsisScript = @"
; CafBarDLA Installer Script
; Configuración NSIS para Windows Installer

!include "MUI2.nsh"

; Configuración general
Name "CafBarDLA Restaurant Management System"
OutFile "$DistDir\CafBarDLA-Setup-$Version.exe"
InstallDir "`$PROGRAMFILES\CafBarDLA"
RequestExecutionLevel admin

; Interfaz
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "English"

; Sección de instalación
Section "CafBarDLA Application"
  SetOutPath "`$INSTDIR"
  File "$DistDir\CafBarDLA.exe"
  File ".env.production.example"
  File "README.md"
  File "requirements.txt"
  
  ; Crear acceso directo en Inicio
  SetOutPath "`$SMPROGRAMS\CafBarDLA"
  CreateShortCut "`$SMPROGRAMS\CafBarDLA\CafBarDLA.lnk" "`$INSTDIR\CafBarDLA.exe"
  CreateShortCut "`$SMPROGRAMS\CafBarDLA\Desinstalar.lnk" "`$INSTDIR\uninstall.exe"
  
  ; Crear desinstalador
  WriteUninstaller "`$INSTDIR\uninstall.exe"
  
  ; Registro de Windows
  WriteRegStr HKEY_LOCAL_MACHINE "Software\Microsoft\Windows\CurrentVersion\Uninstall\CafBarDLA" "DisplayName" "CafBarDLA Restaurant Management System"
  WriteRegStr HKEY_LOCAL_MACHINE "Software\Microsoft\Windows\CurrentVersion\Uninstall\CafBarDLA" "DisplayVersion" "$Version"
  WriteRegStr HKEY_LOCAL_MACHINE "Software\Microsoft\Windows\CurrentVersion\Uninstall\CafBarDLA" "UninstallString" "`$INSTDIR\uninstall.exe"
SectionEnd

; Sección de desinstalación
Section "Uninstall"
  Delete "`$INSTDIR\CafBarDLA.exe"
  Delete "`$INSTDIR\uninstall.exe"
  Delete "`$SMPROGRAMS\CafBarDLA\CafBarDLA.lnk"
  Delete "`$SMPROGRAMS\CafBarDLA\Desinstalar.lnk"
  RMDir "`$SMPROGRAMS\CafBarDLA"
  RMDir "`$INSTDIR"
  DeleteRegKey HKEY_LOCAL_MACHINE "Software\Microsoft\Windows\CurrentVersion\Uninstall\CafBarDLA"
SectionEnd
"@

$nsisScript | Out-File "$BuildDir\CafBarDLA.nsi" -Encoding UTF8
Write-Host "  ✓ Script NSIS generado" -ForegroundColor Green

# Compilar instalador NSIS
Write-Host "`n[5/5] Compilando instalador con NSIS..." -ForegroundColor Green
try {
    & "C:\Program Files (x86)\NSIS\makensis.exe" "$BuildDir\CafBarDLA.nsi" | Out-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Instalador creado exitosamente" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Error compilando NSIS" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Mostrar resultado final
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Build Completado ✓" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$installerFile = Get-Item "$DistDir\CafBarDLA-Setup-$Version.exe" -ErrorAction SilentlyContinue
if ($installerFile) {
    $size = $installerFile.Length / 1MB
    Write-Host "
Instalador listo:
  Archivo: $($installerFile.Name)
  Tamaño: $([Math]::Round($size, 2)) MB
  Ruta: $(Resolve-Path $DistDir)
" -ForegroundColor Yellow
} else {
    Write-Host "ERROR: Instalador no generado" -ForegroundColor Red
    exit 1
}
