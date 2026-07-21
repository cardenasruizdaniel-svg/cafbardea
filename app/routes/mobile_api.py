"""
Mobile API Routes - FASE 7
Endpoints REST optimizados para aplicaciones móviles (app_mesero, etc.)

Endpoints:
- POST   /api/v1/mobile/auth/login        - Autenticación JWT
- POST   /api/v1/mobile/auth/logout       - Revoke token
- GET    /api/v1/mobile/mesas             - Listar mesas del piso
- POST   /api/v1/mobile/comandas          - Crear nueva comanda
- GET    /api/v1/mobile/comandas/{id}     - Detalles comanda
- POST   /api/v1/mobile/comandas/{id}/agregar-producto
- POST   /api/v1/mobile/comandas/{id}/pagar
- GET    /api/v1/mobile/productos         - Catálogo completo
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import uuid

from app.database import get_db
from sqlalchemy.orm import Session
from app.models import Usuario, Mesa, Venta, DetalleVenta, Empresa, Producto
from app.services.jwt_service import JWTService, TokenBlacklist
from app.websocket_manager import connection_manager, event_broadcaster
from sqlalchemy import and_

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/mobile",
    tags=["Mobile API - FASE 7"]
)


# ============================================================================
# Modelos Pydantic
# ============================================================================

class LoginRequest(BaseModel):
    """Request para login móvil"""
    usuario: str = Field(..., description="Usuario o email")
    password: str = Field(..., description="Contraseña")
    device_id: Optional[str] = Field(None, description="ID único del dispositivo")
    device_type: Optional[str] = Field("app_mesero", description="Tipo de dispositivo")


class LoginResponse(BaseModel):
    """Response después de login exitoso"""
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    usuario_nombre: str
    sucursal_id: int
    empresa_id: int
    rol: str
    dispositivo: str


class MesaResponse(BaseModel):
    """Información de mesa para mobile"""
    id: int
    numero: str
    estado: str  # libre, ocupada, reservada, mantenimiento
    capacidad: int
    venta_id: Optional[int] = None


class ProductoResponse(BaseModel):
    """Información de producto para mobile"""
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str]
    precio: float
    categoria: Optional[str]
    disponible: bool
    existencias: Optional[int]


class ComandaProductoRequest(BaseModel):
    """Item para agregar a comanda"""
    producto_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0, le=100)
    notas: Optional[str] = Field(None, max_length=500)


class CrearComandaRequest(BaseModel):
    """Request para crear nueva comanda"""
    mesa_id: int
    productos: List[ComandaProductoRequest]


class ComandaProductoResponse(BaseModel):
    """Producto en comanda"""
    producto_id: int
    nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    notas: Optional[str]
    estado: str  # pendiente, preparando, lista, entregada


class ComandaResponse(BaseModel):
    """Información de comanda para mobile"""
    venta_id: int
    mesa_id: int
    mesa_numero: str
    estado: str  # abierta, pagada, anulada
    productos: List[ComandaProductoResponse]
    subtotal: float
    impuesto: float
    total: float
    fecha_creacion: str
    ultima_actualizacion: str


class AgregarProductoRequest(BaseModel):
    """Request para agregar producto a comanda existente"""
    producto_id: int
    cantidad: int = 1
    notas: Optional[str] = None


class PagarComandaRequest(BaseModel):
    """Request para pagar comanda"""
    medio_pago: str = Field(..., description="efectivo, tarjeta, transferencia")
    cliente_id: Optional[int] = None
    monto_recibido: Optional[float] = None


class PagoResponse(BaseModel):
    """Response después de pago"""
    venta_id: int
    factura_id: str
    estado: str
    total: float
    monto_pagado: float
    cambio: Optional[float]
    medio_pago: str
    timestamp: str


# ============================================================================
# Dependency: Extrae usuario desde Bearer Token
# ============================================================================

async def get_mobile_user(request: Request, db: Session = Depends(get_db)):
    """
    Extrae y valida usuario desde JWT token en header Authorization
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization token"
        )
    
    token = auth_header.replace("Bearer ", "").strip()
    
    # Verificar si está en blacklist
    if TokenBlacklist.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    # Verificar token
    payload = JWTService.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    usuario_id = payload.get("usuario_id")
    
    # Obtener usuario de BD
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return usuario, payload


