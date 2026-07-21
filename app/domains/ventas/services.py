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

from app.models import Venta, DetalleVenta, Producto, Mesa, Cliente, Usuario
from .schemas import VentaCreate, DetalleVentaCreate, PagoCreate, EstadoVenta, TipoPago
from app.config import logger

class VentaService:
    """Servicio de lógica de negocio para ventas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def crear_venta(self, venta_data: VentaCreate, usuario_id: int, empresa_id: int) -> Venta:
        """
        Crear nueva venta con validaciones de negocio
        
        Args:
            venta_data: Datos de la venta desde Pydantic
            usuario_id: ID del empleado que crea la venta
            empresa_id: ID de la empresa (no se usa en modelo actual)
            
        Returns:
            Venta creada
        """
        try:
            # Validar mesa si aplica
            if venta_data.mesa_id:
                mesa = self.db.get(Mesa, venta_data.mesa_id)
                if not mesa:
                    raise ValueError(f"Mesa {venta_data.mesa_id} no existe")
            
            # Validar cliente si aplica
            if venta_data.cliente_id:
                cliente = self.db.get(Cliente, venta_data.cliente_id)
                if not cliente:
                    raise ValueError(f"Cliente {venta_data.cliente_id} no existe")
            
            # Validar productos y calcular montos
            subtotal = Decimal("0")
            detalles_list = []
            
            if venta_data.detalles:
                for det in venta_data.detalles:
                    producto = self.db.get(Producto, det.producto_id)
                    if not producto:
                        raise ValueError(f"Producto {det.producto_id} no existe")
                    
                    monto = det.cantidad * det.precio
                    subtotal += monto
                    detalles_list.append({
                        'producto_id': det.producto_id,
                        'cantidad': det.cantidad,
                        'precio': det.precio,
                        'observaciones': det.observaciones
                    })
            
            if not detalles_list:
                raise ValueError("La venta debe tener al menos 1 detalle")
            
            # Calcular totales
            impuesto = venta_data.impuesto or Decimal("0")
            descuento = venta_data.descuento or Decimal("0")
            propina_pct = (subtotal * (venta_data.propina_porcentaje or Decimal("0")) / Decimal("100"))
            propina_fija = venta_data.propina_fija or Decimal("0")
            propina = max(propina_pct, propina_fija)
            cargo_envio = venta_data.cargo_envio or Decimal("0")
            
            total = max(Decimal("0"), subtotal - descuento + impuesto + propina + cargo_envio)
            
            # Crear venta - mapear tipo_venta del schema a canal del modelo
            venta = Venta(
                empleado_id=usuario_id,
                mesa_id=venta_data.mesa_id,
                cliente_id=venta_data.cliente_id,
                estado="abierta",
                canal=venta_data.tipo_venta.value,  # Mapear TipoVenta enum a canal
                subtotal=subtotal,
                descuento=descuento,
                impuesto=impuesto,
                propina=propina,
                cargo_envio=cargo_envio,
                total=total,
                observacion=venta_data.observaciones
            )
            
            self.db.add(venta)
            self.db.flush()
            
            # Crear detalles
            for det_data in detalles_list:
                detalle = DetalleVenta(
                    venta_id=venta.id,
                    producto_id=det_data['producto_id'],
                    cantidad=det_data['cantidad'],
                    precio=det_data['precio'],
                    nota=det_data.get('observaciones')
                )
                self.db.add(detalle)
            
            self.db.commit()
            self.logger.info(f"Venta {venta.id} creada - Total: {total}")
            return venta
            
        except ValueError as e:
            self.db.rollback()
            self.logger.warning(f"Error validación: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error creando venta: {str(e)}")
            raise
    
    def obtener_venta(self, venta_id: int, empresa_id: int = None) -> Optional[Venta]:
        """Obtener venta por ID"""
        return self.db.get(Venta, venta_id)
    
    def listar_ventas(self, empresa_id: int, estado: Optional[str] = None, 
                     limit: int = 50, offset: int = 0) -> List[Venta]:
        """Listar ventas con paginación"""
        query = self.db.query(Venta)
        
        if estado:
            query = query.filter(Venta.estado == estado)
        
        return query.order_by(Venta.fecha.desc()).limit(limit).offset(offset).all()
    
    def agregar_detalle(self, venta_id: int, detalle_data: DetalleVentaCreate,
                       empresa_id: int = None) -> Venta:
        """Agregar item a venta abierta"""
        venta = self.obtener_venta(venta_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")
        
        if venta.estado != "abierta":
            raise ValueError(f"No se puede agregar a venta en estado {venta.estado}")
        
        producto = self.db.get(Producto, detalle_data.producto_id)
        if not producto:
            raise ValueError(f"Producto {detalle_data.producto_id} no existe")
        
        detalle = DetalleVenta(
            venta_id=venta_id,
            producto_id=detalle_data.producto_id,
            cantidad=detalle_data.cantidad,
            precio=detalle_data.precio,
            nota=detalle_data.observaciones
        )
        
        monto_nuevo = detalle_data.cantidad * detalle_data.precio
        venta.subtotal += monto_nuevo
        venta.total = venta.subtotal - venta.descuento + venta.impuesto + venta.propina + venta.cargo_envio
        
        self.db.add(detalle)
        self.db.commit()
        self.logger.info(f"Detalle agregado a venta {venta_id}")
        return venta
    
    def eliminar_detalle(self, venta_id: int, detalle_id: int, empresa_id: int = None) -> Venta:
        """Eliminar item de venta abierta"""
        venta = self.obtener_venta(venta_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")
        
        if venta.estado != "abierta":
            raise ValueError(f"No se puede eliminar de venta en estado {venta.estado}")
        
        detalle = self.db.get(DetalleVenta, detalle_id)
        if not detalle or detalle.venta_id != venta_id:
            raise ValueError(f"Detalle {detalle_id} no válido")
        
        monto_eliminado = detalle.cantidad * detalle.precio
        venta.subtotal -= monto_eliminado
        venta.total = venta.subtotal - venta.descuento + venta.impuesto + venta.propina + venta.cargo_envio
        
        self.db.delete(detalle)
        self.db.commit()
        self.logger.info(f"Detalle {detalle_id} eliminado de venta {venta_id}")
        return venta
    
    def procesar_pago(self, venta_id: int, pago_data: PagoCreate, empresa_id: int = None) -> Venta:
        """Procesar pago y cerrar venta"""
        venta = self.obtener_venta(venta_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")
        
        if venta.estado not in ["abierta", "suspendida"]:
            raise ValueError(f"Venta no puede procesarse en estado {venta.estado}")
        
        if pago_data.monto < venta.total:
            raise ValueError(
                f"Monto insuficiente: {pago_data.monto} < {venta.total}"
            )
        
        venta.estado = "cerrada"
        venta.medio_pago = pago_data.tipo_pago.value
        venta.fecha_cierre = datetime.now(timezone.utc)
        
        self.db.commit()
        self.logger.info(f"Venta {venta_id} cerrada - Monto: {pago_data.monto}")
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
        """Total de ventas del día cerradas"""
        result = self.db.query(func.sum(Venta.total)) \
            .filter(Venta.estado == "cerrada") \
            .scalar()
        return result or Decimal("0")
    
    def obtener_stats_dia(self, empresa_id: int) -> dict:
        """Estadísticas del día (solo ventas cerradas de hoy)"""
        from datetime import date, datetime as dt
        hoy = date.today()
        
        ventas_cerradas = self.db.query(Venta) \
            .filter(Venta.estado == "cerrada") \
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
