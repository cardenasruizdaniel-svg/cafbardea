"""Servicio de pedidos de cliente (app de cliente).

Gestiona el ciclo de vida del pedido que hace el propio cliente, antes de que se
convierta en una venta formal:

  - autoservicio: el cliente ordena con su nombre. El pedido llega a caja como
    comanda pendiente. Cuando el cajero lo cobra, se genera la venta y se marca
    entregado. El cliente paga en caja al recoger.

  - mesa: el cliente ordena desde una mesa. Queda 'pendiente' hasta que un mesero
    lo acepte (se genera la venta/comanda en esa mesa) o lo rechace.

El pedido vive en su propia tabla; NO toca inventario ni ventas hasta que se
acepta o se cobra. Asi, un pedido rechazado no deja rastro contable.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (Mesa, PedidoCliente, PedidoClienteLinea, Producto,
                        hora_colombia)

logger = logging.getLogger("pedidos_cliente")


class PedidoClienteService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Creacion (desde la app de cliente, sin login)
    # ------------------------------------------------------------------
    def crear_pedido(self, *, tipo: str, items: list[dict],
                     nombre_cliente: str = "", mesa_id: Optional[int] = None,
                     observacion: str = "", empresa_id: int = 1) -> PedidoCliente:
        """Crea un pedido de cliente.

        items: lista de {"producto_id": int, "cantidad": number, "nota": str?}
        tipo: 'autoservicio' o 'mesa'.
        """
        if tipo not in ("autoservicio", "mesa"):
            raise ValueError("Tipo de pedido invalido")
        if not items:
            raise ValueError("El pedido debe tener al menos un producto")
        if tipo == "autoservicio" and not nombre_cliente.strip():
            raise ValueError("El autoservicio requiere el nombre del cliente")
        if tipo == "mesa":
            if not mesa_id:
                raise ValueError("El pedido de mesa requiere una mesa")
            if not self.db.get(Mesa, mesa_id):
                raise ValueError("La mesa no existe")

        pedido = PedidoCliente(
            empresa_id=empresa_id, tipo=tipo,
            nombre_cliente=nombre_cliente.strip(), mesa_id=mesa_id,
            estado="pendiente", observacion=observacion.strip() or None,
            creado=hora_colombia())
        self.db.add(pedido)
        self.db.flush()

        total = Decimal("0")
        for item in items:
            prod = self.db.get(Producto, int(item["producto_id"]))
            if not prod or not prod.activo:
                raise ValueError(f"Producto {item.get('producto_id')} no disponible")
            cantidad = Decimal(str(item.get("cantidad", 1)))
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a cero")
            precio = Decimal(str(prod.precio_venta))
            total += precio * cantidad
            self.db.add(PedidoClienteLinea(
                pedido_id=pedido.id, producto_id=prod.id, cantidad=cantidad,
                precio_unitario=precio, nota=(item.get("nota") or "").strip() or None))

        pedido.total = total
        self.db.flush()
        return pedido

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def listar_pendientes(self, tipo: Optional[str] = None) -> list[PedidoCliente]:
        q = select(PedidoCliente).where(PedidoCliente.estado == "pendiente")
        if tipo:
            q = q.where(PedidoCliente.tipo == tipo)
        return self.db.scalars(q.order_by(PedidoCliente.creado)).all()

    def obtener(self, pedido_id: int) -> Optional[PedidoCliente]:
        return self.db.get(PedidoCliente, pedido_id)

    # ------------------------------------------------------------------
    # Transiciones
    # ------------------------------------------------------------------
    def aceptar_pedido(self, pedido_id: int, usuario_id: Optional[int] = None) -> PedidoCliente:
        """El mesero acepta un pedido de mesa: genera la venta/comanda."""
        pedido = self._pedido_pendiente(pedido_id)
        if pedido.tipo != "mesa":
            raise ValueError("Solo los pedidos de mesa se aceptan con mesero")
        venta = self._materializar_venta(pedido, usuario_id=usuario_id)
        pedido.estado = "aceptado"
        pedido.atendido = hora_colombia()
        pedido.venta_id = venta.id
        self.db.flush()
        return pedido

    def rechazar_pedido(self, pedido_id: int, motivo: str = "") -> PedidoCliente:
        """El mesero rechaza un pedido de mesa."""
        pedido = self._pedido_pendiente(pedido_id)
        pedido.estado = "rechazado"
        pedido.atendido = hora_colombia()
        pedido.motivo_rechazo = (motivo or "").strip() or "Sin motivo"
        self.db.flush()
        return pedido

    def cobrar_autoservicio(self, pedido_id: int, usuario_id: Optional[int] = None):
        """En caja: genera la venta del autoservicio para cobrarla.

        Devuelve la venta creada (en estado 'abierta') para que caja la cobre con
        el flujo normal de pago. Marca el pedido como entregado.
        """
        pedido = self._pedido_pendiente(pedido_id)
        if pedido.tipo != "autoservicio":
            raise ValueError("Solo los pedidos de autoservicio se cobran en caja")
        venta = self._materializar_venta(pedido, usuario_id=usuario_id)
        pedido.estado = "entregado"
        pedido.atendido = hora_colombia()
        pedido.venta_id = venta.id
        self.db.flush()
        return venta

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _pedido_pendiente(self, pedido_id: int) -> PedidoCliente:
        pedido = self.db.get(PedidoCliente, pedido_id)
        if not pedido:
            raise ValueError("Pedido no encontrado")
        if pedido.estado != "pendiente":
            raise ValueError(f"El pedido ya fue {pedido.estado}")
        return pedido

    def _materializar_venta(self, pedido: PedidoCliente,
                            usuario_id: Optional[int] = None):
        """Convierte el pedido en una venta abierta usando VentaService."""
        from app.domains.ventas.services import VentaService
        from app.domains.ventas.schemas import (VentaCreate, DetalleVentaCreate,
                                                 TipoVenta)
        detalles = [
            DetalleVentaCreate(producto_id=l.producto_id, cantidad=l.cantidad,
                               precio=l.precio_unitario)
            for l in pedido.lineas]
        if pedido.tipo == "mesa":
            venta_data = VentaCreate(tipo_venta=TipoVenta.EN_MESA,
                                     mesa_id=pedido.mesa_id, detalles=detalles)
        else:
            venta_data = VentaCreate(tipo_venta=TipoVenta.MOSTRADOR,
                                     detalles=detalles)
        venta = VentaService(self.db).crear_venta(
            venta_data, usuario_id=usuario_id, empresa_id=pedido.empresa_id)
        # Dejar rastro del nombre del cliente en la observacion de la venta.
        if pedido.nombre_cliente:
            venta.observacion = ((venta.observacion or "") +
                                 f" · Cliente: {pedido.nombre_cliente}").strip()
        return venta
