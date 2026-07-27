"""Rutas de la app de cliente (autoservicio y pedido en mesa) y su gestion.

Dos audiencias:
  - Cliente (publico, sin login): ver la carta y crear un pedido.
  - Personal (con sesion): ver pendientes y aceptarlos/rechazarlos/cobrarlos.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.domains.pedidos_cliente.services import PedidoClienteService
from app.models import Producto, Categoria, Mesa, Zona

logger = logging.getLogger("cliente_api")

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter(tags=["cliente"])


@router.get("/cliente", response_class=HTMLResponse)
def app_cliente(request: Request, mesa: int = None, db: Session = Depends(get_db)):
    """Pagina de la app de cliente (autoservicio o mesa).

    Si viene ?mesa=N, arranca en modo pedido de mesa; si no, autoservicio.
    """
    mesa_obj = db.get(Mesa, mesa) if mesa else None
    return _templates.TemplateResponse(request, "cliente.html", {
        "request": request,
        "mesa_id": mesa if mesa_obj else None,
        "mesa_nombre": mesa_obj.nombre if mesa_obj else None,
    })


# ============================================================================
# API PUBLICA (cliente, sin login)
# ============================================================================
@router.get("/api/cliente/carta")
def carta_publica(db: Session = Depends(get_db)):
    """Carta visible para el cliente: productos activos por categoria."""
    productos = db.scalars(
        select(Producto).where(Producto.activo.is_(True))
        .order_by(Producto.nombre)).all()
    cats = {c.id: c.nombre for c in db.scalars(select(Categoria)).all()}
    items = [{
        "id": p.id, "nombre": p.nombre,
        "precio": float(p.precio_venta),
        "categoria": cats.get(p.categoria_id, "General"),
    } for p in productos]
    return {"productos": items}


@router.get("/api/cliente/mesas")
def mesas_publicas(db: Session = Depends(get_db)):
    """Mesas que el cliente puede elegir para un pedido en mesa.

    Solo se ofrecen las mesas libres, agrupadas por zona, para que el comensal
    seleccione la suya si accedio sin un enlace de mesa especifico.
    """
    zonas = db.scalars(select(Zona).order_by(Zona.orden)).all()
    salida = []
    for z in zonas:
        mesas = [{"id": m.id, "nombre": m.nombre, "estado": m.estado}
                 for m in sorted(z.mesas, key=lambda x: x.nombre)]
        if mesas:
            salida.append({"zona": z.nombre, "mesas": mesas})
    return {"zonas": salida}


@router.post("/api/cliente/pedido")
async def crear_pedido_publico(request: Request, db: Session = Depends(get_db)):
    """El cliente crea un pedido (autoservicio o mesa)."""
    datos = await request.json()
    try:
        pedido = PedidoClienteService(db).crear_pedido(
            tipo=datos.get("tipo", "autoservicio"),
            items=datos.get("items", []),
            nombre_cliente=datos.get("nombre_cliente", ""),
            mesa_id=datos.get("mesa_id"),
            observacion=datos.get("observacion", ""))
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "pedido_id": pedido.id, "total": float(pedido.total),
            "estado": pedido.estado,
            "mensaje": ("Tu pedido fue enviado a caja. Paga al recoger."
                        if pedido.tipo == "autoservicio"
                        else "Tu pedido fue enviado. Un mesero lo confirmara.")}


@router.get("/api/cliente/pedido/{pedido_id}")
def estado_pedido_publico(pedido_id: int, db: Session = Depends(get_db)):
    """El cliente consulta el estado de su pedido."""
    pedido = PedidoClienteService(db).obtener(pedido_id)
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    return {"pedido_id": pedido.id, "estado": pedido.estado,
            "tipo": pedido.tipo, "total": float(pedido.total),
            "motivo_rechazo": pedido.motivo_rechazo}


# ============================================================================
# API DE GESTION (personal con sesion)
# ============================================================================
def _exigir_sesion(request: Request):
    if not request.session.get("usuario_id"):
        raise HTTPException(401, "Requiere iniciar sesion")


@router.get("/api/cliente/pendientes")
def listar_pendientes(request: Request, tipo: str = None,
                      db: Session = Depends(get_db)):
    """Personal: lista pedidos pendientes (opcional filtrar por tipo)."""
    _exigir_sesion(request)
    pedidos = PedidoClienteService(db).listar_pendientes(tipo=tipo)
    salida = []
    for p in pedidos:
        salida.append({
            "id": p.id, "tipo": p.tipo, "nombre_cliente": p.nombre_cliente,
            "mesa_id": p.mesa_id, "total": float(p.total),
            "creado": p.creado.isoformat() if p.creado else None,
            "lineas": [{"producto": l.producto.nombre if l.producto else "?",
                        "cantidad": float(l.cantidad),
                        "nota": l.nota} for l in p.lineas],
        })
    return {"pedidos": salida}


@router.post("/api/cliente/pedido/{pedido_id}/aceptar")
def aceptar_pedido(pedido_id: int, request: Request,
                   db: Session = Depends(get_db)):
    """Mesero: acepta un pedido de mesa (genera la comanda/venta)."""
    _exigir_sesion(request)
    try:
        pedido = PedidoClienteService(db).aceptar_pedido(
            pedido_id, usuario_id=request.session.get("usuario_id"))
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "venta_id": pedido.venta_id}


@router.post("/api/cliente/pedido/{pedido_id}/rechazar")
async def rechazar_pedido(pedido_id: int, request: Request,
                          db: Session = Depends(get_db)):
    """Mesero: rechaza un pedido de mesa."""
    _exigir_sesion(request)
    try:
        datos = await request.json()
    except Exception:
        datos = {}
    try:
        PedidoClienteService(db).rechazar_pedido(
            pedido_id, motivo=datos.get("motivo", ""))
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.post("/api/cliente/pedido/{pedido_id}/cobrar")
def cobrar_pedido(pedido_id: int, request: Request,
                  db: Session = Depends(get_db)):
    """Caja: genera la venta de un autoservicio para cobrarla."""
    _exigir_sesion(request)
    try:
        venta = PedidoClienteService(db).cobrar_autoservicio(
            pedido_id, usuario_id=request.session.get("usuario_id"))
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "venta_id": venta.id,
            "mensaje": "Venta generada. Cobra en caja con el flujo normal."}
