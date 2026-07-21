"""
Tests básicos para validar estructura modular - POS Premium FASE 1
Tests simplificados que validan la arquitetura sin depender del modelo actual
"""

import pytest
from decimal import Decimal
from app.domains.ventas.schemas import (
    VentaCreate, DetalleVentaCreate, PagoCreate,
    EstadoVenta, TipoVenta, TipoPago
)


class TestSchemasValidacion:
    """Tests para validación de Schemas Pydantic"""
    
    def test_crear_detalle_venta_valido(self):
        """Test: Crear detalle de venta con datos válidos"""
        detalle = DetalleVentaCreate(
            producto_id=1,
            cantidad=Decimal("2"),
            precio=Decimal("8500")
        )
        
        assert detalle.producto_id == 1
        assert detalle.cantidad == Decimal("2")
        assert detalle.precio == Decimal("8500")
        assert detalle.observaciones is None
    
    def test_crear_detalle_venta_con_observaciones(self):
        """Test: Detalle con observaciones especiales"""
        detalle = DetalleVentaCreate(
            producto_id=5,
            cantidad=Decimal("1"),
            precio=Decimal("15000"),
            observaciones="Sin azúcar"
        )
        
        assert detalle.observaciones == "Sin azúcar"
    
    def test_crear_venta_en_mesa_valida(self):
        """Test: Crear venta en mesa con datos válidos"""
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=1,
            detalles=[
                DetalleVentaCreate(
                    producto_id=1,
                    cantidad=Decimal("2"),
                    precio=Decimal("8500")
                )
            ]
        )
        
        assert venta_data.tipo_venta == TipoVenta.EN_MESA
        assert venta_data.mesa_id == 1
        assert len(venta_data.detalles) == 1
        assert venta_data.descuento == Decimal("0")
    
    def test_crear_venta_para_llevar_sin_mesa(self):
        """Test: Venta para llevar no requiere mesa"""
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.PARA_LLEVAR,
            detalles=[
                DetalleVentaCreate(
                    producto_id=1,
                    cantidad=Decimal("1"),
                    precio=Decimal("10000")
                )
            ]
        )
        
        assert venta_data.tipo_venta == TipoVenta.PARA_LLEVAR
        assert venta_data.mesa_id is None
    
    def test_crear_venta_en_mesa_sin_mesa_falla(self):
        """Test: Validación - EN_MESA requiere mesa_id"""
        with pytest.raises(ValueError, match="mesa_id"):
            VentaCreate(
                tipo_venta=TipoVenta.EN_MESA,
                mesa_id=None,  # Error: falta mesa_id
                detalles=[
                    DetalleVentaCreate(
                        producto_id=1,
                        cantidad=Decimal("1"),
                        precio=Decimal("8500")
                    )
                ]
            )
    
    def test_crear_venta_sin_detalles_falla(self):
        """Test: Validación - debe tener al menos 1 detalle"""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError, match="too_short"):
            VentaCreate(
                tipo_venta=TipoVenta.PARA_LLEVAR,
                detalles=[]  # Error: lista vacía
            )
    
    def test_crear_venta_con_descuento(self):
        """Test: Venta con descuento y propina"""
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=1,
            detalles=[
                DetalleVentaCreate(
                    producto_id=1,
                    cantidad=Decimal("1"),
                    precio=Decimal("10000")
                )
            ],
            descuento=Decimal("1000"),
            propina_porcentaje=Decimal("10")
        )
        
        assert venta_data.descuento == Decimal("1000")
        assert venta_data.propina_porcentaje == Decimal("10")
    
    def test_crear_pago_valido(self):
        """Test: Crear pago con validaciones"""
        pago = PagoCreate(
            tipo_pago=TipoPago.EFECTIVO,
            monto=Decimal("45000"),
            referencia="PAGO-001"
        )
        
        assert pago.tipo_pago == TipoPago.EFECTIVO
        assert pago.monto == Decimal("45000")
        assert pago.referencia == "PAGO-001"
    
    def test_crear_pago_con_tarjeta(self):
        """Test: Pago con tarjeta y referencia de transacción"""
        pago = PagoCreate(
            tipo_pago=TipoPago.TARJETA_CREDITO,
            monto=Decimal("50000"),
            referencia="AUTH123456"
        )
        
        assert pago.tipo_pago == TipoPago.TARJETA_CREDITO
        assert "AUTH" in pago.referencia
    
    def test_tipos_venta_disponibles(self):
        """Test: Validar tipos de venta soportados"""
        tipos = [e.value for e in TipoVenta]
        
        assert "en_mesa" in tipos
        assert "para_llevar" in tipos
        assert "domicilio" in tipos
        assert "mostrador" in tipos
    
    def test_tipos_pago_disponibles(self):
        """Test: Validar tipos de pago soportados"""
        tipos = [e.value for e in TipoPago]
        
        assert "efectivo" in tipos
        assert "tarjeta_credito" in tipos
        assert "tarjeta_debito" in tipos
        assert "transferencia" in tipos
        assert "billetera_digital" in tipos
    
    def test_estados_venta_disponibles(self):
        """Test: Validar estados de venta"""
        estados = [e.value for e in EstadoVenta]
        
        assert "abierta" in estados
        assert "cerrada" in estados
        assert "suspendida" in estados
        assert "cancelada" in estados
        assert "facturada" in estados
    
    def test_conversión_decimal_desde_string(self):
        """Test: Conversión automática de strings a Decimal"""
        detalle = DetalleVentaCreate(
            producto_id=1,
            cantidad="2.50",  # String
            precio="8500.75"   # String
        )
        
        assert isinstance(detalle.cantidad, Decimal)
        assert isinstance(detalle.precio, Decimal)
        assert detalle.cantidad == Decimal("2.50")
        assert detalle.precio == Decimal("8500.75")
    
    def test_venta_con_cliente_frecuente(self):
        """Test: Venta puede asociarse a cliente frecuente"""
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.EN_MESA,
            mesa_id=1,
            cliente_id=10,  # Cliente frecuente
            detalles=[
                DetalleVentaCreate(
                    producto_id=1,
                    cantidad=Decimal("1"),
                    precio=Decimal("8500")
                )
            ]
        )
        
        assert venta_data.cliente_id == 10
    
    def test_venta_domicilio_con_cargo_envio(self):
        """Test: Venta domicilio incluye cargo de envío"""
        venta_data = VentaCreate(
            tipo_venta=TipoVenta.DOMICILIO,
            detalles=[
                DetalleVentaCreate(
                    producto_id=1,
                    cantidad=Decimal("1"),
                    precio=Decimal("8500")
                )
            ],
            cargo_envio=Decimal("5000"),
            referencia_externa="APP-12345"
        )
        
        assert venta_data.cargo_envio == Decimal("5000")
        assert venta_data.referencia_externa == "APP-12345"
