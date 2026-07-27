"""Servicio de Compras y aprovisionamiento.

Cubre el ciclo completo: solicitud -> cotizaciones -> orden -> recepcion ->
factura de compra, mas la anulacion con reversion de inventario.

Antes de este modulo, una compra era una fila plana con UN producto, sin
desglose fiscal, sin estado y sin posibilidad de anulacion: un registro
equivocado contaminaba el costo promedio de forma permanente.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    hora_colombia,
    Compra, Cotizacion, DetalleCompra, DetalleCotizacion, DetalleOrden,
    DetalleRecepcion, DetalleSolicitud, Empresa, OrdenCompra, Producto,
    Proveedor, Recepcion, SolicitudCompra,
)

logger = logging.getLogger(__name__)

CERO = Decimal("0")
CENTAVO = Decimal("0.01")


class ComprasService:
    """Logica de negocio de compras."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    # ------------------------------------------------------------------
    # Consecutivos
    # ------------------------------------------------------------------
    def _consecutivo(self, modelo, prefijo: str) -> str:
        """Genera el siguiente numero con formato PREFIJO-00001."""
        total = self.db.scalar(select(func.count(modelo.id))) or 0
        return f"{prefijo}-{total + 1:05d}"

    # ------------------------------------------------------------------
    # Validaciones comunes
    # ------------------------------------------------------------------
    def _validar_proveedor(self, proveedor_id: int) -> Proveedor:
        proveedor = self.db.get(Proveedor, proveedor_id)
        if not proveedor:
            raise ValueError(f"Proveedor {proveedor_id} no existe")
        if not proveedor.activo:
            raise ValueError(f"El proveedor '{proveedor.nombre}' esta inactivo")
        return proveedor

    def _validar_producto(self, producto_id: int) -> Producto:
        producto = self.db.get(Producto, producto_id)
        if not producto:
            raise ValueError(f"Producto {producto_id} no existe")
        if not producto.activo:
            raise ValueError(f"El producto '{producto.nombre}' esta inactivo")
        return producto

    @staticmethod
    def _validar_lineas(lineas: Iterable[dict]) -> list[dict]:
        lineas = list(lineas or [])
        if not lineas:
            raise ValueError("Debe incluir al menos una linea")
        for ln in lineas:
            if Decimal(str(ln.get("cantidad", 0))) <= 0:
                raise ValueError("La cantidad debe ser mayor que cero")
            if Decimal(str(ln.get("costo_unitario", 0))) < 0:
                raise ValueError("El costo unitario no puede ser negativo")
        return lineas

    # ==================================================================
    # 1. SOLICITUDES
    # ==================================================================
    def crear_solicitud(self, lineas: Iterable[dict], *, empresa_id: int = 1,
                        solicitante_id: Optional[int] = None,
                        justificacion: Optional[str] = None) -> SolicitudCompra:
        lineas = list(lineas or [])
        if not lineas:
            raise ValueError("La solicitud debe incluir al menos un producto")

        solicitud = SolicitudCompra(
            empresa_id=empresa_id,
            numero=self._consecutivo(SolicitudCompra, "SC"),
            solicitante_id=solicitante_id,
            justificacion=justificacion,
        )
        self.db.add(solicitud)
        self.db.flush()

        for ln in lineas:
            producto = self._validar_producto(int(ln["producto_id"]))
            cantidad = Decimal(str(ln["cantidad"]))
            if cantidad <= 0:
                raise ValueError(f"Cantidad invalida para '{producto.nombre}'")
            self.db.add(DetalleSolicitud(
                solicitud_id=solicitud.id, producto_id=producto.id,
                cantidad=cantidad, observacion=ln.get("observacion")))

        self.db.flush()
        self.logger.info("Solicitud %s creada", solicitud.numero)
        return solicitud

    def sugerir_solicitud(self, *, empresa_id: int = 1,
                          solicitante_id: Optional[int] = None) -> Optional[SolicitudCompra]:
        """Genera una solicitud con los productos bajo el minimo.

        Repone hasta el doble del stock minimo, o 1 unidad si no hay minimo.
        """
        productos = self.db.scalars(
            select(Producto).where(
                Producto.activo == True,  # noqa: E712
                Producto.stock_minimo > 0,
                Producto.existencias <= Producto.stock_minimo,
            )
        ).all()
        if not productos:
            return None

        lineas = []
        for p in productos:
            objetivo = (p.stock_minimo or CERO) * 2
            faltante = objetivo - (p.existencias or CERO)
            if faltante <= 0:
                faltante = p.stock_minimo or Decimal("1")
            lineas.append({"producto_id": p.id, "cantidad": faltante,
                           "observacion": "Reposicion automatica por stock bajo minimo"})

        return self.crear_solicitud(
            lineas, empresa_id=empresa_id, solicitante_id=solicitante_id,
            justificacion="Generada automaticamente a partir de stock bajo minimo")

    def aprobar_solicitud(self, solicitud_id: int, *, usuario_id: Optional[int] = None
                          ) -> SolicitudCompra:
        solicitud = self.db.get(SolicitudCompra, solicitud_id)
        if not solicitud:
            raise ValueError(f"Solicitud {solicitud_id} no existe")
        if solicitud.estado != "pendiente":
            raise ValueError(f"La solicitud esta en estado {solicitud.estado}")
        solicitud.estado = "aprobada"
        solicitud.aprobada_por_id = usuario_id
        solicitud.fecha_aprobacion = hora_colombia()
        self.db.flush()
        return solicitud

    def rechazar_solicitud(self, solicitud_id: int, motivo: str, *,
                           usuario_id: Optional[int] = None) -> SolicitudCompra:
        if not (motivo or "").strip():
            raise ValueError("Debe indicar el motivo del rechazo")
        solicitud = self.db.get(SolicitudCompra, solicitud_id)
        if not solicitud:
            raise ValueError(f"Solicitud {solicitud_id} no existe")
        if solicitud.estado != "pendiente":
            raise ValueError(f"La solicitud esta en estado {solicitud.estado}")
        solicitud.estado = "rechazada"
        solicitud.motivo_rechazo = motivo.strip()
        solicitud.aprobada_por_id = usuario_id
        solicitud.fecha_aprobacion = hora_colombia()
        self.db.flush()
        return solicitud

    # ==================================================================
    # 2. COTIZACIONES
    # ==================================================================
    def registrar_cotizacion(self, proveedor_id: int, lineas: Iterable[dict], *,
                             solicitud_id: Optional[int] = None,
                             empresa_id: int = 1, dias_entrega: int = 0,
                             validez_dias: int = 15,
                             forma_pago: str = "contado",
                             observaciones: Optional[str] = None) -> Cotizacion:
        proveedor = self._validar_proveedor(proveedor_id)
        lineas = self._validar_lineas(lineas)

        if solicitud_id:
            solicitud = self.db.get(SolicitudCompra, solicitud_id)
            if not solicitud:
                raise ValueError(f"Solicitud {solicitud_id} no existe")
            if solicitud.estado not in ("aprobada", "cotizada"):
                raise ValueError(
                    f"La solicitud debe estar aprobada (estado actual: {solicitud.estado})")
            solicitud.estado = "cotizada"

        cotizacion = Cotizacion(
            empresa_id=empresa_id, solicitud_id=solicitud_id,
            proveedor_id=proveedor.id, numero=self._consecutivo(Cotizacion, "COT"),
            dias_entrega=dias_entrega, validez_dias=validez_dias,
            forma_pago=forma_pago, observaciones=observaciones,
        )
        self.db.add(cotizacion)
        self.db.flush()

        subtotal = iva_total = CERO
        for ln in lineas:
            producto = self._validar_producto(int(ln["producto_id"]))
            cantidad = Decimal(str(ln["cantidad"]))
            costo = Decimal(str(ln["costo_unitario"]))
            iva_pct = Decimal(str(ln.get("iva_porcentaje", producto.iva_porcentaje or 0)))

            neto = cantidad * costo
            subtotal += neto
            iva_total += neto * iva_pct / Decimal("100")

            self.db.add(DetalleCotizacion(
                cotizacion_id=cotizacion.id, producto_id=producto.id,
                cantidad=cantidad, costo_unitario=costo, iva_porcentaje=iva_pct))

        cotizacion.subtotal = subtotal.quantize(CENTAVO)
        cotizacion.iva = iva_total.quantize(CENTAVO)
        cotizacion.total = (subtotal + iva_total).quantize(CENTAVO)
        self.db.flush()
        self.logger.info("Cotizacion %s de %s por %s",
                         cotizacion.numero, proveedor.nombre, cotizacion.total)
        return cotizacion

    def comparar_cotizaciones(self, solicitud_id: int) -> list[dict]:
        """Compara las ofertas de una solicitud, de menor a mayor total."""
        cotizaciones = self.db.scalars(
            select(Cotizacion).where(Cotizacion.solicitud_id == solicitud_id)
        ).all()
        if not cotizaciones:
            return []

        mejor_total = min(c.total or CERO for c in cotizaciones)
        mejor_plazo = min(c.dias_entrega or 0 for c in cotizaciones)

        filas = []
        for c in cotizaciones:
            total = c.total or CERO
            diferencia = total - mejor_total
            filas.append({
                "cotizacion_id": c.id,
                "numero": c.numero,
                "proveedor_id": c.proveedor_id,
                "proveedor": c.proveedor.nombre if c.proveedor else None,
                "subtotal": c.subtotal,
                "iva": c.iva,
                "total": total,
                "dias_entrega": c.dias_entrega,
                "forma_pago": c.forma_pago,
                "estado": c.estado,
                "es_mas_economica": total == mejor_total,
                "es_mas_rapida": (c.dias_entrega or 0) == mejor_plazo,
                "diferencia_vs_mejor": diferencia.quantize(CENTAVO),
                "sobrecosto_porcentaje": (
                    (diferencia / mejor_total * Decimal("100")).quantize(CENTAVO)
                    if mejor_total > 0 else CERO),
            })
        return sorted(filas, key=lambda f: f["total"])

    def seleccionar_cotizacion(self, cotizacion_id: int) -> Cotizacion:
        """Marca una oferta como elegida y descarta las demas."""
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise ValueError(f"Cotizacion {cotizacion_id} no existe")

        if cotizacion.solicitud_id:
            hermanas = self.db.scalars(
                select(Cotizacion).where(
                    Cotizacion.solicitud_id == cotizacion.solicitud_id,
                    Cotizacion.id != cotizacion.id)
            ).all()
            for h in hermanas:
                h.estado = "descartada"

        cotizacion.estado = "seleccionada"
        self.db.flush()
        return cotizacion

    # ==================================================================
    # 3. ORDENES DE COMPRA
    # ==================================================================
    def crear_orden(self, proveedor_id: int, lineas: Iterable[dict], *,
                    empresa_id: int = 1, usuario_id: Optional[int] = None,
                    solicitud_id: Optional[int] = None,
                    cotizacion_id: Optional[int] = None,
                    fecha_entrega_esperada: Optional[date] = None,
                    forma_pago: str = "contado",
                    observaciones: Optional[str] = None) -> OrdenCompra:
        proveedor = self._validar_proveedor(proveedor_id)
        lineas = self._validar_lineas(lineas)

        orden = OrdenCompra(
            empresa_id=empresa_id, numero=self._consecutivo(OrdenCompra, "OC"),
            proveedor_id=proveedor.id, cotizacion_id=cotizacion_id,
            solicitud_id=solicitud_id, usuario_id=usuario_id,
            fecha_entrega_esperada=fecha_entrega_esperada,
            forma_pago=forma_pago, observaciones=observaciones,
        )
        self.db.add(orden)
        self.db.flush()

        subtotal = iva_total = CERO
        for ln in lineas:
            producto = self._validar_producto(int(ln["producto_id"]))
            cantidad = Decimal(str(ln["cantidad"]))
            costo = Decimal(str(ln["costo_unitario"]))
            iva_pct = Decimal(str(ln.get("iva_porcentaje", producto.iva_porcentaje or 0)))

            neto = cantidad * costo
            subtotal += neto
            iva_total += neto * iva_pct / Decimal("100")

            self.db.add(DetalleOrden(
                orden_id=orden.id, producto_id=producto.id, cantidad=cantidad,
                cantidad_recibida=CERO, costo_unitario=costo, iva_porcentaje=iva_pct))

        orden.subtotal = subtotal.quantize(CENTAVO)
        orden.iva = iva_total.quantize(CENTAVO)
        orden.total = (subtotal + iva_total).quantize(CENTAVO)

        if solicitud_id:
            solicitud = self.db.get(SolicitudCompra, solicitud_id)
            if solicitud:
                solicitud.estado = "ordenada"

        self.db.flush()
        self.logger.info("Orden %s a %s por %s", orden.numero, proveedor.nombre, orden.total)
        return orden

    def crear_orden_desde_cotizacion(self, cotizacion_id: int, *,
                                     usuario_id: Optional[int] = None,
                                     fecha_entrega_esperada: Optional[date] = None
                                     ) -> OrdenCompra:
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise ValueError(f"Cotizacion {cotizacion_id} no existe")
        if cotizacion.estado == "descartada":
            raise ValueError("No se puede ordenar sobre una cotizacion descartada")

        if cotizacion.estado != "seleccionada":
            self.seleccionar_cotizacion(cotizacion_id)

        lineas = [{"producto_id": d.producto_id, "cantidad": d.cantidad,
                   "costo_unitario": d.costo_unitario,
                   "iva_porcentaje": d.iva_porcentaje}
                  for d in cotizacion.detalles]

        return self.crear_orden(
            cotizacion.proveedor_id, lineas, empresa_id=cotizacion.empresa_id,
            usuario_id=usuario_id, solicitud_id=cotizacion.solicitud_id,
            cotizacion_id=cotizacion.id, forma_pago=cotizacion.forma_pago,
            fecha_entrega_esperada=fecha_entrega_esperada,
            observaciones=f"Generada desde cotizacion {cotizacion.numero}")

    def emitir_orden(self, orden_id: int) -> OrdenCompra:
        orden = self.db.get(OrdenCompra, orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no existe")
        if orden.estado != "borrador":
            raise ValueError(f"La orden esta en estado {orden.estado}")
        orden.estado = "emitida"
        self.db.flush()
        return orden

    def anular_orden(self, orden_id: int, motivo: str) -> OrdenCompra:
        if not (motivo or "").strip():
            raise ValueError("Debe indicar el motivo de anulacion")
        orden = self.db.get(OrdenCompra, orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no existe")
        if orden.estado in ("recibida", "cerrada"):
            raise ValueError("No se puede anular una orden ya recibida")
        recibido = sum((d.cantidad_recibida or CERO for d in orden.detalles), CERO)
        if recibido > 0:
            raise ValueError(
                "La orden tiene recepciones parciales; anule primero las compras asociadas")
        orden.estado = "anulada"
        orden.motivo_anulacion = motivo.strip()
        self.db.flush()
        return orden

    # ==================================================================
    # 4. RECEPCIONES
    # ==================================================================
    def recibir(self, orden_id: int, lineas: Iterable[dict], *,
                bodega_id: Optional[int] = None, remision: Optional[str] = None,
                usuario_id: Optional[int] = None,
                observaciones: Optional[str] = None) -> Recepcion:
        """Registra la entrada fisica de mercancia contra una orden.

        Admite recepciones parciales: la orden queda en 'parcial' hasta que
        todas las lineas se completen.
        """
        orden = self.db.get(OrdenCompra, orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no existe")
        if orden.estado not in ("emitida", "parcial"):
            raise ValueError(
                f"Solo se recibe sobre ordenes emitidas (estado actual: {orden.estado})")

        lineas = list(lineas or [])
        if not lineas:
            raise ValueError("Debe indicar al menos una linea a recibir")

        from app.domains.inventario.services import InventarioService
        inventario = InventarioService(self.db)
        if bodega_id is None:
            bodega_id = inventario.bodega_principal(orden.empresa_id).id

        recepcion = Recepcion(
            empresa_id=orden.empresa_id, numero=self._consecutivo(Recepcion, "REC"),
            orden_id=orden.id, bodega_id=bodega_id, remision=remision,
            usuario_id=usuario_id, observaciones=observaciones,
        )
        self.db.add(recepcion)
        self.db.flush()

        por_producto = {d.producto_id: d for d in orden.detalles}

        for ln in lineas:
            producto_id = int(ln["producto_id"])
            cantidad = Decimal(str(ln["cantidad"]))
            if cantidad <= 0:
                raise ValueError("La cantidad recibida debe ser mayor que cero")

            detalle = por_producto.get(producto_id)
            if not detalle:
                producto = self.db.get(Producto, producto_id)
                nombre = producto.nombre if producto else producto_id
                raise ValueError(f"El producto '{nombre}' no esta en la orden {orden.numero}")

            if cantidad > detalle.pendiente:
                producto = self.db.get(Producto, producto_id)
                raise ValueError(
                    f"No se puede recibir {cantidad} de '{producto.nombre}': "
                    f"quedan {detalle.pendiente} pendientes")

            costo = Decimal(str(ln.get("costo_unitario", detalle.costo_unitario)))
            lote_codigo = ln.get("lote_codigo")
            vencimiento = ln.get("fecha_vencimiento")

            self.db.add(DetalleRecepcion(
                recepcion_id=recepcion.id, producto_id=producto_id,
                cantidad=cantidad, costo_unitario=costo,
                lote_codigo=lote_codigo, fecha_vencimiento=vencimiento))

            detalle.cantidad_recibida = (detalle.cantidad_recibida or CERO) + cantidad

            # La entrada al inventario pasa por InventarioService: asi el
            # kardex y el costo promedio quedan coherentes.
            if lote_codigo:
                inventario.crear_lote(
                    producto_id, lote_codigo, cantidad, costo_unitario=costo,
                    fecha_vencimiento=vencimiento, bodega_id=bodega_id,
                    usuario_id=usuario_id, empresa_id=orden.empresa_id)
            else:
                inventario.registrar_movimiento(
                    producto_id=producto_id, tipo="compra", cantidad=cantidad,
                    costo_unitario=costo, bodega_id=bodega_id,
                    referencia=f"{orden.numero}/{recepcion.numero}",
                    usuario_id=usuario_id, empresa_id=orden.empresa_id)

        pendiente_total = sum((d.pendiente for d in orden.detalles), CERO)
        orden.estado = "recibida" if pendiente_total <= 0 else "parcial"

        self.db.flush()
        self.logger.info("Recepcion %s sobre orden %s (%s)",
                         recepcion.numero, orden.numero, orden.estado)
        return recepcion

    # ==================================================================
    # 5. FACTURA DE COMPRA
    # ==================================================================
    def crear_compra(self, proveedor_id: int, lineas: Iterable[dict], *,
                     empresa_id: int = 1, usuario_id: Optional[int] = None,
                     numero_documento: Optional[str] = None,
                     concepto: str = "Compra de mercancia",
                     fecha: Optional[date] = None,
                     forma_pago: str = "contado",
                     retencion_fuente: Decimal = CERO,
                     retencion_iva: Decimal = CERO,
                     orden_compra_id: Optional[int] = None,
                     bodega_id: Optional[int] = None,
                     observaciones: Optional[str] = None,
                     confirmar: bool = True) -> Compra:
        """Registra una factura de compra con varios items.

        Si `confirmar` es True, la mercancia entra al inventario de inmediato.
        En borrador no se mueve stock.
        """
        proveedor = self._validar_proveedor(proveedor_id)
        lineas = self._validar_lineas(lineas)

        if numero_documento:
            duplicada = self.db.scalar(
                select(Compra).where(
                    Compra.proveedor_id == proveedor_id,
                    Compra.numero_documento == numero_documento.strip(),
                    Compra.estado != "anulada")
            )
            if duplicada:
                raise ValueError(
                    f"Ya existe la factura {numero_documento} de '{proveedor.nombre}' "
                    f"(compra {duplicada.id})")

        compra = Compra(
            empresa_id=empresa_id, proveedor_id=proveedor.id, usuario_id=usuario_id,
            fecha=fecha or date.today(), concepto=concepto,
            numero_documento=(numero_documento or "").strip() or None,
            estado="borrador", forma_pago=forma_pago,
            orden_compra_id=orden_compra_id, bodega_id=bodega_id,
            observaciones=observaciones, valor=CERO,
            es_documento_soporte=not proveedor.obligado_facturar,
        )
        self.db.add(compra)
        self.db.flush()

        for ln in lineas:
            producto = self._validar_producto(int(ln["producto_id"]))
            iva_pct = ln.get("iva_porcentaje")
            if iva_pct is None:
                iva_pct = producto.iva_porcentaje or CERO
            self.db.add(DetalleCompra(
                compra_id=compra.id, producto_id=producto.id,
                cantidad=Decimal(str(ln["cantidad"])),
                costo_unitario=Decimal(str(ln["costo_unitario"])),
                descuento_porcentaje=Decimal(str(ln.get("descuento_porcentaje", 0))),
                iva_porcentaje=Decimal(str(iva_pct)),
                lote_codigo=ln.get("lote_codigo"),
                fecha_vencimiento=ln.get("fecha_vencimiento")))

        self.db.flush()
        self.db.refresh(compra)
        self._recalcular_compra(compra, retencion_fuente, retencion_iva)

        if forma_pago == "credito" and proveedor.dias_credito:
            from datetime import timedelta
            compra.fecha_vencimiento = compra.fecha + timedelta(days=proveedor.dias_credito)

        if confirmar:
            self.confirmar_compra(compra.id, usuario_id=usuario_id)

        self.db.flush()
        return compra

    def _recalcular_compra(self, compra: Compra, retencion_fuente: Decimal = None,
                           retencion_iva: Decimal = None) -> None:
        """Recalcula el desglose fiscal a partir de los detalles."""
        subtotal = sum((d.subtotal for d in compra.detalles), CERO)
        descuento = sum((d.valor_descuento for d in compra.detalles), CERO)
        iva = sum((d.valor_iva for d in compra.detalles), CERO)

        if retencion_fuente is not None:
            compra.retencion_fuente = Decimal(str(retencion_fuente))
        if retencion_iva is not None:
            compra.retencion_iva = Decimal(str(retencion_iva))

        compra.subtotal = subtotal.quantize(CENTAVO)
        compra.descuento = descuento.quantize(CENTAVO)
        compra.iva = iva.quantize(CENTAVO)
        compra.total = (subtotal + iva
                        - (compra.retencion_fuente or CERO)
                        - (compra.retencion_iva or CERO)).quantize(CENTAVO)
        # `valor` se conserva por compatibilidad con el modelo anterior
        compra.valor = compra.total

    def confirmar_compra(self, compra_id: int, *, usuario_id: Optional[int] = None) -> Compra:
        """Confirma la compra e ingresa la mercancia al inventario."""
        compra = self.db.get(Compra, compra_id)
        if not compra:
            raise ValueError(f"Compra {compra_id} no existe")
        if compra.estado == "confirmada":
            raise ValueError("La compra ya esta confirmada")
        if compra.estado == "anulada":
            raise ValueError("No se puede confirmar una compra anulada")
        if not compra.detalles:
            raise ValueError("La compra no tiene lineas")

        from app.domains.inventario.services import InventarioService
        inventario = InventarioService(self.db)
        bodega_id = compra.bodega_id or inventario.bodega_principal(compra.empresa_id).id

        referencia = compra.numero_documento or f"COMPRA-{compra.id}"
        for detalle in compra.detalles:
            if detalle.lote_codigo:
                inventario.crear_lote(
                    detalle.producto_id, detalle.lote_codigo, detalle.cantidad,
                    costo_unitario=detalle.costo_unitario,
                    fecha_vencimiento=detalle.fecha_vencimiento,
                    bodega_id=bodega_id, usuario_id=usuario_id or compra.usuario_id,
                    empresa_id=compra.empresa_id)
            else:
                inventario.registrar_movimiento(
                    producto_id=detalle.producto_id, tipo="compra",
                    cantidad=detalle.cantidad, costo_unitario=detalle.costo_unitario,
                    bodega_id=bodega_id, referencia=referencia,
                    usuario_id=usuario_id or compra.usuario_id,
                    empresa_id=compra.empresa_id)

        compra.estado = "confirmada"
        compra.bodega_id = bodega_id
        self.db.flush()
        self.logger.info("Compra %s confirmada por %s", compra.id, compra.total)
        return compra

    def anular_compra(self, compra_id: int, motivo: str, *,
                      usuario_id: Optional[int] = None) -> Compra:
        """Anula una compra revirtiendo stock y costo promedio.

        Antes no existia: una compra mal registrada contaminaba el costo
        promedio del producto de forma permanente, sin manera de deshacerlo.

        La reversion usa el costo promedio VIGENTE, no el de la compra, para
        que el valor del inventario quede consistente.
        """
        if not (motivo or "").strip():
            raise ValueError("Debe indicar el motivo de anulacion")

        compra = self.db.get(Compra, compra_id)
        if not compra:
            raise ValueError(f"Compra {compra_id} no existe")
        if compra.estado == "anulada":
            raise ValueError("La compra ya esta anulada")

        if compra.estado == "confirmada":
            from app.domains.inventario.services import InventarioService
            inventario = InventarioService(self.db)
            bodega_id = compra.bodega_id or inventario.bodega_principal(compra.empresa_id).id
            referencia = f"ANULA-{compra.numero_documento or compra.id}"

            for detalle in compra.detalles:
                producto = self.db.get(Producto, detalle.producto_id)
                if not producto:
                    continue
                disponible = producto.existencias or CERO
                if disponible < detalle.cantidad:
                    raise ValueError(
                        f"No se puede anular: de '{producto.nombre}' quedan {disponible} "
                        f"unidades y la compra ingreso {detalle.cantidad}. "
                        "Parte de la mercancia ya se consumio.")

            for detalle in compra.detalles:
                inventario.registrar_movimiento(
                    producto_id=detalle.producto_id, tipo="ajuste_negativo",
                    cantidad=detalle.cantidad, bodega_id=bodega_id,
                    referencia=referencia,
                    observacion=f"Anulacion de compra {compra.id}: {motivo.strip()}",
                    usuario_id=usuario_id, empresa_id=compra.empresa_id,
                    permitir_negativo=False)

            # Devolver lo recibido en la orden asociada
            if compra.orden_compra_id:
                orden = self.db.get(OrdenCompra, compra.orden_compra_id)
                if orden:
                    por_producto = {d.producto_id: d for d in orden.detalles}
                    for detalle in compra.detalles:
                        d_orden = por_producto.get(detalle.producto_id)
                        if d_orden:
                            d_orden.cantidad_recibida = max(
                                CERO, (d_orden.cantidad_recibida or CERO) - detalle.cantidad)
                    pendiente = sum((d.pendiente for d in orden.detalles), CERO)
                    orden.estado = "emitida" if pendiente == sum(
                        (d.cantidad for d in orden.detalles), CERO) else "parcial"

        compra.estado = "anulada"
        compra.motivo_anulacion = motivo.strip()
        compra.fecha_anulacion = hora_colombia()
        self.db.flush()
        self.logger.info("Compra %s anulada: %s", compra.id, motivo.strip())
        return compra

    # ==================================================================
    # 6. CONSULTAS E INDICADORES
    # ==================================================================
    def listar_compras(self, *, empresa_id: int = 1, estado: Optional[str] = None,
                       proveedor_id: Optional[int] = None,
                       desde: Optional[date] = None, hasta: Optional[date] = None,
                       limit: int = 100) -> list[Compra]:
        q = select(Compra).where(Compra.empresa_id == empresa_id)
        if estado:
            q = q.where(Compra.estado == estado)
        if proveedor_id:
            q = q.where(Compra.proveedor_id == proveedor_id)
        if desde:
            q = q.where(Compra.fecha >= desde)
        if hasta:
            q = q.where(Compra.fecha <= hasta)
        return self.db.scalars(q.order_by(Compra.fecha.desc(), Compra.id.desc())
                               .limit(limit)).all()

    def cuentas_por_pagar(self, *, empresa_id: int = 1) -> list[dict]:
        """Compras a credito confirmadas, con su estado de vencimiento."""
        compras = self.db.scalars(
            select(Compra).where(
                Compra.empresa_id == empresa_id,
                Compra.estado == "confirmada",
                Compra.forma_pago == "credito")
        ).all()
        hoy = date.today()
        filas = []
        for c in compras:
            vence = c.fecha_vencimiento
            dias = (vence - hoy).days if vence else None
            filas.append({
                "compra_id": c.id,
                "numero_documento": c.numero_documento,
                "proveedor": c.proveedor.nombre if c.proveedor else None,
                "fecha": c.fecha,
                "fecha_vencimiento": vence,
                "total": c.total,
                "dias_para_vencer": dias,
                "vencida": bool(dias is not None and dias < 0),
            })
        return sorted(filas, key=lambda f: (f["dias_para_vencer"] is None,
                                            f["dias_para_vencer"] or 0))

    def historial_producto(self, producto_id: int, limit: int = 20) -> list[dict]:
        """Compras de un producto, para ver la evolucion del costo."""
        detalles = self.db.scalars(
            select(DetalleCompra)
            .join(Compra, DetalleCompra.compra_id == Compra.id)
            .where(DetalleCompra.producto_id == producto_id,
                   Compra.estado == "confirmada")
            .order_by(Compra.fecha.desc()).limit(limit)
        ).all()
        return [{
            "compra_id": d.compra_id,
            "fecha": d.compra.fecha,
            "proveedor": d.compra.proveedor.nombre if d.compra.proveedor else None,
            "cantidad": d.cantidad,
            "costo_unitario": d.costo_unitario,
            "total": d.total,
        } for d in detalles]

    def indicadores(self, *, empresa_id: int = 1,
                    desde: Optional[date] = None) -> dict:
        q = select(Compra).where(Compra.empresa_id == empresa_id,
                                 Compra.estado == "confirmada")
        if desde:
            q = q.where(Compra.fecha >= desde)
        compras = self.db.scalars(q).all()

        total = sum((c.total or CERO for c in compras), CERO)
        iva = sum((c.iva or CERO for c in compras), CERO)

        por_proveedor: dict[str, Decimal] = {}
        for c in compras:
            nombre = c.proveedor.nombre if c.proveedor else "Sin proveedor"
            por_proveedor[nombre] = por_proveedor.get(nombre, CERO) + (c.total or CERO)

        ordenes_abiertas = self.db.scalar(
            select(func.count(OrdenCompra.id)).where(
                OrdenCompra.empresa_id == empresa_id,
                OrdenCompra.estado.in_(["emitida", "parcial"]))) or 0

        solicitudes_pendientes = self.db.scalar(
            select(func.count(SolicitudCompra.id)).where(
                SolicitudCompra.empresa_id == empresa_id,
                SolicitudCompra.estado == "pendiente")) or 0

        return {
            "compras": len(compras),
            "total": total.quantize(CENTAVO),
            "iva": iva.quantize(CENTAVO),
            "promedio": (total / len(compras)).quantize(CENTAVO) if compras else CERO,
            "por_proveedor": sorted(
                [{"proveedor": k, "total": v} for k, v in por_proveedor.items()],
                key=lambda x: x["total"], reverse=True),
            "ordenes_abiertas": ordenes_abiertas,
            "solicitudes_pendientes": solicitudes_pendientes,
            "cuentas_por_pagar": len(self.cuentas_por_pagar(empresa_id=empresa_id)),
        }
