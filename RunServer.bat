@echo off
REM ============================================================
REM  CafBarDLA POS - Launcher
REM  Inicia la aplicación FastAPI
REM ============================================================

setlocal enabledelayedexpansion
color 0B

cd /d "%~dp0"

REM Verificar si el entorno virtual existe
if not exist ".buildenv" (
    echo.
    echo [ERROR] Entorno virtual no encontrado.
    echo Por favor, ejecuta primero el instalador: CafBarDLA-Installer.bat
    echo.
    pause
    exit /b 1
)

cls

echo.
echo ============================================================
echo     CafBarDLA POS - Servidor FastAPI
echo     Versión 0.1.0
echo ============================================================
echo.
echo Iniciando aplicación...
echo.

REM Activar entorno virtual
call .buildenv\Scripts\activate.bat

REM Iniciar servidor FastAPI
echo.
echo ============================================================
echo  SERVIDOR INICIADO
echo ============================================================
echo.
echo Acceso LOCAL:
echo   Web: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo Acceso REMOTO (desde tablet/móvil):
echo   1. Obtén la IP de este PC: ipconfig
echo   2. En dispositivo móvil abre: http://IP-DEL-PC:8000
echo   3. Ejemplo: http://192.168.1.100:8000
echo.
echo ============================================================
echo.
echo Usuario: admin
echo Contraseña: admin
echo.
echo Para detener el servidor: Presiona CTRL+C
echo.
echo ============================================================
echo.

REM Iniciar servidor con Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

echo.
echo Servidor detenido.
echo.
pause
