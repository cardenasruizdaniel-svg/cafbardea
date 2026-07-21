#!/usr/bin/env python
"""
setup_postgres_direct.py
Configurar PostgreSQL directamente sin usar psql
"""

import sys
import time
from sqlalchemy import create_engine, text, event
from sqlalchemy.exc import OperationalError, ProgrammingError
import os

# Esperar a que PostgreSQL esté listo
print("=" * 60)
print("CafBarDLA - PostgreSQL Setup (Direct Connection)")
print("=" * 60)

print("\n[1/3] Esperando PostgreSQL...")
time.sleep(3)

# Intentar conectar con postgres user (contraseña vacía)
postgres_urls = [
    "postgresql://postgres@localhost:5432/postgres",
    "postgresql://postgres:@localhost:5432/postgres",
    "postgresql://postgres:postgres@localhost:5432/postgres",
]

engine = None
for url in postgres_urls:
    try:
        print(f"  Intentando: {url.split('@')[1] if '@' in url else url}")
        eng = create_engine(url, echo=False, pool_pre_ping=True)
        
        with eng.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✓ Conectado exitosamente")
            engine = eng
            break
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:80]}")
        continue

if not engine:
    print("\n✗ No se pudo conectar a PostgreSQL")
    print("Posibles soluciones:")
    print("1. Verifica que PostgreSQL está corriendo")
    print("2. Intenta resetear la contraseña de postgres")
    print("3. Abre pgAdmin y configura manualmente")
    sys.exit(1)

print("\n[2/3] Creando usuario y base de datos...")

# SQL commands
commands = [
    "CREATE USER IF NOT EXISTS cafbar_user WITH PASSWORD 'cafbar_secure_password_123';",
    "ALTER USER cafbar_user CREATEDB;",
    "CREATE DATABASE IF NOT EXISTS cafbardla_prod OWNER cafbar_user ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C';",
    "GRANT ALL PRIVILEGES ON DATABASE cafbardla_prod TO cafbar_user;",
]

try:
    with engine.connect() as conn:
        # Necesitamos autocommit para crear base de datos
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        
        for cmd in commands:
            try:
                conn.execute(text(cmd))
                cmd_short = cmd.replace("IF NOT EXISTS", "").strip()[:60]
                print(f"  ✓ {cmd_short}...")
            except ProgrammingError as e:
                if "already exists" in str(e):
                    print(f"  ℹ {str(e)[:60]}...")
                else:
                    raise
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\n[3/3] Verificando conexión con nuevo usuario...")

try:
    test_engine = create_engine(
        "postgresql://cafbar_user:cafbar_secure_password_123@localhost:5432/cafbardla_prod",
        echo=False
    )
    
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✓ Conexión exitosa como cafbar_user")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ Setup PostgreSQL Completado")
print("=" * 60)
print("""
Próximo paso: Ejecutar migraciones Alembic

Comando:
  python scripts/run_migrations_production.ps1
  
O ejecutar alembic directamente:
  alembic upgrade head
""")
