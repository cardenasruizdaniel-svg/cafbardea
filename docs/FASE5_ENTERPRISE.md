# FASE 5: Enterprise Infrastructure - Guía de Implementación

## 🚀 Resumen de lo Implementado

Se ha completado la integración de la infraestructura enterprise para soporte de:
- ✅ Real-time Synchronization (WebSocket)
- ✅ Multi-Tenancy (Sucursales)
- ✅ Role-Based Access Control (RBAC)
- ✅ Connection Management
- ✅ Event Auditing

---

## 📦 Nuevos Archivos Creados

### 1. **app/models_enterprise.py** (367 líneas)
Modelos ORM para infraestructura enterprise:
- `Sucursal`: Multi-tenancy - múltiples localidades por empresa
- `Rol`: Roles predefinidos del sistema
- `Permiso`: Permisos granulares
- `UsuarioRol`: M2M para soporte de múltiples roles
- `ConexionWebSocket`: Rastreo de conexiones activas
- `EventoSincronizacion`: Auditoría de cambios

**Tablas creadas**:
```
- sucursales
- roles
- permisos
- rol_permisos (M2M)
- usuario_roles
- conexiones_websocket
- eventos_sincronizacion
```

### 2. **app/websocket_manager.py** (387 líneas)
Gestor de conexiones WebSocket en tiempo real:
- `MensajeWS`: Dataclass para serialización de mensajes
- `ConnectionManager`: Gestión de conexiones y broadcasting
- `EventBroadcaster`: Sistema de eventos con handlers
- Funcionalidades:
  - Broadcast a toda una sucursal
  - Broadcast a dispositivos específicos (web, app_mesero, kds)
  - Envío a usuario específico
  - Estadísticas de conexiones

### 3. **app/services/rbac_service.py** (251 líneas)
Sistema RBAC (Role-Based Access Control):
- `PermisosService`: Validación granular de permisos
- `RolService`: Gestión de roles y permisos predefinidos
- `inicializar_rbac()`: Setup de infraestructura RBAC

**Roles predefinidos creados**:
- administrador (acceso total)
- gerente (operaciones, reportes)
- cajero (caja, cobros)
- mesero (pedidos, cobro)
- cocinero (comandas)
- bartender (comandas de bar)

**Permisos implementados** (20+):
- ventas.* (crear, editar, eliminar, ver, cobrar)
- caja.* (abrir, cerrar, arqueo, ver)
- mesas.* (gestionar, cambiar estado)
- usuarios.* (crear, editar, eliminar, gestionar roles)
- reportes.* (ver, exportar)
- configuracion.* (editar, ver)
- admin.* (acceso administrativo total)

### 4. **app/routes/websocket.py** (170 líneas)
Endpoints WebSocket para sincronización:
- `@router.websocket("/ws/{token}")`: Endpoint principal WebSocket
- `procesar_evento_ws()`: Procesador de eventos
- `@router.get("/api/v1/websocket/status")`: Status de conexiones
- `@router.get("/api/v1/websocket/usuarios-conectados/{sucursal_id}")`: Usuarios activos

### 5. **app/enterprise_init.py** (40 líneas)
Inicializador de base de datos enterprise:
- `crear_tablas_enterprise()`: Crea todas las nuevas tablas
- `inicializar_datos_enterprise()`: Seed de datos iniciales
- `setup_enterprise_database()`: Setup completo

### 6. **tests/enterprise/test_fase5.py** (432 líneas)
Suite de pruebas para FASE 5:
- Tests de RBAC (permisos, roles, comodines)
- Tests de Sucursal (multi-tenancy)
- Tests de WebSocket (conexiones, mensajes)
- Tests de integración (múltiples roles en sucursales)

---

## 🔗 Integración en app/main.py

Se realizaron los siguientes cambios:

