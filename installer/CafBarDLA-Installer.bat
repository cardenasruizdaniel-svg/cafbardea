@echo off
REM ============================================================
REM  CafBarDLA POS - Instalador Windows Professional Edition
REM  Versión: 0.1.0
REM  Empresa: DLA Tecnología
REM ============================================================

setlocal enabledelayedexpansion
color 0A

REM Cambiar a directorio del script
cd /d "%~dp0"

REM Verificar si se ejecuta con permisos de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Este instalador requiere permisos de administrador.
    echo.
    echo Por favor, haz clic derecho en este archivo y selecciona:
    echo "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

cls

REM ============================================================
REM PANTALLA DE BIENVENIDA
REM ============================================================

echo.
echo ============================================================
echo      CAFBARDLA POS - INSTALADOR PROFESIONAL
echo      Version 0.1.0
echo      DLA Tecnologia - Software - Ciberseguridad
echo ============================================================
echo.
echo Este instalador te guiara en la instalacion de CafBarDLA
echo Sistema de Punto de Venta para Cafeterias y Bares
echo.
echo Caracteristicas:
echo  * Gestion de comandas y mesas
echo  * Control de inventario
echo  * Facturacion electronica
echo  * Sistema Mobile (iOS/Android)
echo  * Kitchen Display System (KDS)
echo  * Reportes y analisis
echo.
timeout /t 3 /nobreak

cls

REM ============================================================
REM VERIFICACIONES PREVIAS
REM ============================================================

echo.
echo [PASO 1/6] Verificando requisitos del sistema...
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo Por favor, descarga Python desde:
    echo https://www.python.org/downloads/
    echo.
    echo Asegurate de seleccionar:
    echo  1. Python 3.10 o superior
    echo  2. Marcar "Add Python to PATH"
    echo  3. Marcar "Install pip"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python !PYTHON_VERSION! encontrado

REM Verificar conexion a Internet (ping a Google DNS)
ping -n 1 8.8.8.8 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Conexion a Internet: Disponible
    set INTERNET=1
) else (
    echo [ADVERTENCIA] Sin conexion a Internet
    echo La instalacion funcionara pero sin descargas adicionales
    set INTERNET=0
)

echo.
echo.

REM ============================================================
REM SELECCIONAR UBICACION DE INSTALACION
REM ============================================================

echo [PASO 2/6] Seleccionar ubicacion de instalacion
echo.

set INSTALL_DIR=C:\Program Files\CafBarDLA

echo Ubicacion por defecto: %INSTALL_DIR%
echo.
echo ^>Presiona ENTER para aceptar, o escribe otra ruta:
set /p CUSTOM_DIR=

if not "!CUSTOM_DIR!"=="" (
    set INSTALL_DIR=!CUSTOM_DIR!
)

echo.
echo Instalando en: %INSTALL_DIR%
echo.

if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo [OK] Carpeta creada
)

echo.
echo.

REM ============================================================
REM COPIAR ARCHIVOS
REM ============================================================

echo [PASO 3/6] Copiando archivos de aplicacion...
echo.

if exist "app" (
    xcopy /E /I /Y /Q app "%INSTALL_DIR%\app" >nul
    echo [OK] Aplicacion copiada
) else (
    echo [ADVERTENCIA] Carpeta 'app' no encontrada
)

if exist "docs" (
    xcopy /E /I /Y /Q docs "%INSTALL_DIR%\docs" >nul
    echo [OK] Documentacion copiada
)

if exist "alembic" (
    xcopy /E /I /Y /Q alembic "%INSTALL_DIR%\alembic" >nul
    echo [OK] Migraciones copiadas
)

if exist "scripts" (
    xcopy /E /I /Y /Q scripts "%INSTALL_DIR%\scripts" >nul
    echo [OK] Scripts copiados
)

copy /Y requirements.txt "%INSTALL_DIR%\" >nul 2>&1
copy /Y alembic.ini "%INSTALL_DIR%\" >nul 2>&1
copy /Y launcher.py "%INSTALL_DIR%\" >nul 2>&1
copy /Y .env.production.example "%INSTALL_DIR%\.env.production.example" >nul 2>&1
copy /Y README.md "%INSTALL_DIR%\" >nul 2>&1

echo [OK] Archivos copiados

echo.
echo.

REM ============================================================
REM CREAR ENTORNO VIRTUAL Y DEPENDENCIAS
REM ============================================================

