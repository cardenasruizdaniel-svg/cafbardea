# 📱 FASE 7: Mobile API Endpoints - Planning & Implementation Guide

## Overview
FASE 7 implements a dedicated mobile API layer for the waiter/mesero app. This enables restaurant staff to take orders on mobile devices while maintaining real-time synchronization with the main POS system via WebSocket.

## Objectives

1. **JWT Authentication:** Secure mobile app authentication independent of web sessions
2. **Mobile-Optimized API:** Lightweight endpoints tailored for mobile client needs
3. **Device Type Support:** Register app_mesero device in WebSocket infrastructure
4. **Offline Support:** Queue orders for sync when connection restored
5. **Push Notifications:** Real-time alerts for order status changes

## Architecture

### Device Types (Updated)
```
web        → Main POS workstations
app_mesero → Waiter mobile app (NEW - FASE 7)
kds        → Kitchen Display System
cajero     → Cash register terminals
```

### Token Formats

**Web/KDS/Cajero (Session-based):**
```
{usuario_id}:{sucursal_id}:{dispositivo}
```

**Mobile (JWT-based):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
{
    "sub": "usuario_id:app_mesero",
    "sucursal_id": 1,
    "dispositivo": "app_mesero",
    "exp": 1703078400,
    "iat": 1703001200,
    "device_id": "uuid-of-device"
}
```

## Implementation Plan

### Step 1: JWT Authentication Service

**File:** `app/services/jwt_service.py` (NEW)

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os

class JWTService:
    SECRET_KEY = os.getenv("JWT_SECRET", "tu-clave-secreta-fase7")
    ALGORITHM = "HS256"
    TOKEN_EXPIRE_HOURS = 24
    
    @classmethod
    def create_token(cls, usuario_id: int, sucursal_id: int, device_id: str) -> str:
        """Crea JWT token para app móvil"""
        expire = datetime.utcnow() + timedelta(hours=cls.TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": f"{usuario_id}:app_mesero",
            "sucursal_id": sucursal_id,
            "dispositivo": "app_mesero",
            "device_id": device_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def verify_token(cls, token: str) -> dict:
        """Verifica y decodifica JWT token"""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except JWTError:
            return None
```

### Step 2: Mobile API Routes

**File:** `app/routes/mobile_api.py` (NEW)

**Endpoints:**

#### POST `/api/v1/mobile/auth/login`
```json
Request:
{
    "usuario": "mesero1",
    "password": "pass123",
    "device_id": "uuid-device-123"
}

Response:
{
    "access_token": "eyJhbGc...",
    "token_type": "bearer",
    "usuario_id": 5,
    "usuario_nombre": "Carlos Mesero",
    "sucursal_id": 1,
    "rol": "mesero",
    "dispositivo": "app_mesero"
}
```

#### GET `/api/v1/mobile/mesas`
```json
Response:
{
    "mesas": [
        {
            "id": 1,
            "numero": "M01",
            "estado": "libre",
            "capacidad": 4,
            "notas": ""
        },
        {
            "id": 2,
            "numero": "M02",
            "estado": "ocupada",
            "capacidad": 2,
            "venta_id": 15
        }
    ]
}
```

#### POST `/api/v1/mobile/comandas`
```json
Request:
{
    "mesa_id": 1,
    "productos": [
        {"producto_id": 5, "cantidad": 2, "notas": "Sin hielo"},
        {"producto_id": 8, "cantidad": 1, "notas": ""}
    ]
}

Response:
{
    "venta_id": 45,
    "mesa_id": 1,
    "estado": "abierta",
    "productos": [...],
    "total": 45.50,
    "timestamp": "2024-12-19T10:30:00"
}
```

#### GET `/api/v1/mobile/comandas/{venta_id}`
```json
Response:
{
    "venta_id": 45,
    "estado": "abierta",
    "productos": [
        {
            "producto_id": 5,
            "nombre": "Café Americano",
            "cantidad": 2,
            "precio": 12.50,
            "subtotal": 25.00,
            "estado_preparacion": "preparando"
        }
    ],
    "total": 45.50,
    "ultima_actualizacion": "2024-12-19T10:32:15"
}
```