# ============================================================================
# Endpoints de Autenticación
# ============================================================================

@router.post("/auth/login", response_model=LoginResponse)
async def mobile_login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login para dispositivos móviles
    Retorna JWT token para usar en requests posteriores
    
    **Parámetros:**
    - usuario: nombre de usuario o email
    - password: contraseña
    - device_id: ID único del dispositivo (UUID recomendado)
    
    **Respuesta:** Token JWT + info del usuario
    """
    logger.info(f"📱 Login attempt: usuario={request.usuario}")
    
    # Buscar usuario
    usuario = db.query(Usuario).filter(
        Usuario.usuario == request.usuario
    ).first()
    
    if not usuario:
        logger.warning(f"❌ Usuario no encontrado: {request.usuario}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verificar password
    if not usuario.verificar_password(request.password):
        logger.warning(f"❌ Contraseña incorrecta para: {request.usuario}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verificar si usuario está activo
    if not usuario.activo:
        logger.warning(f"❌ Usuario inactivo: {usuario.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generar device_id si no se proporciona
    device_id = request.device_id or str(uuid.uuid4())
    
    # Crear JWT token
    token = JWTService.create_token(
        usuario_id=usuario.id,
        sucursal_id=usuario.empresa_id,
        dispositivo=request.device_type,
        device_id=device_id
    )
    
    # Obtener rol del usuario
    rol = "usuario"  # Default
    if usuario.rol:
        rol = usuario.rol
    
    # Obtener empresa
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    
    logger.info(f"✅ Login exitoso: usuario={usuario.id}, dispositivo={device_id}")
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        usuario_id=usuario.id,
        usuario_nombre=usuario.usuario,
        sucursal_id=usuario.empresa_id,
        empresa_id=usuario.empresa_id,
        rol=rol,
        dispositivo=request.device_type
    )


@router.post("/auth/logout")
async def mobile_logout(
    request: Request,
    current_user: tuple = Depends(get_mobile_user)
):
    """
    Logout - Revoca JWT token
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    
    TokenBlacklist.add(token)
    
    logger.info(f"👋 Logout: usuario={current_user[0].id}")
    
    return {"status": "logged_out"}


@router.post("/auth/refresh")
async def refresh_token(
    current_user: tuple = Depends(get_mobile_user),
    request: Request = None
):
    """
    Refresca JWT token para extender sesión
    """
    auth_header = request.headers.get("Authorization", "")
    old_token = auth_header.replace("Bearer ", "").strip()
    
    # Obtener device_id del token anterior
    payload = JWTService.verify_token(old_token)
    device_id = payload.get("device_id") if payload else None
    
    # Crear nuevo token
    new_token = JWTService.create_token(
        usuario_id=current_user[0].id,
        sucursal_id=current_user[0].empresa_id,
        dispositivo="app_mesero",
        device_id=device_id
    )
    
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }


# ============================================================================
# Endpoints de Datos (Mesas, Productos, Comandas)
# ============================================================================

