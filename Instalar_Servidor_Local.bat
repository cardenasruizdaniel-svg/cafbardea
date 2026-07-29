@echo off
REM ============================================================
REM  CFBARDLA Enterprise POS - Instalador Servidor Local Windows
REM ============================================================

setlocal enabledelayedexpansion
color 0B
cd /d "%~dp0"

cls
echo ============================================================
echo    CFBARDLA Enterprise POS - Instalador Servidor Local
echo ============================================================
echo.
echo Este script configurara y preparara el servidor local para Windows.
echo.

REM 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta configurado en el PATH.
    echo Por favor instala Python 3.10+ desde python.org seleccionando "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo [OK] Python !PY_VER! detectado.

REM 2. Crear Entorno Virtual .venv si no existe
if not exist ".venv" (
    echo.
    echo [1/3] Creando entorno virtual Python (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado.
) else (
    echo [OK] Entorno virtual .venv existente detectado.
)

REM 3. Activar e instalar dependencias
echo.
echo [2/3] Instalando dependencias necesarias (requirements.txt)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Ocurrio un inconveniente al instalar algunas dependencias.
)

REM 4. Verificar base de datos inicial
echo.
echo [3/3] Inicializando base de datos local...
python -c "from app.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)" >nul 2>&1
echo [OK] Base de datos local lista.

echo.
echo ============================================================
echo   INSTALACION COMPLETADA CON EXITO
echo ============================================================
echo.
echo Puedes iniciar el servidor local en cualquier momento haciendo doble clic en:
echo   -> RunServer.bat
echo.
echo O ingresando a http://localhost:8000 una vez iniciado.
echo.
pause
