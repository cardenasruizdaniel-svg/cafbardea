from contextlib import asynccontextmanager
from io import StringIO
import csv
import logging
import secrets
from pathlib import Path
from decimal import Decimal
from datetime import datetime, date
from fastapi import FastAPI, Depends, Form, HTTPException, Request
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
from .enterprise_init import setup_enterprise_database
from .services.rbac_service import inicializar_rbac
from .services.jwt_service import JWTService

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed(db: Session):
    if db.scalar(select(func.count(Empresa.id))) == 0:
        empresa = Empresa(nombre="Mi Café", nit="900.000.000-1")
        db.add(empresa)
        db.flush()
        admin_empleado = Empleado(nombre="Administrador inicial", documento="ADMIN-001", cargo="Administrador", salario=0)
        db.add(admin_empleado)
        db.flush()
        db.add(Usuario(empleado_id=admin_empleado.id, empresa_id=empresa.id, usuario="admin", password_hash=passwords.hash("Admin123*"), rol="administrador"))
        salon, terraza = Zona(nombre="Salón", orden=1), Zona(nombre="Terraza", orden=2)
        db.add_all([salon, terraza]); db.flush()
        db.add_all([Mesa(zona_id=salon.id,nombre="M1",capacidad=4,posicion_x=8,posicion_y=15), Mesa(zona_id=salon.id,nombre="M2",capacidad=2,posicion_x=36,posicion_y=22), Mesa(zona_id=terraza.id,nombre="T1",capacidad=4,posicion_x=20,posicion_y=20)])
        cafe, comida = Categoria(nombre="Cafetería"), Categoria(nombre="Comidas")
        db.add_all([cafe,comida]); db.flush()
        db.add_all([Producto(categoria_id=cafe.id,codigo="CAF-001",nombre="Capuchino",precio_venta=8500,costo=2400,existencias=50,stock_minimo=10), Producto(categoria_id=cafe.id,codigo="CAF-002",nombre="Latte",precio_venta=9000,costo=2700,existencias=40,stock_minimo=10), Producto(categoria_id=comida.id,codigo="COM-001",nombre="Croissant",precio_venta=7000,costo=2500,existencias=20,stock_minimo=5)])
        
        # Seed: Crear venta de prueba y comandas para FASE 3
        mesa_salon = db.query(Mesa).filter(Mesa.nombre == "M1").first()
        venta = Venta(mesa_id=mesa_salon.id, estado="abierta", total=0)
        db.add(venta); db.flush()
        
        # Crear comandas de prueba
        db.add_all([
            Comanda(venta_id=venta.id, mesa_id=mesa_salon.id, estado="pendiente", prioridad="normal", notas="Comanda 1"),
            Comanda(venta_id=venta.id, mesa_id=mesa_salon.id, estado="preparando", prioridad="alta", notas="Comanda 2"),
            Comanda(venta_id=venta.id, mesa_id=mesa_salon.id, estado="lista", prioridad="normal", notas="Comanda 3", fecha_entrega=datetime.utcnow())
        ])
        
        # Seed: Crear período de nómina y liquidaciones para FASE 4
        periodo = PeriodoNomina(
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
            periodicidad="mensual",
            estado="borrador"
        )
        db.add(periodo); db.flush()
        
        # Crear liquidaciones para empleados del sistema
        db.add_all([
            LiquidacionNomina(
                periodo_id=periodo.id,
                empleado_id=admin_empleado.id,
                dias_liquidados=30,
                salario_base=2500000,
                estado_electronico="pendiente_configuracion"
            ),
            LiquidacionNomina(
                periodo_id=periodo.id,
                empleado_id=admin_empleado.id,
                dias_liquidados=2,
                salario_base=500000,
                estado_electronico="pendiente_configuracion"
            )
        ])
        
        db.commit()

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

# CORS - permitir solo mismo origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["127.0.0.1", "localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware PRIMERO (debe estar antes de otros middlewares que usen session)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site=settings.session_cookie_samesite,
    https_only=settings.session_cookie_secure
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

