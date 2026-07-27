from contextlib import asynccontextmanager
from io import StringIO
import csv
import logging
import secrets
from pathlib import Path
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
from fastapi import FastAPI, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import *
from .models_enterprise import Sucursal, Rol, Permiso, UsuarioRol, ConexionWebSocket, EventoSincronizacion
from .config import settings, logger
from .domains.ventas import router as ventas_router
from .domains.mesas import router as mesas_router
from .domains.productos import router as productos_router
from .domains.comanda import router as comanda_router
from .domains.nomina import router as nomina_router
from .routes.websocket import router as websocket_router
from .routes.mobile_api import router as mobile_api_router
from .routes.kds_api import router as kds_api_router
from .routes.dashboard_api import router as dashboard_api_router
from .routes.reportes_api import router as reportes_api_router
from .enterprise_init import setup_enterprise_database
from .services.rbac_service import inicializar_rbac
from .services.jwt_service import JWTService
from app.models import hora_colombia

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed(db: Session):
    """Siembra minima de arranque: empresa y usuario administrador.

    Para datos de demostracion completos (mesas, productos con existencias,
    bodegas, empleados por rol y operacion de ejemplo) use:

        python scripts/inicializar_datos.py --reiniciar

    El seed anterior creaba mesas y productos sin `empresa_id`, una venta
    abierta huerfana sin detalles y dos liquidaciones de nomina para el mismo
    empleado. Eso dejaba la base incoherente desde el primer arranque.
    """
    if db.scalar(select(func.count(Empresa.id))) != 0:
        return

    empresa = Empresa(nombre="Mi Cafe", nit="900.000.000-1")
    db.add(empresa)
    db.flush()

    admin = Empleado(nombre="Administrador inicial", documento="ADMIN-001",
                     cargo="Administrador", salario=0)
    db.add(admin)
    db.flush()

    db.add(Usuario(empleado_id=admin.id, empresa_id=empresa.id, usuario="admin",
                   password_hash=passwords.hash("Admin123*"), rol="administrador"))
    db.commit()
    logger.info("Siembra inicial creada. Usuario: admin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
        with Session(engine) as db: seed(db)
    
    # Inicializar infraestructura Enterprise FASE 5
    logger.info("🚀 Inicializando FASE 5 Enterprise...")
    logger.info("📱 Inicializando FASE 7 Mobile API...")
    logger.info(f"🔐 JWT Service: {'LISTO' if JWTService.SECRET_KEY else 'NO CONFIGURADO'}")
    try:
        setup_enterprise_database()
        with Session(engine) as db:
            inicializar_rbac(db)
        logger.info("✅ FASE 5 Enterprise inicializado")
        logger.info("✅ FASE 7 Mobile API ready")
    except Exception as e:
        logger.error(f"Error inicializando Enterprise: {e}")
    yield

app = FastAPI(title="CafBarDLA POS", lifespan=lifespan)
APP_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


# ---------------------------------------------------------------------------
# Manejo global de excepciones (Paso 18).
# Ningun error debe generar una pantalla en blanco: se registra y se muestra
# una pagina amigable. Los errores 500 se auditan y se les asigna una
# referencia para poder rastrearlos en los logs sin exponer detalles tecnicos.
# ---------------------------------------------------------------------------
from starlette.exceptions import HTTPException as StarletteHTTPException


def _quiere_json(request: Request) -> bool:
    ruta = request.url.path
    acepta = request.headers.get("accept", "")
    return ruta.startswith("/api/") or "application/json" in acepta


@app.exception_handler(StarletteHTTPException)
async def manejar_http_exception(request: Request, exc: StarletteHTTPException):
    # 401/403/404 y demas: respuesta JSON para API, pagina para navegador.
    if _quiere_json(request):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    titulos = {403: "Acceso restringido", 404: "Página no encontrada",
               401: "Necesitas iniciar sesión", 400: "Solicitud inválida"}
    try:
        return templates.TemplateResponse(
            request, "error.html",
            {"request": request, "codigo": exc.status_code,
             "titulo": titulos.get(exc.status_code, "Ocurrió un problema"),
             "mensaje": exc.detail or "No se pudo completar la solicitud.",
             "referencia": None},
            status_code=exc.status_code)
    except Exception:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def manejar_error_no_controlado(request: Request, exc: Exception):
    # Error inesperado (500): se registra con una referencia y se audita.
    import uuid
    referencia = uuid.uuid4().hex[:8]
    logger.error("Error no controlado [%s] en %s: %s",
                 referencia, request.url.path, exc, exc_info=True)
    try:
        from .database import SessionLocal as _SLE
        from .domains.auditoria.services import AuditoriaService
        _edb = _SLE()
        try:
            AuditoriaService(_edb).registrar_desde_request(
                request, accion="otro", resultado="error",
                descripcion=f"Error interno [{referencia}] en {request.url.path}")
            _edb.commit()
        finally:
            _edb.close()
    except Exception:
        pass
    if _quiere_json(request):
        return JSONResponse(
            {"detail": "Error interno del servidor", "referencia": referencia},
            status_code=500)
    try:
        return templates.TemplateResponse(
            request, "error.html",
            {"request": request, "codigo": 500,
             "titulo": "Algo salió mal",
             "mensaje": "Ocurrió un error inesperado. El equipo quedó notificado.",
             "referencia": referencia},
            status_code=500)
    except Exception:
        return JSONResponse(
            {"detail": "Error interno", "referencia": referencia},
            status_code=500)

# CORS - permitir solo mismo origen
# CORS: los origenes deben incluir esquema y puerto, si no jamas coinciden.
# El valor anterior ["127.0.0.1", "localhost"] no hacia match con ningun Origin real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log de todas las operaciones para auditoría"""
    # Solo loguear rutas importantes, no estáticas
    if not request.url.path.startswith("/static"):
        usuario = request.session.get("usuario_nombre", "anonimo") if "session" in request.scope else "anonimo"
        logger.info(f"[{request.method}] {request.url.path} - Usuario: {usuario}")
    response = await call_next(request)
    return response

# Mapa ruta -> modulo RBAC. Solo las vistas de modulo se protegen por permiso.
_MODULOS_RUTA = {
    "dashboard": "dashboard", "mesas": "mesas", "caja": "caja",
    "cocina": "cocina", "domicilios": "domicilios", "productos": "productos",
    "inventario": "inventario", "produccion": "produccion",
    "compras": "compras", "gastos": "gastos", "clientes": "clientes",
    "empleados": "empleados", "nomina": "nomina", "informes": "informes",
    "usuarios": "usuarios", "configuracion": "configuracion",
    "auditoria": "auditoria",
    "impresoras": "configuracion",
    "roles": "usuarios",
    "pedidos-pendientes": "caja",
    "backups": "backups",
}


def _modulo_de_ruta(ruta: str):
    """Devuelve el modulo RBAC para una ruta GET de seccion, o None.

    Solo mapea la vista principal del modulo (GET /nomina, etc.), no sus
    sub-rutas de accion, que se controlan aparte.
    """
    partes = [p for p in ruta.split("/") if p]
    if len(partes) != 1:
        return None
    return _MODULOS_RUTA.get(partes[0])


@app.middleware("http")
async def autenticar_sesion(request: Request, call_next):
    """Control de acceso: TODO exige sesion salvo lo declarado publico.

    Modelo deny-by-default. La version anterior listaba /mesas, /caja,
    /productos, /nomina, /usuarios y /configuracion como publicas, lo que
    exponia el sistema completo sin autenticacion.
    """
    ruta = request.url.path

    # Recursos verdaderamente publicos (sin datos de negocio)
    PUBLICAS_EXACTAS = {"/", "/login", "/logout", "/health",
                        "/manifest.webmanifest", "/sw.js", "/offline",
                        "/sw-cliente.js"}
    PUBLICAS_PREFIJO = ("/static", "/favicon.ico")

    # APIs que se autentican por JWT Bearer en su propia capa,
    # no por cookie de sesion. Se excluyen aqui a proposito.
    JWT_PREFIJO = ("/api/v1/mobile/", "/api/v1/kds/")

    # App de cliente: publica y sin login (el comensal ordena sin cuenta).
    # Solo las rutas de cliente; la gestion de pedidos (caja/mesero) NO va aqui.
    CLIENTE_PREFIJO = ("/cliente", "/api/cliente")

    # Documentacion interactiva: solo fuera de produccion
    DOCS_PREFIJO = ("/docs", "/redoc", "/openapi.json")

    if ruta in PUBLICAS_EXACTAS or ruta.startswith(PUBLICAS_PREFIJO):
        return await call_next(request)

    # App de cliente: acceso publico sin sesion.
    if ruta.startswith(CLIENTE_PREFIJO):
        return await call_next(request)

    if ruta.startswith(DOCS_PREFIJO):
        if settings.is_production:
            logger.warning("Intento de acceso a documentacion en produccion: %s", ruta)
            return JSONResponse({"detail": "No encontrado"}, status_code=404)
        return await call_next(request)

    if ruta.startswith(JWT_PREFIJO):
        # La verificacion del Bearer token ocurre en las dependencias del router.
        return await call_next(request)

    # Todo lo demas exige sesion valida
    tiene_sesion = "session" in request.scope and request.session.get("usuario_id")
    if not tiene_sesion:
        if ruta.startswith("/api/"):
            logger.warning("Acceso no autenticado a API: %s", ruta)
            return JSONResponse({"detail": "No autenticado"}, status_code=401)
        logger.info("Redirigiendo a login desde: %s", ruta)
        return RedirectResponse("/login", status_code=303)

    # --- Autorizacion por modulo (RBAC parametrizable, Paso 17) ---
    # Se resuelve el modulo por el primer segmento de la ruta y se verifica que
    # el rol tenga permiso. El super administrador siempre pasa. Si el segmento
    # no corresponde a un modulo con permiso (rutas operativas internas), se
    # deja pasar y la ruta aplica su propio exigir_rol si lo necesita.
    modulo = _modulo_de_ruta(ruta)
    if modulo:
        rol_sesion = request.session.get("rol")
        from .database import SessionLocal, get_db
        from .services.rbac_service import RolService
        # Respetar el override de get_db si esta activo (entorno de pruebas),
        # para consultar la misma base que el resto de la peticion. Fuera de
        # pruebas, abrir una sesion propia.
        override = app.dependency_overrides.get(get_db)
        db_check = override() if override else SessionLocal()
        cerrar = override is None
        try:
            permitido = RolService(db_check).puede_modulo(rol_sesion, modulo)
        except Exception as e:
            # Si el RBAC aun no esta inicializado (tablas ausentes), no se puede
            # verificar; se registra y se permite, para no bloquear el sistema
            # por un problema de infraestructura. En operacion normal las tablas
            # existen (las crea el seed / la migracion).
            logger.error("RBAC no disponible para %s: %s", modulo, e)
            permitido = True
        finally:
            if cerrar:
                db_check.close()
        if not permitido:
            logger.warning("Acceso denegado a modulo %s para rol %s",
                           modulo, request.session.get("rol"))
            # Registrar el acceso denegado en auditoria.
            try:
                from .database import SessionLocal as _SLA
                from .domains.auditoria.services import AuditoriaService
                _ov = app.dependency_overrides.get(get_db)
                _adb = _ov() if _ov else _SLA()
                try:
                    AuditoriaService(_adb).registrar_desde_request(
                        request, accion="acceso_denegado", modulo=modulo,
                        resultado="error",
                        descripcion=f"Intento de acceso sin permiso al módulo {modulo}")
                    _adb.commit()
                finally:
                    if _ov is None:
                        _adb.close()
            except Exception as _e:
                logger.error("No se pudo auditar acceso denegado: %s", _e)
            if ruta.startswith("/api/"):
                return JSONResponse(
                    {"detail": f"Sin acceso al modulo {modulo}"}, status_code=403)
            override2 = app.dependency_overrides.get(get_db)
            _db = override2() if override2 else SessionLocal()
            _cerrar2 = override2 is None
            try:
                empresa = _db.scalar(select(Empresa).limit(1))
                return templates.TemplateResponse(
                    request, "sin_permiso.html",
                    {"request": request, "modulo": modulo, "empresa": empresa,
                     "usuario": {"nombre": request.session.get("usuario_nombre"),
                                 "rol": request.session.get("rol")}},
                    status_code=403)
            finally:
                if _cerrar2:
                    _db.close()

    return await call_next(request)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Middlewares de seguridad HTTP (Paso 16).
# El orden de registro es inverso al de ejecucion. Se registran ANTES que
# SessionMiddleware para que este quede mas externo y la sesion este poblada
# cuando corran el guard de autenticacion y la validacion CSRF.
#
# Orden de ejecucion resultante (de mas externo a mas interno):
#   SecurityHeaders -> RateLimit -> Session -> logging -> autenticar -> CSRF
# Asi el rate limit frena el abuso antes de tocar la sesion, y el CSRF valida
# con la sesion ya disponible.
# ---------------------------------------------------------------------------
from .security.csrf import CSRFMiddleware
from .security.rate_limit import RateLimitMiddleware
from .security.headers import SecurityHeadersMiddleware

app.add_middleware(CSRFMiddleware, activo=settings.csrf_enabled)

# SessionMiddleware se registra AL FINAL a proposito.
# Starlette ejecuta los middlewares en orden INVERSO al de registro, por lo que
# el ultimo registrado es el mas EXTERNO y corre PRIMERO. Asi request.session
# ya esta poblada cuando corre `autenticar_sesion`.
# Registrado antes, el guard de autenticacion no veia la sesion y rechazaba
# a todo usuario ya autenticado.
# ---------------------------------------------------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site=settings.session_cookie_samesite,
    https_only=settings.session_cookie_secure,
    max_age=8 * 3600,  # la sesion caduca en 8 horas (turno laboral)
)

