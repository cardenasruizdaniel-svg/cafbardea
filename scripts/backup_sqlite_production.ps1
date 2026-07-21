# ============================================================================
# backup_sqlite_production.ps1
# Realizar backup automático de base de datos SQLite
# Schedule: Windows Task Scheduler a las 2 AM diarios
# ============================================================================

param(
    [string]$DbFile = "cafbardla_prod.db",
    [string]$BackupPath = "D:\Backups\CafBarDLA",
    [int]$RetentionDays = 30
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $BackupPath "cafbardla_$timestamp.db"
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
Write-Log "Base de datos: $DbFile"
Write-Log "Ruta de backup: $backupFile"

# Verificar que la base de datos existe
if (-not (Test-Path $DbFile)) {
    Write-Log "✗ Error: Base de datos no encontrada: $DbFile"
    exit 1
}

# Realizar backup (copiar archivo)
try {
    Copy-Item -Path $DbFile -Destination $backupFile -Force
    
    if (Test-Path $backupFile) {
        $fileSize = (Get-Item $backupFile).Length / 1MB
        Write-Log "✓ Backup completado exitosamente"
        Write-Log "✓ Tamaño: $([Math]::Round($fileSize, 2)) MB"
    } else {
        Write-Log "✗ Error: Backup no se creó correctamente"
        exit 1
    }
} catch {
    Write-Log "✗ Excepción: $($_.Exception.Message)"
    exit 1
}

# Limpiar backups antiguos
Write-Log "Limpiando backups anteriores a $RetentionDays días..."
Get-ChildItem $BackupPath -Filter "cafbardla_*.db" -ErrorAction SilentlyContinue | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } | 
    ForEach-Object {
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        Write-Log "  - Eliminado: $($_.Name)"
    }

# Estadísticas
$backupCount = @(Get-ChildItem $BackupPath -Filter "cafbardla_*.db" -ErrorAction SilentlyContinue).Count
$totalSize = [Math]::Round((Get-ChildItem $BackupPath -Filter "cafbardla_*.db" -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB, 2)

Write-Log "✓ Backups activos: $backupCount"
Write-Log "✓ Tamaño total: $totalSize MB"
Write-Log "========== BACKUP COMPLETADO =========="
