"""API de consulta de nomina."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/nomina", tags=["nomina"])


@router.get("/periodos/{periodo_id}/resumen")
def resumen_periodo(periodo_id: int, db: Session = Depends(get_db)):
    """Resumen de totales de un periodo liquidado."""
    from .services import NominaService
    try:
        return NominaService(db).resumen_periodo(periodo_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/empleados/{empleado_id}/liquidacion-definitiva")
def liquidacion_definitiva(empleado_id: int, fecha_retiro: str,
                           db: Session = Depends(get_db)):
    """Calcula prestaciones al retiro (no persiste)."""
    from datetime import date
    from .services import NominaService
    try:
        fecha = date.fromisoformat(fecha_retiro)
        return NominaService(db).liquidacion_definitiva(empleado_id, fecha)
    except ValueError as e:
        raise HTTPException(400, str(e))
