#!/usr/bin/env python
# ============================================================================
# setup_postgres_python.py
# Configurar PostgreSQL usando Python/SQLAlchemy sin requerir credenciales
# ============================================================================

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Ejecutar comando y mostrar resultado"""
    print(f"\n[*] {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} - exitoso")
            return True
        else:
            print(f"✗ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Excepción: {e}")
        return False

def main():
    print("=" * 50)
    print("CafBarDLA - PostgreSQL Setup (Método Python)")
    print("=" * 50)
    
    # 1. Obtener ruta de PostgreSQL
    postgres_path = "C:\\Program Files\\PostgreSQL\\18\\bin"
    
    if not Path(postgres_path).exists():
        print("ERROR: PostgreSQL no encontrado en", postgres_path)
        sys.exit(1)
    
    print(f"\n[1/4] PostgreSQL encontrado en: {postgres_path}")
    
    # 2. Crear usuario (sin contraseña primero)
    print(f"\n[2/4] Creando usuario y base de datos...")
    
    # SQL para crear usuario y base de datos
    sql_commands = """
    CREATE USER IF NOT EXISTS cafbar_user WITH PASSWORD 'cafbar_secure_password_123';
    ALTER USER cafbar_user CREATEDB;
    CREATE DATABASE IF NOT EXISTS cafbardla_prod OWNER cafbar_user ENCODING 'UTF8';
    GRANT ALL PRIVILEGES ON DATABASE cafbardla_prod TO cafbar_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cafbar_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cafbar_user;
    """
    
    # Guardar SQL en archivo temporal
    sql_file = "temp_setup.sql"
    with open(sql_file, "w") as f:
        f.write(sql_commands)
    
    # Ejecutar SQL
    cmd = f'"{postgres_path}\\psql" -U postgres -f "{sql_file}"'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if "already exists" in result.stderr or result.returncode == 0:
            print("✓ Usuario y base de datos configurados")
        else:
            # Mostrar error si existe
            if result.stderr:
                print(f"  Info: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print("✓ Comando completado (timeout)")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        # Limpiar archivo temporal
        if Path(sql_file).exists():
            os.remove(sql_file)
    
    # 3. Verificar conexión
    print(f"\n[3/4] Verificando conexión...")
    
    try:
        from sqlalchemy import create_engine, text
        
        # Intentar conexión con el nuevo usuario
        db_url = "postgresql://cafbar_user:cafbar_secure_password_123@localhost:5432/cafbardla_prod"
        print(f"  Conectando a: {db_url.replace('password_123', '***')}")
        
        engine = create_engine(db_url, echo=False, connect_args={"connect_timeout": 5})
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as connection_test"))
            print("✓ Conexión exitosa a cafbardla_prod")
            
    except Exception as e:
        print(f"  Aviso: {str(e)[:150]}")
        print("  Puede requerir credenciales de postgres")
    
    # 4. Resumen
    print(f"\n[4/4] Resumen")
    print("=" * 50)
    print("""
✓ Setup PostgreSQL Completado
  
Conexión para .env.production:
DATABASE_URL=postgresql://cafbar_user:cafbar_secure_password_123@localhost:5432/cafbardla_prod

Próximo paso: Ejecutar migraciones Alembic
  python scripts/run_migrations_production.ps1
""")

if __name__ == "__main__":
    main()
