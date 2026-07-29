@echo off
REM ============================================================
REM  CFBARDLA Enterprise POS - Servidor Local Windows
REM ============================================================

setlocal enabledelayedexpansion
color 0A

cd /d "%~dp0"

REM Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist ".buildenv\Scripts\activate.bat" (
    call .buildenv\Scripts\activate.bat
) else (
    echo.
    echo [INFORMACION] Entorno virtual no detectado. Usando Python global del sistema...
    echo.
)

cls

echo.
echo ============================================================
echo     CFBARDLA Enterprise POS - Servidor Local Windows
echo ============================================================
echo.
echo Iniciando servidor operativo local...
echo.
echo Acceso LOCAL (Este equipo):
echo   Web POS: http://localhost:8000
echo   App Movil Meseros: http://localhost:8000/mobile
echo.
echo Acceso RED LOCAL (Moviles / Tablets / Comanderas en la misma WiFi):
echo   1. Obtener la IP de este equipo ejecutando: ipconfig
echo   2. Abrir en el navegador de la tablet/celular: http://IP-DEL-EQUIPO:8000/mobile
echo.
echo ============================================================
echo.
echo Para detener el servidor: Presiona CTRL+C
echo.
echo ============================================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
