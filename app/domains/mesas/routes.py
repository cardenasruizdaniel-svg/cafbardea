"""
Rutas (Endpoints) para módulo Mesas - FASE 2
Gestión de floor plan, estados y ocupación
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from .schemas import (
    MesaCreate, MesaResponse, MesaUpdate, CambiarEstadoMesa,
    FloorPlanResponse, EstadisticasMesa, ReporteMesaResponse, 
    ZonaResponse, EstadoMesa, FormaMesa
)
from .services import MesaService
from app.config import logger

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

router = APIRouter(
    prefix="/mesas",
    tags=["mesas"],
    responses={
        401: {"description": "No autenticado"},
        404: {"description": "No encontrado"},
        422: {"description": "Validación fallida"}
    }
)

# ============================================================================
# CREAR MESA
# ============================================================================

@router.post(
    "",
    response_model=MesaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva mesa",
    description="Agregar mesa a una zona del restaurante"
)
def crear_mesa(
    mesa_data: MesaCreate,
    db: Session = Depends(get_db)
):
    """Crear nueva mesa en zona"""
    try:
        service = MesaService(db)
        mesa = service.crear_mesa(mesa_data, 1)  # empresa_id=1 por ahora
        
        logger.info(f"Mesa {mesa.nombre} creada en zona {mesa.zona_id}")
        return mesa
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creando mesa: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creando mesa")

# ============================================================================
# OBTENER MESA
# ============================================================================

@router.get(
    "/{mesa_id}",
    response_model=MesaResponse,
    summary="Obtener detalles de mesa"
)
def obtener_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Obtener información completa de una mesa"""
    service = MesaService(db)
    mesa = service.obtener_mesa(mesa_id)
    
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    return mesa

# ============================================================================
# LISTAR MESAS
# ============================================================================

