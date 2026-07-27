"""Reglas de negocio del dominio Ventas.

Cada prueba corresponde a un defecto real encontrado con evidencia ejecutada
antes de corregirlo. Sirven de regresion: si alguna vuelve a fallar, el
defecto original ha reaparecido.
"""
from decimal import Decimal

import pytest

from app.domains.ventas.schemas import (
    DetalleVentaCreate, PagoCreate, TipoPago, VentaCreate,
)
from app.domains.ventas.services import VentaService
from app.models import AlertaStock, Empresa, Mesa, MovimientoInventario, PagoVenta, Producto


@pytest.fixture
def svc(db_session):
    return VentaService(db_session)


@pytest.fixture
def producto(db_session):
    p = db_session.query(Producto).filter(Producto.activo == True).first()
    p.existencias = Decimal("50")
    p.costo = Decimal("2400")
    p.precio_venta = Decimal("8500")
    db_session.commit()
    return p


def _venta(producto, cantidad="1", precio=None, **kw):
    det = DetalleVentaCreate(
        producto_id=producto.id,
        cantidad=Decimal(cantidad),
        precio=Decimal(precio) if precio is not None else producto.precio_venta,
    )
    base = dict(mesa_id=None, tipo_venta="mostrador", detalles=[det])
    base.update(kw)
    return VentaCreate(**base)


class TestPrecio:
    def test_precio_sale_del_catalogo(self, svc, producto):
        v = svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        assert v.detalles[0].precio == Decimal("8500")

    def test_precio_arbitrario_sin_permiso_es_rechazado(self, svc, producto):
        """Antes: un producto de $8.500 podia venderse a $1."""
        with pytest.raises(ValueError, match="no tiene permiso"):
            svc.crear_venta(_venta(producto, precio="1"), usuario_id=1, empresa_id=1)

    def test_precio_arbitrario_con_permiso_se_acepta(self, svc, producto):
        v = svc.crear_venta(_venta(producto, precio="5000"), usuario_id=1,
                            empresa_id=1, puede_precio_libre=True)
        assert v.detalles[0].precio == Decimal("5000")


class TestInventario:
    def test_la_venta_descuenta_stock(self, svc, producto, db_session):
        """Antes: vender 5 unidades dejaba las existencias intactas."""
        svc.crear_venta(_venta(producto, cantidad="5"), usuario_id=1, empresa_id=1)
        db_session.refresh(producto)
        assert producto.existencias == Decimal("45")

    def test_se_registra_movimiento_de_inventario(self, svc, producto, db_session):
        v = svc.crear_venta(_venta(producto, cantidad="2"), usuario_id=1, empresa_id=1)
        mov = db_session.query(MovimientoInventario).filter_by(
            referencia=f"VENTA-{v.id}").first()
        assert mov is not None and mov.cantidad == Decimal("-2")

    def test_stock_negativo_permitido_genera_alerta(self, svc, producto, db_session):
        """Politica: se permite negativo, pero debe quedar alerta."""
        empresa = db_session.get(Empresa, 1)
        empresa.permitir_stock_negativo = True
        producto.existencias = Decimal("1")
        db_session.commit()

        svc.crear_venta(_venta(producto, cantidad="5"), usuario_id=1, empresa_id=1)
        db_session.refresh(producto)
        assert producto.existencias == Decimal("-4")

        # La mas reciente: otras pruebas pueden haber dejado alertas previas
        # sobre el mismo producto.
        alerta = db_session.query(AlertaStock).filter_by(
            producto_id=producto.id, tipo="negativo"
        ).order_by(AlertaStock.id.desc()).first()
        assert alerta is not None
        assert alerta.existencia_resultante == Decimal("-4")

    def test_stock_negativo_bloqueado_si_la_empresa_lo_prohibe(self, svc, producto, db_session):
        empresa = db_session.get(Empresa, 1)
        empresa.permitir_stock_negativo = False
        producto.existencias = Decimal("1")
        db_session.commit()
        try:
            with pytest.raises(ValueError, match="Stock insuficiente"):
                svc.crear_venta(_venta(producto, cantidad="5"), usuario_id=1, empresa_id=1)
        finally:
            empresa.permitir_stock_negativo = True
            db_session.commit()

    def test_eliminar_detalle_devuelve_stock(self, svc, producto, db_session):
        v = svc.crear_venta(_venta(producto, cantidad="3"), usuario_id=1, empresa_id=1)
        db_session.refresh(producto)
        assert producto.existencias == Decimal("47")
        svc.eliminar_detalle(v.id, v.detalles[0].id, empresa_id=1)
        db_session.refresh(producto)
        assert producto.existencias == Decimal("50")

    def test_producto_inactivo_no_se_vende(self, svc, producto, db_session):
        producto.activo = False
        db_session.commit()
        try:
            with pytest.raises(ValueError, match="inactivo"):
                svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        finally:
            producto.activo = True
            db_session.commit()


