@echo off
REM Crear paquete de distribución CafBarDLA

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Empaquetador de Distribución - CafBarDLA POS
echo ============================================================
echo.

set "PROJECT_ROOT=d:\CafBarDLA"
set "DIST_DIR=%PROJECT_ROOT%\dist"
set "PACKAGE_NAME=CafBarDLA-0.1.0-WindowsInstaller"
set "TEMP_PACKAGE=%DIST_DIR%\temp_package"

REM Crear directorio dist
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

echo [1/3] Copiando archivos...
echo.

REM Limpiar temporal
if exist "%TEMP_PACKAGE%" rmdir /s /q "%TEMP_PACKAGE%" >nul
mkdir "%TEMP_PACKAGE%"

REM Copiar archivos
echo Copiando: app\
xcopy "%PROJECT_ROOT%\app" "%TEMP_PACKAGE%\app" /E /I /Q >nul
echo Copiando: docs\
xcopy "%PROJECT_ROOT%\docs" "%TEMP_PACKAGE%\docs" /E /I /Q >nul
echo Copiando: scripts\
xcopy "%PROJECT_ROOT%\scripts" "%TEMP_PACKAGE%\scripts" /E /I /Q >nul
echo Copiando: alembic\
xcopy "%PROJECT_ROOT%\alembic" "%TEMP_PACKAGE%\alembic" /E /I /Q >nul
echo Copiando: installer\
xcopy "%PROJECT_ROOT%\installer" "%TEMP_PACKAGE%\installer" /E /I /Q >nul
echo Copiando archivos raíz...
copy "%PROJECT_ROOT%\requirements.txt" "%TEMP_PACKAGE%\" >nul
copy "%PROJECT_ROOT%\alembic.ini" "%TEMP_PACKAGE%\" >nul
copy "%PROJECT_ROOT%\launcher.py" "%TEMP_PACKAGE%\" >nul
copy "%PROJECT_ROOT%\.env.production.example" "%TEMP_PACKAGE%\" >nul
copy "%PROJECT_ROOT%\README.md" "%TEMP_PACKAGE%\" >nul

echo ✓ Archivos copiados
echo.

REM Crear README.txt
echo [2/3] Creando archivo de instrucciones...
echo.

(
echo.
echo ===============================================================================
echo    CafBarDLA POS - Sistema de Punto de Venta - Version 0.1.0
echo    DLA Tecnologia - support@dlatecnologia.com
echo ===============================================================================
echo.
echo CONTENIDO:
echo  - app/              Codigo fuente
echo  - docs/             Documentacion completa
echo  - scripts/          Scripts de instalacion
echo  - alembic/          Migraciones de base de datos
echo  - installer/        Instalador automatico
echo.
echo.
echo INSTALACION RAPIDA:
echo ==================
echo.
echo 1. Ejecuta como Administrador:
echo    installer\InstalarCafBarDLA.bat
echo.
echo 2. Sigue las instrucciones
echo.
echo 3. ¡Listo! Accede a http://localhost:8000
echo.
echo.
echo DOCUMENTACION:
echo ================
echo Ver archivos en la carpeta docs/ para:
echo  - MANUAL_COMPLETO.pdf  - Guia completa de instalacion
echo  - CLOUD_DEPLOYMENT_GUIDE.md - Deploy en la nube
echo.
echo.
echo CREDENCIALES POR DEFECTO:
echo ==========================
echo Usuario: admin
echo Contrasena: admin
echo.
echo ⚠ IMPORTANTE: Cambiar contrasena en la primera conexion!
echo.
echo.
echo REQUISITOS:
echo ==============
echo - Windows 10 o superior
echo - Python 3.10+ (https://www.python.org/downloads/)
echo - 2 GB de espacio libre
echo.
echo.
echo SOPORTE:
echo =========
echo Email: support@dlatecnologia.com
echo Telefono: +57 1 2345678
echo.
) > "%TEMP_PACKAGE%\INSTALAR_PRIMERO.txt"

echo ✓ Archivo de instrucciones creado
echo.

REM Crear ZIP usando PowerShell
echo [3/3] Creando archivo ZIP...
echo.

powershell -NoProfile -Command "^
    Add-Type -Assembly 'System.IO.Compression.FileSystem'; ^
    [System.IO.Compression.ZipFile]::CreateFromDirectory('%TEMP_PACKAGE%', '%DIST_DIR%\%PACKAGE_NAME%.zip', [System.IO.Compression.CompressionLevel]::Optimal, $false) ^
" 2>nul

REM Verificar si se creo el ZIP
if exist "%DIST_DIR%\%PACKAGE_NAME%.zip" (
    for /f "usebackq tokens=1,2" %%A in (`powershell -NoProfile -Command "Write-Host ([math]::Round((Get-Item '%DIST_DIR%\%PACKAGE_NAME%.zip').Length / 1MB, 2))"`) do set SIZE_MB=%%A
    
    echo ✓ ZIP creado: %SIZE_MB% MB
    echo.
    echo ============================================================
    echo ✅ PAQUETE LISTO PARA DISTRIBUIR!
    echo ============================================================
    echo.
    echo 📦 Archivo: %DIST_DIR%\%PACKAGE_NAME%.zip
    echo.
    echo 📋 Instrucciones para usuarios:
    echo    1. Descargar: %PACKAGE_NAME%.zip
    echo    2. Extraer en carpeta deseada
    echo    3. Leer: INSTALAR_PRIMERO.txt
    echo    4. Ejecutar: installer\InstalarCafBarDLA.bat (como Admin)
    echo    5. Acceder a: http://localhost:8000
    echo.
    
    REM Limpiar temporal
    rmdir /s /q "%TEMP_PACKAGE%" >nul
    
) else (
    echo ❌ Error creando ZIP
    rmdir /s /q "%TEMP_PACKAGE%" >nul
    pause
    exit /b 1
)

echo.
pause
