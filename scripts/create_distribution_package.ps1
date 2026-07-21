# Crear paquete de distribución de CafBarDLA
# Este script crea un ZIP listo para distribuir

$ProjectRoot = "d:\CafBarDLA"
$DistDir = "$ProjectRoot\dist"
$PackageName = "CafBarDLA-0.1.0-WindowsInstaller"
$PackagePath = "$DistDir\$PackageName.zip"

Write-Host "`n" + ("="*60) -ForegroundColor Cyan
Write-Host "📦 Empaquetador de Distribución CafBarDLA" -ForegroundColor Cyan
Write-Host ("="*60) -ForegroundColor Cyan
Write-Host ""

# Crear directorio dist
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
}

Write-Host "📋 Archivos a incluir:" -ForegroundColor Yellow
Write-Host ""

# Archivos/carpetas a incluir
$ItemsToInclude = @(
    @{ Path = "$ProjectRoot\app"; Name = "app" }
    @{ Path = "$ProjectRoot\docs"; Name = "docs" }
    @{ Path = "$ProjectRoot\scripts"; Name = "scripts" }
    @{ Path = "$ProjectRoot\alembic"; Name = "alembic" }
    @{ Path = "$ProjectRoot\installer"; Name = "installer" }
    @{ Path = "$ProjectRoot\requirements.txt"; Name = "requirements.txt" }
    @{ Path = "$ProjectRoot\alembic.ini"; Name = "alembic.ini" }
    @{ Path = "$ProjectRoot\launcher.py"; Name = "launcher.py" }
    @{ Path = "$ProjectRoot\.env.production.example"; Name = ".env.production.example" }
    @{ Path = "$ProjectRoot\README.md"; Name = "README.md" }
)

# Crear archivo temporal para el ZIP
$TempDir = "$DistDir\temp_package"
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

Write-Host "1️⃣  Copiando archivos..." -ForegroundColor Cyan

foreach ($Item in $ItemsToInclude) {
    if (Test-Path $Item.Path) {
        $DestPath = "$TempDir\$($Item.Name)"
        if ((Get-Item $Item.Path).PSIsContainer) {
            Copy-Item $Item.Path -Destination $DestPath -Recurse -Force | Out-Null
            Write-Host "   ✓ $($Item.Name)/ copiado" -ForegroundColor Green
        } else {
            Copy-Item $Item.Path -Destination $DestPath -Force | Out-Null
            Write-Host "   ✓ $($Item.Name) copiado" -ForegroundColor Green
        }
    }
}

# Crear archivo README.txt con instrucciones de instalación
$ReadmeContent = @"
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    CafBarDLA POS - Sistema de Punto de Venta                ║
║                                                                              ║
║                               Versión 0.1.0                                 ║
║                                                                              ║
║                    Empresa: DLA Tecnología                                   ║
║                    Soporte: support@dlatecnologia.com                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝


📋 CONTENIDO DEL PAQUETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• app/                          - Código fuente de la aplicación
• docs/                         - Documentación completa (PDF, Manual)
• scripts/                      - Scripts de instalación y administración
• alembic/                      - Migraciones de base de datos
• installer/                    - Instalador interactivo (.bat)
• requirements.txt              - Dependencias Python
• alembic.ini                   - Configuración de migraciones
• launcher.py                   - Script de inicio
• .env.production.example       - Plantilla de configuración


🚀 INSTALACIÓN RÁPIDA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPCIÓN 1: Instalador Automático (RECOMENDADO)
──────────────────────────────────────────────

1. Haz doble clic en: installer\InstalarCafBarDLA.bat
   (Ejecutar como administrador)

2. Sigue las instrucciones en pantalla

3. ¡Listo! La aplicación estará instalada

⚠ REQUISITO: Python 3.10+ instalado en el sistema
   Descarga desde: https://www.python.org/downloads/


OPCIÓN 2: Instalación Manual
──────────────────────────────

1. Abre PowerShell como Administrador

2. Navega a la carpeta del proyecto:
   cd C:\donde\descargaste\CafBarDLA

3. Crea el entorno virtual:
   python -m venv .buildenv

4. Activa el entorno virtual:
   .buildenv\Scripts\Activate.ps1

5. Instala dependencias:
   pip install -r requirements.txt

6. Crea el archivo de configuración:
   copy .env.production.example .env.production

7. Edita la configuración (opcional):
   notepad .env.production

8. Inicializa la base de datos:
   alembic upgrade head

9. Ejecuta la aplicación:
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

10. Accede a: http://localhost:8000


📖 DOCUMENTACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ver archivos en la carpeta "docs/":

• MANUAL_COMPLETO.pdf
  └─ Guía completa de instalación, configuración y funcionamiento

