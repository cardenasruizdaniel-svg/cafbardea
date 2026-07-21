"""
REST API routes para Nómina (Payroll Management) - FASE 4
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.domains.nomina.schemas import (
    PeriodoNominaCreate,
    PeriodoNominaResponse,
    LiquidacionNominaCreate,
    LiquidacionNominaUpdate,
    LiquidacionNominaResponse,
    ReciboNominaResponse,
    EstadisticasNomina,
    ProcesarNominaCreate,
    EstadoNomina,
    TipoNomina
)
from app.domains.nomina.services import NominaService

router = APIRouter()


# ============================================================================
# PERÍODOS DE NÓMINA
# ============================================================================

@router.post("/nomina/periodos", response_model=PeriodoNominaResponse, status_code=201, tags=["nomina"])
async def crear_periodo(
    periodo_data: PeriodoNominaCreate,
    db: Session = Depends(get_db)
) -> PeriodoNominaResponse:
    """Crear nuevo período de nómina"""
    try:
        service = NominaService(db)
        periodo = service.crear_periodo(periodo_data)
        return PeriodoNominaResponse.model_validate(periodo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/nomina/periodos/{periodo_id}", response_model=PeriodoNominaResponse, tags=["nomina"])
async def obtener_periodo(
    periodo_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> PeriodoNominaResponse:
    """Obtener período de nómina por ID"""
    service = NominaService(db)
    periodo = service.obtener_periodo(periodo_id)

    if not periodo:
        raise HTTPException(status_code=404, detail="Período no encontrado")

    return PeriodoNominaResponse.model_validate(periodo)


@router.get("/nomina/periodos", response_model=List[PeriodoNominaResponse], tags=["nomina"])
async def listar_periodos(db: Session = Depends(get_db)) -> List[PeriodoNominaResponse]:
    """Listar todos los períodos de nómina"""
    service = NominaService(db)
    periodos = service.listar_periodos()
    return [PeriodoNominaResponse.model_validate(p) for p in periodos]


@router.get("/nomina/periodos/actual/vigente", response_model=Optional[PeriodoNominaResponse], tags=["nomina"])
async def obtener_periodo_actual(db: Session = Depends(get_db)) -> Optional[PeriodoNominaResponse]:
    """Obtener período de nómina vigente (actual)"""
    service = NominaService(db)
    periodo = service.obtener_periodo_actual()

    if not periodo:
        raise HTTPException(status_code=404, detail="No hay período vigente")

    return PeriodoNominaResponse.model_validate(periodo)


# ============================================================================
# LIQUIDACIONES DE NÓMINA
# ============================================================================

@router.post("/nomina/liquidaciones", response_model=LiquidacionNominaResponse, status_code=201, tags=["nomina"])
async def crear_liquidacion(
    liquidacion_data: LiquidacionNominaCreate,
    db: Session = Depends(get_db)
) -> LiquidacionNominaResponse:
    """Crear liquidación de nómina para un empleado"""
    try:
        service = NominaService(db)
        liquidacion = service.crear_liquidacion(liquidacion_data)
        return LiquidacionNominaResponse.model_validate(liquidacion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/nomina/liquidaciones/{liquidacion_id}", response_model=LiquidacionNominaResponse, tags=["nomina"])
async def obtener_liquidacion(
    liquidacion_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> LiquidacionNominaResponse:
    """Obtener liquidación de nómina por ID"""
    service = NominaService(db)
    liquidacion = service.obtener_liquidacion(liquidacion_id)

    if not liquidacion:
        raise HTTPException(status_code=404, detail="Liquidación no encontrada")

    return LiquidacionNominaResponse.model_validate(liquidacion)


@router.get("/nomina/periodos/{periodo_id}/liquidaciones", response_model=List[LiquidacionNominaResponse], tags=["nomina"])
async def listar_liquidaciones_periodo(
    periodo_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> List[LiquidacionNominaResponse]:
    """Listar liquidaciones de un período de nómina"""
    service = NominaService(db)
    liquidaciones = service.listar_liquidaciones_periodo(periodo_id)
    return [LiquidacionNominaResponse.model_validate(l) for l in liquidaciones]


@router.get("/nomina/empleados/{empleado_id}/liquidaciones", response_model=List[LiquidacionNominaResponse], tags=["nomina"])
async def listar_liquidaciones_empleado(
    empleado_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> List[LiquidacionNominaResponse]:
    """Listar liquidaciones de un empleado"""
    service = NominaService(db)
    liquidaciones = service.listar_liquidaciones_empleado(empleado_id)
    return [LiquidacionNominaResponse.model_validate(l) for l in liquidaciones]


@router.patch("/nomina/liquidaciones/{liquidacion_id}", response_model=LiquidacionNominaResponse, tags=["nomina"])
async def actualizar_liquidacion(
    liquidacion_id: int = Path(..., gt=0),
    data: LiquidacionNominaUpdate = None,
    db: Session = Depends(get_db)
) -> LiquidacionNominaResponse:
    """Actualizar datos de liquidación de nómina"""
    try:
        service = NominaService(db)
        liquidacion = service.actualizar_liquidacion(liquidacion_id, data)
        return LiquidacionNominaResponse.model_validate(liquidacion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# PROCESAMIENTO DE NÓMINA
# ============================================================================

@router.post("/nomina/periodos/{periodo_id}/procesar", tags=["nomina"])
async def procesar_periodo(
    periodo_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Procesar todas las liquidaciones de un período"""
    try:
        service = NominaService(db)
        resultado = service.procesar_periodo(periodo_id)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/nomina/periodos/{periodo_id}/pagar", tags=["nomina"])