#### POST `/api/v1/mobile/comandas/{venta_id}/agregar-producto`
```json
Request:
{
    "producto_id": 10,
    "cantidad": 1,
    "notas": "Temperatura ambiente"
}

Response:
{
    "venta_id": 45,
    "producto_id": 10,
    "estado": "añadido",
    "nuevoPrecio": 57.00
}
```

#### POST `/api/v1/mobile/comandas/{venta_id}/pagar`
```json
Request:
{
    "medio_pago": "efectivo",
    "cliente_id": null,
    "monto_efectivo": 60.00
}

Response:
{
    "venta_id": 45,
    "factura_id": "FAC-2024-001234",
    "estado": "pagada",
    "total": 57.00,
    "cambio": 3.00,
    "timestamp": "2024-12-19T10:35:00"
}
```

#### GET `/api/v1/mobile/productos`
```json
Response:
{
    "productos": [
        {
            "id": 1,
            "nombre": "Café Americano",
            "precio": 12.50,
            "descripcion": "Café 12oz",
            "categoria": "bebidas",
            "disponible": true,
            "imagen_url": "/images/cafe-americano.jpg"
        }
    ]
}
```

#### GET `/api/v1/mobile/notificaciones`
```
WebSocket connection: /ws-mobile/{jwt_token}
Events:
- comanda.lista (orden lista para entregar)
- comanda.cancelada (orden cancelada en cocina)
- mesa.reservada (mesa fue reservada)
- venta.actualizada (cambios en la comanda)
```

### Step 3: Mobile Device Registration

**Modelo actualizado:** `ConexionWebSocket`

```python
# Añadir campos
dispositivo: str  # 'app_mesero'
jwt_token: Optional[str]  # Token JWT para mobile
device_fingerprint: Optional[str]  # ID único del dispositivo
sistema_operativo: Optional[str]  # 'iOS' o 'Android'
version_app: Optional[str]  # Versión de la app
```

### Step 4: Bearer Token Middleware

**Middleware:** `app/middleware.py` (Extend existing)

```python
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import re

# Bearer token validator para mobile
bearer_scheme = HTTPBearer()

async def validate_jwt_middleware(request: Request, call_next):
    """Valida JWT tokens para endpoints /api/v1/mobile/*"""
    if request.url.path.startswith("/api/v1/mobile"):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
        
        token = auth_header.replace("Bearer ", "")
        payload = JWTService.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        request.state.usuario_id = int(payload["sub"].split(":")[0])
        request.state.sucursal_id = payload["sucursal_id"]
        request.state.dispositivo = payload["dispositivo"]
        request.state.device_id = payload.get("device_id")
    
    return await call_next(request)
```

### Step 5: Offline Sync Support

**Model:** `app/models_enterprise.py` (Extend)

```python
class EventoPendienteSync(Base):
    """Eventos pendientes de sincronización (offline support)"""
    __tablename__ = "eventos_pendientes_sync"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    dispositivo_id: Mapped[str]  # device_id del app
    evento_tipo: Mapped[str]  # 'comanda.creada', 'comanda.pagada'
    entidad: Mapped[str]  # 'venta', 'mesa'
    entidad_id: Mapped[int]
    datos_evento: Mapped[dict] = mapped_column(JSON)
    creado_en: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    sincronizado: Mapped[bool] = mapped_column(default=False)
    intentos_sync: Mapped[int] = mapped_column(default=0)
    ultimo_intento: Mapped[Optional[datetime]]
```

### Step 6: Tests

**File:** `tests/enterprise/test_fase7_mobile_api.py`