• CLOUD_DEPLOYMENT_GUIDE.md
  └─ Instrucciones para desplegar en la nube (Docker, Heroku, AWS, etc.)

• MANUAL_USUARIO.md
  └─ Manual para usuarios finales

• MANUAL_TECNICO.md
  └─ Documentación técnica para desarrolladores

• GO_LIVE_CHECKLIST.md
  └─ Checklist antes de ir a producción


🔐 CREDENCIALES POR DEFECTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Usuario: admin
Contraseña: admin

⚠ IMPORTANTE: Cambiar contraseña en la primera conexión!


🌐 ACCESO A LA APLICACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Después de iniciar la aplicación, accede a:

Interfaz Web:        http://localhost:8000
Documentación API:   http://localhost:8000/docs
ReDoc:               http://localhost:8000/redoc
OpenAPI JSON:        http://localhost:8000/openapi.json


📱 ACCESO DESDE OTROS DISPOSITIVOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Desde tablet/smartphone en la misma red:

http://IP-DEL-SERVIDOR:8000

Ejemplo: http://192.168.1.100:8000


❓ TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P: "Python no está instalado"
R: Descarga desde https://www.python.org/downloads/
   Asegúrate de marcar "Add Python to PATH" durante la instalación

P: "Puerto 8000 ya está en uso"
R: Usa otro puerto:
   uvicorn app.main:app --port 8001

P: "Error de permisos"
R: Ejecuta PowerShell como Administrador
   Click derecho → "Ejecutar como administrador"

P: "Base de datos corrupta"
R: Elimina el archivo cafbardla_prod.db y ejecuta:
   alembic upgrade head


💬 SOPORTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Email:   support@dlatecnologia.com
Teléfono: +57 1 2345678
WhatsApp: +57 310 5678901
Portal:   https://support.dlatecnologia.com


════════════════════════════════════════════════════════════════════════════════

Gracias por elegir CafBarDLA ☕

════════════════════════════════════════════════════════════════════════════════
"@

$ReadmeContent | Out-File -FilePath "$TempDir\INSTALAR_PRIMERO.txt" -Encoding UTF8
Write-Host "   ✓ INSTALAR_PRIMERO.txt creado" -ForegroundColor Green

Write-Host ""
Write-Host "2️⃣  Creando archivo ZIP..." -ForegroundColor Cyan

# Crear ZIP usando PowerShell
if (Get-Command Compress-Archive -ErrorAction SilentlyContinue) {
    # Usar Compress-Archive (Windows 10+)
    Compress-Archive -Path "$TempDir\*" -DestinationPath $PackagePath -Force
} else {
    # Alternativa: usar System.IO.Compression
    [System.Reflection.Assembly]::LoadWithPartialName("System.IO.Compression.FileSystem") | Out-Null
    [System.IO.Compression.ZipFile]::CreateFromDirectory($TempDir, $PackagePath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
}

# Limpiar temporal
Remove-Item $TempDir -Recurse -Force

# Verificar
if (Test-Path $PackagePath) {
    $SizeMB = (Get-Item $PackagePath).Length / (1MB)
    
    Write-Host "✓ ZIP creado`n" -ForegroundColor Green
    
    Write-Host ("="*60) -ForegroundColor Green
    Write-Host "✅ PAQUETE LISTO PARA DISTRIBUIR!" -ForegroundColor Green
    Write-Host ("="*60) -ForegroundColor Green
    Write-Host ""
    
    Write-Host "📦 Información:" -ForegroundColor Cyan
    Write-Host "   Nombre: $PackageName.zip" -ForegroundColor White
    Write-Host "   Ubicación: $PackagePath" -ForegroundColor White
    Write-Host "   Tamaño: $([math]::Round($SizeMB, 2)) MB" -ForegroundColor White
    Write-Host ""
    
    Write-Host "📋 Instrucciones para el usuario:" -ForegroundColor Cyan
    Write-Host "   1. Descargar: $PackageName.zip" -ForegroundColor White
    Write-Host "   2. Extraer en la carpeta deseada (ej: C:\CafBarDLA)" -ForegroundColor White
    Write-Host "   3. Abrir carpeta extraída" -ForegroundColor White
    Write-Host "   4. Leer: INSTALAR_PRIMERO.txt" -ForegroundColor White
    Write-Host "   5. Ejecutar: installer\InstalarCafBarDLA.bat como Administrador" -ForegroundColor White
    Write-Host ""
    
    Write-Host "🚀 Para compartir:" -ForegroundColor Cyan
    Write-Host "   Enviar archivo: $PackagePath" -ForegroundColor Gray
    Write-Host ""
    
} else {
    Write-Host "❌ Error creando ZIP`n" -ForegroundColor Red
    exit 1
}

Write-Host ""