# Estos dos quedan mas externos que la sesion (corren primero): el rate limit
# frena el abuso antes de deserializar la sesion, y los headers se aplican a
# TODAS las respuestas, incluso las de bloqueo.
app.add_middleware(
    RateLimitMiddleware,
    activo=settings.rate_limit_enabled,
    limite_general=settings.rate_limit_requests,
    periodo_general=settings.rate_limit_period,
    limite_login=settings.rate_limit_login_requests,
    periodo_login=settings.rate_limit_login_period,
)
app.add_middleware(SecurityHeadersMiddleware, hsts=settings.hsts_enabled)


def context(request, db):
    empresa = db.scalar(select(Empresa).limit(1))
    # Token CSRF estable por sesion: se genera una sola vez y se reutiliza.
    # Antes se regeneraba en cada render, lo que invalidaba formularios ya
    # abiertos (p. ej. dos pestañas) y rompia la validacion.
    csrf_token = request.session.get("csrf_token")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = csrf_token
    return {
        "request": request,
        "empresa": empresa,
        "usuario": {
            "nombre": request.session.get("usuario_nombre"),
            "rol": request.session.get("rol")
        },
        "csrf_token": csrf_token
    }

def exigir_rol(request: Request, *roles: str):
    """Compatibilidad: exige que el rol de la sesion este entre los indicados.

    Se conserva para no romper las rutas existentes. El super administrador
    siempre pasa. La verificacion por modulo (mas moderna) es exigir_modulo.
    """
    rol_sesion = request.session.get("rol")
    # El super admin (nivel maximo) siempre pasa.
    if rol_sesion and rol_sesion.lower() in ("administrador", "super administrador"):
        return
    if rol_sesion not in roles:
        raise HTTPException(403, "No tiene permisos para esta acción")


def exigir_modulo(request: Request, modulo: str, db: Session):
    """Autorizacion por modulo resuelta contra el RBAC en base de datos.

    Es la via parametrizable: el acceso depende de los permisos asignados al
    rol, no de strings codificados. El super administrador siempre pasa.
    """
    from .domains.rbac.services import RBACService
    rol_sesion = request.session.get("rol")
    if not rol_sesion:
        raise HTTPException(403, "No tiene permisos para esta acción")
    if not RBACService(db).puede(rol_sesion, modulo):
        raise HTTPException(403, f"No tiene acceso al módulo {modulo}")