```python
# Nuevos imports
from .models_enterprise import Sucursal, Rol, Permiso, UsuarioRol, ConexionWebSocket, EventoSincronizacion
from .routes.websocket import router as websocket_router
from .enterprise_init import setup_enterprise_database
from .services.rbac_service import inicializar_rbac

# En el lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
        with Session(engine) as db: seed(db)
    
    # Inicializar FASE 5
    setup_enterprise_database()
    with Session(engine) as db:
        inicializar_rbac(db)

# Registrar router WebSocket
app.include_router(websocket_router, tags=["websocket"])
```

---

## 🧪 Testing

### Ejecutar Tests Enterprise
```bash
cd d:\CafBarDLA
python -m pytest tests/enterprise/test_fase5.py -v
```

### Tests Incluidos
- ✅ RBAC: Creación de permisos y roles
- ✅ RBAC: Validación de permisos
- ✅ RBAC: Permisos comodín (ventas.*)
- ✅ Sucursal: Creación de sucursales
- ✅ Sucursal: Multi-sucursal por empresa
- ✅ WebSocket: Creación de mensajes
- ✅ WebSocket: Conexión y desconexión
- ✅ WebSocket: Estadísticas
- ✅ Integración: Usuario con múltiples roles en sucursales

---

## 🔌 Uso de WebSocket

### Conectarse a WebSocket
```javascript
// Formato del token: {usuario_id}:{sucursal_id}:{dispositivo}
const token = "1:1:web";  // Usuario 1, Sucursal 1, Dispositivo web
const ws = new WebSocket(`ws://127.0.0.1:8000/ws/${token}`);

ws.onopen = () => console.log("Conectado");
ws.onmessage = (event) => {
    const mensaje = JSON.parse(event.data);
    console.log("Evento:", mensaje.evento);
    console.log("Datos:", mensaje.datos);
};
```

### Dispositivos Soportados
- `web`: POS Web
- `app_mesero`: App para Meseros
- `kds`: Kitchen Display System
- `cajero`: Terminal de caja

### Eventos Implementados
```
- usuario.conectado
- usuario.desconectado
- venta.actualizar
- mesa.cambio_estado
- comanda.estado
- caja.*
- (extensible a nuevos eventos)
```

---

## 🛡️ Uso de RBAC

### Validar Permiso en Ruta
```python
from app.services.rbac_service import PermisosService
from app.database import get_db

@app.post("/api/v1/ventas/crear")
def crear_venta(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.session.get("usuario_id")
    permisos = PermisosService(db)
    
    # Validar permiso específico
    permisos.requiere_permiso(usuario_id, "ventas.crear")
    
    # Lógica de creación...
    return {"exito": True}
```

### Verificaciones de Permiso
```python
# Tiene un permiso específico
if permisos.tiene_permiso(usuario_id, "ventas.crear"):
    # hacer algo

# Tiene alguno de los permisos
if permisos.tiene_alguno(usuario_id, ["caja.abrir", "caja.cerrar"]):
    # hacer algo

# Tiene todos los permisos
if permisos.tiene_todos(usuario_id, ["ventas.crear", "ventas.editar"]):
    # hacer algo

# Permisos comodín: "admin.*" coincide con "admin.cualquier_cosa"
```

---

## 📊 Estadísticas de Conexión

### Obtener Estado de WebSocket
```bash
curl http://127.0.0.1:8000/api/v1/websocket/status
```

Respuesta:
```json
{
  "estado": "activo",
  "timestamp": "2026-07-19T12:45:30.930000",
  "total_conexiones": 3,
  "total_usuarios_conectados": 2,
  "sucursales_activas": 1
}
```

### Usuarios Conectados por Sucursal
```bash
curl http://127.0.0.1:8000/api/v1/websocket/usuarios-conectados/1
```

Respuesta:
```json
{
  "sucursal_id": 1,
  "usuarios_conectados": {
    "1": "web",
    "2": "app_mesero"
  },
  "total": 2
}
```

---

## 🗂️ Estructura de Directorios

```
app/
├── models.py (existente, 25 modelos)
├── models_enterprise.py (NEW - 6 nuevos modelos)
├── websocket_manager.py (NEW - Gestor de WebSocket)
├── enterprise_init.py (NEW - Inicializador)
├── services/
│   ├── __init__.py
│   └── rbac_service.py (NEW - Sistema RBAC)
├── routes/
│   ├── __init__.py
│   └── websocket.py (NEW - Endpoints WebSocket)
└── main.py (modificado para integrar FASE 5)

tests/
└── enterprise/
    ├── __init__.py
    └── test_fase5.py (NEW - Tests FASE 5)
```

---

## 🔄 Flujo de Sincronización en Tiempo Real

```
1. Cliente se conecta a /ws/{token}
   └─> ConnectionManager.connect() registra conexión
   └─> EventoSincronizacion crea registro en BD

2. Cliente envía evento (ej: venta.actualizar)
   └─> procesar_evento_ws() procesa el evento
   └─> EventoSincronizacion se guarda para auditoría
   └─> EventBroadcaster.broadcast_evento() lo redistribuye

3. EventBroadcaster distribuye según:
   ├─> Sucursal (todos los usuarios)
   ├─> Dispositivo específico (web, app_mesero, kds)
   └─> Usuario específico (único usuario)

4. Todos los clientes conectados reciben notificación
   └─> UI se actualiza automáticamente (real-time)
```

---

## 🚀 Próximos Pasos

### 1. Frontend WebSocket Client
```javascript
// Crear cliente JavaScript para conectarse y escuchar eventos
// Ubicar en static/js/websocket-client.js
class WebSocketClient {
    constructor(usuarioId, sucursalId, dispositivo) {
        this.token = `${usuarioId}:${sucursalId}:${dispositivo}`;
        this.ws = new WebSocket(`ws://127.0.0.1:8000/ws/${this.token}`);
        this.setupListeners();
    }
    
    setupListeners() {
        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            this.handleEvent(msg.evento, msg.datos);
        };
    }
    
    handleEvent(evento, datos) {
        // Actualizar UI según evento
    }
}
```

### 2. Integración en Plantillas
```html
<script>
    const wsClient = new WebSocketClient(
        {{ usuario.id }},
        {{ empresa.id }},
        'web'
    );
