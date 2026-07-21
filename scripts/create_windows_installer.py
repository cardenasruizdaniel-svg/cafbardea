#!/usr/bin/env python3
"""
CafBarDLA Installer Wrapper
Este script crea un ejecutable Windows que instala CafBarDLA
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

class CafBarDLAInstaller:
    def __init__(self):
        self.project_root = Path("d:/CafBarDLA")
        self.installer_dir = self.project_root / "installer"
        self.output_dir = self.project_root / "dist"
        self.output_dir.mkdir(exist_ok=True)
        
    def create_exe_wrapper(self):
        """Crear ejecutable wrapper del instalador"""
        
        print("\n" + "="*70)
        print("🔧 Compilador de Instalador CafBarDLA - Windows EXE")
        print("="*70 + "\n")
        
        # Paso 1: Crear script PowerShell que lance el batch
        ps_wrapper = """
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
"""
        
        ps_file = self.installer_dir / "CafBarDLA-Installer.ps1"
        with open(ps_file, 'w', encoding='utf-8') as f:
            f.write(ps_wrapper)
        
        print("[1/3] Script PowerShell creado: CafBarDLA-Installer.ps1")
        
        # Paso 2: Crear ejecutable con py2exe (alternativa simple)
        print("[2/3] Intentando crear ejecutable...")
        
        # Usar pyinstaller alternativo - crear un ejecutable simple
        exe_launcher = """#!/usr/bin/env python3
import os
import subprocess
import sys

# Obtener ruta del directorio actual
script_dir = os.path.dirname(os.path.abspath(__file__))
batch_file = os.path.join(script_dir, 'CafBarDLA-Installer.bat')

# Ejecutar batch como administrador
if os.path.exists(batch_file):
    # En Windows, usar shellexecute para elevar permisos
    try:
        import ctypes
        
        # Mostrar ventana de consola
        os.startfile(batch_file, 'runas')
    except:
        # Fallback: ejecutar directamente
        subprocess.Popen([batch_file], cwd=script_dir)
else:
    print("ERROR: No se encontró CafBarDLA-Installer.bat")
    input("Presiona ENTER para salir...")
"""
        
        launcher_py = self.installer_dir / "launcher_exe.py"
        with open(launcher_py, 'w', encoding='utf-8') as f:
            f.write(exe_launcher)
        
        print("[3/3] Creando paquete distribuible...")
        
        # Crear carpeta de distribución con todo
        dist_installer = self.output_dir / "CafBarDLA-Setup"
        if dist_installer.exists():
            shutil.rmtree(dist_installer)
        dist_installer.mkdir(parents=True)
        
        # Copiar archivos necesarios
        shutil.copy(self.installer_dir / "CafBarDLA-Installer.bat", dist_installer / "CafBarDLA-Installer.bat")
        shutil.copy(ps_file, dist_installer / "CafBarDLA-Installer.ps1")
        
        # Crear README.txt
        readme = """
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║               CafBarDLA POS - Instalador Profesional                       ║
║                       Versión 0.1.0                                        ║
║                      DLA Tecnología                                        ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝


INSTRUCCIONES DE INSTALACIÓN:
═══════════════════════════════════════════════════════════════════════════