@app.middleware("http")
async def autenticar_sesion(request: Request, call_next):
    """Verificar autenticación - excluir rutas públicas"""
    rutas_publicas_exactas = {"/", "/login", "/health", "/dashboard", "/logout"}
    rutas_publicas_prefijo = (
        "/static", "/docs", "/openapi.json",
        "/api/v1/ventas/catalogo",
        "/api/v1/mesas/catalogo",
        "/api/v1/productos/catalogo",
        "/api/v1/comanda/catalogo",
        "/api/v1/nomina/catalogo",
        "/api/v1/mobile/auth/",  # Mobile authentication endpoints (login, logout, refresh)
        "/api/v1/mobile/",  # All mobile API endpoints use JWT Bearer token auth (not session)
        "/api/v1/kds/auth/",  # KDS authentication endpoints (login, logout)
        "/api/v1/kds/",  # All KDS API endpoints use JWT Bearer token auth (not session)
        # Rutas del frontend que requieren autenticación interna
        "/mobile",
        "/mesas", "/caja", "/domicilios", "/cocina",
        "/productos", "/inventario", "/produccion",
        "/compras", "/gastos", "/clientes", "/empleados",
        "/nomina", "/informes", "/usuarios", "/configuracion",
        "/comanda", "/pedido", "/factura", "/api/comanda"
    )
    
    # Verificar ruta exacta o prefijo
    es_publica = (request.url.path in rutas_publicas_exactas or 
                  any(request.url.path.startswith(p) for p in rutas_publicas_prefijo))
    
    # Si es pública, pasar directo
    if es_publica:
        if request.url.path == "/login":
            logger.info(f"[MIDDLEWARE] GET /login - es pública, pasando directo")
        return await call_next(request)
    
    # Si no es pública, verificar autenticación
    # Verificar que session exists antes de acceder
    if "session" not in request.scope or not request.session.get("usuario_id"):
        if request.url.path.startswith("/api/"): 
            logger.warning(f"Acceso no autenticado a API: {request.url.path}")
            return JSONResponse({"detail":"No autenticado"}, status_code=401)
        logger.warning(f"Redirigiendo a login desde: {request.url.path}")
        return RedirectResponse("/login", status_code=303)
    
    return await call_next(request)