echo [PASO 4/6] Configurar entorno Python...
echo.

cd /d "%INSTALL_DIR%"

if not exist ".buildenv" (
    echo Creando entorno virtual...
    python -m venv .buildenv
    echo [OK] Entorno virtual creado
)

REM Activar entorno virtual
call .buildenv\Scripts\activate.bat

echo Instalando dependencias Python...
pip install --upgrade pip -q >nul 2>&1
pip install -r requirements.txt -q >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] Dependencias instaladas
) else (
    echo [ERROR] Falló la instalacion de dependencias
    echo Intenta manualmente: pip install -r requirements.txt
)

echo.
echo.

REM ============================================================
REM CONFIGURAR BASE DE DATOS
REM ============================================================

echo [PASO 5/6] Inicializar base de datos...
echo.

if not exist ".env.production" (
    copy .env.production.example .env.production >nul
    echo [OK] Archivo .env.production creado
)

alembic upgrade head >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Base de datos inicializada
) else (
    echo [ADVERTENCIA] No se pudo inicializar BD automaticamente
    echo Puedes hacerlo manualmente luego
)

echo.
echo.

REM ============================================================
REM CREAR ACCESOS DIRECTOS
REM ============================================================

echo [PASO 6/6] Crear accesos directos...
echo.

REM Crear acceso directo en escritorio
set "DESKTOP=%USERPROFILE%\Desktop"

REM Usar PowerShell para crear acceso directo (más confiable)
powershell -NoProfile -Command "^
    try {^
        `$WshShell = New-Object -ComObject WScript.Shell; ^
        `$Shortcut = `$WshShell.CreateShortcut('%DESKTOP%\CafBarDLA.lnk'); ^
        `$Shortcut.TargetPath = 'cmd.exe'; ^
        `$Shortcut.Arguments = '/c cd /d \"%INSTALL_DIR%\" ^& .buildenv\Scripts\activate.bat ^& uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4'; ^
        `$Shortcut.WorkingDirectory = '%INSTALL_DIR%'; ^
        `$Shortcut.IconLocation = '%INSTALL_DIR%\app\static\favicon.ico'; ^
        `$Shortcut.Save(); ^
        Write-Host '[OK] Acceso directo creado en escritorio'; ^
    } catch { ^
        Write-Host '[ADVERTENCIA] No se pudo crear acceso directo'; ^
    } ^
"

REM Crear acceso directo en menu inicio (opcional)

echo.
echo.

REM ============================================================
REM COMPLETACION
REM ============================================================

cls

echo.
echo ============================================================
echo  ✓ INSTALACION COMPLETADA EXITOSAMENTE
echo ============================================================
echo.
echo Ubicacion: %INSTALL_DIR%
echo.
echo.
echo PROXIMOS PASOS:
echo ===============
echo.
echo 1. INICIAR APLICACION
echo    - Haz doble clic en: CafBarDLA.lnk (en tu escritorio)
echo    O ejecuta en PowerShell:
echo    
echo      cd "%INSTALL_DIR%"
echo      .buildenv\Scripts\activate.bat
echo      uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
echo.
echo 2. ACCEDER A LA APLICACION
echo    - Navegador: http://localhost:8000
echo    - Usuario: admin
echo    - Contrasena: admin
echo.
echo 3. CONFIGURAR (Opcional)
echo    - Edita: "%INSTALL_DIR%\.env.production"
echo    - Cambia credenciales, dominio, puertos, etc.
echo.
echo 4. ACCESO DESDE MOVILES (Tablet/Smartphone)
echo    - Abre navegador en tu dispositivo
echo    - Ingresa: http://IP-DEL-PC:8000
echo    - Ejemplo: http://192.168.1.100:8000
echo    - ¡Listo! Usa la app desde el movil
echo.
echo 5. DOCUMENTACION
echo    - Lee: "%INSTALL_DIR%\docs\MANUAL_COMPLETO.md"
echo    - O abre: "%INSTALL_DIR%\docs\MANUAL_COMPLETO.html"
echo.
echo.
echo SOPORTE:
echo =========
echo Email: support@dlatecnologia.com
echo Telefono: +57 1 2345678
echo WhatsApp: +57 310 5678901
echo.
echo.
echo ============================================================
echo  Gracias por elegir CafBarDLA ☕
echo ============================================================
echo.

pause
