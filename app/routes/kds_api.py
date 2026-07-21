"""
KDS (Kitchen Display System) API Routes - FASE 8
Endpoints REST optimizados para pantallas de cocina

Endpoints:
- GET    /api/v1/kds/auth/login         - Autenticación KDS (chef/cocinero)
- POST   /api/v1/kds/auth/logout        - Cerrar sesión
- GET    /api/v1/kds/pedidos            - Órdenes pendientes por preparar
- PUT    /api/v1/kds/pedidos/{id}/estado - Actualizar estado de comanda
- GET    /api/v1/kds/estado             - Estado general cocina
- GET    /api/v1/kds/estadisticas       - Estadísticas de operación
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.database import get_db
from sqlalchemy.orm import Session
from app.models import Usuario, Venta, DetalleVenta, Empresa, Producto, Empleado, Mesa
from app.services.jwt_service import JWTService, TokenBlacklist
from app.websocket_manager import connection_manager, event_broadcaster
from sqlalchemy import and_

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/kds",
    tags=["KDS API - FASE 8"]
)


# ============================================================================
# Modelos Pydantic
# ============================================================================

class KDSLoginRequest(BaseModel):
    """Request para login KDS"""
    usuario: str = Field(..., description="Usuario chef/cocinero")
    password: str = Field(..., description="Contraseña")
    device_id: Optional[str] = Field(None, description="ID único del dispositivo")


class KDSLoginResponse(BaseModel):
    """Response después de login exitoso"""
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    usuario_nombre: str
    rol: str
    dispositivo: str


class PedidoItemResponse(BaseModel):
    """Detalle de producto en pedido"""
    producto_id: int
    codigo: str
    nombre: str
    cantidad: int
    estado: str  # pendiente, preparando, lista, entregada
    tiempo_preparacion: Optional[int] = None  # minutos estimados
    notas: Optional[str]
    mesa_numero: str


class PedidoKDSResponse(BaseModel):
    """Información de pedido para cocina"""
    venta_id: int
    mesa_id: int
    mesa_numero: str
    estado: str  # abierta, en_preparacion, lista, pagada
    prioridad: str  # normal, urgente, vip
    items: List[PedidoItemResponse]
    tiempo_llegada: str  # ISO timestamp
    notas_especiales: Optional[str]
    cocinero_asignado: Optional[str]


class ActualizarEstadoRequest(BaseModel):
    """Request para actualizar estado de comanda"""
    estado: str = Field(..., description="Estado: preparando, lista")
    tiempo_estimado: Optional[int] = Field(None, description="Tiempo en minutos")
    notas: Optional[str] = Field(None, description="Notas del cocinero")


class EstadoCocinaResponse(BaseModel):
    """Estado general de la cocina"""
    total_pendientes: int
    total_preparando: int
    total_listas: int
    promedio_tiempo: Optional[float]
    pedidos_urgentes: int
    capacidad_actual: float  # % de ocupación


# ============================================================================
# Autenticación KDS
# ============================================================================

async def get_kds_user(request: Request, db: Session = Depends(get_db)):
    """
    Extrae y valida usuario desde JWT token en header Authorization
    Valida que sea chef o cocinero
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
    dispositivo = payload.get("dispositivo", "")
    
    # Obtener usuario de BD
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Validar que sea KDS
    if dispositivo != "kds":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This token is not valid for KDS access"
        )
    
    # Validar rol: solo chef, cocinero
    if usuario.rol not in ["chef", "cocinero"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must have chef or cocinero role"
        )
    
    return usuario, payload


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/auth/login", response_model=KDSLoginResponse)
async def kds_login(
    request: KDSLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login KDS - retorna JWT token para dispositivo de cocina
    """
    usuario = db.query(Usuario).filter(
        Usuario.usuario == request.usuario
    ).first()
    
    if not usuario or not usuario.verificar_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    # Validar rol
    if usuario.rol not in ["chef", "cocinero"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must have chef or cocinero role for KDS access"
        )
    
    # Crear token JWT para KDS
    device_id = request.device_id or "kds-default"
    token = JWTService.create_token(
        usuario_id=usuario.id,
        sucursal_id=usuario.empresa_id,
        dispositivo="kds",
        device_id=device_id
    )
    
    # Obtener nombre del empleado
    empleado_nombre = "Chef"
    if usuario.empleado_id:
        empleado = db.query(Empleado).filter(
            Empleado.id == usuario.empleado_id
        ).first()
        if empleado:
            empleado_nombre = empleado.nombre
    
    logger.info(f"✅ KDS Login: usuario={usuario.usuario}, rol={usuario.rol}")
    
    return KDSLoginResponse(
        access_token=token,
        token_type="bearer",
        usuario_id=usuario.id,
        usuario_nombre=empleado_nombre,
        rol=usuario.rol,
        dispositivo="kds"
    )


@router.post("/auth/logout")
async def kds_logout(
    current_user: tuple = Depends(get_kds_user),
    db: Session = Depends(get_db)
):
    """Logout KDS - revoca token"""
    usuario, payload = current_user
    token = payload.get("token")
    if token:
        TokenBlacklist.add_to_blacklist(token)
    
    logger.info(f"✅ KDS Logout: usuario={usuario.usuario}")
    return {"status": "logged out"}


@router.get("/pedidos", response_model=List[PedidoKDSResponse])
async def obtener_pedidos(
    current_user: tuple = Depends(get_kds_user),
    db: Session = Depends(get_db),
    estado_filtro: Optional[str] = None
):
    """
    Obtiene órdenes pendientes para cocina
    Filtra por: pendiente, preparando, lista
    """
    usuario, payload = current_user
    
    # Query base: órdenes abiertas o en preparación
    query = db.query(Venta).filter(
        and_(
            Venta.empresa_id == usuario.empresa_id,
            Venta.estado.in_(["abierta", "en_preparacion"])
        )
    )
    
    # Aplicar filtro de estado si existe
    if estado_filtro:
        query = query.filter(Venta.estado == estado_filtro)
    
    ventas = query.all()
    
    resultado = []
    for venta in ventas:
        if not venta.mesa_id:
            continue
            
        mesa = db.query(Mesa).filter(Mesa.id == venta.mesa_id).first()
        
        # Construir items
        items = []
        detalles = db.query(DetalleVenta).filter(
            DetalleVenta.venta_id == venta.id
        ).all()
        
        for detalle in detalles:
            producto = db.query(Producto).filter(
                Producto.id == detalle.producto_id
            ).first()
            
            if producto:
                items.append(PedidoItemResponse(
                    producto_id=producto.id,
                    codigo=producto.codigo,
                    nombre=producto.nombre,
                    cantidad=int(detalle.cantidad),
                    estado=detalle.estado_cocina or "pendiente",
                    tiempo_preparacion=None,
                    notas=detalle.nota,
                    mesa_numero=mesa.nombre if mesa else "?"
                ))
        
        # Construir pedido KDS
        if items:
            resultado.append(PedidoKDSResponse(
                venta_id=venta.id,
                mesa_id=venta.mesa_id,
                mesa_numero=mesa.nombre if mesa else "?",
                estado=venta.estado,
                prioridad="urgente" if venta.estado == "en_preparacion" else "normal",
                items=items,
                tiempo_llegada=venta.fecha.isoformat() if venta.fecha else "",
                notas_especiales=venta.observacion,
                cocinero_asignado=None
            ))
    
    logger.info(f"📋 KDS: {len(resultado)} pedidos obtenidos")
    return resultado


@router.put("/pedidos/{venta_id}/estado")
async def actualizar_estado_pedido(
    venta_id: int,
    request: ActualizarEstadoRequest,
    current_user: tuple = Depends(get_kds_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza estado de preparación de comanda
    Estados permitidos: preparando, lista
    """
    usuario, payload = current_user
    
    # Obtener venta
    venta = db.query(Venta).filter(
        and_(
            Venta.id == venta_id,
            Venta.empresa_id == usuario.empresa_id
        )
    ).first()
    
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {venta_id} not found"
        )
    
    # Validar estado
    if request.estado not in ["preparando", "lista"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'preparando' or 'lista'"
        )
    
    # Actualizar todos los detalles
    detalles = db.query(DetalleVenta).filter(
        DetalleVenta.venta_id == venta_id
    ).all()
    
    for detalle in detalles:
        detalle.estado_cocina = request.estado
    
    # Actualizar estado venta
    if request.estado == "lista":
        venta.estado = "lista_para_servir"
    elif request.estado == "preparando":
        venta.estado = "en_preparacion"
    
    db.commit()
    
    logger.info(f"✅ KDS: Venta {venta_id} → estado={request.estado}")
    
    # Emitir evento WebSocket
    mesa = db.query(Mesa).filter(Mesa.id == venta.mesa_id).first()
    await event_broadcaster.broadcast_evento(
        sucursal_id=usuario.empresa_id,
        evento="pedido.actualizado",
        datos={
            "venta_id": venta_id,
            "estado": request.estado,
            "mesa_id": venta.mesa_id,
            "mesa_numero": mesa.nombre if mesa else "?"
        },
        dispositivos_destino=["app_mesero", "kds"]
    )
    
    return {
        "status": "updated",
        "venta_id": venta_id,
        "estado": request.estado
    }