def context(request, db):
    empresa = db.scalar(select(Empresa).limit(1))
    # Generar CSRF token para formularios
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
    if request.session.get("rol") not in roles: raise HTTPException(403, "No tiene permisos para esta acción")

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
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, usuario: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Ruta de autenticación con logging de auditoría"""
    usuario_limpio = usuario.strip()
    
    # Log del intento de login
    logger.info(f"Intento de login para usuario: {usuario_limpio}")
    
    cuenta = db.scalar(select(Usuario).where((Usuario.usuario == usuario_limpio) & (Usuario.activo == True)))
    
    if not cuenta or not passwords.verify(password, cuenta.password_hash):
        logger.warning(f"Login fallido para usuario: {usuario_limpio} (credenciales inválidas)")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuario o contraseña incorrectos."},
            status_code=401
        )
    
    # Login exitoso
    logger.info(f"Login exitoso para usuario: {usuario_limpio} (ID: {cuenta.id})")
    request.session.update({
        "usuario_id": cuenta.id,
        "usuario_nombre": cuenta.usuario,
        "rol": cuenta.rol,
        "empleado_id": cuenta.empleado_id,
        "empresa_id": cuenta.empresa_id,
        "login_time": datetime.now().isoformat()
    })
    return RedirectResponse("/dashboard", 303)

@app.post("/logout")
def logout(request: Request):
    """Logout con logging de auditoría"""
    usuario = request.session.get("usuario_nombre", "desconocido")
    logger.info(f"Logout para usuario: {usuario}")
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
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "empresa": empresa,
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
    """Consume insumos con merma y devuelve su costo promedio ponderado."""
    requerimientos = []
    for detalle in receta.detalles:
        producto = db.get(Producto, detalle.insumo_id)
        cantidad = detalle.cantidad * unidades * (Decimal("1") + detalle.merma_porcentaje / Decimal("100"))
        if not producto or producto.existencias < cantidad: raise HTTPException(400, f"Inventario insuficiente: insumo #{detalle.insumo_id}")
        requerimientos.append((producto, cantidad))
    costo_total = Decimal("0")
    for producto, cantidad in requerimientos:
        costo_total += cantidad * producto.costo
        producto.existencias -= cantidad
        db.add(MovimientoInventario(producto_id=producto.id, tipo="consumo_receta", cantidad=-cantidad, costo_unitario=producto.costo, referencia=referencia))
    return costo_total

@app.get("/health")
def health(): return {"status":"ok", "service":"cafbardla"}

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    today = func.date(Venta.fecha)
    total = db.scalar(select(func.coalesce(func.sum(Venta.total),0)).where(today == func.current_date(), Venta.estado=="pagada"))
    abiertas = db.scalar(select(func.count(Venta.id)).where(Venta.estado=="abierta"))
    bajos = db.scalars(select(Producto).where(Producto.existencias <= Producto.stock_minimo, Producto.activo==True)).all()
    return templates.TemplateResponse("dashboard.html", context(request,db) | {"total":total,"abiertas":abiertas,"bajos":bajos})

@app.get("/mesas", response_class=HTMLResponse)
def mesas(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("mesas.html", context(request,db) | {"zonas":db.scalars(select(Zona).order_by(Zona.orden)).all()})

@app.post("/zonas")
def crear_zona(nombre: str = Form(...), db: Session = Depends(get_db)):
    db.add(Zona(nombre=nombre, orden=db.scalar(select(func.count(Zona.id)))+1)); db.commit(); return RedirectResponse("/mesas",303)

@app.post("/mesas")
def crear_mesa(zona_id:int=Form(...),nombre:str=Form(...),capacidad:int=Form(4),db:Session=Depends(get_db)):
    db.add(Mesa(zona_id=zona_id,nombre=nombre,capacidad=capacidad)); db.commit(); return RedirectResponse("/mesas",303)

@app.get("/comanda/{mesa_id}", response_class=HTMLResponse)
def comanda(mesa_id:int,request:Request,db:Session=Depends(get_db)):
    mesa=db.get(Mesa,mesa_id)
    if not mesa: raise HTTPException(404)
    venta=db.scalar(select(Venta).where(Venta.mesa_id==mesa_id,Venta.estado=="abierta"))
    return templates.TemplateResponse("comanda.html",context(request,db)|{"mesa":mesa,"venta":venta,"productos":db.scalars(select(Producto).where(Producto.activo==True)).all(),"clientes":db.scalars(select(Cliente).order_by(Cliente.nombre)).all(),"mesas_destino":db.scalars(select(Mesa).where(Mesa.id != mesa_id).order_by(Mesa.nombre)).all()})

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
def anular_venta(venta_id: int, motivo: str = Form(...), db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id)
    if not venta or venta.estado != "abierta" or not motivo.strip(): raise HTTPException(400, "Indique el motivo de anulación")
    venta.estado, venta.motivo_anulacion = "anulada", motivo.strip()
    if venta.mesa_id: db.get(Mesa, venta.mesa_id).estado = "libre"
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
            if p.existencias < d.cantidad: raise HTTPException(400, f"Inventario insuficiente: {p.nombre}")
            p.existencias -= d.cantidad; d.costo_unitario = p.costo
            db.add(MovimientoInventario(producto_id=p.id,tipo="salida_venta",cantidad=-d.cantidad,costo_unitario=p.costo,referencia=f"Venta {venta.id}"))
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
    return templates.TemplateResponse(
        "factura.html",
        context(request, db) | {"venta": venta, "productos": productos, "cliente": cliente, "es_movil": es_movil}
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

    return templates.TemplateResponse(
        "mobile_dashboard.html",
        {
            "request": request,
            "empresa": empresa,
            "usuario": {"nombre": usuario.usuario, "rol": usuario.rol},
            "total_ventas": total_ventas,
            "pendientes_cocina": pendientes_cocina,
            "mesas_ocupadas": mesas_ocupadas,
        },
    )

@app.get("/inventario", response_class=HTMLResponse)
def inventario(request:Request,db:Session=Depends(get_db)):
    return templates.TemplateResponse("inventario.html",context(request,db)|{"productos":db.scalars(select(Producto).order_by(Producto.nombre)).all()})

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
    return templates.TemplateResponse("informes.html", context(request,db) | {"ventas":ventas,"gastos":gastos,"costos_ventas":costos_ventas,"compras_total":compras_total,"produccion_total":produccion_total,"nomina_total":nomina_total,"valor_inventario":valor_inventario,"bajos":bajos,"inventario":inventario,"desde":desde,"hasta":hasta,"medios":medios,"productos_top":productos_top,"cantidad_ventas":len(ventas_rows)})

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
    return templates.TemplateResponse("productos.html", context(request, db) | {"productos": db.scalars(select(Producto).order_by(Producto.nombre)).all(), "categorias": db.scalars(select(Categoria).order_by(Categoria.nombre)).all()})

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
        db.add(MovimientoInventario(producto_id=producto.id, tipo="saldo_inicial", cantidad=existencias, costo_unitario=costo, referencia="Creación de producto"))
    db.commit(); return RedirectResponse("/productos", 303)

@app.post("/productos/{producto_id}/editar")
def editar_producto(producto_id: int, nombre: str = Form(...), precio_venta: Decimal = Form(...), costo: Decimal = Form(...), stock_minimo: Decimal = Form(...), db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if not producto: raise HTTPException(404)
    producto.nombre, producto.precio_venta, producto.costo, producto.stock_minimo = nombre.strip(), precio_venta, costo, stock_minimo
    db.commit(); return RedirectResponse("/productos", 303)

@app.post("/productos/{producto_id}/estado")
def cambiar_estado_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if not producto: raise HTTPException(404)
    producto.activo = not producto.activo; db.commit(); return RedirectResponse("/productos", 303)

@app.post("/inventario/movimiento")
def movimiento_inventario(producto_id: int = Form(...), tipo: str = Form(...), cantidad: Decimal = Form(...), costo_unitario: Decimal = Form(0), referencia: str = Form(""), db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if not producto or cantidad <= 0: raise HTTPException(400, "Movimiento inválido")
    signo = Decimal("1") if tipo in ("entrada", "ajuste_positivo") else Decimal("-1")
    producto.existencias += signo * cantidad
    db.add(MovimientoInventario(producto_id=producto.id, tipo=tipo, cantidad=signo*cantidad, costo_unitario=costo_unitario, referencia=referencia or None))
    db.commit(); return RedirectResponse("/inventario", 303)

@app.get("/gastos", response_class=HTMLResponse)
def gastos(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("gastos.html", context(request, db) | {"gastos": db.scalars(select(Gasto).order_by(Gasto.fecha.desc()).limit(100)).all()})

@app.post("/gastos")
def crear_gasto(fecha: date = Form(...), concepto: str = Form(...), categoria: str = Form(...), valor: Decimal = Form(...), proveedor: str = Form(""), db: Session = Depends(get_db)):
    if valor <= 0: raise HTTPException(400, "El valor debe ser mayor a cero")
    db.add(Gasto(fecha=fecha, concepto=concepto.strip(), categoria=categoria.strip(), valor=valor, proveedor=proveedor.strip() or None)); db.commit()
    return RedirectResponse("/gastos", 303)

@app.get("/clientes", response_class=HTMLResponse)
def clientes(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("clientes.html", context(request, db) | {"clientes": db.scalars(select(Cliente).order_by(Cliente.nombre)).all(), "abonos": db.scalars(select(AbonoCartera).order_by(AbonoCartera.fecha.desc()).limit(20)).all()})

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
    return templates.TemplateResponse("empleados.html", context(request, db) | {"empleados": db.scalars(select(Empleado).order_by(Empleado.nombre)).all(), "turnos": db.scalars(select(Turno).order_by(Turno.entrada.desc()).limit(50)).all()})

@app.post("/empleados")
def crear_empleado(nombre: str = Form(...), documento: str = Form(...), cargo: str = Form(...), salario: Decimal = Form(0), tipo_documento: str = Form("CC"), fecha_ingreso: date | None = Form(None), tipo_contrato: str = Form("indefinido"), eps: str = Form(""), pension: str = Form(""), arl: str = Form(""), db: Session = Depends(get_db)):
    if db.scalar(select(Empleado).where(Empleado.documento == documento.strip())): raise HTTPException(400, "El documento ya existe")
    db.add(Empleado(nombre=nombre.strip(), documento=documento.strip(), cargo=cargo.strip(), salario=salario, tipo_documento=tipo_documento, fecha_ingreso=fecha_ingreso, tipo_contrato=tipo_contrato, eps=eps.strip() or None, pension=pension.strip() or None, arl=arl.strip() or None)); db.commit()
    return RedirectResponse("/empleados", 303)

@app.post("/turnos/entrada")
def entrada_turno(empleado_id: int = Form(...), db: Session = Depends(get_db)):
    if not db.get(Empleado, empleado_id): raise HTTPException(404)
    abierto = db.scalar(select(Turno).where(Turno.empleado_id == empleado_id, Turno.salida == None))
    if not abierto: db.add(Turno(empleado_id=empleado_id)); db.commit()
    return RedirectResponse("/empleados", 303)

@app.post("/turnos/{turno_id}/salida")
def salida_turno(turno_id: int, db: Session = Depends(get_db)):
    turno = db.get(Turno, turno_id)
    if turno and not turno.salida: turno.salida = datetime.utcnow(); db.commit()
    return RedirectResponse("/empleados", 303)

@app.get("/produccion", response_class=HTMLResponse)
def produccion(request: Request, db: Session = Depends(get_db)):
    recetas = db.scalars(select(Receta)).all()
    ordenes = db.scalars(select(OrdenProduccion).order_by(OrdenProduccion.fecha.desc()).limit(30)).all()
    return templates.TemplateResponse("produccion.html", context(request, db) | {"recetas": recetas, "ordenes": ordenes, "productos": db.scalars(select(Producto).order_by(Producto.nombre)).all(), "insumos": db.scalars(select(Producto).where(Producto.tipo.in_(["insumo", "elaborado"])).order_by(Producto.nombre)).all()})

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
def ejecutar_produccion(receta_id: int, lotes: Decimal = Form(...), db: Session = Depends(get_db)):
    receta = db.get(Receta, receta_id)
    if not receta or receta.tipo_receta != "produccion" or lotes <= 0: raise HTTPException(400, "Producción inválida")
    detalles = receta.detalles
    if not detalles: raise HTTPException(400, "La receta no tiene insumos")
    producto = db.get(Producto, receta.producto_id)
    costo_total = consumir_receta(db, receta, lotes, f"Producción receta {receta.id}")
    producido = receta.rendimiento * lotes
    costo_unitario = (costo_total / producido).quantize(Decimal("0.01"))
    valor_existente = producto.existencias * producto.costo
    producto.existencias += producido
    producto.costo = ((valor_existente + costo_total) / producto.existencias).quantize(Decimal("0.01")) if producto.existencias else costo_unitario
    db.add(MovimientoInventario(producto_id=producto.id, tipo="entrada_produccion", cantidad=producido, costo_unitario=costo_unitario, referencia=f"Receta {receta.id}"))
    db.add(OrdenProduccion(receta_id=receta.id, lotes=lotes, unidades_producidas=producido, costo_total=costo_total, costo_unitario=costo_unitario))
    db.commit(); return RedirectResponse("/produccion", 303)

@app.get("/caja", response_class=HTMLResponse)
def caja(request: Request, db: Session = Depends(get_db)):
    sesion = db.scalar(select(SesionCaja).where(SesionCaja.cierre == None).order_by(SesionCaja.apertura.desc()))
    ventas_efectivo = Decimal("0")
    if sesion:
        ventas_efectivo = db.scalar(select(func.coalesce(func.sum(Venta.total),0)).where(Venta.fecha >= sesion.apertura, Venta.estado == "pagada", Venta.medio_pago == "efectivo"))
    return templates.TemplateResponse("caja.html", context(request, db) | {"sesion": sesion, "efectivo_esperado": (sesion.base_inicial + ventas_efectivo) if sesion else 0, "ventas_efectivo": ventas_efectivo})

@app.get("/domicilios", response_class=HTMLResponse)
def domicilios(request: Request, db: Session = Depends(get_db)):
    filas = db.execute(select(Domicilio, Venta, Cliente.nombre.label("cliente"), Empleado.nombre.label("repartidor")).join(Venta, Venta.id == Domicilio.venta_id).outerjoin(Cliente, Cliente.id == Venta.cliente_id).outerjoin(Empleado, Empleado.id == Domicilio.repartidor_id).order_by(Venta.fecha.desc()).limit(100)).all()
    return templates.TemplateResponse("domicilios.html", context(request, db) | {"filas": filas, "clientes": db.scalars(select(Cliente).order_by(Cliente.nombre)).all(), "repartidores": db.scalars(select(Empleado).where(Empleado.activo == True).order_by(Empleado.nombre)).all()})

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
    return templates.TemplateResponse("pedido.html", context(request, db) | {"venta": venta, "domicilio": domicilio, "productos": db.scalars(select(Producto).where(Producto.activo == True)).all()})

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
    sesion.cierre, sesion.efectivo_declarado, sesion.observacion_cierre = datetime.utcnow(), efectivo_declarado, observacion_cierre or None
    db.commit(); return RedirectResponse("/caja", 303)

@app.get("/configuracion", response_class=HTMLResponse)
def configuracion(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    return templates.TemplateResponse("configuracion.html", context(request, db))

@app.get("/nomina", response_class=HTMLResponse)
def nomina(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    periodos = db.scalars(select(PeriodoNomina).order_by(PeriodoNomina.fecha_fin.desc()).limit(30)).all()
    liquidaciones = db.execute(select(LiquidacionNomina, Empleado.nombre, PeriodoNomina.fecha_inicio, PeriodoNomina.fecha_fin).join(Empleado, Empleado.id == LiquidacionNomina.empleado_id).join(PeriodoNomina, PeriodoNomina.id == LiquidacionNomina.periodo_id).order_by(LiquidacionNomina.id.desc()).limit(100)).all()
    return templates.TemplateResponse("nomina.html", context(request, db) | {"parametros": db.scalar(select(ParametrosNomina).order_by(ParametrosNomina.vigencia_desde.desc())), "periodos": periodos, "liquidaciones": liquidaciones, "empleados": db.scalars(select(Empleado).where(Empleado.activo == True).order_by(Empleado.nombre)).all()})

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
    exigir_rol(request, "administrador")
    periodo = db.get(PeriodoNomina, periodo_id); parametros = db.scalar(select(ParametrosNomina).order_by(ParametrosNomina.vigencia_desde.desc()))
    if not periodo or periodo.estado != "borrador" or not parametros: raise HTTPException(400, "Configure los parámetros y use un período en borrador")
    dias = Decimal(str((periodo.fecha_fin - periodo.fecha_inicio).days + 1))
    for empleado in db.scalars(select(Empleado).where(Empleado.activo == True)).all():
        if db.scalar(select(LiquidacionNomina).where(LiquidacionNomina.periodo_id == periodo.id, LiquidacionNomina.empleado_id == empleado.id)): continue
        salario_base = (empleado.salario * dias / Decimal("30")).quantize(Decimal("0.01"))
        auxilio = (parametros.auxilio_transporte * dias / Decimal("30")) if parametros.tope_auxilio_transporte and empleado.salario <= parametros.tope_auxilio_transporte else Decimal("0")
        devengados = salario_base + auxilio
        deducciones = (salario_base * (parametros.salud_empleado_pct + parametros.pension_empleado_pct) / Decimal("100")).quantize(Decimal("0.01"))
        db.add(LiquidacionNomina(periodo_id=periodo.id, empleado_id=empleado.id, dias_liquidados=dias, salario_base=salario_base, devengados=devengados, deducciones=deducciones, neto=devengados-deducciones))
    periodo.estado = "liquidado"; db.commit(); return RedirectResponse("/nomina", 303)

@app.get("/compras", response_class=HTMLResponse)
def compras(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "caja")
    filas = db.execute(select(Compra, Proveedor.nombre, Proveedor.obligado_facturar).join(Proveedor, Proveedor.id == Compra.proveedor_id).order_by(Compra.fecha.desc()).limit(100)).all()
    return templates.TemplateResponse("compras.html", context(request, db) | {"proveedores": db.scalars(select(Proveedor).order_by(Proveedor.nombre)).all(), "productos": db.scalars(select(Producto).where(Producto.activo == True).order_by(Producto.nombre)).all(), "filas": filas})

@app.post("/proveedores")
def crear_proveedor(request: Request, nombre: str = Form(...), tipo_documento: str = Form("NIT"), documento: str = Form(...), telefono: str = Form(""), email: str = Form(""), obligado_facturar: bool = Form(False), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "caja")
    db.add(Proveedor(nombre=nombre.strip(), tipo_documento=tipo_documento, documento=documento.strip(), telefono=telefono.strip() or None, email=email.strip() or None, obligado_facturar=obligado_facturar)); db.commit(); return RedirectResponse("/compras", 303)

@app.post("/compras")
def registrar_compra(request: Request, proveedor_id: int = Form(...), fecha: date = Form(...), concepto: str = Form(...), valor: Decimal = Form(...), numero_documento: str = Form(""), producto_id: int | None = Form(None), cantidad: Decimal | None = Form(None), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "caja")
    proveedor = db.get(Proveedor, proveedor_id); empresa = db.scalar(select(Empresa).limit(1))
    if not proveedor or valor <= 0: raise HTTPException(400, "Compra inválida")
    soporte = not proveedor.obligado_facturar
    estado = "pendiente_proveedor" if soporte and empresa.facturador_electronico and empresa.proveedor_tecnologico else ("pendiente_configuracion" if soporte else "factura_proveedor_registrada")
    producto = db.get(Producto, producto_id) if producto_id else None
    costo_unitario = None
    if producto:
        if not cantidad or cantidad <= 0: raise HTTPException(400, "Indique una cantidad para la entrada de inventario")
        costo_unitario = (valor / cantidad).quantize(Decimal("0.01"))
        valor_existente = producto.existencias * producto.costo
        producto.existencias += cantidad
        producto.costo = ((valor_existente + valor) / producto.existencias).quantize(Decimal("0.01"))
        db.add(MovimientoInventario(producto_id=producto.id, tipo="compra", cantidad=cantidad, costo_unitario=costo_unitario, referencia=numero_documento.strip() or f"Compra {fecha}"))
    db.add(Compra(proveedor_id=proveedor.id, fecha=fecha, concepto=concepto.strip(), valor=valor, numero_documento=numero_documento.strip() or None, es_documento_soporte=soporte, estado_electronico=estado, producto_id=producto.id if producto else None, cantidad=cantidad if producto else None, costo_unitario=costo_unitario)); db.commit(); return RedirectResponse("/compras", 303)

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

@app.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request, db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    return templates.TemplateResponse("usuarios.html", context(request, db) | {"usuarios": db.scalars(select(Usuario).order_by(Usuario.usuario)).all(), "empleados": db.scalars(select(Empleado).where(Empleado.activo == True).order_by(Empleado.nombre)).all()})

@app.post("/usuarios")
def crear_usuario(request: Request, usuario: str = Form(...), password: str = Form(...), rol: str = Form(...), empleado_id: int | None = Form(None), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador")
    if rol not in ("administrador", "caja", "mesero", "cocina") or len(password) < 8: raise HTTPException(400, "Rol o contraseña inválidos")
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
    return templates.TemplateResponse("cocina.html", context(request, db) | {"filas": filas})

@app.post("/cocina/{detalle_id}/estado")
def estado_cocina(detalle_id: int, request: Request, estado: str = Form(...), db: Session = Depends(get_db)):
    exigir_rol(request, "administrador", "cocina")
    detalle = db.get(DetalleVenta, detalle_id)
    if not detalle or estado not in ("pendiente", "preparando", "listo", "entregado"): raise HTTPException(400, "Estado inválido")
    detalle.estado_cocina = estado; db.commit(); return RedirectResponse("/cocina", 303)

@app.get("/api/tema")
def tema(db:Session=Depends(get_db)):
    e=db.scalar(select(Empresa).limit(1)); return {"nombre":e.nombre,"primario":e.color_primario,"secundario":e.color_secundario,"logo":e.logo_url}
