"""Servicio de Produccion.

Cubre recetas con costeo teorico, ejecucion de ordenes que pasan por el
kardex, merma trazable, aprovechables que abaratan el producto principal, y
anulacion con reversion de inventario.

Antes, `consumir_receta` restaba existencias a mano y recalculaba el costo por
su cuenta: era la cuarta implementacion distinta del movimiento de inventario,
y el consumo de produccion no aparecia en el kardex con saldos.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.inventario.services import InventarioService
from app.models import (
    hora_colombia,
    ConsumoProduccion, MovimientoInventario, OrdenProduccion, Producto,
    Receta, RecetaDetalle,
)

logger = logging.getLogger(__name__)

CERO = Decimal("0")
CENTAVO = Decimal("0.01")


class ProduccionService:
    def __init__(self, db: Session):
        self.db = db
        self.inv = InventarioService(db)
        self.logger = logger

    # ==================================================================
    # RECETAS
    # ==================================================================
    def crear_receta(self, producto_id: int, *, rendimiento: Decimal = Decimal("1"),
                     tipo_receta: str = "produccion",
                     instrucciones: Optional[str] = None) -> Receta:
        producto = self.db.get(Producto, producto_id)
        if not producto:
            raise ValueError(f"Producto {producto_id} no existe")
        if rendimiento <= 0:
            raise ValueError("El rendimiento debe ser mayor que cero")
        if tipo_receta not in ("produccion", "venta"):
            raise ValueError("tipo_receta debe ser 'produccion' o 'venta'")
        if self.db.scalar(select(Receta).where(Receta.producto_id == producto_id)):
            raise ValueError(f"El producto '{producto.nombre}' ya tiene receta")

        receta = Receta(producto_id=producto_id, rendimiento=rendimiento,
                        tipo_receta=tipo_receta, instrucciones=instrucciones)
        self.db.add(receta)
        self.db.flush()
        return receta

    def agregar_insumo(self, receta_id: int, insumo_id: int, cantidad: Decimal, *,
                       merma_porcentaje: Decimal = CERO) -> RecetaDetalle:
        receta = self.db.get(Receta, receta_id)
        if not receta:
            raise ValueError(f"Receta {receta_id} no existe")
        insumo = self.db.get(Producto, insumo_id)
        if not insumo:
            raise ValueError(f"Insumo {insumo_id} no existe")
        if insumo_id == receta.producto_id:
            raise ValueError("Un producto no puede ser insumo de su propia receta")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        if merma_porcentaje < 0:
            raise ValueError("La merma no puede ser negativa")

        detalle = RecetaDetalle(
            receta_id=receta_id, insumo_id=insumo_id, cantidad=cantidad,
            merma_porcentaje=merma_porcentaje, rol="insumo")
        self.db.add(detalle)
        self.db.flush()
        return detalle

    def agregar_aprovechable(self, receta_id: int, producto_id: int,
                             cantidad: Decimal, valor_unitario: Decimal) -> RecetaDetalle:
        """Registra un subproducto que la produccion genera y abarata el principal."""
        receta = self.db.get(Receta, receta_id)
        if not receta:
            raise ValueError(f"Receta {receta_id} no existe")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        if valor_unitario < 0:
            raise ValueError("El valor no puede ser negativo")

        detalle = RecetaDetalle(
            receta_id=receta_id, insumo_id=producto_id, cantidad=cantidad,
            rol="aprovechable", valor_aprovechable=valor_unitario)
        self.db.add(detalle)
        self.db.flush()
        return detalle

    # ==================================================================
    # COSTEO TEORICO
    # ==================================================================
    def costear_receta(self, receta_id: int, *, lotes: Decimal = Decimal("1")) -> dict:
        """Costo teorico de producir `lotes` de la receta, con el costo actual.

        Antes no existia: no se podia saber el costo de un elaborado hasta
        ejecutar la produccion.
        """
        receta = self.db.get(Receta, receta_id)
        if not receta:
            raise ValueError(f"Receta {receta_id} no existe")

        costo_insumos = CERO
        valor_aprovechables = CERO
        lineas = []

        for d in receta.detalles:
            producto = self.db.get(Producto, d.insumo_id)
            nombre = producto.nombre if producto else f"#{d.insumo_id}"

            if d.rol == "aprovechable":
                cantidad = d.cantidad * lotes
                valor = (cantidad * (d.valor_aprovechable or CERO))
                valor_aprovechables += valor
                lineas.append({
                    "producto": nombre, "rol": "aprovechable",
                    "cantidad": cantidad, "costo_unitario": d.valor_aprovechable,
                    "costo_total": valor,
                })
            else:
                merma = Decimal("1") + (d.merma_porcentaje or CERO) / Decimal("100")
                cantidad = d.cantidad * lotes * merma
                costo_unit = producto.costo if producto else CERO
                total = cantidad * costo_unit
                costo_insumos += total
                lineas.append({
                    "producto": nombre, "rol": "insumo",
                    "cantidad": cantidad.quantize(Decimal("0.001")),
                    "costo_unitario": costo_unit, "costo_total": total.quantize(CENTAVO),
                })

        producido = (receta.rendimiento or Decimal("1")) * lotes
        costo_neto = costo_insumos - valor_aprovechables
        costo_unitario = (costo_neto / producido).quantize(CENTAVO) if producido > 0 else CERO

        return {
            "receta_id": receta.id,
            "producto": receta.producto.nombre if receta.producto else None,
            "lotes": lotes,
            "unidades": producido,
            "costo_insumos": costo_insumos.quantize(CENTAVO),
            "valor_aprovechables": valor_aprovechables.quantize(CENTAVO),
            "costo_neto": costo_neto.quantize(CENTAVO),
            "costo_unitario": costo_unitario,
            "lineas": lineas,
        }

    def recalcular_costo_producto(self, producto_id: int) -> Decimal:
        """Recalcula el costo unitario de un producto con receta y lo guarda."""
        receta = self.db.scalar(select(Receta).where(Receta.producto_id == producto_id))
        if not receta:
            return CERO
        c = self.costear_receta(receta.id)
        costo_unitario = c["costo_unitario"]
        prod = self.db.get(Producto, producto_id)
        if prod:
            prod.costo = costo_unitario
            self.db.flush()
        return costo_unitario

    def recalcular_todos_los_costos(self) -> int:
        """Recalcula en cascada los costos de todas las recetas registradas."""
        recetas = self.db.scalars(select(Receta)).all()
        if not recetas:
            return 0
        actualizados = 0
        for _ in range(3):
            for r in recetas:
                if r.producto_id:
                    self.recalcular_costo_producto(r.producto_id)
                    actualizados += 1
        return actualizados

    # ==================================================================
    # EJECUCION
    # ==================================================================
    def ejecutar(self, receta_id: int, lotes: Decimal, *, empresa_id: int = 1,
                 usuario_id: Optional[int] = None, bodega_id: Optional[int] = None,
                 observaciones: Optional[str] = None) -> OrdenProduccion:
        """Ejecuta una produccion: consume insumos, genera el producto y los
        aprovechables, todo a traves del kardex.
        """
        receta = self.db.get(Receta, receta_id)
        if not receta:
            raise ValueError(f"Receta {receta_id} no existe")
        if receta.tipo_receta != "produccion":
            raise ValueError("Solo se ejecutan recetas de tipo 'produccion'")
        if lotes <= 0:
            raise ValueError("Los lotes deben ser mayores que cero")
        if not receta.detalles:
            raise ValueError("La receta no tiene insumos")

        producto_final = self.db.get(Producto, receta.producto_id)
        if not producto_final:
            raise ValueError("El producto de la receta no existe")

        if bodega_id is None:
            bodega_id = self.inv.bodega_principal(empresa_id).id

        insumos = [d for d in receta.detalles if d.rol == "insumo"]
        aprovechables = [d for d in receta.detalles if d.rol == "aprovechable"]

        # 1. Verificar existencias ANTES de mover nada
        requerimientos = []
        for d in insumos:
            producto = self.db.get(Producto, d.insumo_id)
            merma_factor = Decimal("1") + (d.merma_porcentaje or CERO) / Decimal("100")
            cantidad_base = d.cantidad * lotes
            cantidad_total = cantidad_base * merma_factor
            if not producto:
                raise ValueError(f"Insumo #{d.insumo_id} no existe")
            if (producto.existencias or CERO) < cantidad_total:
                raise ValueError(
                    f"Inventario insuficiente de '{producto.nombre}': "
                    f"requiere {cantidad_total}, hay {producto.existencias or CERO}")
            requerimientos.append((producto, d, cantidad_base, cantidad_total))

        producido = (receta.rendimiento or Decimal("1")) * lotes

        orden = OrdenProduccion(
            empresa_id=empresa_id, receta_id=receta.id,
            numero=self._consecutivo(), lotes=lotes,
            unidades_producidas=producido, bodega_id=bodega_id,
            usuario_id=usuario_id, observaciones=observaciones,
            estado="confirmada",
        )
        self.db.add(orden)
        self.db.flush()

        # 2. Consumir insumos por el kardex
        costo_insumos = CERO
        merma_valor = CERO
        for producto, d, cantidad_base, cantidad_total in requerimientos:
            costo_unit = producto.costo or CERO
            costo_linea = cantidad_total * costo_unit
            costo_insumos += costo_linea
            merma_cant = cantidad_total - cantidad_base
            merma_valor += merma_cant * costo_unit

            self.inv.registrar_movimiento(
                producto_id=producto.id, tipo="consumo_receta",
                cantidad=cantidad_total, bodega_id=bodega_id,
                referencia=orden.numero, usuario_id=usuario_id,
                empresa_id=empresa_id, permitir_negativo=False)

            self.db.add(ConsumoProduccion(
                orden_id=orden.id, producto_id=producto.id, rol="insumo",
                cantidad_base=cantidad_base, cantidad_merma=merma_cant,
                cantidad_total=cantidad_total, costo_unitario=costo_unit,
                costo_total=costo_linea.quantize(CENTAVO)))

        # 3. Ingresar aprovechables (abaratan el principal)
        valor_aprovechables = CERO
        for d in aprovechables:
            producto = self.db.get(Producto, d.insumo_id)
            if not producto:
                continue
            cantidad = d.cantidad * lotes
            valor_unit = d.valor_aprovechable or CERO
            valor_total = cantidad * valor_unit
            valor_aprovechables += valor_total

            self.inv.registrar_movimiento(
                producto_id=producto.id, tipo="produccion_entrada",
                cantidad=cantidad, costo_unitario=valor_unit, bodega_id=bodega_id,
                referencia=f"{orden.numero}/APR", usuario_id=usuario_id,
                empresa_id=empresa_id)

            self.db.add(ConsumoProduccion(
                orden_id=orden.id, producto_id=producto.id, rol="aprovechable",
                cantidad_base=cantidad, cantidad_total=cantidad,
                costo_unitario=valor_unit, costo_total=valor_total.quantize(CENTAVO)))

        # 4. Costo del producto final (neto de aprovechables)
        costo_neto = costo_insumos - valor_aprovechables
        costo_unitario = (costo_neto / producido).quantize(CENTAVO) if producido > 0 else CERO

        self.inv.registrar_movimiento(
            producto_id=producto_final.id, tipo="produccion_entrada",
            cantidad=producido, costo_unitario=costo_unitario, bodega_id=bodega_id,
            referencia=orden.numero, usuario_id=usuario_id, empresa_id=empresa_id)

        orden.costo_insumos = costo_insumos.quantize(CENTAVO)
        orden.valor_aprovechables = valor_aprovechables.quantize(CENTAVO)
        orden.costo_total = costo_neto.quantize(CENTAVO)
        orden.costo_unitario = costo_unitario
        orden.merma_valor = merma_valor.quantize(CENTAVO)

        self.db.flush()
        self.logger.info("Produccion %s: %s unidades de '%s' a $%s c/u",
                         orden.numero, producido, producto_final.nombre, costo_unitario)
        return orden

    def _consecutivo(self) -> str:
        total = self.db.scalar(select(func.count(OrdenProduccion.id))) or 0
        return f"OP-{total + 1:05d}"

    # ==================================================================
    # ANULACION
    # ==================================================================
    def anular(self, orden_id: int, motivo: str, *,
               usuario_id: Optional[int] = None) -> OrdenProduccion:
        """Anula una produccion revirtiendo insumos, aprovechables y producto.

        Antes no existia: una produccion mal ejecutada consumia insumos sin
        retorno posible.
        """
        if not (motivo or "").strip():
            raise ValueError("Debe indicar el motivo de anulacion")

        orden = self.db.get(OrdenProduccion, orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no existe")
        if orden.estado == "anulada":
            raise ValueError("La orden ya esta anulada")

        producto_final = self.db.get(Producto, orden.receta.producto_id)
        bodega_id = orden.bodega_id or self.inv.bodega_principal(orden.empresa_id).id

        # 1. El producto final debe seguir disponible para poder retirarlo
        if producto_final and (producto_final.existencias or CERO) < orden.unidades_producidas:
            raise ValueError(
                f"No se puede anular: de '{producto_final.nombre}' quedan "
                f"{producto_final.existencias or CERO} y la produccion genero "
                f"{orden.unidades_producidas}. Parte ya se consumio.")

        ref = f"ANULA-{orden.numero}"
        consumos = self.db.scalars(
            select(ConsumoProduccion).where(ConsumoProduccion.orden_id == orden.id)
        ).all()

        # 2. Retirar el producto final
        if producto_final:
            self.inv.registrar_movimiento(
                producto_id=producto_final.id, tipo="ajuste_negativo",
                cantidad=orden.unidades_producidas, bodega_id=bodega_id,
                referencia=ref, usuario_id=usuario_id, empresa_id=orden.empresa_id,
                observacion=f"Anulacion produccion {orden.numero}", permitir_negativo=False)

        # 3. Retirar aprovechables y devolver insumos
        for c in consumos:
            if c.rol == "aprovechable":
                self.inv.registrar_movimiento(
                    producto_id=c.producto_id, tipo="ajuste_negativo",
                    cantidad=c.cantidad_total, bodega_id=bodega_id, referencia=ref,
                    usuario_id=usuario_id, empresa_id=orden.empresa_id,
                    permitir_negativo=False)
            elif c.rol == "insumo":
                self.inv.registrar_movimiento(
                    producto_id=c.producto_id, tipo="ajuste_positivo",
                    cantidad=c.cantidad_total, costo_unitario=c.costo_unitario,
                    bodega_id=bodega_id, referencia=ref, usuario_id=usuario_id,
                    empresa_id=orden.empresa_id)

        orden.estado = "anulada"
        orden.motivo_anulacion = motivo.strip()
        orden.fecha_anulacion = hora_colombia()
        self.db.flush()
        self.logger.info("Produccion %s anulada: %s", orden.numero, motivo.strip())
        return orden

    # ==================================================================
    # CONSULTAS
    # ==================================================================
    def listar_ordenes(self, *, empresa_id: int = 1, estado: Optional[str] = None,
                       limit: int = 50) -> list[OrdenProduccion]:
        q = select(OrdenProduccion).where(OrdenProduccion.empresa_id == empresa_id)
        if estado:
            q = q.where(OrdenProduccion.estado == estado)
        return self.db.scalars(
            q.order_by(OrdenProduccion.fecha.desc()).limit(limit)).all()

    def indicadores(self, *, empresa_id: int = 1) -> dict:
        ordenes = self.db.scalars(
            select(OrdenProduccion).where(
                OrdenProduccion.empresa_id == empresa_id,
                OrdenProduccion.estado == "confirmada")
        ).all()
        costo_total = sum((o.costo_total or CERO for o in ordenes), CERO)
        merma_total = sum((o.merma_valor or CERO for o in ordenes), CERO)
        aprovechado = sum((o.valor_aprovechables or CERO for o in ordenes), CERO)
        return {
            "ordenes": len(ordenes),
            "costo_producido": costo_total.quantize(CENTAVO),
            "merma_valor": merma_total.quantize(CENTAVO),
            "valor_aprovechado": aprovechado.quantize(CENTAVO),
            "recetas_activas": self.db.scalar(
                select(func.count(Receta.id)).where(Receta.activa == True)) or 0,  # noqa: E712
        }