@router.get("/mesas", response_model=List[MesaResponse])
async def get_mesas(
    current_user: tuple = Depends(get_mobile_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las mesas de la sucursal del usuario
    Incluye estado actual y venta_id si está ocupada
    """
    usuario, payload = current_user
    
    mesas = db.query(Mesa).filter(
        Mesa.empresa_id == usuario.empresa_id
    ).all()
    
    resultado = []
    for mesa in mesas:
        # Obtener venta activa si existe
        venta_activa = db.query(Venta).filter(
            and_(Venta.mesa_id == mesa.id, Venta.estado == "abierta")
        ).first()
        
        resultado.append(MesaResponse(
            id=mesa.id,
            numero=mesa.nombre,
            estado=mesa.estado,
            capacidad=mesa.capacidad,
            venta_id=venta_activa.id if venta_activa else None
        ))
    
    logger.info(f"📋 {len(resultado)} mesas obtenidas para usuario {usuario.id}")
    return resultado


@router.get("/productos", response_model=List[ProductoResponse])
async def get_productos(
    current_user: tuple = Depends(get_mobile_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene catálogo de productos disponibles
    """
    usuario, payload = current_user
    
    productos = db.query(Producto).filter(
        and_(
            Producto.empresa_id == usuario.empresa_id,
            Producto.activo == True
        )
    ).all()
    
    resultado = [
        ProductoResponse(
            id=p.id,
            codigo=p.codigo,
            nombre=p.nombre,
            descripcion=None,  # Producto model doesn't have descripcion field
            precio=float(p.precio_venta),
            categoria=None,  # Would need separate query
            disponible=p.existencias > 0,
            existencias=int(p.existencias)
        )
        for p in productos
    ]
    
    logger.info(f"🛒 {len(resultado)} productos obtenidos")
    return resultado


@router.get("/comandas/{venta_id}", response_model=ComandaResponse)
async def get_comanda(
    venta_id: int,
    current_user: tuple = Depends(get_mobile_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene detalles de una comanda específica
    """
    usuario, payload = current_user
    
    venta = db.query(Venta).filter(
        and_(
            Venta.id == venta_id,
            Venta.empresa_id == usuario.empresa_id
        )
    ).first()
    
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    mesa = db.query(Mesa).filter(Mesa.id == venta.mesa_id).first()
    detalles = db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta_id).all()
    
    productos = []
    for detalle in detalles:
        producto = db.query(Producto).filter(Producto.id == detalle.producto_id).first()
        productos.append(ComandaProductoResponse(
            producto_id=producto.id,
            nombre=producto.nombre,
            cantidad=detalle.cantidad,
            precio_unitario=float(detalle.precio),
            subtotal=float(detalle.cantidad * detalle.precio),
            notas=detalle.nota,
            estado="entregada"  # TODO: Obtener estado real desde comanda
        ))
    
    return ComandaResponse(
        venta_id=venta.id,
        mesa_id=venta.mesa_id,
        mesa_numero=mesa.nombre if mesa else "N/A",
        estado=venta.estado,
        productos=productos,
        subtotal=float(venta.subtotal),
        impuesto=float(venta.impuesto),
        total=float(venta.total),
        fecha_creacion=venta.fecha.isoformat() if venta.fecha else "",
        ultima_actualizacion=venta.fecha.isoformat() if venta.fecha else ""
    )


# ============================================================================
# Endpoints de Operaciones (Crear, Agregar, Pagar)
# ============================================================================

@router.post("/comandas", response_model=ComandaResponse)
async def crear_comanda(
    request: CrearComandaRequest,
    current_user: tuple = Depends(get_mobile_user),
    db: Session = Depends(get_db)
):
    """
    Crea nueva comanda para una mesa
    """
    usuario, payload = current_user
    
    # Obtener mesa
    mesa = db.query(Mesa).filter(
        and_(
            Mesa.id == request.mesa_id,
            Mesa.empresa_id == usuario.empresa_id
        )
    ).first()
    
    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Crear venta
    venta = Venta(
        mesa_id=mesa.id,
        empresa_id=usuario.empresa_id,
        estado="abierta",
        usuario_id=usuario.id,
        subtotal=0,
        impuesto=0,
        total=0
    )
    
    # Agregar detalles
    total = 0
    for item in request.productos:
        producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {item.producto_id} not found"
            )
        
        detalle = DetalleVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            cantidad=item.cantidad,
            precio=float(producto.precio_venta),
            nota=item.notas
        )
        venta.detalles.append(detalle)
        total += float(producto.precio_venta) * item.cantidad
    
    venta.subtotal = total
    venta.impuesto = total * 0.08  # 8% impuesto
    venta.total = venta.subtotal + venta.impuesto
    
    db.add(venta)
    db.commit()
    db.refresh(venta)
    
    # Actualizar estado mesa
    mesa.estado = "ocupada"
    db.commit()
    
    logger.info(f"✅ Comanda creada: venta_id={venta.id}, mesa_id={mesa.id}")
    
    # Emitir evento WebSocket
    await event_broadcaster.broadcast_evento(
        sucursal_id=usuario.empresa_id,
        evento="comanda.creada",
        datos={
            "venta_id": venta.id,
            "mesa_id": mesa.id,
            "mesa_numero": mesa.nombre,
            "usuario_id": usuario.id
        },
        dispositivos_destino=["app_mesero", "kds"]
    )
    
    # Retornar comanda creada
    return await get_comanda(venta.id, current_user, db)


@router.post("/comandas/{venta_id}/agregar-producto")
async def agregar_producto(
    venta_id: int,
    request: AgregarProductoRequest,
    current_user: tuple = Depends(get_mobile_user),
    db: Session = Depends(get_db)
):
    """
    Agrega producto a comanda existente
    """
    usuario, payload = current_user
    
    venta = db.query(Venta).filter(
        and_(
            Venta.id == venta_id,
            Venta.empresa_id == usuario.empresa_id
        )
    ).first()
    
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if venta.estado != "abierta":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not open"
        )
    
    producto = db.query(Producto).filter(Producto.id == request.producto_id).first()
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Crear detalle
    detalle = DetalleVenta(
        venta_id=venta_id,
        producto_id=producto.id,
        cantidad=request.cantidad,
        precio=float(producto.precio_venta),
        nota=request.notas
    )
    
    db.add(detalle)
    
    # Recalcular totales
    venta.subtotal += float(producto.precio) * request.cantidad
    venta.impuesto = venta.subtotal * 0.08
    venta.total = venta.subtotal + venta.impuesto
    
    db.commit()
    
    logger.info(f"✅ Producto agregado: venta_id={venta_id}, producto_id={producto.id}")
    
    # Emitir evento
    await event_broadcaster.broadcast_evento({
        "tipo": "evento",
        "evento": "comanda.producto_agregado",
        "datos": {
            "venta_id": venta_id,
            "producto_id": producto.id,
            "cantidad": request.cantidad
        }
    })
    
    return {
        "venta_id": venta_id,
        "estado": "producto_agregado",
        "nuevo_total": float(venta.total)
    }


@router.post("/comandas/{venta_id}/pagar", response_model=PagoResponse)
async def pagar_comanda(
    venta_id: int,
    request: PagarComandaRequest,
    current_user: tuple = Depends(get_mobile_user),
    db: Session = Depends(get_db)
):
    """
    Procesa pago de comanda y cierra orden
    """
    usuario, payload = current_user
    
    venta = db.query(Venta).filter(
        and_(
            Venta.id == venta_id,
            Venta.empresa_id == usuario.empresa_id
        )
    ).first()
    
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if venta.estado != "abierta":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already closed"
        )
    
    # Marcar como pagada
    venta.estado = "pagada"
    venta.medio_pago = request.medio_pago
    venta.fecha_pago = datetime.utcnow()
    
    # Generar factura ID
    factura_id = f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{venta_id}"
    
    # Actualizar mesa
    mesa = db.query(Mesa).filter(Mesa.id == venta.mesa_id).first()
    if mesa:
        mesa.estado = "libre"
    
    db.commit()
    
    logger.info(f"✅ Comanda pagada: venta_id={venta_id}, medio={request.medio_pago}")
    
    # Emitir evento
    await event_broadcaster.broadcast_evento({
        "tipo": "evento",
        "evento": "comanda.pagada",
        "datos": {
            "venta_id": venta_id,
            "total": float(venta.total),
            "medio_pago": request.medio_pago
        }
    })
    
    return PagoResponse(
        venta_id=venta.id,
        factura_id=factura_id,
        estado="pagada",
        total=float(venta.total),
        monto_pagado=float(venta.total),
        cambio=request.monto_recibido - venta.total if request.monto_recibido else None,
        medio_pago=request.medio_pago,
        timestamp=datetime.utcnow().isoformat()
    )


logger.info("🚀 Mobile API routes (FASE 7) cargadas")