@router.get("/estado", response_model=EstadoCocinaResponse)
async def obtener_estado_cocina(
    current_user: tuple = Depends(get_kds_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene estado general de la cocina
    Cuenta órdenes por estado
    """
    usuario, payload = current_user
    
    # Contar por estado
    pendientes = db.query(Venta).filter(
        and_(
            Venta.empresa_id == usuario.empresa_id,
            Venta.estado == "abierta"
        )
    ).count()
    
    preparando = db.query(Venta).filter(
        and_(
            Venta.empresa_id == usuario.empresa_id,
            Venta.estado == "en_preparacion"
        )
    ).count()
    
    listas = db.query(Venta).filter(
        and_(
            Venta.empresa_id == usuario.empresa_id,
            Venta.estado == "lista_para_servir"
        )
    ).count()
    
    urgentes = preparando  # TODO: Implementar concepto de urgencia
    
    total = pendientes + preparando + listas
    capacidad = (preparando / max(10, total)) * 100 if total > 0 else 0
    
    return EstadoCocinaResponse(
        total_pendientes=pendientes,
        total_preparando=preparando,
        total_listas=listas,
        promedio_tiempo=None,  # TODO: Calcular de detalles históricos
        pedidos_urgentes=urgentes,
        capacidad_actual=capacidad
    )


@router.get("/estadisticas")
async def obtener_estadisticas(
    current_user: tuple = Depends(get_kds_user),
    db: Session = Depends(get_db)
):
    """
    Estadísticas operacionales de cocina
    """
    usuario, payload = current_user
    
    # TODO: Implementar estadísticas
    return {
        "estadistica": "En desarrollo",
        "mensaje": "FASE 8 en progreso"
    }