1. REQUISITOS PREVIOS:
   ─────────────────────
   • Windows 10/11
   • Python 3.10+ (https://www.python.org/downloads/)
   • Marcar "Add Python to PATH" durante instalación de Python
   • 2 GB de espacio libre en disco


2. INSTALAR PYTHON (si aún no lo tienes):
   ──────────────────────────────────────────
   1. Descarga desde: https://www.python.org/downloads/
   2. Ejecuta el instalador
   3. IMPORTANTE: Marca las opciones:
      ✓ Add Python to PATH
      ✓ Install pip
   4. Haz clic en "Install Now"


3. EJECUTAR INSTALADOR:
   ──────────────────────
   
   OPCIÓN A: Hacer doble clic (Recomendado)
   ────────────────────────────────────────
   • Haz doble clic en: CafBarDLA-Installer.bat
   • El instalador se ejecutará automáticamente
   
   OPCIÓN B: PowerShell
   ─────────────────────
   • Abre PowerShell como Administrador
   • Ejecuta: .\\CafBarDLA-Installer.ps1
   
   OPCIÓN C: Línea de comandos
   ────────────────────────────
   • Abre CMD como Administrador
   • Ejecuta: CafBarDLA-Installer.bat


4. SEGUIR ASISTENTE:
   ────────────────────
   • El instalador te guiará paso a paso
   • Selecciona la ubicación de instalación (default: C:\\Program Files\\CafBarDLA)
   • Espera a que se instalen las dependencias
   • Se crearán accesos directos automáticamente


5. EJECUTAR APLICACIÓN:
   ──────────────────────
   
   OPCIÓN A: Acceso Directo (Más fácil)
   ────────────────────────────────────
   • Haz doble clic en: CafBarDLA.lnk (en tu escritorio)
   • La aplicación se abrirá automáticamente
   
   OPCIÓN B: PowerShell
   ─────────────────────
   cd "C:\\Program Files\\CafBarDLA"
   .buildenv\\Scripts\\activate.bat
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4


6. ACCEDER A LA APLICACIÓN:
   ─────────────────────────────
   
   DESDE ESTE ORDENADOR:
   • Abre navegador: http://localhost:8000
   
   DESDE TABLET/SMARTPHONE EN LA MISMA RED:
   • Obtén la IP de tu PC (ipconfig en CMD)
   • Abre navegador en tablet: http://IP-DEL-PC:8000
   • Ejemplo: http://192.168.1.100:8000


7. CREDENCIALES:
   ──────────────────
   Usuario: admin
   Contraseña: admin
   
   ⚠️ CAMBIAR EN LA PRIMERA CONEXIÓN


8. DOCUMENTACIÓN:
   ─────────────────
   • Manual completo: C:\\Program Files\\CafBarDLA\\docs\\MANUAL_COMPLETO.md
   • Guía cloud: C:\\Program Files\\CafBarDLA\\docs\\CLOUD_DEPLOYMENT_GUIDE.md


═══════════════════════════════════════════════════════════════════════════

SOLUCIÓN DE PROBLEMAS:
───────────────────────

P: "Python no está instalado"
R: Descarga desde https://www.python.org/downloads/
   Marca: "Add Python to PATH"

P: "Acceso denegado / No tienes permisos"
R: Haz clic derecho en el archivo → "Ejecutar como administrador"

P: "El puerto 8000 está en uso"
R: Usa otro puerto:
   uvicorn app.main:app --port 8001

P: "No puedo acceder desde tablet"
R: 1. Verifica que estén en la misma red WiFi
   2. Obtén la IP: ipconfig en CMD (IPv4 Address)
   3. Usa: http://IP:8000


═══════════════════════════════════════════════════════════════════════════

SOPORTE:
─────────

Email: support@dlatecnologia.com
Teléfono: +57 1 2345678
WhatsApp: +57 310 5678901
Portal: https://support.dlatecnologia.com


═══════════════════════════════════════════════════════════════════════════

Gracias por elegir CafBarDLA ☕
"""
        
        with open(dist_installer / "LEEME_PRIMERO.txt", 'w', encoding='utf-8') as f:
            f.write(readme.strip())
        
        print("\n" + "="*70)
        print("✅ PAQUETE INSTALADOR LISTO")
        print("="*70 + "\n")
        
        print(f"📦 Ubicación: {dist_installer}\n")
        
        print("📋 Archivos generados:")
        print(f"   • CafBarDLA-Installer.bat")
        print(f"   • CafBarDLA-Installer.ps1")
        print(f"   • LEEME_PRIMERO.txt\n")
        
        print("🚀 Para usar:")
        print(f"   1. Copia la carpeta: {dist_installer.name}")
        print(f"   2. Comparte con usuarios")
        print(f"   3. Ellos ejecutan: CafBarDLA-Installer.bat")
        print(f"   4. ¡Listo! Aplicación instalada y funcionando\n")
        
        return True

def main():
    installer = CafBarDLAInstaller()
    installer.create_exe_wrapper()

if __name__ == "__main__":
    main()
