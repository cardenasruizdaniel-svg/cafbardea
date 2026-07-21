"""
REST API routes para Comanda (Kitchen Management) - FASE 3
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.domains.comanda.schemas import (
    ComandaCreate,
    ComandaUpdate,
    CambiarEstadoComanda,
    ComandaResponse,
    ComandaDetalleResponse,
    EstadisticasComanda,
    ListaEsperaComanda,
    EstadoComanda,
    PrioridadComanda
)
from app.domains.comanda.services import ComandaService

router = APIRouter()


@router.post("/comanda", response_model=ComandaResponse, status_code=201, tags=["comanda"])
async def crear_comanda(
    comanda_data: ComandaCreate,
    db: Session = Depends(get_db)
) -> ComandaResponse:
    """Crear nueva comanda en cocina"""
    try:
        service = ComandaService(db)
        comanda = service.crear_comanda(comanda_data)
        return ComandaResponse.model_validate(comanda)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creando comanda")


@router.get("/comanda/{comanda_id}", response_model=ComandaResponse, tags=["comanda"])
async def obtener_comanda(
    comanda_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> ComandaResponse:
    """Obtener comanda por ID"""
    service = ComandaService(db)
    comanda = service.obtener_comanda(comanda_id)
    
    if not comanda:
        raise HTTPException(status_code=404, detail="Comanda no encontrada")
    
    return ComandaResponse.model_validate(comanda)


@router.get("/comanda", response_model=List[ComandaResponse], tags=["comanda"])
async def listar_comandas(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    prioridad: Optional[str] = Query(None, description="Filtrar por prioridad"),
    mesa_id: Optional[int] = Query(None, description="Filtrar por mesa"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> List[ComandaResponse]:
    """Listar comandas con filtros"""
    service = ComandaService(db)
    
    # Obtener todas las comandas pendientes por defecto
    if not estado:
        comandas = service.obtener_comandas_pendientes()
    else:
        comandas = service.listar_comandas_por_estado(estado)
    
    # Filtrar por prioridad si se proporciona
    if prioridad:
        comandas = [c for c in comandas if c.prioridad == prioridad]
    
    # Filtrar por mesa si se proporciona
    if mesa_id:
        comandas = [c for c in comandas if c.mesa_id == mesa_id]
    
    # Aplicar paginación
    comandas_paginadas = comandas[offset:offset + limit]
    
    return [ComandaResponse.model_validate(c) for c in comandas_paginadas]


@router.patch("/comanda/{comanda_id}", response_model=ComandaResponse, tags=["comanda"])
async def actualizar_comanda(
    comanda_id: int = Path(..., gt=0),
    comanda_data: ComandaUpdate = None,
    db: Session = Depends(get_db)
) -> ComandaResponse:
    """Actualizar datos de comanda (prioridad, notas)"""
    service = ComandaService(db)
    comanda = service.obtener_comanda(comanda_id)
    
    if not comanda:
        raise HTTPException(status_code=404, detail="Comanda no encontrada")
    
    if comanda_data.prioridad:
        comanda.prioridad = comanda_data.prioridad
    
    if comanda_data.notas:
        comanda.notas = comanda_data.notas
    
    db.commit()
    db.refresh(comanda)
    
    return ComandaResponse.model_validate(comanda)


@router.post("/comanda/{comanda_id}/estado", response_model=ComandaResponse, tags=["comanda"])
async def cambiar_estado_comanda(
    comanda_id: int = Path(..., gt=0),
    cambio: CambiarEstadoComanda = None,
    db: Session = Depends(get_db)
) -> ComandaResponse:
    """Cambiar estado de comanda (pendiente → preparando → lista → entregada)"""
    try:
        service = ComandaService(db)
        comanda = service.cambiar_estado(comanda_id, cambio)
        return ComandaResponse.model_validate(comanda)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/comanda/{comanda_id}/prioridad", response_model=ComandaResponse, tags=["comanda"])
async def aumentar_prioridad(
    comanda_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> ComandaResponse:
    """Aumentar prioridad de comanda (normal → alta → urgente)"""
    try:
        service = ComandaService(db)
        comanda = service.aumentar_prioridad(comanda_id)
        return ComandaResponse.model_validate(comanda)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/comanda/lista/espera", response_model=List[ListaEsperaComanda], tags=["comanda"])
async def obtener_lista_espera(db: Session = Depends(get_db)) -> List[ListaEsperaComanda]:
    """Obtener lista de espera (comandas pendientes con tiempo de espera)"""
    service = ComandaService(db)
    lista = service.obtener_lista_espera()
    return lista


@router.get("/comanda/mesa/{mesa_id}", response_model=List[ComandaResponse], tags=["comanda"])
async def obtener_comandas_mesa(
    mesa_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> List[ComandaResponse]:
    """Obtener comandas asociadas a una mesa"""
    service = ComandaService(db)
    comandas = service.obtener_comandas_por_mesa(mesa_id)
    return [ComandaResponse.model_validate(c) for c in comandas]


@router.get("/comanda/{comanda_id}/detalles", response_model=ComandaDetalleResponse, tags=["comanda"])
async def obtener_detalles_comanda(
    comanda_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> ComandaDetalleResponse:
    """Obtener comanda con detalles de items"""
    service = ComandaService(db)
    detalles = service.obtener_detalles_comanda(comanda_id)
    
    if not detalles:
        raise HTTPException(status_code=404, detail="Comanda no encontrada")
    
    return ComandaDetalleResponse(**detalles)


@router.get("/comanda/reportes/estadisticas", response_model=EstadisticasComanda, tags=["comanda"])
async def obtener_estadisticas(db: Session = Depends(get_db)) -> EstadisticasComanda:
    """Obtener estadísticas de comandas"""
    service = ComandaService(db)
    stats = service.obtener_estadisticas()
    return EstadisticasComanda(**stats)


# === Endpoints públicos de catálogo ===

@router.get("/comanda/catalogo/estados", tags=["catalogo"], include_in_schema=True)
async def listar_estados_comanda() -> List[str]:
    """[PÚBLICO] Listar estados válidos de comanda"""
    return [e.value for e in EstadoComanda]


@router.get("/comanda/catalogo/prioridades", tags=["catalogo"], include_in_schema=True)
async def listar_prioridades_comanda() -> List[str]:
    """[PÚBLICO] Listar prioridades válidas de comanda"""
    return [p.value for p in PrioridadComanda]
