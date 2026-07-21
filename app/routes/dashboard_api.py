"""
Dashboard KPI API - FASE 10
Endpoints de KPIs en tiempo real con comparativas

Endpoints:
- GET /api/v1/dashboard/kpis            - KPIs principales + comparativas
- GET /api/v1/dashboard/ventas-por-hora - Ventas por hora del día
- GET /api/v1/dashboard/top-productos   - Top 5 productos del día
- GET /api/v1/dashboard/categorias      - Distribución por categoría
- GET /api/v1/dashboard/mesas           - Ocupación de mesas en tiempo real
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging

from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_
from app.models import (
    Venta, DetalleVenta, Producto, Categoria,
    Mesa, Empresa
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard KPI - FASE 10"]
)


# ============================================================================
# Schemas
# ============================================================================

class KPIComparativa(BaseModel):
    valor_actual: float
    valor_anterior: float
    variacion_pct: float    # positivo = creció, negativo = bajó
    tendencia: str          # "sube", "baja", "igual"


class DashboardKPIs(BaseModel):
    fecha: str
    hora_actualizacion: str

    # KPIs del día
    ingresos_hoy: float
    transacciones_hoy: int
    ticket_promedio_hoy: float
    mesas_ocupadas: int
    mesas_totales: int
    ocupacion_pct: float
    alertas_stock: int

    # Comparativas
    vs_ayer: KPIComparativa
    vs_semana_pasada: KPIComparativa


class VentasPorHora(BaseModel):
    hora: int           # 0-23
    label: str          # "08:00"
    total: float
    transacciones: int


class TopProducto(BaseModel):
    nombre: str
    cantidad: float
    ingresos: float


class DistribucionCategoria(BaseModel):
    categoria: str
    ingresos: float
    porcentaje: float


class EstadoMesas(BaseModel):
    libres: int
    ocupadas: int
    reservadas: int
    totales: int
    ocupacion_pct: float


# ============================================================================
# Helpers
# ============================================================================

def _empresa_id(db: Session) -> int:
    row = db.query(Empresa).first()
    return row.id if row else 1


def _ingresos_dia(db: Session, empresa_id: int, dia: date) -> tuple:
    """Retorna (total, cantidad) de ventas pagadas en un día."""
    rows = db.query(Venta).filter(
        Venta.empresa_id == empresa_id,
        Venta.estado.in_(["pagada", "credito"]),
        func.date(Venta.fecha) == dia
    ).all()
    total = float(sum(v.total for v in rows))
    return total, len(rows)


def _variacion(actual: float, anterior: float) -> KPIComparativa:
    if anterior == 0:
        pct = 100.0 if actual > 0 else 0.0
    else:
        pct = round((actual - anterior) / anterior * 100, 1)

    if pct > 1:
        tendencia = "sube"
    elif pct < -1:
        tendencia = "baja"
    else:
        tendencia = "igual"

    return KPIComparativa(
        valor_actual=actual,
        valor_anterior=anterior,
        variacion_pct=pct,
        tendencia=tendencia
    )


# ============================================================================
# GET /kpis
# ============================================================================

@router.get("/kpis", response_model=DashboardKPIs)
def obtener_kpis(db: Session = Depends(get_db)):
    """
    KPIs principales del negocio con comparativas vs ayer y semana anterior.
    Diseñado para actualizarse cada 30–60 segundos desde el dashboard.
    """
    empresa_id = _empresa_id(db)
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    hace_7_dias = hoy - timedelta(days=7)

    # Hoy
    ingresos_hoy, tx_hoy = _ingresos_dia(db, empresa_id, hoy)
    ticket_hoy = ingresos_hoy / tx_hoy if tx_hoy else 0.0

    # Ayer
    ingresos_ayer, _ = _ingresos_dia(db, empresa_id, ayer)

    # Mismo día semana pasada
    ingresos_semana, _ = _ingresos_dia(db, empresa_id, hace_7_dias)

    # Mesas
    mesas = db.query(Mesa).filter(Mesa.empresa_id == empresa_id).all()
    totales = len(mesas)
    ocupadas = sum(1 for m in mesas if m.estado == "ocupada")
    ocupacion = round(ocupadas / totales * 100, 1) if totales else 0.0

    # Stock bajo
    alertas = db.query(Producto).filter(
        Producto.empresa_id == empresa_id,
        Producto.activo == True,
        Producto.existencias <= Producto.stock_minimo
    ).count()

    ahora = datetime.now(timezone.utc)

    logger.info(f"📊 KPIs: hoy=${ingresos_hoy:,.0f}, tx={tx_hoy}, mesas={ocupadas}/{totales}")

    return DashboardKPIs(
        fecha=hoy.isoformat(),
        hora_actualizacion=ahora.strftime("%H:%M:%S"),
        ingresos_hoy=ingresos_hoy,
        transacciones_hoy=tx_hoy,
        ticket_promedio_hoy=round(ticket_hoy, 2),
        mesas_ocupadas=ocupadas,
        mesas_totales=totales,
        ocupacion_pct=ocupacion,
        alertas_stock=alertas,
        vs_ayer=_variacion(ingresos_hoy, ingresos_ayer),
        vs_semana_pasada=_variacion(ingresos_hoy, ingresos_semana)
    )


# ============================================================================
# GET /ventas-por-hora
# ============================================================================

@router.get("/ventas-por-hora", response_model=List[VentasPorHora])
def ventas_por_hora(
    dia: Optional[date] = Query(None, description="Día a consultar (default: hoy)"),
    db: Session = Depends(get_db)
):
    """Ventas agrupadas por hora del día — para gráfico de líneas."""
    empresa_id = _empresa_id(db)
    consulta_dia = dia or date.today()

    ventas = db.query(Venta).filter(
        Venta.empresa_id == empresa_id,
        Venta.estado.in_(["pagada", "credito"]),
        func.date(Venta.fecha) == consulta_dia
    ).all()

    # Agrupar manualmente por hora (compatible SQLite + Postgres)
    por_hora: dict = {h: {"total": 0.0, "tx": 0} for h in range(7, 24)}
    for v in ventas:
        h = v.fecha.hour
        if h in por_hora:
            por_hora[h]["total"] += float(v.total)
            por_hora[h]["tx"] += 1

    return [
        VentasPorHora(
            hora=h,
            label=f"{h:02d}:00",
            total=round(datos["total"], 2),
            transacciones=datos["tx"]
        )
        for h, datos in sorted(por_hora.items())
    ]


# ============================================================================
# GET /top-productos
# ============================================================================

@router.get("/top-productos", response_model=List[TopProducto])
def top_productos(
    dia: Optional[date] = Query(None),
    limite: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Top N productos por ingresos en el día — para gráfico de barras."""
    empresa_id = _empresa_id(db)
    consulta_dia = dia or date.today()

    rows = (
        db.query(
            Producto.nombre,
            func.sum(DetalleVenta.cantidad).label("cantidad"),
            func.sum(DetalleVenta.precio * DetalleVenta.cantidad).label("ingresos")
        )
        .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(
            Venta.empresa_id == empresa_id,
            Venta.estado.in_(["pagada", "credito"]),
            func.date(Venta.fecha) == consulta_dia
        )
        .group_by(Producto.nombre)
        .order_by(func.sum(DetalleVenta.precio * DetalleVenta.cantidad).desc())
        .limit(limite)
        .all()
    )

    return [
        TopProducto(
            nombre=r.nombre,
            cantidad=float(r.cantidad or 0),
            ingresos=float(r.ingresos or 0)
        )
        for r in rows
    ]