class TestCosto:
    def test_se_guarda_el_costo_unitario(self, svc, producto):
        """Sin costo no hay margen: antes quedaba en 0."""
        v = svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        assert v.detalles[0].costo_unitario == Decimal("2400")


class TestMultitenancy:
    def test_listar_aisla_por_empresa(self, svc, producto):
        """Antes: listar con empresa_id=999 devolvia ventas de la empresa 1."""
        svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        assert svc.listar_ventas(empresa_id=999) == []
        assert len(svc.listar_ventas(empresa_id=1)) >= 1

    def test_obtener_aisla_por_empresa(self, svc, producto):
        v = svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        assert svc.obtener_venta(v.id, empresa_id=999) is None
        assert svc.obtener_venta(v.id, empresa_id=1) is not None


class TestPago:
    def test_se_registra_monto_y_cambio(self, svc, producto, db_session):
        """Antes no quedaba rastro del pago: imposible cuadrar caja."""
        v = svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        total = v.total
        svc.procesar_pago(v.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO,
                                           monto=total + Decimal("1500")),
                          empresa_id=1, usuario_id=1)
        pago = db_session.query(PagoVenta).filter_by(venta_id=v.id).first()
        assert pago is not None
        assert pago.monto_recibido == total + Decimal("1500")
        assert pago.monto_aplicado == total
        assert pago.cambio == Decimal("1500")

    def test_pago_insuficiente_se_rechaza(self, svc, producto):
        v = svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        with pytest.raises(ValueError, match="insuficiente"):
            svc.procesar_pago(v.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO,
                                               monto=v.total - Decimal("1")), empresa_id=1)


class TestMesa:
    def test_abrir_venta_ocupa_la_mesa(self, svc, producto, db_session):
        """Antes la mesa seguia 'libre' con una venta abierta encima."""
        mesa = db_session.query(Mesa).first()
        mesa.estado = "libre"
        db_session.commit()
        svc.crear_venta(_venta(producto, mesa_id=mesa.id, tipo_venta="en_mesa"),
                        usuario_id=1, empresa_id=1)
        db_session.refresh(mesa)
        assert mesa.estado == "ocupada"

    def test_pagar_libera_la_mesa(self, svc, producto, db_session):
        from app.models import Venta
        mesa = db_session.query(Mesa).first()
        # Cerrar ventas abiertas previas sobre la mesa: la mesa solo se libera
        # cuando NO queda ninguna otra venta abierta encima.
        db_session.query(Venta).filter(
            Venta.mesa_id == mesa.id,
            Venta.estado.in_(["abierta", "suspendida"]),
        ).update({"estado": "cancelada"}, synchronize_session=False)
        mesa.estado = "libre"
        db_session.commit()
        v = svc.crear_venta(_venta(producto, mesa_id=mesa.id, tipo_venta="en_mesa"),
                            usuario_id=1, empresa_id=1)
        svc.procesar_pago(v.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO, monto=v.total),
                          empresa_id=1)
        db_session.refresh(mesa)
        assert mesa.estado == "libre"


class TestTotales:
    def test_total_dia_solo_cuenta_hoy_y_su_empresa(self, svc, producto, db_session):
        """Antes sumaba ventas de cualquier dia y de cualquier empresa."""
        v = svc.crear_venta(_venta(producto), usuario_id=1, empresa_id=1)
        svc.procesar_pago(v.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO, monto=v.total),
                          empresa_id=1)
        assert svc.obtener_total_dia(empresa_id=1) >= v.total
        assert svc.obtener_total_dia(empresa_id=999) == Decimal("0")

    def test_descuento_mayor_al_subtotal_se_rechaza(self, svc, producto):
        with pytest.raises(ValueError, match="descuento"):
            svc.crear_venta(_venta(producto, descuento=Decimal("999999")),
                            usuario_id=1, empresa_id=1)