async def pagar_periodo(
    periodo_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Marcar período de nómina como pagado"""
    try:
        service = NominaService(db)
        resultado = service.pagar_periodo(periodo_id)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# RECIBOS Y REPORTES
# ============================================================================

@router.get("/nomina/liquidaciones/{liquidacion_id}/recibo", response_model=ReciboNominaResponse, tags=["nomina"])
async def obtener_recibo_nomina(
    liquidacion_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
) -> ReciboNominaResponse:
    """Obtener recibo de pago de nómina"""
    service = NominaService(db)
    recibo = service.obtener_recibo_nomina(liquidacion_id)

    if not recibo:
        raise HTTPException(status_code=404, detail="Liquidación no encontrada")

    return ReciboNominaResponse(**recibo)


@router.get("/nomina/reportes/estadisticas", response_model=EstadisticasNomina, tags=["nomina"])
async def obtener_estadisticas(
    periodo_id: Optional[int] = Query(None, description="Filtrar por período"),
    db: Session = Depends(get_db)
) -> EstadisticasNomina:
    """Obtener estadísticas de nómina"""
    service = NominaService(db)
    stats = service.obtener_estadisticas(periodo_id)
    return EstadisticasNomina(**stats)


@router.get("/nomina/empleados/{empleado_id}/deuda", tags=["nomina"])
async def obtener_deuda_empleado(
    empleado_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Obtener deuda de nómina de un empleado"""
    service = NominaService(db)
    deuda = service.obtener_deuda_empleado(empleado_id)

    return {
        "empleado_id": empleado_id,
        "deuda_total": deuda
    }


# ============================================================================
# CATÁLOGOS PÚBLICOS
# ============================================================================

@router.get("/nomina/catalogo/estados", tags=["catalogo"], include_in_schema=True)
async def listar_estados_nomina() -> List[str]:
    """[PÚBLICO] Listar estados válidos de nómina"""
    return [e.value for e in EstadoNomina]


@router.get("/nomina/catalogo/tipos", tags=["catalogo"], include_in_schema=True)
async def listar_tipos_nomina() -> List[str]:
    """[PÚBLICO] Listar tipos de nómina"""
    return [t.value for t in TipoNomina]
