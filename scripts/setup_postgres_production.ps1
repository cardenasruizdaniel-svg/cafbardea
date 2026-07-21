# ============================================================================
# setup_postgres_production.ps1
# Crear base de datos PostgreSQL para CafBarDLA en producción
# Requerimientos: PostgreSQL 13+ instalado en Windows
# ============================================================================

param(
    [string]$PostgresPassword = "postgres",
    [string]$DbName = "cafbardla_prod",
    [string]$DbUser = "cafbar_user",
    [string]$DbPassword = "cafbar_secure_password_123",
    [string]$DbHost = "localhost"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CafBarDLA - PostgreSQL Production Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verificar si PostgreSQL está instalado
$pgPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $pgPath) {
    Write-Host "ERROR: PostgreSQL no está instalado o no está en PATH" -ForegroundColor Red
    Write-Host "Descargar de: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[1/5] Verificando conexión a PostgreSQL..." -ForegroundColor Green
try {
    $env:PGPASSWORD = $PostgresPassword
    & psql -h $DbHost -U postgres -c "SELECT version();" -q
    Write-Host "✓ Conexión exitosa a PostgreSQL" -ForegroundColor Green
} catch {
    Write-Host "✗ No se puede conectar a PostgreSQL" -ForegroundColor Red
    Write-Host "Verificar: servicio de PostgreSQL esté corriendo, puerto 5432 disponible" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[2/5] Creando usuario de base de datos: $DbUser" -ForegroundColor Green
$createUserSQL = @"
DO
`$`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DbUser') THEN
    CREATE USER $DbUser WITH PASSWORD '$DbPassword' CREATEDB;
    GRANT CREATEDB ON DATABASE postgres TO $DbUser;
  END IF;
END
`$`$;
"@

try {
    $env:PGPASSWORD = $PostgresPassword
    $createUserSQL | & psql -h $DbHost -U postgres -q
    Write-Host "✓ Usuario $DbUser creado/verificado" -ForegroundColor Green
} catch {
    Write-Host "✗ Error creando usuario" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

Write-Host "`n[3/5] Creando base de datos: $DbName" -ForegroundColor Green
try {
    $env:PGPASSWORD = $PostgresPassword
    & psql -h $DbHost -U postgres -c "CREATE DATABASE $DbName OWNER $DbUser ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';" -q 2>&1 | ForEach-Object {
        if ($_ -notlike "*already exists*") { Write-Host $_ }
    }
    Write-Host "✓ Base de datos $DbName creada/verificada" -ForegroundColor Green
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

Write-Host "`n[4/5] Configurando permisos" -ForegroundColor Green
$permissionsSQL = @"
GRANT ALL PRIVILEGES ON DATABASE $DbName TO $DbUser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DbUser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DbUser;
"@

try {
    $env:PGPASSWORD = $PostgresPassword
    $permissionsSQL | & psql -h $DbHost -U postgres -d $DbName -q
    Write-Host "✓ Permisos configurados" -ForegroundColor Green
} catch {
    Write-Host "✗ Error configurando permisos" -ForegroundColor Red
}

Write-Host "`n[5/5] Verificando conexión con usuario de aplicación" -ForegroundColor Green
try {
    $env:PGPASSWORD = $DbPassword
    & psql -h $DbHost -U $DbUser -d $DbName -c "SELECT current_database();" -q
    Write-Host "✓ Conexión exitosa como $DbUser" -ForegroundColor Green
} catch {
    Write-Host "✗ Error de conexión como usuario de aplicación" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup PostgreSQL Completado ✓" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "
Conexión de cadena para .env.production:
DATABASE_URL=postgresql://$DbUser`:$DbPassword@$DbHost`:5432/$DbName

Siguiente paso: Ejecutar migraciones Alembic
" -ForegroundColor Yellow