# ============================================================================
# REGISTRAR ROUTERS - ARQUITECTURA MODULAR
# ============================================================================
app.include_router(ventas_router, prefix="/api/v1", tags=["api-v1"])
app.include_router(mesas_router, prefix="/api/v1", tags=["api-v1"])
app.include_router(productos_router, prefix="/api/v1", tags=["api-v1"])
app.include_router(comanda_router, prefix="/api/v1", tags=["api-v1"])
app.include_router(nomina_router, prefix="/api/v1", tags=["api-v1"])
app.include_router(websocket_router, tags=["websocket"])  # FASE 5: WebSocket
app.include_router(mobile_api_router, tags=["Mobile API - FASE 7"])  # FASE 7: Mobile API
app.include_router(kds_api_router, tags=["KDS API - FASE 8"])  # FASE 8: Kitchen Display System
# Routers antes definidos pero NUNCA registrados (829 lineas inertes).
app.include_router(dashboard_api_router)
from .routes.cliente_api import router as cliente_api_router
app.include_router(cliente_api_router, tags=["App Cliente"])
app.include_router(reportes_api_router)

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.session.get("usuario_id")
    if usuario_id:
        # Verificar que el usuario existe en la BD
        usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))
        if usuario:
            logger.info(f"[LOGIN_FORM] Usuario {usuario_id} válido, redirigiendo a dashboard")
            return RedirectResponse("/dashboard", 303)
        else:
            logger.warning(f"[LOGIN_FORM] Usuario_id {usuario_id} NO existe en BD, limpiando sesión")
            request.session.clear()
    # Retornar template login con estilos
    return templates.TemplateResponse(request, "login.html", {"error": None})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, usuario: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Ruta de autenticación con logging de auditoría"""
    usuario_limpio = usuario.strip()
    
    # Log del intento de login
    logger.info(f"Intento de login para usuario: {usuario_limpio}")
    
    cuenta = db.scalar(select(Usuario).where((Usuario.usuario == usuario_limpio) & (Usuario.activo == True)))
    
    if not cuenta or not passwords.verify(password, cuenta.password_hash):
        logger.warning(f"Login fallido para usuario: {usuario_limpio} (credenciales inválidas)")
        from .domains.auditoria.services import AuditoriaService
        AuditoriaService(db).registrar(
            accion="acceso", resultado="error",
            usuario_nombre=usuario_limpio,
            ip=AuditoriaService._ip(request),
            descripcion="Login fallido (credenciales inválidas)")
        db.commit()
        return templates.TemplateResponse(request, "login.html", {"error": "Usuario o contraseña incorrectos."},
            status_code=401
        )
    
    # Verificar que el usuario tiene permiso de acceso al sistema web. Un
    # empleado puede tener usuario solo para marcar entrada/salida, sin acceso
    # a ninguna aplicacion.
    if not getattr(cuenta, "acceso_web", True):
        logger.warning(f"Usuario {usuario_limpio} sin acceso web intentó ingresar")
        from .domains.auditoria.services import AuditoriaService
        AuditoriaService(db).registrar(
            accion="acceso", resultado="error", usuario_id=cuenta.id,
            usuario_nombre=cuenta.usuario, rol=cuenta.rol,
            ip=AuditoriaService._ip(request),
            descripcion="Intento de acceso web sin permiso de acceso web")
        db.commit()
        return templates.TemplateResponse(request, "login.html",
            {"error": "Tu usuario no tiene acceso al sistema web. Contacta al administrador."},
            status_code=403)

    # Login exitoso
    logger.info(f"Login exitoso para usuario: {usuario_limpio} (ID: {cuenta.id})")
    # Sembrar el token CSRF en la sesion desde ya, para que cualquier POST
    # posterior tenga con que validarse (no todas las paginas traen un form).
    if not request.session.get("csrf_token"):
        request.session["csrf_token"] = secrets.token_urlsafe(32)
    request.session.update({
        "usuario_id": cuenta.id,
        "usuario_nombre": cuenta.usuario,
        "rol": cuenta.rol,
        "empleado_id": cuenta.empleado_id,
        "empresa_id": cuenta.empresa_id,
        "login_time": datetime.now().isoformat()
    })
    from .domains.auditoria.services import AuditoriaService
    AuditoriaService(db).registrar(
        accion="acceso", resultado="exito",
        usuario_id=cuenta.id, usuario_nombre=cuenta.usuario, rol=cuenta.rol,
        ip=AuditoriaService._ip(request), empresa_id=cuenta.empresa_id or 1,
        descripcion="Inicio de sesión")
    db.commit()
    return RedirectResponse("/dashboard", 303)

@app.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    """Logout con logging de auditoría"""
    usuario = request.session.get("usuario_nombre", "desconocido")
    logger.info(f"Logout para usuario: {usuario}")
    from .domains.auditoria.services import AuditoriaService
    AuditoriaService(db).registrar_desde_request(
        request, accion="acceso", descripcion="Cierre de sesión")
    db.commit()
    request.session.clear()
    return RedirectResponse("/login", 303)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal"""
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse("/login", 303)
    
    # Obtener datos del usuario y empresa
    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))
    if not usuario:
        request.session.clear()
        return RedirectResponse("/login", 303)
    
    empresa = db.get(Empresa, usuario.empresa_id)
    
    # Estadísticas del día
    today = func.date(Venta.fecha)
    total_ventas = db.scalar(select(func.coalesce(func.sum(Venta.total), 0)).where((today == func.current_date()) & (Venta.estado == "pagada")))
    ventas_abiertas = db.scalar(select(func.count(Venta.id)).where(Venta.estado == "abierta"))
    productos_bajos = db.scalars(select(Producto).where((Producto.existencias <= Producto.stock_minimo) & (Producto.activo == True))).all()
    
    logger.info(f"[DASHBOARD] Usuario {usuario_id} ({usuario.usuario}) accediendo a dashboard")
    
    return templates.TemplateResponse(request, "dashboard.html", {"empresa": empresa,
        "usuario": {"nombre": usuario.usuario, "rol": usuario.rol},
        "total": total_ventas,
        "abiertas": ventas_abiertas,
        "bajos": productos_bajos
    })

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Raíz redirige a dashboard o login"""
    usuario_id = request.session.get("usuario_id")
    if usuario_id:
        return RedirectResponse("/dashboard", 303)
    return RedirectResponse("/login", 303)

def recalcular_venta(venta: Venta) -> None:
    subtotal = sum((detalle.precio * detalle.cantidad for detalle in venta.detalles), Decimal("0"))
    venta.subtotal = subtotal
    venta.total = max(Decimal("0"), subtotal - (venta.descuento or 0)) + (venta.propina or 0) + (venta.impuesto or 0) + (venta.cargo_envio or 0)

def consumir_receta(db: Session, receta: Receta, unidades: Decimal, referencia: str) -> Decimal:
    """Consume los insumos de una receta a traves de InventarioService.

    Se usa al vender productos con receta de tipo "venta". Antes restaba
    existencias a mano y registraba el movimiento por su cuenta: era una
    implementacion paralela del inventario que no dejaba saldos en el kardex.
    """
    from .domains.inventario.services import InventarioService
    inventario = InventarioService(db)
    costo_total = Decimal("0")

    # Verificar existencias antes de mover nada
    requerimientos = []
    for detalle in receta.detalles:
        if getattr(detalle, "rol", "insumo") != "insumo":
            continue
        producto = db.get(Producto, detalle.insumo_id)
        merma = Decimal("1") + (detalle.merma_porcentaje or Decimal("0")) / Decimal("100")
        cantidad = detalle.cantidad * unidades * merma
        if not producto or (producto.existencias or Decimal("0")) < cantidad:
            nombre = producto.nombre if producto else f"#{detalle.insumo_id}"
            raise HTTPException(400, f"Inventario insuficiente: {nombre}")
        requerimientos.append((producto, cantidad))

    for producto, cantidad in requerimientos:
        costo_total += cantidad * (producto.costo or Decimal("0"))
        inventario.registrar_movimiento(
            producto_id=producto.id, tipo="consumo_receta", cantidad=cantidad,
            referencia=referencia, empresa_id=producto.empresa_id or 1,
            permitir_negativo=False)
    return costo_total

@app.get("/health")
def health(): return {"status":"ok", "service":"cafbardla"}


@app.get("/auditoria", response_class=HTMLResponse)
def vista_auditoria(request: Request, accion: str = None, modulo: str = None,
                    db: Session = Depends(get_db)):
    """Pantalla de auditoría: quién hizo qué, cuándo y desde dónde."""
    exigir_rol(request, "administrador")
    from .domains.auditoria.services import AuditoriaService
    registros = AuditoriaService(db).listar(
        limite=200, accion=accion or None, modulo=modulo or None)
    return templates.TemplateResponse(request, "auditoria.html",
        context(request, db) | {"registros": registros,
                                "filtro_accion": accion or "",
                                "filtro_modulo": modulo or ""})


def _backup_service():
    from .domains.backup.services import BackupService
    import os as _os
    return BackupService(settings.database_url,
                         backup_dir=_os.environ.get("BACKUP_DIR", "backups"))


@app.get("/backups", response_class=HTMLResponse)
def vista_backups(request: Request, db: Session = Depends(get_db)):
    """Pantalla de copias de seguridad: crear, verificar, restaurar."""
    exigir_rol(request, "administrador")
    copias = _backup_service().listar()
    return templates.TemplateResponse(request, "backups.html",
        context(request, db) | {"copias": copias})


@app.post("/backups/crear")
def crear_backup(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .domains.auditoria.services import AuditoriaService
    try:
        m = _backup_service().crear(etiqueta="manual")
        AuditoriaService(db).registrar_desde_request(
            request, accion="crear", modulo="backups", entidad="Backup",
            entidad_id=m["nombre"], descripcion="Copia de seguridad creada",
            despues={"nombre": m["nombre"], "tamano": m["tamano_zip"]})
        db.commit()
    except Exception as e:
        logger.error("Error creando backup: %s", e)
        raise HTTPException(500, "No se pudo crear la copia de seguridad")
    return RedirectResponse("/backups", 303)


@app.post("/backups/restaurar")
def restaurar_backup(request: Request, nombre: str = Form(...),
                     db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .domains.auditoria.services import AuditoriaService
    try:
        r = _backup_service().restaurar(nombre)
        AuditoriaService(db).registrar_desde_request(
            request, accion="editar", modulo="backups", entidad="Backup",
            entidad_id=nombre, resultado="exito",
            descripcion=f"Restauración desde copia {nombre}")
        db.commit()
    except Exception as e:
        logger.error("Error restaurando backup: %s", e)
        raise HTTPException(400, f"No se pudo restaurar: {e}")
    return RedirectResponse("/backups", 303)


# ---------------------------------------------------------------------------
# PWA: manifest, service worker y pagina offline (Paso 13).
# Son publicos a proposito: el navegador los pide antes de cualquier sesion.
# El service worker se sirve desde la raiz para tener scope "/" (si se sirviera
# bajo /static tendria scope /static y no podria interceptar navegaciones).
# ---------------------------------------------------------------------------
@app.get("/manifest.webmanifest", include_in_schema=False)
def pwa_manifest():
    from fastapi.responses import FileResponse
    return FileResponse(
        str(APP_DIR / "static" / "manifest.webmanifest"),
        media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def pwa_service_worker():
    from fastapi.responses import FileResponse
    # Sin cache HTTP: asi el navegador siempre ve la ultima version del SW.
    return FileResponse(
        str(APP_DIR / "static" / "sw.js"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.get("/sw-cliente.js", include_in_schema=False)
def pwa_sw_cliente():
    """Service worker de la app de cliente, servido desde la raiz para tener
    scope sobre /cliente."""
    from fastapi.responses import FileResponse
    return FileResponse(
        str(APP_DIR / "static" / "sw-cliente.js"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/cliente"})


@app.get("/offline", response_class=HTMLResponse, include_in_schema=False)
def pwa_offline(request: Request):
    return templates.TemplateResponse(request, "offline.html", {})

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    today = func.date(Venta.fecha)
    total = db.scalar(select(func.coalesce(func.sum(Venta.total),0)).where(today == func.current_date(), Venta.estado=="pagada"))
    abiertas = db.scalar(select(func.count(Venta.id)).where(Venta.estado=="abierta"))
    bajos = db.scalars(select(Producto).where(Producto.existencias <= Producto.stock_minimo, Producto.activo==True)).all()
    return templates.TemplateResponse(request, "dashboard.html", context(request,db) | {"total":total,"abiertas":abiertas,"bajos":bajos})

@app.get("/mesas", response_class=HTMLResponse)
def mesas(request: Request, db: Session = Depends(get_db)):
    """Plano de salon con datos operativos en vivo.

    Antes solo pasaba las zonas: el plano no mostraba tiempo de ocupacion,
    consumo acumulado ni mesero, porque esos datos no existian.
    """
    from .domains.mesas.services import MesaService
    servicio = MesaService(db)
    zonas = db.scalars(select(Zona).order_by(Zona.orden)).all()

    detalles = {}
    for zona in zonas:
        for mesa in zona.mesas:
            try:
                detalles[mesa.id] = servicio.detalle_mesa(mesa.id)
            except ValueError:
                continue

    return templates.TemplateResponse(request, "mesas.html", context(request, db) | {
        "zonas": zonas,
        "detalles": detalles,
        "estadisticas": servicio.obtener_estadisticas(),
        "reservas": servicio.reservas_activas(),
    })

@app.post("/zonas")
def crear_zona(request: Request, nombre: str = Form(...),
               db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "gerente")
    db.add(Zona(nombre=nombre.strip(),
                orden=(db.scalar(select(func.count(Zona.id))) or 0) + 1))
    db.commit()
    return RedirectResponse("/mesas", 303)


@app.post("/zonas/{zona_id}/eliminar")
def eliminar_zona(zona_id: int, request: Request, db: Session = Depends(get_db)):
    """Elimina una zona solo si no tiene mesas."""
    exigir_rol(request, "administrador", "gerente")
    zona = db.get(Zona, zona_id)
    if not zona:
        raise HTTPException(404, "Zona no encontrada")
    if db.scalar(select(func.count(Mesa.id)).where(Mesa.zona_id == zona_id)):
        raise HTTPException(400, "No se puede eliminar: la zona tiene mesas. Muévelas o elimínalas primero.")
    db.delete(zona)
    db.commit()
    return RedirectResponse("/mesas", 303)

@app.post("/mesas")
def crear_mesa(request: Request, zona_id: int = Form(...), nombre: str = Form(...),
               capacidad: int = Form(4), forma: str = Form("redonda"),
               db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "gerente")
    # Posicion inicial escalonada para que las mesas nuevas no queden encimadas.
    n = db.scalar(select(func.count(Mesa.id)).where(Mesa.zona_id == zona_id)) or 0
    px = 8 + (n % 6) * 15
    py = 10 + (n // 6) * 20
    tamano = {"rectangular": (96, 56)}.get(forma, (64, 64))
    db.add(Mesa(zona_id=zona_id, nombre=nombre.strip(), capacidad=capacidad,
                forma=forma, posicion_x=px, posicion_y=py,
                ancho=tamano[0], alto=tamano[1]))
    db.commit()
    return RedirectResponse("/mesas", 303)


@app.post("/mesas/{mesa_id}/layout")
async def guardar_layout_mesa(mesa_id: int, request: Request,
                              db: Session = Depends(get_db)):
    """Guarda posicion, forma y tamano de una mesa (arrastrar/redimensionar).

    Recibe JSON del editor visual. Solo administradores y gerentes.
    """
    exigir_rol(request, "administrador", "gerente")
    mesa = db.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(404, "Mesa no encontrada")
    datos = await request.json()
    # Se aceptan solo campos de disposicion; con limites sanos.
    if "posicion_x" in datos:
        mesa.posicion_x = max(0, min(100, int(datos["posicion_x"])))
    if "posicion_y" in datos:
        mesa.posicion_y = max(0, min(100, int(datos["posicion_y"])))
    if "forma" in datos and datos["forma"] in ("redonda", "cuadrada", "rectangular"):
        mesa.forma = datos["forma"]
    if "ancho" in datos:
        mesa.ancho = max(32, min(240, int(datos["ancho"])))
    if "alto" in datos:
        mesa.alto = max(32, min(240, int(datos["alto"])))
    if "capacidad" in datos:
        mesa.capacidad = max(1, min(50, int(datos["capacidad"])))
    db.commit()
    return {"ok": True, "mesa_id": mesa_id}


@app.post("/mesas/{mesa_id}/eliminar")
def eliminar_mesa(mesa_id: int, request: Request, db: Session = Depends(get_db)):
    """Elimina una mesa si no tiene una venta abierta."""
    exigir_rol(request, "administrador", "gerente")
    mesa = db.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(404, "Mesa no encontrada")
    venta_abierta = db.scalar(select(Venta).where(
        Venta.mesa_id == mesa_id, Venta.estado == "abierta"))
    if venta_abierta:
        raise HTTPException(400, "No se puede eliminar: la mesa tiene una cuenta abierta")
    db.delete(mesa)
    db.commit()
    return RedirectResponse("/mesas", 303)

@app.get("/comanda/{mesa_id}", response_class=HTMLResponse)
def comanda(mesa_id:int,request:Request,db:Session=Depends(get_db)):
    mesa=db.get(Mesa,mesa_id)
    if not mesa: raise HTTPException(404)
    venta=db.scalar(select(Venta).where(Venta.mesa_id==mesa_id,Venta.estado=="abierta"))
    return templates.TemplateResponse(request, "comanda.html", context(request,db)|{"mesa":mesa,"venta":venta,"productos":db.scalars(select(Producto).where(Producto.activo==True)).all(),"clientes":db.scalars(select(Cliente).order_by(Cliente.nombre)).all(),"mesas_destino":db.scalars(select(Mesa).where(Mesa.id != mesa_id).order_by(Mesa.nombre)).all()})

@app.post("/api/comanda/{mesa_id}/items")
def agregar_item(mesa_id:int, request: Request, producto_id:int=Form(...),cantidad:float=Form(1),nota:str=Form(""),db:Session=Depends(get_db)):
    mesa=db.get(Mesa,mesa_id); producto=db.get(Producto,producto_id)
    if not mesa or not producto: raise HTTPException(404)
    venta=db.scalar(select(Venta).where(Venta.mesa_id==mesa_id,Venta.estado=="abierta"))
    if not venta: venta=Venta(mesa_id=mesa_id, empleado_id=request.session.get("empleado_id")); db.add(venta); db.flush(); mesa.estado="ocupada"
    db.add(DetalleVenta(venta_id=venta.id,producto_id=producto.id,cantidad=cantidad,precio=producto.precio_venta,nota=nota or None))
    recalcular_venta(venta)
    empresa = db.scalar(select(Empresa).limit(1))
    venta.impuesto = (venta.subtotal * empresa.impuesto_porcentaje / Decimal("100")).quantize(Decimal("0.01"))
    recalcular_venta(venta); db.commit()
    return {"ok":True,"total":str(venta.total)}

@app.post("/api/ventas/{venta_id}/ajustes")
def ajustar_venta(venta_id: int, descuento: Decimal = Form(0), propina: Decimal = Form(0), impuesto: Decimal = Form(0), db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id)
    if not venta or venta.estado != "abierta": raise HTTPException(404)
    if min(descuento, propina, impuesto) < 0: raise HTTPException(400, "Los valores no pueden ser negativos")
    venta.descuento, venta.propina, venta.impuesto = descuento, propina, impuesto
    recalcular_venta(venta); db.commit()
    return {"ok": True, "total": str(venta.total)}

@app.post("/api/ventas/{venta_id}/items/{detalle_id}/eliminar")
def eliminar_item(venta_id: int, detalle_id: int, db: Session = Depends(get_db)):
    venta, detalle = db.get(Venta, venta_id), db.get(DetalleVenta, detalle_id)
    if not venta or not detalle or detalle.venta_id != venta.id or venta.estado != "abierta": raise HTTPException(404)
    db.delete(detalle); db.flush(); recalcular_venta(venta); db.commit()
    return {"ok": True, "total": str(venta.total)}

@app.post("/api/ventas/{venta_id}/trasladar")
def trasladar_venta(venta_id: int, mesa_destino_id: int = Form(...), db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id); destino = db.get(Mesa, mesa_destino_id)
    if not venta or not destino or venta.estado != "abierta" or venta.mesa_id == destino.id: raise HTTPException(400, "Traslado inválido")
    origen = db.get(Mesa, venta.mesa_id)
    cuenta_destino = db.scalar(select(Venta).where(Venta.mesa_id == destino.id, Venta.estado == "abierta"))
    if cuenta_destino:
        for detalle in venta.detalles: detalle.venta_id = cuenta_destino.id
        db.flush(); recalcular_venta(cuenta_destino)
        venta.estado = "transferida"; venta.total = 0
    else:
        venta.mesa_id = destino.id
    origen.estado, destino.estado = "libre", "ocupada"
    db.commit(); return {"ok": True, "destino": destino.id}

@app.post("/api/ventas/{venta_id}/anular")
def anular_venta(venta_id: int, request: Request, motivo: str = Form(...), db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id)
    if not venta or venta.estado != "abierta" or not motivo.strip(): raise HTTPException(400, "Indique el motivo de anulación")
    antes = {"estado": venta.estado, "total": venta.total}
    venta.estado, venta.motivo_anulacion = "anulada", motivo.strip()
    if venta.mesa_id: db.get(Mesa, venta.mesa_id).estado = "libre"
    from .domains.auditoria.services import AuditoriaService
    AuditoriaService(db).registrar_desde_request(
        request, accion="anular", modulo="caja", entidad="Venta",
        entidad_id=venta.id, descripcion=f"Anulación de venta. Motivo: {motivo.strip()}",
        antes=antes, despues={"estado": "anulada", "motivo": motivo.strip()})
    db.commit(); return {"ok": True}

@app.post("/api/ventas/{venta_id}/pagar")
def pagar(venta_id:int, medio_pago: str = Form("efectivo"), cliente_id: int | None = Form(None), db:Session=Depends(get_db)):
    venta=db.get(Venta,venta_id)
    if not venta or venta.estado!="abierta": raise HTTPException(404)
    if medio_pago == "credito":
        cliente = db.get(Cliente, cliente_id) if cliente_id else None
        if not cliente: raise HTTPException(400, "Seleccione un cliente para crédito")
        if cliente.cupo_credito and cliente.saldo_cartera + venta.total > cliente.cupo_credito: raise HTTPException(400, "El cupo de crédito es insuficiente")
        cliente.saldo_cartera += venta.total; venta.cliente_id = cliente.id
    for d in venta.detalles:
        p = db.get(Producto, d.producto_id)
        receta = db.scalar(select(Receta).where(Receta.producto_id == p.id, Receta.tipo_receta == "venta"))
        if receta:
            costo = consumir_receta(db, receta, d.cantidad, f"Venta {venta.id}")
            d.costo_unitario = (costo / d.cantidad).quantize(Decimal("0.01"))
        else:
            d.costo_unitario = p.costo
            # Salida por el kardex, no restando existencias a mano.
            from .domains.inventario.services import InventarioService
            try:
                InventarioService(db).registrar_movimiento(
                    producto_id=p.id, tipo="venta", cantidad=d.cantidad,
                    referencia=f"Venta {venta.id}", empresa_id=p.empresa_id or 1,
                    permitir_negativo=False)
            except ValueError as e:
                raise HTTPException(400, str(e))
    empresa = db.scalar(select(Empresa).limit(1))
    venta.numero_factura = f"{empresa.prefijo_factura}-{empresa.consecutivo_factura:06d}"
    empresa.consecutivo_factura += 1
    venta.estado="credito" if medio_pago == "credito" else "pagada"; venta.medio_pago=medio_pago
    if venta.mesa_id: db.get(Mesa,venta.mesa_id).estado="libre"
    db.commit(); return {"ok":True, "factura_url":f"/facturas/{venta.id}"}

@app.get("/facturas/{venta_id}", response_class=HTMLResponse)
def factura(venta_id: int, request: Request, db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id)
    if not venta or venta.estado not in ("pagada", "credito"): raise HTTPException(404)
    productos = {p.id: p for p in db.scalars(select(Producto)).all()}
    cliente = db.get(Cliente, venta.cliente_id) if venta.cliente_id else None
    user_agent = request.headers.get("user-agent", "")
    es_movil = any(token in user_agent.lower() for token in ("android", "iphone", "ipad", "mobile"))
    return templates.TemplateResponse(request, "factura.html", context(request, db) | {"venta": venta, "productos": productos, "cliente": cliente, "es_movil": es_movil}
    )

@app.get("/mobile", response_class=HTMLResponse)
def mobile_dashboard(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse("/login", 303)

    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))
    if not usuario:
        request.session.clear()
        return RedirectResponse("/login", 303)

    empresa = db.get(Empresa, usuario.empresa_id)
    today = func.date(Venta.fecha)
    total_ventas = db.scalar(select(func.coalesce(func.sum(Venta.total), 0)).where((today == func.current_date()) & (Venta.estado == "pagada")))
    pendientes_cocina = db.scalar(select(func.count(Comanda.id)).where(Comanda.estado.in_(["pendiente", "preparando"])))
    mesas_ocupadas = db.scalar(select(func.count(Mesa.id)).where(Mesa.estado == "ocupada"))

    return templates.TemplateResponse(request, "mobile_dashboard.html", {"empresa": empresa,
            "usuario": {"nombre": usuario.usuario, "rol": usuario.rol},
            "total_ventas": total_ventas,
            "pendientes_cocina": pendientes_cocina,
            "mesas_ocupadas": mesas_ocupadas,
        },
    )

@app.get("/inventario", response_class=HTMLResponse)
def inventario(request: Request, db: Session = Depends(get_db)):
    """Vista de inventario con alertas, lotes criticos y valor total.

    Antes solo listaba productos: las alertas que generaba Ventas y los
    vencimientos de lotes no se mostraban en ninguna parte.
    """
    from .domains.inventario.services import InventarioService
    servicio = InventarioService(db)
    empresa_id = request.session.get("empresa_id") or 1

    productos = db.scalars(select(Producto).order_by(Producto.nombre)).all()
    nombres_producto = {p.id: p.nombre for p in productos}

    lotes_criticos = servicio.lotes_vencidos() + servicio.lotes_por_vencer(dias=30)
    vistos, unicos = set(), []
    for l in lotes_criticos:
        if l.id not in vistos:
            vistos.add(l.id)
            unicos.append(l)

    return templates.TemplateResponse(request, "inventario.html", context(request, db) | {
        "productos": productos,
        "nombres_producto": nombres_producto,
        "alertas": servicio.alertas_pendientes(limite=20),
        "lotes_criticos": unicos,
        "bodegas": db.scalars(select(Bodega).where(Bodega.activa == True)).all(),
        "valor_inventario": servicio.valor_inventario(empresa_id),
    })

@app.get("/informes", response_class=HTMLResponse)
def informes(request: Request, desde: date | None = None, hasta: date | None = None, db: Session = Depends(get_db)):
    ventas_q = select(Venta).where(Venta.estado.in_(["pagada", "credito"]))
    gastos_q = select(Gasto)
    if desde:
        ventas_q = ventas_q.where(func.date(Venta.fecha) >= desde); gastos_q = gastos_q.where(Gasto.fecha >= desde)
    if hasta:
        ventas_q = ventas_q.where(func.date(Venta.fecha) <= hasta); gastos_q = gastos_q.where(Gasto.fecha <= hasta)
    ventas_rows = db.scalars(ventas_q).all()
    ventas = sum((v.total for v in ventas_rows), Decimal("0"))
    gastos = sum((g.valor for g in db.scalars(gastos_q).all()), Decimal("0"))
    medios: dict[str, Decimal] = {}
    for venta in ventas_rows:
        clave = venta.medio_pago or "sin definir"; medios[clave] = medios.get(clave, Decimal("0")) + venta.total
    productos_q = select(Producto.nombre, func.sum(DetalleVenta.cantidad).label("cantidad"), func.sum(DetalleVenta.precio * DetalleVenta.cantidad).label("valor"), func.sum(DetalleVenta.costo_unitario * DetalleVenta.cantidad).label("costo")).join(DetalleVenta, DetalleVenta.producto_id == Producto.id).join(Venta, Venta.id == DetalleVenta.venta_id).where(Venta.estado.in_(["pagada", "credito"]))
    if desde: productos_q = productos_q.where(func.date(Venta.fecha) >= desde)
    if hasta: productos_q = productos_q.where(func.date(Venta.fecha) <= hasta)
    productos_top = db.execute(productos_q.group_by(Producto.nombre).order_by(func.sum(DetalleVenta.precio * DetalleVenta.cantidad).desc()).limit(10)).all()
    costos_q = select(func.coalesce(func.sum(DetalleVenta.costo_unitario * DetalleVenta.cantidad), 0)).join(Venta, Venta.id == DetalleVenta.venta_id).where(Venta.estado.in_(["pagada", "credito"]))
    if desde: costos_q = costos_q.where(func.date(Venta.fecha) >= desde)
    if hasta: costos_q = costos_q.where(func.date(Venta.fecha) <= hasta)
    costos_ventas = db.scalar(costos_q)
    compras_q = select(Compra)
    produccion_q = select(OrdenProduccion)
    nomina_q = select(LiquidacionNomina).join(PeriodoNomina, PeriodoNomina.id == LiquidacionNomina.periodo_id)
    if desde:
        compras_q = compras_q.where(Compra.fecha >= desde); produccion_q = produccion_q.where(func.date(OrdenProduccion.fecha) >= desde); nomina_q = nomina_q.where(PeriodoNomina.fecha_fin >= desde)
    if hasta:
        compras_q = compras_q.where(Compra.fecha <= hasta); produccion_q = produccion_q.where(func.date(OrdenProduccion.fecha) <= hasta); nomina_q = nomina_q.where(PeriodoNomina.fecha_fin <= hasta)
    compras_total = sum((c.valor for c in db.scalars(compras_q).all()), Decimal("0"))
    produccion_total = sum((o.costo_total for o in db.scalars(produccion_q).all()), Decimal("0"))
    nomina_total = sum((l.neto for l in db.scalars(nomina_q).all()), Decimal("0"))
    inventario = db.scalars(select(Producto).where(Producto.activo == True).order_by(Producto.nombre)).all()
    valor_inventario = sum((p.existencias * p.costo for p in inventario), Decimal("0"))
    bajos = [p for p in inventario if p.existencias <= p.stock_minimo]
    return templates.TemplateResponse(request, "informes.html", context(request,db) | {"ventas":ventas,"gastos":gastos,"costos_ventas":costos_ventas,"compras_total":compras_total,"produccion_total":produccion_total,"nomina_total":nomina_total,"valor_inventario":valor_inventario,"bajos":bajos,"inventario":inventario,"desde":desde,"hasta":hasta,"medios":medios,"productos_top":productos_top,"cantidad_ventas":len(ventas_rows)})

@app.get("/informes/export/ventas")
def exportar_ventas(desde: date | None = None, hasta: date | None = None, db: Session = Depends(get_db)):
    ventas_q = select(Venta).where(Venta.estado.in_(["pagada", "credito"])).order_by(Venta.fecha)
    if desde: ventas_q = ventas_q.where(func.date(Venta.fecha) >= desde)
    if hasta: ventas_q = ventas_q.where(func.date(Venta.fecha) <= hasta)
    salida = StringIO(); writer = csv.writer(salida)
    writer.writerow(["Factura", "Fecha", "Canal", "Medio de pago", "Subtotal", "Impuesto", "Costo ventas", "Total"])
    for venta in db.scalars(ventas_q).all():
        costo = sum((d.costo_unitario * d.cantidad for d in venta.detalles), Decimal("0"))
        writer.writerow([venta.numero_factura or f"Venta-{venta.id}", venta.fecha.isoformat(), venta.canal, venta.medio_pago or "", venta.subtotal, venta.impuesto, costo, venta.total])
    return Response("\ufeff" + salida.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=ventas-cafbardla.csv"})

@app.get("/productos", response_class=HTMLResponse)
def productos(request: Request, db: Session = Depends(get_db)):
    from .domains.impresion.services import ImpresionService
    svc = ImpresionService(db)
    return templates.TemplateResponse(request, "productos.html", context(request, db) | {"productos": db.scalars(select(Producto).order_by(Producto.nombre)).all(), "categorias": db.scalars(select(Categoria).order_by(Categoria.nombre)).all(), "grupos_impresion": svc.listar_grupos(), "impresoras": svc.listar_impresoras()})

@app.post("/productos/categorias")
def crear_categoria(nombre: str = Form(...), db: Session = Depends(get_db)):
    nombre = nombre.strip()
    if nombre and not db.scalar(select(Categoria).where(Categoria.nombre == nombre)):
        db.add(Categoria(nombre=nombre)); db.commit()
    return RedirectResponse("/productos", 303)

@app.post("/productos")
def crear_producto(codigo: str = Form(...), nombre: str = Form(...), categoria_id: int | None = Form(None), tipo: str = Form("venta"), precio_venta: Decimal = Form(0), costo: Decimal = Form(0), existencias: Decimal = Form(0), stock_minimo: Decimal = Form(0), db: Session = Depends(get_db)):
    if db.scalar(select(Producto).where(Producto.codigo == codigo.strip())):
        raise HTTPException(400, "El código ya existe")
    producto = Producto(codigo=codigo.strip(), nombre=nombre.strip(), categoria_id=categoria_id or None, tipo=tipo, precio_venta=precio_venta, costo=costo, existencias=existencias, stock_minimo=stock_minimo)
    db.add(producto); db.flush()
    if existencias:
        # Saldo inicial por el kardex, para que el movimiento quede registrado
        # con su saldo. Antes se insertaba a mano, saltandose InventarioService.
        from .domains.inventario.services import InventarioService
        InventarioService(db).registrar_movimiento(
            producto_id=producto.id, tipo="ajuste_positivo", cantidad=existencias,
            costo_unitario=costo, referencia="Saldo inicial",
            empresa_id=producto.empresa_id or 1)
    db.commit(); return RedirectResponse("/productos", 303)

@app.post("/productos/{producto_id}/editar")
def editar_producto(producto_id: int, nombre: str = Form(...), precio_venta: Decimal = Form(...), costo: Decimal = Form(...), stock_minimo: Decimal = Form(...), db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if not producto: raise HTTPException(404)
    producto.nombre, producto.precio_venta, producto.costo, producto.stock_minimo = nombre.strip(), precio_venta, costo, stock_minimo
    db.commit(); return RedirectResponse("/productos", 303)

@app.post("/productos/{producto_id}/impresion")
def asignar_impresion_producto(
        producto_id: int, request: Request,
        grupo_impresion_id: str = Form(None),
        impresora_id: str = Form(None),
        db: Session = Depends(get_db)):
    """Asigna a un producto su grupo de impresión y/o impresora específica."""
    exigir_rol(request, "administrador")
    producto = db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(404)
    producto.grupo_impresion_id = (
        int(grupo_impresion_id) if grupo_impresion_id and grupo_impresion_id.strip()
        else None)
    producto.impresora_id = (
        int(impresora_id) if impresora_id and impresora_id.strip() else None)
    db.commit()
    return RedirectResponse("/productos", 303)


@app.post("/productos/{producto_id}/estado")
def cambiar_estado_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if not producto: raise HTTPException(404)
    producto.activo = not producto.activo; db.commit(); return RedirectResponse("/productos", 303)

@app.post("/inventario/movimiento")
def movimiento_inventario(request: Request, producto_id: int = Form(...), tipo: str = Form(...),
                          cantidad: Decimal = Form(...), costo_unitario: Decimal = Form(0),
                          referencia: str = Form(""), bodega_id: Optional[int] = Form(None),
                          db: Session = Depends(get_db)):
    """Registrar movimiento a traves del servicio unico de inventario.

    Antes esta ruta sumaba o restaba directamente sin validar existencias ni
    actualizar el costo: un producto con 2 unidades admitia una salida de 100
    y quedaba en -98 sin dejar rastro ni alerta.
    """
    from .domains.inventario.services import InventarioService
    servicio = InventarioService(db)
    try:
        servicio.registrar_movimiento(
            producto_id=producto_id,
            tipo=tipo,
            cantidad=cantidad,
            costo_unitario=costo_unitario or None,
            bodega_id=bodega_id,
            referencia=referencia.strip() or None,
            usuario_id=request.session.get("usuario_id"),
            empresa_id=request.session.get("empresa_id") or 1,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/inventario", 303)


@app.get("/inventario/kardex/{producto_id}", response_class=HTMLResponse)
def inventario_kardex(producto_id: int, request: Request, db: Session = Depends(get_db)):
    """Kardex de un producto: movimientos con saldo y costo resultante."""
    from .domains.inventario.services import InventarioService
    producto = db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(404, "Producto no encontrado")
    servicio = InventarioService(db)
    return templates.TemplateResponse(request, "kardex.html", context(request, db) | {
        "producto": producto,
        "movimientos": servicio.kardex(producto_id),
    })

@app.get("/gastos", response_class=HTMLResponse)
def gastos(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "gastos.html", context(request, db) | {"gastos": db.scalars(select(Gasto).order_by(Gasto.fecha.desc()).limit(100)).all()})

@app.post("/gastos")
def crear_gasto(fecha: date = Form(...), concepto: str = Form(...), categoria: str = Form(...), valor: Decimal = Form(...), proveedor: str = Form(""), db: Session = Depends(get_db)):
    if valor <= 0: raise HTTPException(400, "El valor debe ser mayor a cero")
    db.add(Gasto(fecha=fecha, concepto=concepto.strip(), categoria=categoria.strip(), valor=valor, proveedor=proveedor.strip() or None)); db.commit()
    return RedirectResponse("/gastos", 303)

@app.get("/clientes", response_class=HTMLResponse)
def clientes(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "clientes.html", context(request, db) | {"clientes": db.scalars(select(Cliente).order_by(Cliente.nombre)).all(), "abonos": db.scalars(select(AbonoCartera).order_by(AbonoCartera.fecha.desc()).limit(20)).all()})

@app.post("/clientes")
def crear_cliente(nombre: str = Form(...), documento: str = Form(""), telefono: str = Form(""), cupo_credito: Decimal = Form(0), db: Session = Depends(get_db)):
    db.add(Cliente(nombre=nombre.strip(), documento=documento.strip() or None, telefono=telefono.strip() or None, cupo_credito=cupo_credito)); db.commit()
    return RedirectResponse("/clientes", 303)

@app.post("/cartera/abonos")
def registrar_abono(cliente_id: int = Form(...), fecha: date = Form(...), valor: Decimal = Form(...), medio_pago: str = Form("efectivo"), observacion: str = Form(""), db: Session = Depends(get_db)):
    cliente = db.get(Cliente, cliente_id)
    if not cliente or valor <= 0: raise HTTPException(400, "Abono inválido")
    cliente.saldo_cartera = max(Decimal("0"), cliente.saldo_cartera - valor)
    db.add(AbonoCartera(cliente_id=cliente_id, fecha=fecha, valor=valor, medio_pago=medio_pago, observacion=observacion or None)); db.commit()
    return RedirectResponse("/clientes", 303)

@app.get("/empleados", response_class=HTMLResponse)
def empleados(request: Request, db: Session = Depends(get_db)):
    # Mapa empleado_id -> usuario, para mostrar quien ya tiene acceso al sistema.
    usuarios_por_empleado = {
        u.empleado_id: u for u in db.scalars(
            select(Usuario).where(Usuario.empleado_id.isnot(None))).all()}
    return templates.TemplateResponse(request, "empleados.html", context(request, db) | {"empleados": db.scalars(select(Empleado).order_by(Empleado.nombre)).all(), "turnos": db.scalars(select(Turno).where(Turno.estado != "anulado").order_by(Turno.entrada.desc()).limit(50)).all(), "turnos_abiertos": {t.empleado_id: t for t in db.scalars(select(Turno).where(Turno.estado.in_(("abierto", "en_receso")))).all()}, "usuarios_por_empleado": usuarios_por_empleado})


@app.post("/empleados/{empleado_id}/usuario")
def asignar_usuario_empleado(
        empleado_id: int, request: Request,
        usuario: str = Form(...), password: str = Form(""),
        rol: str = Form("mesero"),
        acceso_web: str = Form(None), acceso_app_pedidos: str = Form(None),
        db: Session = Depends(get_db)):
    """Crea o actualiza el usuario de un empleado y define su acceso.

    Los accesos son casillas: si no vienen en el formulario, quedan en False.
    Un empleado puede tener usuario sin acceso a ninguna app (solo marca turnos).
    """
    exigir_rol(request, "administrador")
    from .domains.auditoria.services import AuditoriaService
    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(404, "Empleado no encontrado")

    web = acceso_web is not None
    app_ped = acceso_app_pedidos is not None
    usuario_limpio = usuario.strip()

    # ¿Ya tiene usuario? Actualizar; si no, crear.
    cuenta = db.scalar(select(Usuario).where(Usuario.empleado_id == empleado_id))
    if cuenta:
        # Validar que el nombre de usuario no choque con otro.
        otro = db.scalar(select(Usuario).where(
            Usuario.usuario == usuario_limpio, Usuario.id != cuenta.id))
        if otro:
            raise HTTPException(400, "Ese nombre de usuario ya está en uso")
        cuenta.usuario = usuario_limpio
        cuenta.rol = rol
        cuenta.acceso_web = web
        cuenta.acceso_app_pedidos = app_ped
        if password.strip():
            cuenta.password_hash = passwords.hash(password.strip())
        accion, desc = "editar", f"Actualización de usuario para {empleado.nombre}"
    else:
        if db.scalar(select(Usuario).where(Usuario.usuario == usuario_limpio)):
            raise HTTPException(400, "Ese nombre de usuario ya está en uso")
        if not password.strip():
            raise HTTPException(400, "La contraseña es obligatoria para un usuario nuevo")
        cuenta = Usuario(
            empleado_id=empleado_id, empresa_id=empleado.empresa_id or 1,
            usuario=usuario_limpio, password_hash=passwords.hash(password.strip()),
            rol=rol, activo=True, acceso_web=web, acceso_app_pedidos=app_ped)
        db.add(cuenta)
        accion, desc = "crear", f"Creación de usuario para {empleado.nombre}"

    AuditoriaService(db).registrar_desde_request(
        request, accion=accion, modulo="empleados", entidad="Usuario",
        entidad_id=usuario_limpio,
        descripcion=desc,
        despues={"usuario": usuario_limpio, "rol": rol,
                 "acceso_web": web, "acceso_app_pedidos": app_ped})
    db.commit()
    return RedirectResponse("/empleados", 303)

@app.post("/empleados/{empleado_id}/foto")
async def subir_foto_empleado(
        empleado_id: int, request: Request,
        foto: UploadFile = File(...),
        consentimiento: str = Form(None),
        db: Session = Depends(get_db)):
    """Registra la foto del empleado (estructura para reconocimiento facial).

    Requiere consentimiento del empleado para el tratamiento del dato biometrico
    (Ley 1581 de 2012). El motor de reconocimiento en si no se implementa aqui:
    se guarda la foto y se deja el campo de codificacion facial listo.
    """
    exigir_rol(request, "administrador")
    from .domains.auditoria.services import AuditoriaService
    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(404, "Empleado no encontrado")
    if consentimiento is None:
        raise HTTPException(
            400, "Se requiere el consentimiento del empleado para registrar su foto")

    # Validar tipo de imagen.
    tipos_ok = {"image/jpeg", "image/png", "image/webp"}
    if foto.content_type not in tipos_ok:
        raise HTTPException(400, "La foto debe ser JPEG, PNG o WEBP")
    contenido = await foto.read()
    if len(contenido) > 5 * 1024 * 1024:
        raise HTTPException(400, "La foto no debe superar 5 MB")

    # Guardar en disco bajo static/fotos_empleados.
    ext = {"image/jpeg": ".jpg", "image/png": ".png",
           "image/webp": ".webp"}[foto.content_type]
    carpeta = APP_DIR / "static" / "fotos_empleados"
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"empleado_{empleado_id}{ext}"
    (carpeta / nombre_archivo).write_bytes(contenido)

    empleado.foto = f"/static/fotos_empleados/{nombre_archivo}"
    empleado.consentimiento_biometrico = True
    empleado.fecha_consentimiento = fecha_colombia()
    AuditoriaService(db).registrar_desde_request(
        request, accion="editar", modulo="empleados", entidad="Empleado",
        entidad_id=empleado_id,
        descripcion=f"Registro de foto de {empleado.nombre} (con consentimiento)")
    db.commit()
    return RedirectResponse("/empleados", 303)


@app.post("/empleados")
def crear_empleado(nombre: str = Form(...), documento: str = Form(...), cargo: str = Form(...), salario: Decimal = Form(0), tipo_documento: str = Form("CC"), fecha_ingreso: date | None = Form(None), tipo_contrato: str = Form("indefinido"), eps: str = Form(""), pension: str = Form(""), arl: str = Form(""), db: Session = Depends(get_db)):
    if db.scalar(select(Empleado).where(Empleado.documento == documento.strip())): raise HTTPException(400, "El documento ya existe")
    db.add(Empleado(nombre=nombre.strip(), documento=documento.strip(), cargo=cargo.strip(), salario=salario, tipo_documento=tipo_documento, fecha_ingreso=fecha_ingreso, tipo_contrato=tipo_contrato, eps=eps.strip() or None, pension=pension.strip() or None, arl=arl.strip() or None)); db.commit()
    return RedirectResponse("/empleados", 303)

@app.post("/turnos/entrada")
def entrada_turno(request: Request, empleado_id: int = Form(...),
                  db: Session = Depends(get_db)):
    """Marca entrada a traves de AsistenciaService."""
    from .domains.asistencia.services import AsistenciaService
    try:
        AsistenciaService(db).marcar_entrada(
            empleado_id, empresa_id=request.session.get("empresa_id") or 1)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/empleados", 303)

@app.post("/turnos/{empleado_id}/receso")
def receso_turno(empleado_id: int, request: Request, db: Session = Depends(get_db)):
    from .domains.asistencia.services import AsistenciaService
    try:
        AsistenciaService(db).marcar_salida_receso(empleado_id)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/empleados", 303)

@app.post("/turnos/{empleado_id}/regreso")
def regreso_turno(empleado_id: int, request: Request, db: Session = Depends(get_db)):
    from .domains.asistencia.services import AsistenciaService
    try:
        AsistenciaService(db).marcar_regreso_receso(empleado_id)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/empleados", 303)

@app.post("/turnos/{empleado_id}/salida")
def salida_turno(empleado_id: int, request: Request, db: Session = Depends(get_db)):
    """Marca salida, calcula horas y genera novedad de extra automaticamente."""
    from .domains.asistencia.services import AsistenciaService
    try:
        AsistenciaService(db).marcar_salida(empleado_id)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/empleados", 303)

@app.get("/produccion", response_class=HTMLResponse)
def produccion(request: Request, db: Session = Depends(get_db)):
    """Vista de produccion con costeo teorico e indicadores."""
    from .domains.produccion.services import ProduccionService
    servicio = ProduccionService(db)
    empresa_id = request.session.get("empresa_id") or 1

    recetas = db.scalars(select(Receta).where(Receta.tipo_receta == "produccion")).all()
    costos = {}
    for r in recetas:
        if r.detalles:
            try:
                costos[r.id] = servicio.costear_receta(r.id)
            except ValueError:
                pass

    ordenes = servicio.listar_ordenes(empresa_id=empresa_id, limit=30)
    return templates.TemplateResponse(request, "produccion.html", context(request, db) | {
        "recetas": db.scalars(select(Receta)).all(),
        "costos": costos,
        "ordenes": ordenes,
        "indicadores": servicio.indicadores(empresa_id=empresa_id),
        "productos": db.scalars(select(Producto).order_by(Producto.nombre)).all(),
        "insumos": db.scalars(
            select(Producto).where(Producto.tipo.in_(["insumo", "elaborado"]))
            .order_by(Producto.nombre)).all(),
    })

@app.post("/produccion/recetas")
def crear_receta(producto_id: int = Form(...), tipo_receta: str = Form("produccion"), rendimiento: Decimal = Form(1), instrucciones: str = Form(""), db: Session = Depends(get_db)):
    if db.scalar(select(Receta).where(Receta.producto_id == producto_id)): raise HTTPException(400, "El producto ya tiene receta")
    producto = db.get(Producto, producto_id)
    if not producto or rendimiento <= 0 or tipo_receta not in ("produccion", "venta"): raise HTTPException(400, "Receta inválida")
    if tipo_receta == "produccion" and producto.tipo != "elaborado": raise HTTPException(400, "Una receta de producción debe generar un producto elaborado")
    if tipo_receta == "venta" and producto.tipo != "venta": raise HTTPException(400, "Una receta de venta debe corresponder a un producto de venta")
    db.add(Receta(producto_id=producto_id, rendimiento=rendimiento, instrucciones=instrucciones or None, tipo_receta=tipo_receta)); db.commit()
    return RedirectResponse("/produccion", 303)

@app.post("/produccion/recetas/{receta_id}/insumos")
def agregar_insumo_receta(receta_id: int, insumo_id: int = Form(...), cantidad: Decimal = Form(...), merma_porcentaje: Decimal = Form(0), db: Session = Depends(get_db)):
    if not db.get(Receta, receta_id) or cantidad <= 0: raise HTTPException(400, "Dato inválido")
    if merma_porcentaje < 0: raise HTTPException(400, "La merma no puede ser negativa")
    db.add(RecetaDetalle(receta_id=receta_id, insumo_id=insumo_id, cantidad=cantidad, merma_porcentaje=merma_porcentaje)); db.commit()
    return RedirectResponse("/produccion", 303)

@app.post("/produccion/recetas/{receta_id}/ejecutar")
def ejecutar_produccion(receta_id: int, request: Request, lotes: Decimal = Form(...),
                        db: Session = Depends(get_db)):
    """Ejecutar produccion a traves de ProduccionService.

    Antes esta ruta restaba insumos a mano y recalculaba el costo por su
    cuenta. Ahora delega en el servicio, que pasa por el kardex, registra la
    merma y permite anular.
    """
    from .domains.produccion.services import ProduccionService
    try:
        ProduccionService(db).ejecutar(
            receta_id, lotes, empresa_id=request.session.get("empresa_id") or 1,
            usuario_id=request.session.get("usuario_id"))
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/produccion", 303)


@app.post("/produccion/ordenes/{orden_id}/anular")
def anular_produccion_web(orden_id: int, request: Request,
                          motivo: str = Form(...), db: Session = Depends(get_db)):
    """Anular una orden de produccion revirtiendo el inventario."""
    exigir_rol(request, "administrador", "caja")
    from .domains.produccion.services import ProduccionService
    try:
        ProduccionService(db).anular(
            orden_id, motivo, usuario_id=request.session.get("usuario_id"))
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/produccion", 303)

@app.get("/pedidos-pendientes", response_class=HTMLResponse)
def pedidos_pendientes(request: Request, db: Session = Depends(get_db)):
    """Pantalla del personal: pedidos de cliente pendientes (mesa y autoservicio)."""
    from .domains.pedidos_cliente.services import PedidoClienteService
    svc = PedidoClienteService(db)
    return templates.TemplateResponse(request, "pedidos_pendientes.html",
        context(request, db) | {
            "autoservicio": svc.listar_pendientes(tipo="autoservicio"),
            "mesa": svc.listar_pendientes(tipo="mesa")})


@app.get("/caja", response_class=HTMLResponse)
def caja(request: Request, db: Session = Depends(get_db)):
    sesion = db.scalar(select(SesionCaja).where(SesionCaja.cierre == None).order_by(SesionCaja.apertura.desc()))
    ventas_efectivo = Decimal("0")
    if sesion:
        ventas_efectivo = db.scalar(select(func.coalesce(func.sum(Venta.total),0)).where(Venta.fecha >= sesion.apertura, Venta.estado == "pagada", Venta.medio_pago == "efectivo"))
    return templates.TemplateResponse(request, "caja.html", context(request, db) | {"sesion": sesion, "efectivo_esperado": (sesion.base_inicial + ventas_efectivo) if sesion else 0, "ventas_efectivo": ventas_efectivo})

@app.get("/domicilios", response_class=HTMLResponse)
def domicilios(request: Request, db: Session = Depends(get_db)):
    filas = db.execute(select(Domicilio, Venta, Cliente.nombre.label("cliente"), Empleado.nombre.label("repartidor")).join(Venta, Venta.id == Domicilio.venta_id).outerjoin(Cliente, Cliente.id == Venta.cliente_id).outerjoin(Empleado, Empleado.id == Domicilio.repartidor_id).order_by(Venta.fecha.desc()).limit(100)).all()
    return templates.TemplateResponse(request, "domicilios.html", context(request, db) | {"filas": filas, "clientes": db.scalars(select(Cliente).order_by(Cliente.nombre)).all(), "repartidores": db.scalars(select(Empleado).where(Empleado.activo == True).order_by(Empleado.nombre)).all()})

@app.post("/domicilios")
def crear_domicilio(request: Request, cliente_id: int = Form(...), direccion: str = Form(...), barrio: str = Form(""), contacto: str = Form(""), repartidor_id: int | None = Form(None), cargo_envio: Decimal = Form(0), db: Session = Depends(get_db)):
    if not db.get(Cliente, cliente_id) or not direccion.strip() or cargo_envio < 0: raise HTTPException(400, "Datos de domicilio inválidos")
    venta = Venta(cliente_id=cliente_id, empleado_id=request.session.get("empleado_id"), canal="domicilio", cargo_envio=cargo_envio)
    db.add(venta); db.flush()
    db.add(Domicilio(venta_id=venta.id, direccion=direccion.strip(), barrio=barrio.strip() or None, contacto=contacto.strip() or None, repartidor_id=repartidor_id or None))
    db.commit(); return RedirectResponse(f"/pedidos/{venta.id}", 303)

@app.get("/pedidos/{venta_id}", response_class=HTMLResponse)
def pedido_domicilio(venta_id: int, request: Request, db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id); domicilio = db.scalar(select(Domicilio).where(Domicilio.venta_id == venta_id))
    if not venta or not domicilio or venta.canal != "domicilio": raise HTTPException(404)
    return templates.TemplateResponse(request, "pedido.html", context(request, db) | {"venta": venta, "domicilio": domicilio, "productos": db.scalars(select(Producto).where(Producto.activo == True)).all()})

@app.post("/api/pedidos/{venta_id}/items")
def agregar_item_domicilio(venta_id: int, producto_id: int = Form(...), cantidad: Decimal = Form(1), nota: str = Form(""), db: Session = Depends(get_db)):
    venta, producto = db.get(Venta, venta_id), db.get(Producto, producto_id)
    if not venta or venta.canal != "domicilio" or venta.estado != "abierta" or not producto or cantidad <= 0: raise HTTPException(400, "Pedido o producto inválido")
    db.add(DetalleVenta(venta_id=venta.id, producto_id=producto.id, cantidad=cantidad, precio=producto.precio_venta, nota=nota or None)); db.flush()
    recalcular_venta(venta); empresa = db.scalar(select(Empresa).limit(1)); venta.impuesto = (venta.subtotal * empresa.impuesto_porcentaje / Decimal("100")).quantize(Decimal("0.01")); recalcular_venta(venta)
    db.commit(); return {"ok": True, "total": str(venta.total)}

@app.post("/domicilios/{domicilio_id}/estado")
def estado_domicilio(domicilio_id: int, estado: str = Form(...), repartidor_id: int | None = Form(None), db: Session = Depends(get_db)):
    domicilio = db.get(Domicilio, domicilio_id)
    if not domicilio or estado not in ("recibido", "preparando", "listo", "en_camino", "entregado", "cancelado"): raise HTTPException(400, "Estado inválido")
    domicilio.estado = estado
    if repartidor_id: domicilio.repartidor_id = repartidor_id
    db.commit(); return RedirectResponse("/domicilios", 303)

@app.post("/caja/abrir")
def abrir_caja(base_inicial: Decimal = Form(0), db: Session = Depends(get_db)):
    abierta = db.scalar(select(SesionCaja).where(SesionCaja.cierre == None))
    if not abierta: db.add(SesionCaja(base_inicial=base_inicial)); db.commit()
    return RedirectResponse("/caja", 303)

@app.post("/caja/{sesion_id}/cerrar")
def cerrar_caja(sesion_id: int, efectivo_declarado: Decimal = Form(...), observacion_cierre: str = Form(""), db: Session = Depends(get_db)):
    sesion = db.get(SesionCaja, sesion_id)
    if not sesion or sesion.cierre: raise HTTPException(400, "Caja no disponible")
    sesion.cierre, sesion.efectivo_declarado, sesion.observacion_cierre = hora_colombia(), efectivo_declarado, observacion_cierre or None
    db.commit(); return RedirectResponse("/caja", 303)

@app.get("/configuracion", response_class=HTMLResponse)
def configuracion(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    return templates.TemplateResponse(request, "configuracion.html", context(request, db))


@app.get("/impresoras", response_class=HTMLResponse)
def vista_impresoras(request: Request, db: Session = Depends(get_db)):
    """Configuración de impresoras y grupos de impresión."""
    exigir_rol(request, "administrador")
    from .domains.impresion.services import ImpresionService
    svc = ImpresionService(db)
    return templates.TemplateResponse(request, "impresoras.html",
        context(request, db) | {
            "impresoras": svc.listar_impresoras(),
            "grupos": svc.listar_grupos()})


@app.post("/impresoras")
def crear_impresora(request: Request, nombre: str = Form(...),
                    destino: str = Form("local"),
                    tipo_conexion: str = Form("local"),
                    es_por_defecto: str = Form(None),
                    db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .domains.impresion.services import ImpresionService
    from .domains.auditoria.services import AuditoriaService
    try:
        imp = ImpresionService(db).crear_impresora(
            nombre, destino, tipo_conexion, es_por_defecto is not None)
        AuditoriaService(db).registrar_desde_request(
            request, accion="crear", modulo="configuracion", entidad="Impresora",
            entidad_id=imp.id, descripcion=f"Impresora creada: {nombre}")
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse("/impresoras", 303)


@app.post("/impresoras/grupos")
def crear_grupo_impresion(request: Request, nombre: str = Form(...),
                          impresora_id: str = Form(None),
                          db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .domains.impresion.services import ImpresionService
    from .domains.auditoria.services import AuditoriaService
    try:
        imp_id = int(impresora_id) if impresora_id and impresora_id.strip() else None
        g = ImpresionService(db).crear_grupo(nombre, imp_id)
        AuditoriaService(db).registrar_desde_request(
            request, accion="crear", modulo="configuracion",
            entidad="GrupoImpresion", entidad_id=g.id,
            descripcion=f"Grupo de impresión creado: {nombre}")
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse("/impresoras", 303)

@app.get("/nomina", response_class=HTMLResponse)
def nomina(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .domains.nomina.services import NominaService
    servicio = NominaService(db)
    periodos = db.scalars(select(PeriodoNomina).order_by(PeriodoNomina.fecha_fin.desc()).limit(30)).all()
    resumenes = {}
    for per in periodos:
        if per.estado in ("liquidado", "cerrado"):
            try:
                resumenes[per.id] = servicio.resumen_periodo(per.id)
            except ValueError:
                pass
    liquidaciones = db.execute(
        select(LiquidacionNomina, Empleado.nombre, PeriodoNomina.fecha_inicio,
               PeriodoNomina.fecha_fin)
        .join(Empleado, Empleado.id == LiquidacionNomina.empleado_id)
        .join(PeriodoNomina, PeriodoNomina.id == LiquidacionNomina.periodo_id)
        .order_by(LiquidacionNomina.id.desc()).limit(100)).all()
    novedades = db.execute(
        select(NovedadNomina, Empleado.nombre)
        .join(Empleado, Empleado.id == NovedadNomina.empleado_id)
        .where(NovedadNomina.aplicada == False)
        .order_by(NovedadNomina.fecha.desc()).limit(30)).all()
    try:
        parametros = servicio.parametros_vigentes()
    except ValueError:
        parametros = None
    return templates.TemplateResponse(request, "nomina.html", context(request, db) | {
        "parametros": parametros, "periodos": periodos, "resumenes": resumenes,
        "liquidaciones": liquidaciones, "novedades": novedades,
        "empleados": db.scalars(
            select(Empleado).where(Empleado.activo == True)
            .order_by(Empleado.nombre)).all()})

@app.post("/nomina/parametros")
def guardar_parametros_nomina(request: Request, vigencia_desde: date = Form(...), salario_minimo: Decimal = Form(0), auxilio_transporte: Decimal = Form(0), tope_auxilio_transporte: Decimal = Form(0), salud_empleado_pct: Decimal = Form(0), pension_empleado_pct: Decimal = Form(0), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    if min(salario_minimo, auxilio_transporte, tope_auxilio_transporte, salud_empleado_pct, pension_empleado_pct) < 0: raise HTTPException(400, "Los parámetros no pueden ser negativos")
    db.add(ParametrosNomina(vigencia_desde=vigencia_desde, salario_minimo=salario_minimo, auxilio_transporte=auxilio_transporte, tope_auxilio_transporte=tope_auxilio_transporte, salud_empleado_pct=salud_empleado_pct, pension_empleado_pct=pension_empleado_pct)); db.commit()
    return RedirectResponse("/nomina", 303)

@app.post("/nomina/periodos")
def crear_periodo_nomina(request: Request, fecha_inicio: date = Form(...), fecha_fin: date = Form(...), periodicidad: str = Form(...), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    if fecha_fin < fecha_inicio or periodicidad not in ("quincenal", "mensual"): raise HTTPException(400, "Período inválido")
    db.add(PeriodoNomina(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, periodicidad=periodicidad)); db.commit(); return RedirectResponse("/nomina", 303)

@app.post("/nomina/periodos/{periodo_id}/liquidar")
def liquidar_periodo_nomina(periodo_id: int, request: Request, db: Session = Depends(get_db)):
    """Liquida un periodo a traves de NominaService.

    Antes esta ruta solo calculaba salario + auxilio + salud + pension, sin
    horas extra, recargos, aportes patronales, provisiones ni retencion. Ahora
    delega en el servicio, que aplica la legislacion completa.
    """
    exigir_rol(request, "administrador")
    from .domains.nomina.services import NominaService
    from .domains.auditoria.services import AuditoriaService
    try:
        periodo = NominaService(db).liquidar_periodo(periodo_id)
        AuditoriaService(db).registrar_desde_request(
            request, accion="editar", modulo="nomina", entidad="PeriodoNomina",
            entidad_id=periodo_id, descripcion="Liquidación de nómina del período",
            despues={"estado": "liquidado", "neto": periodo.total_neto})
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/nomina", 303)


@app.post("/nomina/periodos/{periodo_id}/anular")
def anular_periodo_nomina(periodo_id: int, request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .domains.nomina.services import NominaService
    from .domains.auditoria.services import AuditoriaService
    try:
        NominaService(db).anular_liquidacion(periodo_id)
        AuditoriaService(db).registrar_desde_request(
            request, accion="anular", modulo="nomina", entidad="PeriodoNomina",
            entidad_id=periodo_id, descripcion="Anulación de liquidación de nómina")
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/nomina", 303)


@app.post("/nomina/novedades")
def registrar_novedad_nomina(request: Request, empleado_id: int = Form(...),
                             tipo: str = Form(...), periodo_id: int = Form(None),
                             cantidad: Decimal = Form(0), valor: Decimal = Form(0),
                             descripcion: str = Form(""),
                             db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .domains.nomina.services import NominaService
    try:
        nov = NominaService(db).registrar_novedad(
            empleado_id, tipo, cantidad=cantidad, valor=valor,
            empresa_id=request.session.get("empresa_id") or 1,
            descripcion=descripcion or None)
        if periodo_id:
            nov.periodo_id = periodo_id
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/nomina", 303)


@app.get("/nomina/liquidaciones/{liquidacion_id}/desprendible")
def descargar_desprendible(liquidacion_id: int, request: Request,
                           db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from fastapi.responses import Response
    from .domains.nomina.documentos import desprendible_pdf
    try:
        pdf = desprendible_pdf(db, liquidacion_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f"attachment; filename=desprendible_{liquidacion_id}.pdf"})


@app.get("/nomina/periodos/{periodo_id}/electronica")
def descargar_nomina_electronica(periodo_id: int, request: Request,
                                 db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from fastapi.responses import JSONResponse
    from .domains.nomina.documentos import nomina_electronica_json
    try:
        datos = nomina_electronica_json(db, periodo_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return JSONResponse(content=datos, headers={
        "Content-Disposition": f"attachment; filename=nomina_electronica_{periodo_id}.json"})

@app.get("/compras", response_class=HTMLResponse)
def compras(request: Request, db: Session = Depends(get_db)):
    """Vista de compras con indicadores, cuentas por pagar y ordenes abiertas."""
    exigir_rol(request, "administrador", "caja")
    from .domains.compras.services import ComprasService

    servicio = ComprasService(db)
    empresa_id = request.session.get("empresa_id") or 1

    filas = db.execute(
        select(Compra, Proveedor.nombre, Proveedor.obligado_facturar)
        .join(Proveedor, Proveedor.id == Compra.proveedor_id)
        .order_by(Compra.fecha.desc(), Compra.id.desc()).limit(100)
    ).all()

    ordenes = db.scalars(
        select(OrdenCompra).where(
            OrdenCompra.empresa_id == empresa_id,
            OrdenCompra.estado.in_(["emitida", "parcial"]))
        .order_by(OrdenCompra.fecha.desc()).limit(20)
    ).all()

    return templates.TemplateResponse(request, "compras.html", context(request, db) | {
        "proveedores": db.scalars(
            select(Proveedor).where(Proveedor.activo == True)
            .order_by(Proveedor.nombre)).all(),
        "productos": db.scalars(
            select(Producto).where(Producto.activo == True)
            .order_by(Producto.nombre)).all(),
        "filas": filas,
        "indicadores": servicio.indicadores(empresa_id=empresa_id),
        "cuentas_por_pagar": servicio.cuentas_por_pagar(empresa_id=empresa_id),
        "ordenes_abiertas": ordenes,
    })

@app.post("/proveedores")
def crear_proveedor(request: Request, nombre: str = Form(...), tipo_documento: str = Form("NIT"), documento: str = Form(...), telefono: str = Form(""), email: str = Form(""), obligado_facturar: bool = Form(False), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "caja")
    db.add(Proveedor(nombre=nombre.strip(), tipo_documento=tipo_documento, documento=documento.strip(), telefono=telefono.strip() or None, email=email.strip() or None, obligado_facturar=obligado_facturar)); db.commit(); return RedirectResponse("/compras", 303)

@app.post("/compras")
def registrar_compra(request: Request, proveedor_id: int = Form(...),
                     fecha: date = Form(...), concepto: str = Form(...),
                     numero_documento: str = Form(""),
                     producto_id: Optional[int] = Form(None),
                     cantidad: Optional[Decimal] = Form(None),
                     costo_unitario: Optional[Decimal] = Form(None),
                     iva_porcentaje: Optional[Decimal] = Form(None),
                     forma_pago: str = Form("contado"),
                     valor: Optional[Decimal] = Form(None),
                     db: Session = Depends(get_db)):
    """Registrar factura de compra a traves de ComprasService.

    Antes esta ruta insertaba una fila plana con UN producto y calculaba el
    costo por su cuenta. Ahora delega en el servicio, que lleva el desglose
    fiscal, el kardex y permite anular.
    """
    exigir_rol(request, "administrador", "caja")
    from .domains.compras.services import ComprasService

    servicio = ComprasService(db)
    empresa_id = request.session.get("empresa_id") or 1
    usuario_id = request.session.get("usuario_id")

    try:
        if producto_id and cantidad:
            unitario = costo_unitario
            if unitario is None:
                if not valor:
                    raise HTTPException(400, "Indique el costo unitario o el valor total")
                unitario = (valor / cantidad).quantize(Decimal("0.01"))
            lineas = [{
                "producto_id": producto_id,
                "cantidad": cantidad,
                "costo_unitario": unitario,
                "iva_porcentaje": iva_porcentaje,
            }]
        else:
            # Gasto sin inventario: se registra como servicio sin producto.
            raise HTTPException(
                400, "Indique producto y cantidad. Para gastos sin inventario use /gastos")

        servicio.crear_compra(
            proveedor_id, lineas, empresa_id=empresa_id, usuario_id=usuario_id,
            numero_documento=numero_documento, concepto=concepto.strip(),
            fecha=fecha, forma_pago=forma_pago)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/compras", 303)


@app.post("/compras/{compra_id}/anular")
def anular_compra_web(compra_id: int, request: Request,
                      motivo: str = Form(...), db: Session = Depends(get_db)):
    """Anular una compra revirtiendo el inventario."""
    exigir_rol(request, "administrador", "caja")
    from .domains.compras.services import ComprasService
    try:
        ComprasService(db).anular_compra(
            compra_id, motivo, usuario_id=request.session.get("usuario_id"))
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    return RedirectResponse("/compras", 303)


@app.post("/configuracion")
def actualizar_empresa(request: Request, nombre: str = Form(...), nit: str = Form(""), logo_url: str = Form(""), color_primario: str = Form(...), color_secundario: str = Form(...), moneda: str = Form("COP"), direccion: str = Form(""), telefono: str = Form(""), prefijo_factura: str = Form("POS"), consecutivo_factura: int = Form(1), impuesto_porcentaje: Decimal = Form(0), tipo_persona: str = Form("juridica"), tipo_sociedad: str = Form(""), regimen_tributario: str = Form("ordinario"), facturador_electronico: bool = Form(False), proveedor_tecnologico: str = Form(""), modo_electronico: str = Form("pruebas"), prefijo_nomina: str = Form("NE"), consecutivo_nomina: int = Form(1), software_nomina_id: str = Form(""), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    if tipo_persona not in ("juridica", "natural") or regimen_tributario not in ("ordinario", "simple") or modo_electronico not in ("pruebas", "produccion"): raise HTTPException(400, "Clasificación tributaria inválida")
    if facturador_electronico and modo_electronico == "produccion" and not proveedor_tecnologico.strip(): raise HTTPException(400, "Para producción electrónica configure el proveedor tecnológico")
    empresa = db.scalar(select(Empresa).limit(1))
    empresa.nombre, empresa.nit, empresa.logo_url = nombre.strip(), nit.strip() or None, logo_url.strip() or None
    empresa.color_primario, empresa.color_secundario, empresa.moneda = color_primario, color_secundario, moneda.strip().upper()
    empresa.direccion, empresa.telefono = direccion.strip() or None, telefono.strip() or None
    empresa.prefijo_factura, empresa.consecutivo_factura, empresa.impuesto_porcentaje = prefijo_factura.strip().upper()[:12] or "POS", max(1, consecutivo_factura), max(Decimal("0"), impuesto_porcentaje)
    empresa.tipo_persona, empresa.tipo_sociedad, empresa.regimen_tributario = tipo_persona, (tipo_sociedad.strip().upper() or None) if tipo_persona == "juridica" else None, regimen_tributario
    empresa.facturador_electronico, empresa.proveedor_tecnologico, empresa.modo_electronico = facturador_electronico, proveedor_tecnologico.strip() or None, modo_electronico
    empresa.prefijo_nomina, empresa.consecutivo_nomina, empresa.software_nomina_id = prefijo_nomina.strip().upper()[:12] or "NE", max(1, consecutivo_nomina), software_nomina_id.strip() or None
    db.commit(); return RedirectResponse("/configuracion", 303)

@app.get("/roles", response_class=HTMLResponse)
def vista_roles(request: Request, db: Session = Depends(get_db)):
    """Gestión de roles y permisos por módulo (RBAC parametrizable)."""
    exigir_rol(request, "administrador")
    from .services.rbac_service import RolService
    svc = RolService(db)
    roles = svc.listar_roles()
    modulos = svc.modulos_disponibles()
    # permisos actuales por rol, para marcar las casillas
    permisos_por_rol = {r.id: svc.permisos_modulo_de(r.nombre) for r in roles}
    return templates.TemplateResponse(request, "roles.html",
        context(request, db) | {"roles": roles, "modulos": modulos,
                                "permisos_por_rol": permisos_por_rol})


@app.post("/roles")
def crear_rol(request: Request, nombre: str = Form(...),
              nivel_acceso: int = Form(30),
              modulos: list[str] = Form(default=[]),
              db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .services.rbac_service import RolService
    from .domains.auditoria.services import AuditoriaService
    try:
        rol = RolService(db).crear_rol(
            nombre, nivel_acceso=nivel_acceso, modulos=modulos)
        AuditoriaService(db).registrar_desde_request(
            request, accion="crear", modulo="usuarios", entidad="Rol",
            entidad_id=rol.id, descripcion=f"Rol creado: {nombre}",
            despues={"nombre": nombre, "modulos": modulos})
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse("/roles", 303)


@app.post("/roles/{rol_id}/permisos")
def actualizar_permisos_rol(rol_id: int, request: Request,
                            modulos: list[str] = Form(default=[]),
                            db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .services.rbac_service import RolService
    from .domains.auditoria.services import AuditoriaService
    try:
        rol = RolService(db).actualizar_permisos_modulo(rol_id, modulos)
        AuditoriaService(db).registrar_desde_request(
            request, accion="editar", modulo="usuarios", entidad="Rol",
            entidad_id=rol_id, descripcion=f"Permisos actualizados: {rol.nombre}",
            despues={"modulos": modulos})
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse("/roles", 303)


@app.post("/roles/{rol_id}/eliminar")
def eliminar_rol(rol_id: int, request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    from .services.rbac_service import RolService
    from .domains.auditoria.services import AuditoriaService
    try:
        RolService(db).eliminar_rol(rol_id)
        AuditoriaService(db).registrar_desde_request(
            request, accion="eliminar", modulo="usuarios", entidad="Rol",
            entidad_id=rol_id, descripcion="Rol eliminado")
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse("/roles", 303)


@app.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    return templates.TemplateResponse(request, "usuarios.html", context(request, db) | {"usuarios": db.scalars(select(Usuario).order_by(Usuario.usuario)).all(), "empleados": db.scalars(select(Empleado).where(Empleado.activo == True).order_by(Empleado.nombre)).all()})

@app.post("/usuarios")
def crear_usuario(request: Request, usuario: str = Form(...), password: str = Form(...), rol: str = Form(...), empleado_id: int | None = Form(None), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    # El rol debe existir en el RBAC (parametrizable), no en una lista fija.
    from .services.rbac_service import RolService
    if not RolService(db).rol_por_nombre_flexible(rol) or len(password) < 8:
        raise HTTPException(400, "Rol inexistente o contraseña menor a 8 caracteres")
    if db.scalar(select(Usuario).where(Usuario.usuario == usuario.strip())): raise HTTPException(400, "El usuario ya existe")
    db.add(Usuario(usuario=usuario.strip(), password_hash=passwords.hash(password), rol=rol, empleado_id=empleado_id or None)); db.commit()
    return RedirectResponse("/usuarios", 303)

@app.post("/usuarios/{usuario_id}/estado")
def estado_usuario(usuario_id: int, request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    cuenta = db.get(Usuario, usuario_id)
    if not cuenta: raise HTTPException(404)
    if cuenta.id == request.session.get("usuario_id"): raise HTTPException(400, "No puede desactivar su propia cuenta")
    cuenta.activo = not cuenta.activo; db.commit(); return RedirectResponse("/usuarios", 303)

@app.get("/cocina", response_class=HTMLResponse)
def cocina(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "cocina")
    filas = db.execute(select(DetalleVenta, Producto.nombre, Mesa.nombre.label("mesa"), Venta.fecha).join(Producto, Producto.id == DetalleVenta.producto_id).join(Venta, Venta.id == DetalleVenta.venta_id).outerjoin(Mesa, Mesa.id == Venta.mesa_id).where(DetalleVenta.estado_cocina.in_(["pendiente", "preparando", "listo"]), Venta.estado == "abierta").order_by(Venta.fecha)).all()
    return templates.TemplateResponse(request, "cocina.html", context(request, db) | {"filas": filas})

@app.post("/cocina/{detalle_id}/estado")
def estado_cocina(detalle_id: int, request: Request, estado: str = Form(...), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "cocina")
    detalle = db.get(DetalleVenta, detalle_id)
    if not detalle or estado not in ("pendiente", "preparando", "listo", "entregado"): raise HTTPException(400, "Estado inválido")
    detalle.estado_cocina = estado; db.commit(); return RedirectResponse("/cocina", 303)

@app.get("/api/tema")
def tema(db:Session=Depends(get_db)):
    e=db.scalar(select(Empresa).limit(1)); return {"nombre":e.nombre,"primario":e.color_primario,"secundario":e.color_secundario,"logo":e.logo_url}