@router.get(
    "",
    response_model=List[ReporteMesaResponse],
    summary="Listar mesas por zona"
)
def listar_mesas(
    zona_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Listar todas las mesas de una zona"""
    if not zona_id:
        raise HTTPException(status_code=422, detail="zona_id es requerido")
    
    service = MesaService(db)
    mesas = service.listar_mesas_por_zona(zona_id)
    
    # Convertir a ReporteMesaResponse
    return [
        ReporteMesaResponse(
            id=m.id,
            nombre=m.nombre,
            zona=m.zona.nombre if m.zona else "Desconocida",
            capacidad=m.capacidad,
            estado=m.estado,
            ocupacion="Disponible" if m.estado == "disponible" else f"Ocupada"
        )
        for m in mesas
    ]

# ============================================================================
# FLOOR PLAN COMPLETO
# ============================================================================

@router.get(
    "/plano/completo",
    response_model=FloorPlanResponse,
    summary="Obtener plano completo",
    description="Retorna todas las zonas, mesas y estadísticas de ocupación"
)
def obtener_floor_plan(db: Session = Depends(get_db)):
    """Obtener plano completo del restaurante con estadísticas"""
    service = MesaService(db)
    plano = service.obtener_floor_plan()
    
    return FloorPlanResponse(
        restaurante="Mi Café",
        zonas=[
            ZonaResponse(
                id=zona.id,
                nombre=zona.nombre,
                orden=zona.orden,
                mesas_count=len(zona.mesas),
                mesas_disponibles=len([m for m in zona.mesas if m.estado == "disponible"]),
                mesas=[
                    MesaResponse(
                        id=m.id,
                        zona_id=m.zona_id,
                        nombre=m.nombre,
                        capacidad=m.capacidad,
                        posicion_x=m.posicion_x,
                        posicion_y=m.posicion_y,
                        forma=m.forma,
                        estado=m.estado,
                        venta_activa=None,
                        numero_personas=None
                    )
                    for m in zona.mesas
                ]
            )
            for zona in plano["zonas"]
        ],
        estadisticas=plano["estadisticas"]
    )

# ============================================================================
# ACTUALIZAR MESA
# ============================================================================

@router.patch(
    "/{mesa_id}",
    response_model=MesaResponse,
    summary="Actualizar mesa"
)
def actualizar_mesa(
    mesa_id: int,
    mesa_data: MesaUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar información de mesa"""
    try:
        service = MesaService(db)
        mesa = service.actualizar_mesa(mesa_id, mesa_data)
        
        logger.info(f"Mesa {mesa.nombre} actualizada")
        return mesa
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

# ============================================================================
# CAMBIAR ESTADO
# ============================================================================

@router.post(
    "/{mesa_id}/estado",
    response_model=MesaResponse,
    summary="Cambiar estado de mesa"
)
def cambiar_estado_mesa(
    mesa_id: int,
    cambio: CambiarEstadoMesa,
    db: Session = Depends(get_db)
):
    """
    Cambiar estado de mesa
    
    Estados válidos:
    - disponible: Mesa lista para usar
    - ocupada: Mesa con clientes
    - reservada: Mesa reservada
    - limpieza: En proceso de limpieza
    - mantenimiento: Requiere reparación
    """
    try:
        service = MesaService(db)
        mesa = service.cambiar_estado(mesa_id, cambio)
        
        logger.info(f"Mesa {mesa.nombre} cambió estado a {mesa.estado}")
        return mesa
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

# ============================================================================
# OCUPAR/LIBERAR MESA
# ============================================================================

@router.post(
    "/{mesa_id}/ocupar",
    response_model=MesaResponse,
    summary="Ocupar mesa (iniciar venta)"
)
def ocupar_mesa(
    mesa_id: int,
    venta_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Marcar mesa como ocupada por venta"""
    try:
        service = MesaService(db)
        mesa = service.ocupar_mesa(mesa_id, venta_id)
        return mesa
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post(
    "/{mesa_id}/liberar",
    response_model=MesaResponse,
    summary="Liberar mesa (cerrar venta)"
)
def liberar_mesa(mesa_id: int, db: Session = Depends(get_db)):
    """Liberar mesa (cambiar a disponible)"""
    try:
        service = MesaService(db)
        mesa = service.liberar_mesa(mesa_id)
        return mesa
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post(
    "/{mesa_id}/limpieza",
    response_model=MesaResponse,
    summary="Marcar en limpieza"
)
def marcar_limpieza(mesa_id: int, db: Session = Depends(get_db)):
    """Marcar mesa en limpieza"""
    try:
        service = MesaService(db)
        mesa = service.marcar_limpieza(mesa_id)
        return mesa
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

# ============================================================================
# ESTADÍSTICAS
# ============================================================================

@router.get(
    "/reportes/ocupacion",
    response_model=EstadisticasMesa,
    summary="Estadísticas de ocupación"
)
def obtener_estadisticas(db: Session = Depends(get_db)):
    """Obtener estadísticas de ocupación actual"""
    service = MesaService(db)
    stats = service.obtener_estadisticas()
    
    return EstadisticasMesa(
        fecha="2026-07-19",
        total_mesas=stats["total_mesas"],
        ocupadas=stats["ocupadas"],
        disponibles=stats["disponibles"],
        en_limpieza=stats["en_limpieza"],
        reservadas=stats["reservadas"],
        ocupacion_promedio=stats["ocupacion_porcentaje"],
        mesas_por_estado=stats["por_estado"]
    )

# ============================================================================
# ESTADOS DISPONIBLES (Catálogo)
# ============================================================================

@router.get(
    "/catalogo/estados",
    response_model=List[str],
    summary="Estados de mesa disponibles"
)
def obtener_estados():
    """Estados válidos para una mesa"""
    return [e.value for e in EstadoMesa]

@router.get(
    "/catalogo/formas",
    response_model=List[str],
    summary="Formas de mesa disponibles"
)
def obtener_formas():
    """Formas de mesa disponibles"""
    return [f.value for f in FormaMesa]