</script>
```

### 3. Permisos en Rutas
```python
# Decorador para validar permisos
def require_permission(permission):
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            usuario_id = request.session.get("usuario_id")
            db = ...
            permisos = PermisosService(db)
            permisos.requiere_permiso(usuario_id, permission)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.post("/api/v1/ventas/crear")
@require_permission("ventas.crear")
async def crear_venta(...):
    ...
```

---

## 📝 Logs de Inicialización

El servidor genera los siguientes logs al iniciarse:

```
🚀 Inicializando FASE 5 Enterprise...
✓ Tablas Enterprise creadas exitosamente
Permisos del sistema inicializados
✓ Rol 'administrador' creado exitosamente
✓ Rol 'gerente' creado exitosamente
✓ Rol 'cajero' creado exitosamente
✓ Rol 'mesero' creado exitosamente
✓ Rol 'cocinero' creado exitosamente
✓ Rol 'bartender' creado exitosamente
✓ RBAC inicializado exitosamente
✅ FASE 5 Enterprise inicializado
```

---

## 🔐 Seguridad

### Validación de Token WebSocket
```python
# Token format: {usuario_id}:{sucursal_id}:{dispositivo}
# Validaciones:
# 1. Usuario debe existir en BD
# 2. Formato debe ser válido
# 3. Dispositivo debe estar en lista permitida
```

### Permisos Granulares
```python
# Antes de cualquier acción, se valida:
usuario_roles = db.query(UsuarioRol).filter(
    UsuarioRol.usuario_id == usuario_id,
    UsuarioRol.activo == True,
    UsuarioRol.rol.permisos.any(Permiso.codigo == permission)
).first()
```

---

## 📞 Soporte

Para más información sobre FASE 5, consultar:
- [Conversation Summary](./CONVERSATION_SUMMARY.md)
- [PROMPT MAESTRO](./PROMPT_MAESTRO.md)
- [Test Suite](./tests/enterprise/test_fase5.py)

---

**Estado**: ✅ FASE 5 - Completada e Integrada
**Fecha**: 2026-07-19
**Servidor**: http://127.0.0.1:8000
