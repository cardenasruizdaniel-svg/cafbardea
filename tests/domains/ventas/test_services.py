"""
Tests para módulo Ventas - POS Premium
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domains.ventas import VentaService
from app.domains.ventas.schemas import (
    VentaCreate, DetalleVentaCreate, PagoCreate, TipoVenta, TipoPago
)
from app.models import Venta, Mesa, Producto, Usuario


class TestVentaService:
    """Tests para lógica de negocio de ventas"""
    
    def test_crear_venta_en_mesa(self, db_session: Session):
        """Test: Crear venta en mesa con validaciones"""
        service = VentaService(db_session)
        
        # Obtener datos de prueba
        usuario = db_session.query(Usuario).first()
        empresa = db_session.query(__import__('app.models', fromlist=['Empresa']).Empresa).first()
        mesa = db_session.query(Mesa).first()
        producto = db_session.query(Producto).first()
        
        # Crear venta
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=producto.id,
                    cantidad=Decimal("2"),
                    precio=Decimal("8500")
                )
            ]
        )
        
        venta = service.crear_venta(venta_data, usuario.id, empresa.id)
        
        # Validaciones
        assert venta.id is not None
        assert venta.estado == "abierta"
        assert venta.canal == "en_mesa"
        assert venta.mesa_id == mesa.id
        assert venta.subtotal == Decimal("17000")  # 2 * 8500
        assert venta.total == Decimal("17000")
        assert len(venta.detalles) == 1
    
    def test_crear_venta_con_descuento(self, db_session: Session):
        """Test: Crear venta con descuento"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        producto = db_session.query(Producto).first()
        
        # Venta con descuento
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=producto.id,
                    cantidad=Decimal("1"),
                    precio=Decimal("10000")
                )
            ],
            descuento=Decimal("1000")  # Descuento de $1000
        )
        
        venta = service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
        
        assert venta.subtotal == Decimal("10000")
        assert venta.descuento == Decimal("1000")
        assert venta.total == Decimal("9000")  # 10000 - 1000
    
    def test_crear_venta_con_propina_porcentaje(self, db_session: Session):
        """Test: Calcular propina por porcentaje"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        producto = db_session.query(Producto).first()
        
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=producto.id,
                    cantidad=Decimal("1"),
                    precio=Decimal("10000")
                )
            ],
            propina_porcentaje=Decimal("10")  # 10% de propina
        )
        
        venta = service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
        
        assert venta.propina == Decimal("1000")  # 10% de 10000
        assert venta.total == Decimal("11000")  # 10000 + 1000
    
    def test_crear_venta_sin_mesa(self, db_session: Session):
        """Test: Validar error cuando falta mesa en EN_MESA"""
        from pydantic import ValidationError
        
        usuario = db_session.query(Usuario).first()
        producto = db_session.query(Producto).first()
        
        # La validación sucede en Pydantic, no en el servicio
        with pytest.raises(ValidationError):
            VentaCreate(
                tipo_venta=TipoVenta.EN_MESA,
                mesa_id=None,  # Error: falta mesa_id
                detalles=[
                    DetalleVentaCreate(
                        producto_id=producto.id,
                        cantidad=Decimal("1"),
                        precio=Decimal("8500")
                    )
                ]
            )
    
    def test_crear_venta_producto_invalido(self, db_session: Session):
        """Test: Error con producto que no existe"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=9999,  # Producto no existe
                    cantidad=Decimal("1"),
                    precio=Decimal("8500")
                )
            ]
        )
        
        with pytest.raises(ValueError):
            service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
    
    def test_agregar_detalle_a_venta(self, db_session: Session):
        """Test: Agregar item a venta abierta"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        productos = db_session.query(Producto).all()
        
        # Crear venta inicial
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=productos[0].id,
                    cantidad=Decimal("1"),
                    precio=Decimal("8500")
                )
            ]
        )
        
        venta = service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
        assert venta.subtotal == Decimal("8500")
        
        # Agregar otro producto
        nuevo_detalle = DetalleVentaCreate(
            producto_id=productos[1].id,
            cantidad=Decimal("2"),
            precio=Decimal("9000")
        )
        
        venta_actualizada = service.agregar_detalle(venta.id, nuevo_detalle, usuario.empresa_id)
        
        assert venta_actualizada.subtotal == Decimal("26500")  # 8500 + (2 * 9000)
        assert len(venta_actualizada.detalles) == 2
    
    def test_procesar_pago_venta(self, db_session: Session):
        """Test: Procesar pago y cerrar venta"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        producto = db_session.query(Producto).first()
        
        # Crear venta
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=producto.id,
                    cantidad=Decimal("1"),
                    precio=Decimal("8500")
                )
            ]
        )
        
        venta = service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
        assert venta.estado == "abierta"
        
        # Procesar pago
        pago = PagoCreate(
            tipo_pago=TipoPago.EFECTIVO,
            monto=Decimal("10000")  # Pago con cambio
        )
        
        venta_pagada = service.procesar_pago(venta.id, pago, usuario.empresa_id)
        
        assert venta_pagada.estado == "cerrada"
        assert venta_pagada.fecha_cierre is not None
    
    def test_procesar_pago_monto_insuficiente(self, db_session: Session):
        """Test: Error cuando monto de pago es insuficiente"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        producto = db_session.query(Producto).first()
        
        # Crear venta
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=producto.id,
                    cantidad=Decimal("2"),
                    precio=Decimal("10000")
                )
            ]
        )
        
        venta = service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
        
        # Pago insuficiente
        pago = PagoCreate(
            tipo_pago=TipoPago.EFECTIVO,
            monto=Decimal("15000")  # Menos que 20000
        )
        
        with pytest.raises(ValueError, match="Monto insuficiente"):
            service.procesar_pago(venta.id, pago, usuario.empresa_id)
    
    def test_suspender_venta(self, db_session: Session):
        """Test: Suspender venta"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        producto = db_session.query(Producto).first()
        
        # Crear venta
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=mesa.id,
            detalles=[
                DetalleVentaCreate(
                    producto_id=producto.id,
                    cantidad=Decimal("1"),
                    precio=Decimal("8500")
                )
            ]
        )
        
        venta = service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
        
        # Suspender
        venta_suspendida, codigo = service.suspender_venta(venta.id, usuario.empresa_id)
        
        assert venta_suspendida.estado == "suspendida"
        assert codigo.startswith("SUS-")
    
    def test_obtener_stats_dia(self, db_session: Session):
        """Test: Obtener estadísticas del día"""
        service = VentaService(db_session)
        
        usuario = db_session.query(Usuario).first()
        mesa = db_session.query(Mesa).first()
        producto = db_session.query(Producto).first()
        
        # Crear y cerrar 2 ventas
        for i in range(2):
            venta_data = VentaCreate(
                tipo_venta=TipoVenta.EN_MESA,
                mesa_id=mesa.id,
                detalles=[
                    DetalleVentaCreate(
                        producto_id=producto.id,
                        cantidad=Decimal("1"),
                        precio=Decimal("8500")
                    )
                ]
            )
            
            venta = service.crear_venta(venta_data, usuario.id, usuario.empresa_id)
            
            pago = PagoCreate(
                tipo_pago=TipoPago.EFECTIVO,
                monto=Decimal("8500")
            )
            
            service.procesar_pago(venta.id, pago, usuario.empresa_id)
        
        # Obtener stats
        stats = service.obtener_stats_dia(usuario.empresa_id)
        
        # Verificar que hay al menos 2 ventas (las del test)
        assert stats["total_ventas"] >= 2
        # Las 2 ventas del test suman 17000 (8500 cada una)
        assert stats["monto_total"] >= Decimal("17000")
        # El promedio debe ser consistente
        assert stats["promedio_venta"] > Decimal("0")
