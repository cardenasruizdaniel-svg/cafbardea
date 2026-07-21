#!/usr/bin/env python3
"""Crear paquete de distribución CafBarDLA"""

import shutil
import os
from pathlib import Path

def create_distribution_package():
    """Crear ZIP de distribución"""
    
    print("\n" + "="*60)
    print("📦 Empaquetador de Distribución - CafBarDLA POS")
    print("="*60 + "\n")
    
    PROJECT_ROOT = Path("d:/CafBarDLA")
    DIST_DIR = PROJECT_ROOT / "dist"
    PACKAGE_NAME = "CafBarDLA-0.1.0-WindowsInstaller"
    TEMP_PACKAGE = DIST_DIR / "temp_package"
    
    # Crear directorio dist
    DIST_DIR.mkdir(exist_ok=True)
    
    print("[1/3] Copiando archivos...\n")
    
    # Limpiar temporal
    if TEMP_PACKAGE.exists():
        shutil.rmtree(TEMP_PACKAGE)
    TEMP_PACKAGE.mkdir(parents=True, exist_ok=True)
    
    # Archivos a copiar
    items_to_copy = [
        ("app", "app"),
        ("docs", "docs"),
        ("scripts", "scripts"),
        ("alembic", "alembic"),
        ("installer", "installer"),
        ("requirements.txt", "requirements.txt"),
        ("alembic.ini", "alembic.ini"),
        ("launcher.py", "launcher.py"),
        (".env.production.example", ".env.production.example"),
        ("README.md", "README.md"),
    ]
    
    for src, dst in items_to_copy:
        src_path = PROJECT_ROOT / src
        dst_path = TEMP_PACKAGE / dst
        
        if src_path.exists():
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                print(f"  ✓ {src}/ copiado")
            else:
                shutil.copy2(src_path, dst_path)
                print(f"  ✓ {src} copiado")
    
    print("\n[2/3] Creando archivo de instrucciones...\n")
    
    # Crear archivo INSTALAR_PRIMERO.txt
    readme_content = """
===============================================================================
    CafBarDLA POS - Sistema de Punto de Venta - Versión 0.1.0
    DLA Tecnología - support@dlatecnologia.com
===============================================================================

CONTENIDO:
 - app/              Código fuente
 - docs/             Documentación completa
 - scripts/          Scripts de instalación
 - alembic/          Migraciones de base de datos
 - installer/        Instalador automático


INSTALACIÓN RÁPIDA:
===================

1. Ejecuta como Administrador:
   installer\\InstalarCafBarDLA.bat

2. Sigue las instrucciones

3. ¡Listo! Accede a http://localhost:8000


DOCUMENTACIÓN:
===============
Ver archivos en la carpeta docs/ para:
 - MANUAL_COMPLETO.md  - Guía completa de instalación
 - CLOUD_DEPLOYMENT_GUIDE.md - Deploy en la nube


CREDENCIALES POR DEFECTO:
==========================
Usuario: admin
Contraseña: admin

⚠ IMPORTANTE: Cambiar contraseña en la primera conexión!


REQUISITOS:
============
- Windows 10 o superior
- Python 3.10+ (https://www.python.org/downloads/)
- 2 GB de espacio libre


SOPORTE:
=========
Email: support@dlatecnologia.com
Teléfono: +57 1 2345678
"""
    
    with open(TEMP_PACKAGE / "INSTALAR_PRIMERO.txt", "w", encoding="utf-8") as f:
        f.write(readme_content.strip())
    
    print("  ✓ Archivo de instrucciones creado")
    
    print("\n[3/3] Creando archivo ZIP...\n")
    
    # Crear ZIP
    zip_path = DIST_DIR / PACKAGE_NAME
    shutil.make_archive(str(zip_path), 'zip', TEMP_PACKAGE)
    
    zip_file = DIST_DIR / f"{PACKAGE_NAME}.zip"
    
    # Limpiar temporal
    shutil.rmtree(TEMP_PACKAGE)
    
    # Verificar
    if zip_file.exists():
        size_mb = zip_file.stat().st_size / (1024 * 1024)
        
        print("="*60)
        print("✅ PAQUETE LISTO PARA DISTRIBUIR!")
        print("="*60 + "\n")
        
        print("📦 Información:")
        print(f"   Archivo: {zip_file.name}")
        print(f"   Ubicación: {zip_file}")
        print(f"   Tamaño: {size_mb:.2f} MB\n")
        
        print("📋 Instrucciones para usuarios:")
        print("   1. Descargar: CafBarDLA-0.1.0-WindowsInstaller.zip")
        print("   2. Extraer en carpeta deseada")
        print("   3. Leer: INSTALAR_PRIMERO.txt")
        print("   4. Ejecutar: installer\\InstalarCafBarDLA.bat (como Admin)")
        print("   5. Acceder a: http://localhost:8000\n")
        
        print("🚀 Para compartir:")
        print(f"   Enviar archivo: {zip_file}\n")
        
        return True
    else:
        print("❌ Error creando ZIP\n")
        return False

if __name__ == "__main__":
    success = create_distribution_package()
    exit(0 if success else 1)
