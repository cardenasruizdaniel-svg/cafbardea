@echo off
REM CafBarDLA - Instalador Automático para Windows
REM Este script instala la aplicación en: C:\Program Files\CafBarDLA

setlocal enabledelayedexpansion
cd /d "%~dp0"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Verificaciones iniciales
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo.
echo ===============================================
echo   CafBarDLA POS - Instalador
echo   Versión 0.1.0
echo ===============================================
echo.

REM Verificar permisos de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Este instalador requiere permisos de administrador.
    echo.
    echo Por favor, haz clic derecho en este archivo y selecciona:
    echo "Ejecutar como administrador"
    pause
    exit /b 1
)

echo [1/5] Verificando requisitos...
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no está instalado o no está en el PATH.
    echo.
    echo Descarga Python desde: https://www.python.org/downloads/
    echo Durante la instalación, marca la opción "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% encontrado

REM Verificar Git (opcional pero recomendado)
git --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3" %%i in ('git --version') do set GIT_VERSION=%%i
    echo ✓ Git !GIT_VERSION! encontrado
) else (
    echo ⚠ Git no encontrado (opcional, se puede usar ZIP)
)

echo.
echo [2/5] Seleccionar carpeta de instalación...
echo.

REM Ubicación por defecto
set INSTALL_DIR=C:\Program Files\CafBarDLA

echo Carpeta de instalación por defecto: %INSTALL_DIR%
echo.
echo ¿Deseas cambiarla? (s/n)
set /p CHANGE_DIR=
if /i "%CHANGE_DIR%"=="s" (
    echo Ingresa la ruta completa (ej: D:\CafBarDLA):
    set /p INSTALL_DIR=
)

echo.
echo Instalando en: %INSTALL_DIR%
echo.

REM Crear carpeta
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo ✓ Carpeta creada
)

echo.
echo [3/5] Descargar/Copiar archivos...
echo.

REM Copiar archivos del proyecto
if exist "app" (
    echo ✓ Copiando código fuente...
    xcopy /E /I /Y app "%INSTALL_DIR%\app" >nul
    xcopy /E /I /Y docs "%INSTALL_DIR%\docs" >nul
    xcopy /E /I /Y scripts "%INSTALL_DIR%\scripts" >nul
    xcopy /E /I /Y alembic "%INSTALL_DIR%\alembic" >nul
    copy /Y requirements.txt "%INSTALL_DIR%\" >nul
    copy /Y .env.production.example "%INSTALL_DIR%\.env.production.example" >nul
    copy /Y alembic.ini "%INSTALL_DIR%\" >nul
    copy /Y launcher.py "%INSTALL_DIR%\" >nul
    echo ✓ Archivos copiados
) else (
    echo ERROR: No se encuentran los archivos del proyecto.
    echo Asegúrate de ejecutar este script desde la carpeta raíz de CafBarDLA.
    pause
    exit /b 1
)

echo.
echo [4/5] Instalar dependencias Python...
echo.

cd /d "%INSTALL_DIR%"

REM Crear entorno virtual
if not exist ".buildenv" (
    echo Creando entorno virtual...
    python -m venv .buildenv
    echo ✓ Entorno virtual creado
)

REM Activar entorno virtual
call .buildenv\Scripts\activate.bat

REM Instalar dependencias
echo Instalando paquetes Python (esto puede tardar un par de minutos)...
pip install --upgrade pip -q
pip install -r requirements.txt -q

if %errorlevel% neq 0 (
    echo ERROR: Falló la instalación de dependencias
    pause
    exit /b 1
)

echo ✓ Dependencias instaladas

REM Crear archivo de configuración
if not exist ".env.production" (
    echo.
    echo [5/5] Configuración inicial...
    echo.
    
    copy .env.production.example .env.production
    echo ✓ Archivo .env.production creado
    
    echo.
    echo IMPORTANTE: Edita el archivo .env.production con tus datos
    echo Ubicación: "%INSTALL_DIR%\.env.production"
    echo.
)

REM Inicializar base de datos
echo.
echo Inicializando base de datos...
alembic upgrade head >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Base de datos inicializada
) else (
    echo ⚠ Falló la inicialización de BD (puedes hacerlo manualmente después)
)

echo.
echo ===============================================
echo ✓ Instalación completada exitosamente!
echo ===============================================
echo.
echo Pasos siguientes:
echo.
echo 1. Edita la configuración:
echo    "%INSTALL_DIR%\.env.production"
echo.
echo 2. Para ejecutar la aplicación:
echo    PowerShell -Command "cd '%INSTALL_DIR%'; .\.buildenv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
echo.
echo 3. Accede a:
echo    http://localhost:8000
echo.
echo Usuario por defecto: admin / admin
echo.
echo Para más información, ver:
echo    "%INSTALL_DIR%\docs\MANUAL_COMPLETO.md"
echo.
pause

endlocal
