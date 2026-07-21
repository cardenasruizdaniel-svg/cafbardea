Param(
    [switch]$DownAfterCheck
)

$ErrorActionPreference = "Stop"

function Write-Step {
    Param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    Param([string]$Message)
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Write-Warn {
    Param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    Param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Test-CommandAvailable {
    Param(
        [string]$Name,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Fail "$Name no esta instalado o no esta en PATH."
        Write-Host "Sugerencia: $InstallHint" -ForegroundColor Yellow
        exit 1
    }

    Write-Ok "$Name disponible"
}

function Wait-ForHealth {
    Param(
        [string]$Url,
        [int]$Retries = 30,
        [int]$DelaySeconds = 2
    )

    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Ok "Healthcheck exitoso en $Url"
                return
            }
        } catch {
            Start-Sleep -Seconds $DelaySeconds
        }

        Write-Host "Intento $i/$Retries esperando healthcheck..." -ForegroundColor DarkGray
    }

    Write-Fail "No se pudo validar healthcheck en $Url"
    exit 1
}

try {
    Write-Step "Verificando prerrequisitos"
    Test-CommandAvailable -Name "docker" -InstallHint "Instala Docker Desktop desde https://www.docker.com/products/docker-desktop"
    Test-CommandAvailable -Name "docker-compose" -InstallHint "Activa Docker Compose v1 o crea alias hacia Docker Compose v2"

    if (-not (Test-Path ".env.production")) {
        Write-Fail "No existe .env.production en la raiz del proyecto."
        Write-Host "Copia .env.production.example a .env.production y configura claves seguras." -ForegroundColor Yellow
        exit 1
    }
    Write-Ok "Archivo .env.production encontrado"

    Write-Step "Validando sintaxis de docker-compose"
    docker-compose config | Out-Null
    Write-Ok "docker-compose.yml valido"

    Write-Step "Construyendo imagen"
    docker-compose build

    Write-Step "Levantando servicios"
    docker-compose up -d

    Write-Step "Revisando estado de contenedores"
    docker-compose ps

    Write-Step "Esperando healthcheck HTTP"
    Wait-ForHealth -Url "http://localhost:8000/health"

    Write-Step "Mostrando ultimos logs del servicio web"
    docker-compose logs --tail=80 web

    Write-Ok "Validacion Docker de produccion completada"

    if ($DownAfterCheck) {
        Write-Step "Deteniendo servicios por parametro -DownAfterCheck"
        docker-compose down
        Write-Ok "Servicios detenidos"
    } else {
        Write-Warn "Servicios en ejecucion. Para detener: docker-compose down"
    }

} catch {
    Write-Fail "Error durante validacion Docker: $($_.Exception.Message)"
    exit 1
}