# ============================================================================
# GET /categorias
# ============================================================================

@router.get("/categorias", response_model=List[DistribucionCategoria])
def distribucion_categorias(
    dia: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Distribución de ingresos por categoría — para gráfico de pastel."""
    empresa_id = _empresa_id(db)
    consulta_dia = dia or date.today()

    rows = (
        db.query(
            Categoria.nombre,
            func.sum(DetalleVenta.precio * DetalleVenta.cantidad).label("ingresos")
        )
        .join(Producto, Producto.categoria_id == Categoria.id)
        .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(
            Venta.empresa_id == empresa_id,
            Venta.estado.in_(["pagada", "credito"]),
            func.date(Venta.fecha) == consulta_dia
        )
        .group_by(Categoria.nombre)
        .order_by(func.sum(DetalleVenta.precio * DetalleVenta.cantidad).desc())
        .all()
    )

    total = sum(float(r.ingresos or 0) for r in rows)

    return [
        DistribucionCategoria(
            categoria=r.nombre,
            ingresos=float(r.ingresos or 0),
            porcentaje=round(float(r.ingresos or 0) / total * 100, 1) if total else 0.0
        )
        for r in rows
    ]


# ============================================================================
# GET /mesas
# ============================================================================

@router.get("/mesas", response_model=EstadoMesas)
def estado_mesas(db: Session = Depends(get_db)):
    """Estado de ocupación de mesas en tiempo real — para gauge."""
    empresa_id = _empresa_id(db)

    mesas = db.query(Mesa).filter(Mesa.empresa_id == empresa_id).all()
    totales = len(mesas)
    libres = sum(1 for m in mesas if m.estado == "libre")
    ocupadas = sum(1 for m in mesas if m.estado == "ocupada")
    reservadas = sum(1 for m in mesas if m.estado == "reservada")
    ocupacion = round(ocupadas / totales * 100, 1) if totales else 0.0

    return EstadoMesas(
        libres=libres,
        ocupadas=ocupadas,
        reservadas=reservadas,
        totales=totales,
        ocupacion_pct=ocupacion
    )
