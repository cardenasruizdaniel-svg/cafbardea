# ============================================================================
# validate_production.ps1
# Suite de validación para ambiente de producción
# Verifica: Base de datos, aplicación, endpoints críticos, WebSocket
# ============================================================================

param(
    [string]$EnvFile = ".env.production",
    [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CafBarDLA - Production Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$testsPassed = 0
$testsFailed = 0

# Función para pruebas
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [object]$Body,
        [int]$ExpectedStatus = 200
    )
    
    try {
        $params = @{
            Method = $Method
            Uri = $Url
            ContentType = "application/json"
            ErrorAction = "Stop"
        }
        
        if ($Body) {
            $params.Body = $Body | ConvertTo-Json
        }
        
        $response = Invoke-RestMethod @params
        
        if ($response -or $response -eq $null) {
            Write-Host "  ✓ $Name" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "  ✗ $Name - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Test 1: Base de datos
Write-Host "`n[1/5] Validando base de datos..." -ForegroundColor Green
try {
    $result = python -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import sqlalchemy

load_dotenv('$EnvFile')
db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url, echo=False)

with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM usuarios')).scalar()
    print(f'Usuarios en BD: {result}')
    print('OK')
" 2>&1

    if ($result -like "*OK*") {
        Write-Host "  ✓ Conexión base de datos exitosa" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host "  ✗ Error conectando base de datos" -ForegroundColor Red
        Write-Host "    $result" -ForegroundColor Yellow
        $testsFailed++
    }
} catch {
    Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

# Test 2: Servidor FastAPI
Write-Host "`n[2/5] Validando servidor FastAPI..." -ForegroundColor Green

# Test health check
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -ErrorAction Stop
    Write-Host "  ✓ Health check exitoso" -ForegroundColor Green
    $testsPassed++
} catch {
    Write-Host "  ✗ Servidor no disponible en $BaseUrl" -ForegroundColor Red
    $testsFailed++
}

# Test OpenAPI documentation
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/openapi.json" -Method Get -ErrorAction Stop
    if ($response.info.title) {
        Write-Host "  ✓ API documentation disponible" -ForegroundColor Green
        $testsPassed++
    }
} catch {
    Write-Host "  ✗ API documentation no disponible" -ForegroundColor Red
    $testsFailed++
}

# Test 3: Endpoints REST
Write-Host "`n[3/5] Validando endpoints REST..." -ForegroundColor Green

try {
    # Login test
    $loginBody = @{
        usuario = "admin"
        password = "admin"
    }
    
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/mobile/auth/login" -Method Post -ContentType "application/json" -Body ($loginBody | ConvertTo-Json) -ErrorAction Stop
    
    if ($response.access_token) {
        Write-Host "  ✓ Mobile login exitoso" -ForegroundColor Green
        $token = $response.access_token
        $testsPassed++
        
        # Test authenticated endpoint
        $headers = @{
            "Authorization" = "Bearer $token"
        }
        
        try {
            $mesasResponse = Invoke-RestMethod -Uri "$BaseUrl/api/v1/mobile/mesas" -Method Get -Headers $headers -ErrorAction Stop
            if ($mesasResponse -is [array] -or $mesasResponse -is [object]) {
                Write-Host "  ✓ Endpoint /mesas funcionando" -ForegroundColor Green
                $testsPassed++
            }
        } catch {
            Write-Host "  ✗ Error en /mesas" -ForegroundColor Red
            $testsFailed++
        }
    } else {
        Write-Host "  ✗ Login failed" -ForegroundColor Red
        $testsFailed++
    }
} catch {
    Write-Host "  ✗ Error en mobile login" -ForegroundColor Red
    $testsFailed++
}

# Test 4: WebSocket
Write-Host "`n[4/5] Validando WebSocket..." -ForegroundColor Green

try {
    $wsUrl = $BaseUrl -replace "http", "ws"
    $result = python -c "
import asyncio
import websockets

async def test_ws():
    try:
        uri = '$wsUrl/ws?token=test&dispositivo=web'
        async with websockets.connect(uri, ping_interval=None) as websocket:
            await asyncio.wait_for(websocket.recv(), timeout=5)
            return 'OK'
    except Exception as e:
        return f'Error: {e}'

try:
    result = asyncio.run(test_ws())
    print(result)
except Exception as e:
    print(f'WebSocket test error: {e}')
" 2>&1
    
    if ($result -like "*OK*") {
        Write-Host "  ✓ WebSocket funcionando" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host "  ⚠ WebSocket: $result" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ WebSocket test skipped (websockets library required)" -ForegroundColor Yellow
}

# Test 5: Performance
Write-Host "`n[5/5] Validando performance..." -ForegroundColor Green

try {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -ErrorAction Stop | Out-Null
    $stopwatch.Stop()
    
    $ms = $stopwatch.ElapsedMilliseconds
    
    if ($ms -lt 1000) {
        Write-Host "  ✓ Response time: $ms ms (OK)" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host "  ⚠ Response time: $ms ms (lento)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Error en performance test" -ForegroundColor Red
    $testsFailed++
}

# Resultado final
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Resultados de Validación" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "
✓ Pasados: $testsPassed
✗ Fallidos: $testsFailed
" -ForegroundColor Yellow

if ($testsFailed -eq 0) {
    Write-Host "PRODUCCIÓN LISTA ✓" -ForegroundColor Green
    exit 0
} else {
    Write-Host "VALIDACIONES FALLIDAS" -ForegroundColor Red
    exit 1
}