```python
import pytest
from fastapi.testclient import TestClient

class TestMobileAuth:
    """Tests de autenticación JWT para mobile"""
    
    def test_jwt_login_success(self, client):
        """Login exitoso genera JWT token"""
        response = client.post("/api/v1/mobile/auth/login", json={
            "usuario": "mesero1",
            "password": "pass123",
            "device_id": "device-uuid-123"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    def test_jwt_login_invalid_credentials(self, client):
        """Login con credenciales inválidas falla"""
        response = client.post("/api/v1/mobile/auth/login", json={
            "usuario": "mesero1",
            "password": "wrong_password",
            "device_id": "device-uuid-123"
        })
        assert response.status_code == 401

class TestMobileAPI:
    """Tests de endpoints móviles"""
    
    def test_get_mesas_requires_auth(self, client):
        """GET /mesas requiere JWT token"""
        response = client.get("/api/v1/mobile/mesas")
        assert response.status_code == 401
    
    def test_get_mesas_with_token(self, client, mobile_token):
        """GET /mesas con token válido"""
        response = client.get(
            "/api/v1/mobile/mesas",
            headers={"Authorization": f"Bearer {mobile_token}"}
        )
        assert response.status_code == 200
        assert "mesas" in response.json()

class TestOfflineSync:
    """Tests de sincronización offline"""
    
    def test_eventos_pendientes_sync_stored(self, db):
        """Eventos creados offline se almacenan para sync"""
        evento = EventoPendienteSync(
            dispositivo_id="device-123",
            evento_tipo="comanda.creada",
            entidad="venta",
            entidad_id=45,
            datos_evento={"mesa_id": 1}
        )
        db.add(evento)
        db.commit()
        assert evento.id is not None
        assert not evento.sincronizado
```

## Implementation Timeline

### Week 1: Core API & Auth
- JWT Service implementation
- Mobile login endpoint
- Bearer token middleware
- Device registration

### Week 2: Core Endpoints
- GET mesas (floor plan)
- POST comandas (create order)
- POST agregar-producto (add item)
- GET productos (menu)

### Week 3: Order Management
- GET comandas/{id} (order details)
- POST comandas/{id}/pagar (payment)
- DELETE comandas/{id}/producto (remove item)

### Week 4: Sync & Notifications
- Offline event storage
- Reconnection sync logic
- WebSocket notifications
- Test suite

## Expected Metrics

| Metric | Target |
|--------|--------|
| New API Endpoints | 8+ |
| JWT Token Expiry | 24 hours |
| Offline Event Limit | 100 pending events |
| API Response Time | <200ms |
| Test Coverage | 100% |
| Tests Expected | 15-20 |

## Dependencies to Add

```bash
pip install python-jose[cryptography]
pip install pydantic-extra-types  # Para validación de device_id
```

## Integration Points

- ✅ WebSocket manager (device type: app_mesero)
- ✅ RBAC system (role-based access for meseros)
- ✅ Database models (new EventoPendienteSync)
- ✅ Event broadcaster (mobile notifications)
- ✅ Authentication middleware (JWT validation)

## Security Considerations

1. **Token Expiry:** 24-hour expiry for mobile tokens
2. **Device Fingerprinting:** Prevent token reuse on different devices
3. **Rate Limiting:** Max 100 API calls/minute per device
4. **Encrypted Payloads:** Sensitive data encrypted in offline queue
5. **HTTPS Only:** Enforce HTTPS for all mobile API endpoints
6. **CORS:** Allow only registered mobile app origins

## Deployment Checklist

- [ ] Add JWT_SECRET to environment variables
- [ ] Database migrations for EventoPendienteSync
- [ ] SSL/TLS certificates for HTTPS
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Mobile app development guide
- [ ] Load testing (10+ concurrent mobile users)
- [ ] Error handling & logging
- [ ] Monitoring dashboard

## Next Steps

After FASE 7 completion:
- **FASE 8:** Kitchen Display System (KDS)
- **FASE 9:** Complete multi-device integration and stress testing

## References

- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [WebSocket for Mobile Push](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Offline-First Architecture](https://offlinefirst.org/)

---
**Document Version:** 1.0
**Last Updated:** 2024-12-19
**Status:** Ready for Implementation
