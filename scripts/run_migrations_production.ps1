# ============================================================================
# run_migrations_production.ps1
# Ejecutar migraciones Alembic en base de datos de producción
# ============================================================================

param(
    [string]$EnvFile = ".env.production"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CafBarDLA - Alembic Migrations" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verificar si el archivo .env.production existe
if (-not (Test-Path $EnvFile)) {
    Write-Host "ERROR: No se encuentra $EnvFile" -ForegroundColor Red
    Write-Host "Ejecutar primero: setup_postgres_production.ps1" -ForegroundColor Yellow
    exit 1
}

# Cargar variables de ambiente
Write-Host "`n[1/3] Cargando configuración desde $EnvFile..." -ForegroundColor Green
$env | Where-Object { $_.Key -match "^(DATABASE_URL|JWT_SECRET_KEY|SESSION_SECRET_KEY)" } | ForEach-Object {
    Write-Host "  - $($_.Key)" -ForegroundColor Gray
}

Write-Host "`n[2/3] Verificando conexión a base de datos..." -ForegroundColor Green
try {
    $result = python -c "
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('$EnvFile')
db_url = os.getenv('DATABASE_URL')
print(f'Conectando a: {db_url.split(\"@\")[1] if \"@\" in db_url else \"SQLite\"}')

engine = create_engine(db_url, echo=False)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
print('✓ Conexión exitosa')
" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host $result -ForegroundColor Green
    } else {
        Write-Host "✗ Error de conexión:" -ForegroundColor Red
        Write-Host $result -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "✗ Error verificando conexión" -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/3] Ejecutando migraciones Alembic..." -ForegroundColor Green
Write-Host "  Comando: alembic upgrade head" -ForegroundColor Gray

try {
    # Ejecutar Alembic con output directo
    $env:DATABASE_URL = $(python -c "
import os
from dotenv import load_dotenv
load_dotenv('$EnvFile')
print(os.getenv('DATABASE_URL'))
")
    
    & alembic upgrade head
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Migraciones completadas exitosamente" -ForegroundColor Green
    } else {
        Write-Host "✗ Error durante migraciones" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Error ejecutando Alembic" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Migraciones Completadas ✓" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "
Base de datos lista para producción.
Próximo paso: Configurar backups automáticos
" -ForegroundColor Yellow
