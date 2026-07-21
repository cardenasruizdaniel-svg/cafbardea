# ============================================================================
# schedule_backup_task.ps1
# Crear tarea en Windows Task Scheduler para backups diarios
# Ejecutar como: powershell -ExecutionPolicy Bypass -File schedule_backup_task.ps1
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CafBarDLA - Schedule Backup Task" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verificar que se ejecuta como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "ERROR: Este script debe ejecutarse como Administrador" -ForegroundColor Red
    Write-Host "Click derecho > Ejecutar como administrador" -ForegroundColor Yellow
    exit 1
}

$taskName = "CafBarDLA-Backup"
$scriptPath = "D:\CafBarDLA\scripts\backup_postgres_production.ps1"

# Verificar que el script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: No se encuentra $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/3] Verificando tarea existente..." -ForegroundColor Green
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Tarea existente encontrada. Eliminando..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "✓ Tarea eliminada" -ForegroundColor Green
}

Write-Host "`n[2/3] Creando nueva tarea..." -ForegroundColor Green

# Crear acción de tarea
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# Crear trigger (2 AM diarios)
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

# Crear configuración de tarea
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Registrar tarea
$task = Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Backup automático de CafBarDLA PostgreSQL" `
    -RunLevel Highest `
    -ErrorAction Stop

Write-Host "✓ Tarea creada exitosamente" -ForegroundColor Green

Write-Host "`n[3/3] Detalles de la tarea:" -ForegroundColor Green
Write-Host "  Nombre: $taskName" -ForegroundColor Gray
Write-Host "  Ejecución: Diariamente a las 2:00 AM" -ForegroundColor Gray
Write-Host "  Script: $scriptPath" -ForegroundColor Gray
Write-Host "  Estado: $($task.State)" -ForegroundColor Gray

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Tarea Programada ✓" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "
Los backups se ejecutarán automáticamente a las 2:00 AM.
Para verificar: Ejecutar
  Get-ScheduledTask -TaskName 'CafBarDLA-Backup'

Para ejecutar backup manualmente:
  powershell -File D:\CafBarDLA\scripts\backup_postgres_production.ps1
" -ForegroundColor Yellow
