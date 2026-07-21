#!/usr/bin/env python3
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
