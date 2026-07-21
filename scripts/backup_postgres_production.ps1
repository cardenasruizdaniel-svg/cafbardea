# ============================================================================
# backup_postgres_production.ps1
# Realizar backup automático de base de datos PostgreSQL
# Schedule: Windows Task Scheduler a las 2 AM diarios
# ============================================================================

param(
    [string]$DbHost = "localhost",
    [string]$DbUser = "cafbar_user",
    [string]$DbPassword = "cafbar_secure_password_123",
    [string]$DbName = "cafbardla_prod",
    [string]$BackupPath = "D:\Backups\CafBarDLA",
    [int]$RetentionDays = 30,
    [bool]$EmailAlert = $false
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $BackupPath "cafbardla_$timestamp.sql"
$logFile = Join-Path $BackupPath "backups.log"

# Crear directorio si no existe
if (-not (Test-Path $BackupPath)) {
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
}

# Función para log
function Write-Log {
    param([string]$Message)
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

Write-Log "========== BACKUP INICIADO =========="
Write-Log "Base de datos: $DbName"
Write-Log "Ruta: $backupFile"

# Ejecutar pg_dump
try {
    $env:PGPASSWORD = $DbPassword
    & pg_dump -h $DbHost -U $DbUser -d $DbName --format=plain --compress=9 --verbose > $backupFile 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $fileSize = (Get-Item $backupFile).Length / 1MB
        Write-Log "✓ Backup completado exitosamente"
        Write-Log "✓ Tamaño: $([Math]::Round($fileSize, 2)) MB"
    } else {
        Write-Log "✗ Error durante backup"
        exit 1
    }
} catch {
    Write-Log "✗ Excepción: $($_.Exception.Message)"
    exit 1
}

# Limpiar backups antiguos
Write-Log "Limpiando backups anteriores a $RetentionDays días..."
Get-ChildItem $BackupPath -Filter "cafbardla_*.sql" -ErrorAction SilentlyContinue | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } | 
    ForEach-Object {
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        Write-Log "  - Eliminado: $($_.Name)"
    }

# Estadísticas
$backupCount = @(Get-ChildItem $BackupPath -Filter "cafbardla_*.sql" -ErrorAction SilentlyContinue).Count
Write-Log "✓ Backups activos: $backupCount"

Write-Log "========== BACKUP COMPLETADO =========="

# Opcional: Enviar alerta por email
if ($EmailAlert) {
    Write-Log "Enviando notificación por email..."
    # TODO: Implementar envío de email si es necesario
}
