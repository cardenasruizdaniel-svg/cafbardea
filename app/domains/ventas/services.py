"""
Service Layer para Ventas - Lógica de negocio centralizada
Aísla la lógica de DB, validaciones y cálculos
"""

import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import (
    hora_colombia,
    Venta, DetalleVenta, Producto, Mesa, Cliente, Usuario,
    Empresa, MovimientoInventario, PagoVenta, AlertaStock,
)
from .schemas import VentaCreate, DetalleVentaCreate, PagoCreate, EstadoVenta, TipoPago
from app.config import logger

class VentaService:
    """Servicio de lógica de negocio para ventas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    # ------------------------------------------------------------------
    # Helpers de negocio
    # ------------------------------------------------------------------
    def _empresa(self, empresa_id: int) -> Optional[Empresa]:
        return self.db.get(Empresa, empresa_id) if empresa_id else None

    def _resolver_precio(
        self,
        producto: Producto,
        precio_solicitado: Optional[Decimal],
        puede_precio_libre: bool,
    ) -> Decimal:
        """El precio proviene del catalogo.

        Solo un usuario con el permiso `ventas.precio_libre` puede imponer un
        precio distinto. Antes el precio venia del request sin control alguno,
        de modo que un cliente podia comprar un producto de $8.500 por $1.
        """
        precio_catalogo = producto.precio_venta or Decimal("0")
        if precio_solicitado is None:
            return precio_catalogo
        if precio_solicitado == precio_catalogo:
            return precio_catalogo
        if not puede_precio_libre:
            raise ValueError(
                f"El precio de '{producto.nombre}' es {precio_catalogo}; "
                f"no tiene permiso para venderlo a {precio_solicitado}"
            )
        if precio_solicitado < 0:
            raise ValueError("El precio no puede ser negativo")
        return precio_solicitado

    def _descargar_inventario(
        self,
        producto: Producto,
        cantidad: Decimal,
        referencia: str,
        permitir_negativo: bool,
    ) -> None:
        """Descarga existencias delegando en el servicio unico de inventario.

        Antes existian TRES implementaciones distintas del mismo concepto
        (ventas, compras y la ruta /inventario/movimiento), cada una con reglas
        propias. Ahora todas pasan por InventarioService, que ademas mantiene
        el kardex y el costo promedio.
        """
        from app.domains.inventario.services import InventarioService

        InventarioService(self.db).registrar_movimiento(
            producto_id=producto.id,
            tipo="venta",
            cantidad=cantidad,
            bodega_id=None,
            referencia=referencia,
            empresa_id=producto.empresa_id or 1,
            permitir_negativo=permitir_negativo,
        )

    def _recalcular(self, venta: Venta) -> None:
        """Recalcula subtotal y total a partir de los detalles reales."""
        subtotal = sum(
            ((d.cantidad or Decimal("0")) * (d.precio or Decimal("0")) for d in venta.detalles),
            Decimal("0"),
        )
        venta.subtotal = subtotal
        venta.total = max(
            Decimal("0"),
            subtotal
            - (venta.descuento or Decimal("0"))
            + (venta.impuesto or Decimal("0"))
            + (venta.propina or Decimal("0"))
            + (venta.cargo_envio or Decimal("0")),
        )

    # ------------------------------------------------------------------
    def crear_venta(
        self,
        venta_data: VentaCreate,
        usuario_id: int,
        empresa_id: int,
        puede_precio_libre: bool = False,
    ) -> Venta:
        """Crear venta aplicando reglas de negocio.

        - El precio sale del catalogo salvo permiso explicito.
        - Se descarga inventario y se registra el movimiento.
        - Se guarda el costo unitario para poder calcular margen.
        - La mesa pasa a 'ocupada'.
        """
        try:
            empresa = self._empresa(empresa_id)
            permitir_negativo = bool(getattr(empresa, "permitir_stock_negativo", True))

            if venta_data.mesa_id:
                mesa = self.db.get(Mesa, venta_data.mesa_id)
                if not mesa:
                    raise ValueError(f"Mesa {venta_data.mesa_id} no existe")
                if empresa_id and mesa.empresa_id != empresa_id:
                    raise ValueError("La mesa pertenece a otra empresa")
            else:
                mesa = None

            if venta_data.cliente_id:
                cliente = self.db.get(Cliente, venta_data.cliente_id)
                if not cliente:
                    raise ValueError(f"Cliente {venta_data.cliente_id} no existe")

            if not venta_data.detalles:
                raise ValueError("La venta debe tener al menos 1 detalle")

            preparados = []
            for det in venta_data.detalles:
                producto = self.db.get(Producto, det.producto_id)
                if not producto:
                    raise ValueError(f"Producto {det.producto_id} no existe")
                if not producto.activo:
                    raise ValueError(f"El producto '{producto.nombre}' esta inactivo")
                if empresa_id and producto.empresa_id != empresa_id:
                    raise ValueError(f"El producto '{producto.nombre}' pertenece a otra empresa")

                precio = self._resolver_precio(producto, det.precio, puede_precio_libre)
                preparados.append((producto, det.cantidad, precio, det.observaciones))

            subtotal = sum((c * p for _, c, p, _ in preparados), Decimal("0"))

            impuesto = venta_data.impuesto or Decimal("0")
            descuento = venta_data.descuento or Decimal("0")
            if descuento > subtotal:
                raise ValueError("El descuento no puede superar el subtotal")

            propina_pct = subtotal * (venta_data.propina_porcentaje or Decimal("0")) / Decimal("100")
            propina = max(propina_pct, venta_data.propina_fija or Decimal("0"))
            cargo_envio = venta_data.cargo_envio or Decimal("0")
            total = max(Decimal("0"), subtotal - descuento + impuesto + propina + cargo_envio)

            venta = Venta(
                empresa_id=empresa_id,
                usuario_id=usuario_id,
                empleado_id=usuario_id,
                mesa_id=venta_data.mesa_id,
                cliente_id=venta_data.cliente_id,
                estado="abierta",
                canal=venta_data.tipo_venta.value,
                subtotal=subtotal,
                descuento=descuento,
                impuesto=impuesto,
                propina=propina,
                cargo_envio=cargo_envio,
                total=total,
                observacion=venta_data.observaciones,
            )
            self.db.add(venta)
            self.db.flush()

            referencia = f"VENTA-{venta.id}"
            for producto, cantidad, precio, obs in preparados:
                self.db.add(DetalleVenta(
                    venta_id=venta.id,
                    producto_id=producto.id,
                    cantidad=cantidad,
                    precio=precio,
                    nota=obs,
                    costo_unitario=producto.costo or Decimal("0"),
                ))
                self._descargar_inventario(producto, cantidad, referencia, permitir_negativo)

            if mesa:
                # Abrir el servicio de la mesa registrando hora, mesero y
                # comensales. Antes solo se cambiaba el estado.
                mesa.estado = "ocupada"
                if mesa.fecha_apertura is None:
                    from datetime import datetime as _dt
                    mesa.fecha_apertura = hora_colombia()
                if mesa.mesero_id is None:
                    mesa.mesero_id = usuario_id

            self.db.commit()
            self.logger.info("Venta %s creada - Total: %s", venta.id, total)
            return venta

        except ValueError as e:
            self.db.rollback()
            self.logger.warning("Error validacion: %s", e)
            raise
        except Exception as e:
            self.db.rollback()
            self.logger.error("Error creando venta: %s", e)
            raise

    def obtener_venta(self, venta_id: int, empresa_id: int = None) -> Optional[Venta]:
        """Obtener venta por ID, aislada por empresa.

        Antes ignoraba `empresa_id`, de modo que cualquier empresa podia leer
        las ventas de otra conociendo el ID.
        """
        venta = self.db.get(Venta, venta_id)
        if venta is None:
            return None
        if empresa_id is not None and venta.empresa_id != empresa_id:
            return None
        return venta

    def listar_ventas(self, empresa_id: int, estado: Optional[str] = None,
                      limit: int = 50, offset: int = 0) -> List[Venta]:
        """Listar ventas de UNA empresa.

        Antes recibia `empresa_id` y no lo usaba: una consulta con empresa_id=999
        devolvia las ventas de la empresa 1.
        """
        query = self.db.query(Venta)
        if empresa_id is not None:
            query = query.filter(Venta.empresa_id == empresa_id)
        if estado:
            query = query.filter(Venta.estado == estado)
        return query.order_by(Venta.fecha.desc()).limit(limit).offset(offset).all()

    def agregar_detalle(self, venta_id: int, detalle_data: DetalleVentaCreate,
                        empresa_id: int = None, puede_precio_libre: bool = False) -> Venta:
        """Agregar item a venta abierta, descargando inventario."""
        venta = self.obtener_venta(venta_id, empresa_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")
        if venta.estado != "abierta":
            raise ValueError(f"No se puede agregar a venta en estado {venta.estado}")

        producto = self.db.get(Producto, detalle_data.producto_id)
        if not producto:
            raise ValueError(f"Producto {detalle_data.producto_id} no existe")
        if not producto.activo:
            raise ValueError(f"El producto '{producto.nombre}' esta inactivo")

        precio = self._resolver_precio(producto, detalle_data.precio, puede_precio_libre)
        empresa = self._empresa(empresa_id or venta.empresa_id)
        permitir_negativo = bool(getattr(empresa, "permitir_stock_negativo", True))

        self.db.add(DetalleVenta(
            venta_id=venta_id,
            producto_id=producto.id,
            cantidad=detalle_data.cantidad,
            precio=precio,
            nota=detalle_data.observaciones,
            costo_unitario=producto.costo or Decimal("0"),
        ))
        self._descargar_inventario(producto, detalle_data.cantidad,
                                   f"VENTA-{venta_id}", permitir_negativo)

        self.db.flush()
        self.db.refresh(venta)
        self._recalcular(venta)
        self.db.commit()
        self.logger.info("Detalle agregado a venta %s", venta_id)
        return venta

    def eliminar_detalle(self, venta_id: int, detalle_id: int, empresa_id: int = None) -> Venta:
        """Eliminar item de venta abierta, devolviendo el stock."""
        venta = self.obtener_venta(venta_id, empresa_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")
        if venta.estado != "abierta":
            raise ValueError(f"No se puede eliminar de venta en estado {venta.estado}")

        detalle = self.db.get(DetalleVenta, detalle_id)
        if not detalle or detalle.venta_id != venta_id:
            raise ValueError(f"Detalle {detalle_id} no valido")

        # Devolver existencias: antes se eliminaba el item sin reponer stock.
        producto = self.db.get(Producto, detalle.producto_id)
        if producto:
            from app.domains.inventario.services import InventarioService
            InventarioService(self.db).registrar_movimiento(
                producto_id=producto.id,
                tipo="devolucion_venta",
                cantidad=detalle.cantidad,
                bodega_id=None,
                referencia=f"VENTA-{venta_id}",
                empresa_id=producto.empresa_id or 1,
            )

        self.db.delete(detalle)
        self.db.flush()
        self.db.refresh(venta)
        self._recalcular(venta)
        self.db.commit()
        self.logger.info("Detalle %s eliminado de venta %s", detalle_id, venta_id)
        return venta

    def procesar_pago(self, venta_id: int, pago_data: PagoCreate,
                      empresa_id: int = None, usuario_id: int = None) -> Venta:
        """Registrar pago, cerrar venta y liberar la mesa.

        Antes solo cambiaba el estado y guardaba el medio de pago: no quedaba
        rastro del monto recibido ni del cambio, por lo que era imposible
        cuadrar la caja.
        """
        venta = self.obtener_venta(venta_id, empresa_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")

        if venta.estado not in ["abierta", "suspendida"]:
            raise ValueError(f"Venta no puede procesarse en estado {venta.estado}")

        if pago_data.monto < venta.total:
            raise ValueError(f"Monto insuficiente: {pago_data.monto} < {venta.total}")

        cambio = pago_data.monto - venta.total

        self.db.add(PagoVenta(
            venta_id=venta.id,
            tipo_pago=pago_data.tipo_pago.value,
            monto_recibido=pago_data.monto,
            monto_aplicado=venta.total,
            cambio=cambio,
            referencia=pago_data.referencia,
            usuario_id=usuario_id,
        ))

        venta.estado = "pagada"
        venta.medio_pago = pago_data.tipo_pago.value
        venta.fecha_cierre = datetime.now(timezone.utc)

        if venta.mesa_id:
            mesa = self.db.get(Mesa, venta.mesa_id)
            if mesa:
                abiertas = self.db.query(Venta).filter(
                    Venta.mesa_id == mesa.id,
                    Venta.estado.in_(["abierta", "suspendida"]),
                    Venta.id != venta.id,
                ).count()
                if abiertas == 0:
                    mesa.estado = "libre"
                    mesa.fecha_apertura = None
                    mesa.mesero_id = None
                    mesa.comensales = None

        self.db.commit()
        self.logger.info("Venta %s cerrada - Recibido: %s Cambio: %s",
                         venta_id, pago_data.monto, cambio)
        return venta

    def suspender_venta(self, venta_id: int, empresa_id: int = None) -> Tuple[Venta, str]:
        """Suspender venta para recuperarla después"""
        venta = self.obtener_venta(venta_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")
        
        if venta.estado == "suspendida":
            raise ValueError("Venta ya está suspendida")
        
        venta.estado = "suspendida"
        self.db.commit()
        
        codigo = f"SUS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{venta_id}"
        self.logger.info(f"Venta {venta_id} suspendida - Código: {codigo}")
        return venta, codigo
    
    def obtener_total_dia(self, empresa_id: int) -> Decimal:
        """Total de ventas cerradas HOY para la empresa.

        Antes sumaba las ventas cerradas de cualquier dia y de cualquier
        empresa, por lo que el dato del dashboard nunca fue correcto.
        """
        from datetime import date, datetime as dt
        hoy = date.today()
        q = self.db.query(func.sum(Venta.total)).filter(
            Venta.estado == "pagada",
            Venta.fecha_cierre >= dt.combine(hoy, dt.min.time()),
            Venta.fecha_cierre <= dt.combine(hoy, dt.max.time()),
        )
        if empresa_id is not None:
            q = q.filter(Venta.empresa_id == empresa_id)
        return q.scalar() or Decimal("0")

    def obtener_stats_dia(self, empresa_id: int) -> dict:
        """Estadísticas del día (solo ventas cerradas de hoy)"""
        from datetime import date, datetime as dt
        hoy = date.today()
        
        q = self.db.query(Venta).filter(Venta.estado == "pagada")
        if empresa_id is not None:
            q = q.filter(Venta.empresa_id == empresa_id)
        ventas_cerradas = q \
            .filter(Venta.fecha_cierre >= dt.combine(hoy, dt.min.time())) \
            .filter(Venta.fecha_cierre < dt.combine(hoy, dt.max.time())) \
            .all()
        
        total_monto = sum((v.total for v in ventas_cerradas), Decimal("0"))
        
        return {
            "total_ventas": len(ventas_cerradas),
            "monto_total": total_monto,
            "promedio_venta": (
                total_monto / len(ventas_cerradas)
                if ventas_cerradas else Decimal("0")
            ),
            "items_vendidos": sum(len(v.detalles) for v in ventas_cerradas) if ventas_cerradas else 0
        }
