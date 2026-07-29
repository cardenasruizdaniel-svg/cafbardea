"""Modulo del MESERO: su propio plano de mesas y toma de pedidos.

Antes, la app de meseros enviaba a la ventana de mesas de la web (gestion). Aqui
el mesero tiene su PROPIO modulo, optimizado para celular/tactil:
  - Plano de mesas por zona (visual, como la web pero para tocar).
  - Al tocar una mesa: abre la comanda para tomar el pedido de una vez.
  - Comandar: impresion incremental (solo los productos nuevos).

Reglas de negocio:
  - El mesero NO puede cobrar ni liberar la mesa (eso es solo del cajero en caja).
  - La impresion al comandar toma solo los ultimos productos agregados.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Mesa, Zona, Venta, DetalleVenta, Producto, Categoria

logger = logging.getLogger("mesero_api")
router = APIRouter(tags=["mesero"])

_templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _exigir_sesion(request: Request):
    if not request.session.get("usuario_id"):
        raise HTTPException(401, "Requiere iniciar sesion")


# ============================================================================
# PLANO DE MESAS DEL MESERO
# ============================================================================
@router.get("/mobile/mesas", response_class=HTMLResponse)
def mesero_mesas(request: Request, db: Session = Depends(get_db)):
    """Plano de mesas del mesero (su propio modulo, no la web)."""
    _exigir_sesion(request)
    from sqlalchemy.orm import selectinload
    zonas = db.scalars(
        select(Zona).options(selectinload(Zona.mesas)).order_by(Zona.orden)
    ).all()

    # Garantizar que mesas huérfanas se asignen a una zona visible
    mesas_sin_zona = db.scalars(select(Mesa).where(Mesa.zona_id.is_(None))).all()
    if mesas_sin_zona:
        if not zonas:
            zona_def = Zona(nombre="Zona Principal", orden=1)
            db.add(zona_def)
            db.commit()
            db.refresh(zona_def)
            zonas = [zona_def]
        z_def = zonas[0]
        for m in mesas_sin_zona:
            m.zona_id = z_def.id
        db.commit()
        zonas = db.scalars(
            select(Zona).options(selectinload(Zona.mesas)).order_by(Zona.orden)
        ).all()

    return _templates.TemplateResponse(request, "mesero_mesas.html", {
        "request": request,
        "zonas": zonas,
        "usuario": {"nombre": request.session.get("usuario_nombre", ""),
                    "rol": request.session.get("rol", "")},
    })


@router.get("/mobile/comanda/{mesa_id}", response_class=HTMLResponse)
def mesero_comanda(mesa_id: int, request: Request, db: Session = Depends(get_db)):
    """Pantalla de comanda del mesero para una mesa: tomar pedido."""
    _exigir_sesion(request)
    mesa = db.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(404, "Mesa no encontrada")
    venta = db.scalar(select(Venta).where(
        Venta.mesa_id == mesa_id, Venta.estado == "abierta"))
    productos = db.scalars(
        select(Producto).where(Producto.activo.is_(True))
        .order_by(Producto.nombre)).all()
    cats = {c.id: c.nombre for c in db.scalars(select(Categoria)).all()}
    prod_data = [{"id": p.id, "nombre": p.nombre,
                  "precio": float(p.precio_venta),
                  "categoria": cats.get(p.categoria_id, "General")}
                 for p in productos]
    # lineas actuales de la venta
    lineas = []
    if venta:
        for d in venta.detalles:
            prod = db.get(Producto, d.producto_id)
            lineas.append({"id": d.id, "producto": prod.nombre if prod else "?",
                           "cantidad": float(d.cantidad),
                           "comandado": d.comandado})
    return _templates.TemplateResponse(request, "mesero_comanda.html", {
        "request": request, "mesa": mesa,
        "venta_id": venta.id if venta else None,
        "productos": prod_data, "lineas": lineas,
        "total": float(venta.total) if venta else 0,
    })


@router.get("/mobile/cocina", response_class=HTMLResponse)
def mesero_cocina(request: Request, db: Session = Depends(get_db)):
    """Pantalla de cocina KDS optimizada para la app movil."""
    _exigir_sesion(request)
    items = db.scalars(
        select(DetalleVenta)
        .where(DetalleVenta.estado_cocina.in_(["pendiente", "preparando", "listo"]))
        .order_by(DetalleVenta.id.desc())
        .limit(50)
    ).all()

    filas = []
    for d in items:
        prod = db.get(Producto, d.producto_id)
        venta = db.get(Venta, d.venta_id) if d.venta_id else None
        mesa = db.get(Mesa, venta.mesa_id) if (venta and venta.mesa_id) else None
        filas.append({
            "id": d.id,
            "producto": prod.nombre if prod else f"Producto #{d.producto_id}",
            "cantidad": d.cantidad,
            "nota": d.nota or "",
            "estado": d.estado_cocina or "pendiente",
            "mesa": mesa.nombre if mesa else "Mostrador",
        })

    return _templates.TemplateResponse(request, "mobile_cocina.html", {
        "request": request,
        "filas": filas,
        "usuario": {"nombre": request.session.get("usuario_nombre", ""),
                    "rol": request.session.get("rol", "")},
    })


# ============================================================================
# API: tomar pedido y comandar
# ============================================================================
@router.post("/api/mesero/mesa/{mesa_id}/agregar")
async def mesero_agregar(mesa_id: int, request: Request,
                         db: Session = Depends(get_db)):
    """Agrega un producto a la comanda de la mesa (abre venta si no hay)."""
    _exigir_sesion(request)
    from app.main import recalcular_venta
    from app.models import Empresa
    from decimal import Decimal

    datos = await request.json()
    producto_id = int(datos["producto_id"])
    cantidad = float(datos.get("cantidad", 1))
    nota = (datos.get("nota") or "").strip() or None

    mesa = db.get(Mesa, mesa_id)
    producto = db.get(Producto, producto_id)
    if not mesa or not producto:
        raise HTTPException(404, "Mesa o producto no encontrado")

    venta = db.scalar(select(Venta).where(
        Venta.mesa_id == mesa_id, Venta.estado == "abierta"))
    if not venta:
        venta = Venta(mesa_id=mesa_id,
                      empleado_id=request.session.get("empleado_id"))
        db.add(venta)
        db.flush()
        mesa.estado = "ocupada"

    db.add(DetalleVenta(venta_id=venta.id, producto_id=producto.id,
                        cantidad=cantidad, precio=producto.precio_venta,
                        nota=nota))
    recalcular_venta(venta)
    empresa = db.scalar(select(Empresa).limit(1))
    if empresa:
        venta.impuesto = (venta.subtotal * empresa.impuesto_porcentaje /
                          Decimal("100")).quantize(Decimal("0.01"))
        recalcular_venta(venta)
    db.commit()
    return {"ok": True, "venta_id": venta.id, "total": float(venta.total)}


@router.post("/api/mesero/mesa/{mesa_id}/comandar")
def mesero_comandar(mesa_id: int, request: Request,
                    db: Session = Depends(get_db)):
    """Comanda la mesa: imprime SOLO los productos nuevos (incremental)."""
    _exigir_sesion(request)
    from app.domains.impresion.services import ImpresionService

    venta = db.scalar(select(Venta).where(
        Venta.mesa_id == mesa_id, Venta.estado == "abierta"))
    if not venta:
        raise HTTPException(400, "La mesa no tiene una comanda abierta")

    try:
        resultado = ImpresionService(db).comandar_venta(venta.id)
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, **resultado}


@router.post("/api/mesero/mesa/{mesa_id}/item/{detalle_id}/quitar")
def mesero_quitar_item(mesa_id: int, detalle_id: int, request: Request,
                       db: Session = Depends(get_db)):
    """Quita un item NO comandado. Los ya comandados no se pueden quitar
    (ya se enviaron a cocina); eso lo maneja la caja."""
    _exigir_sesion(request)
    from app.main import recalcular_venta
    detalle = db.get(DetalleVenta, detalle_id)
    venta = db.scalar(select(Venta).where(
        Venta.mesa_id == mesa_id, Venta.estado == "abierta"))
    if not detalle or not venta or detalle.venta_id != venta.id:
        raise HTTPException(404, "Item no encontrado")
    if detalle.comandado:
        raise HTTPException(
            400, "Ese producto ya fue comandado; pídele a caja que lo anule")
    db.delete(detalle)
    recalcular_venta(venta)
    db.commit()
    return {"ok": True, "total": float(venta.total)}
