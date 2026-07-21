
# CafBarDLA Installer Launcher
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFile = Join-Path $ScriptDir "CafBarDLA-Installer.bat"

Write-Host ""
Write-Host "┌" + ("─"*68) + "┐"
Write-Host "│" + " "*10 + "CafBarDLA POS - Instalador Profesional" + " "*19 + "│"
Write-Host "│" + " "*15 + "Versión 0.1.0 - DLA Tecnología" + " "*23 + "│"
Write-Host "└" + ("─"*68) + "┘"
Write-Host ""

# Verificar permisos de administrador
$IsAdmin = [bool]([System.Security.Principal.WindowsIdentity]::GetCurrent().Groups -match "S-1-5-32-544")
if (-not $IsAdmin) {
    Write-Host "⚠️  Este instalador requiere permisos de administrador." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Reiniciando con permisos de administrador..." -ForegroundColor Cyan
    
    Start-Process PowerShell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`"" -Verb RunAs
    exit
}

# Ejecutar instalador batch
if (Test-Path $BatchFile) {
    & $BatchFile
} else {
    Write-Host "❌ Error: No se encontró el instalador" -ForegroundColor Red
    Write-Host "Archivo esperado: $BatchFile" -ForegroundColor Red
    Read-Host "Presiona ENTER para salir"
}
