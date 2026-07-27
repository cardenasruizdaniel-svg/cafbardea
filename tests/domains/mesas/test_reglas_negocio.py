"""Reglas de negocio del dominio Mesas.

Cada prueba corresponde a un defecto observado ejecutando el codigo real.
"""
from datetime import datetime
from decimal import Decimal

import pytest

from app.domains.mesas.schemas import ReservarMesa
from app.domains.mesas.services import MesaService
from app.domains.ventas.schemas import DetalleVentaCreate, PagoCreate, TipoPago, VentaCreate
from app.domains.ventas.services import VentaService
from app.models import Mesa, Producto, ReservaMesa, Venta


@pytest.fixture
def mesas(db_session):
    return MesaService(db_session)


@pytest.fixture
def ventas(db_session):
    return VentaService(db_session)


@pytest.fixture
def mesa(db_session):
    m = db_session.query(Mesa).first()
    db_session.query(Venta).filter(
        Venta.mesa_id == m.id,
        Venta.estado.in_(["abierta", "suspendida"]),
    ).update({"estado": "cancelada"}, synchronize_session=False)
    m.estado = "libre"
    m.fecha_apertura = None
    m.mesero_id = None
    m.comensales = None
    m.mesa_padre_id = None
    db_session.commit()
    return m


@pytest.fixture
def producto(db_session):
    p = db_session.query(Producto).filter(Producto.activo == True).first()
    p.existencias = Decimal("500")
    p.precio_venta = Decimal("10000")
    db_session.commit()
    return p


def _venta_en_mesa(producto, mesa_id):
    return VentaCreate(
        mesa_id=mesa_id, tipo_venta="en_mesa",
        detalles=[DetalleVentaCreate(producto_id=producto.id,
                                     cantidad=Decimal("1"),
                                     precio=producto.precio_venta)],
    )


class TestEstadosCoherentes:
    def test_el_estado_libre_es_el_unico_valido(self, mesas, mesa):
        """Antes Mesas usaba 'disponible' y el resto del sistema 'libre'."""
        assert mesa.estado == "libre"
        mesas.ocupar_mesa(mesa.id, venta_id=1)
        assert mesa.estado == "ocupada"

    def test_ocupar_desde_libre_ya_no_falla(self, mesas, mesa):
        """Antes: ocupar_mesa exigia 'disponible' y rechazaba 'libre'."""
        resultado = mesas.ocupar_mesa(mesa.id, venta_id=1)
        assert resultado.estado == "ocupada"

    def test_floor_plan_cuenta_las_mesas_libres(self, mesas, db_session):
        """Antes el plano contaba 0 disponibles porque buscaba otro estado."""
        for m in db_session.query(Mesa).all():
            m.estado = "libre"
        db_session.commit()
        fp = mesas.obtener_floor_plan()
        assert fp["estadisticas"]["mesas_disponibles"] == fp["estadisticas"]["total_mesas"]


class TestDatosOperativos:
    def test_ocupar_registra_hora_mesero_y_comensales(self, mesas, mesa):
        """Antes no se sabia cuanto llevaba ocupada ni quien la atendia."""
        mesas.ocupar_mesa(mesa.id, venta_id=1, mesero_id=1, comensales=3)
        assert mesa.fecha_apertura is not None
        assert mesa.mesero_id == 1
        assert mesa.comensales == 3
        assert mesa.minutos_ocupada() is not None

    def test_no_admite_mas_comensales_que_capacidad(self, mesas, mesa):
        with pytest.raises(ValueError, match="admite"):
            mesas.ocupar_mesa(mesa.id, venta_id=1, comensales=mesa.capacidad + 5)

    def test_liberar_limpia_los_datos_del_servicio(self, mesas, mesa):
        mesas.ocupar_mesa(mesa.id, venta_id=1, mesero_id=1, comensales=2)
        mesas.liberar_mesa(mesa.id)
        assert mesa.estado == "libre"
        assert mesa.fecha_apertura is None
        assert mesa.mesero_id is None

    def test_consumo_acumulado(self, mesas, ventas, mesa, producto):
        ventas.crear_venta(_venta_en_mesa(producto, mesa.id), usuario_id=1, empresa_id=1)
        assert mesas.consumo_actual(mesa.id) == Decimal("10000")

    def test_detalle_mesa_reune_todo(self, mesas, ventas, mesa, producto):
        ventas.crear_venta(_venta_en_mesa(producto, mesa.id), usuario_id=1, empresa_id=1)
        d = mesas.detalle_mesa(mesa.id)
        assert d["estado"] == "ocupada"
        assert d["consumo"] == Decimal("10000")
        assert d["ventas_abiertas"] == 1
        assert d["minutos_ocupada"] is not None


class TestLiberacionSegura:
    def test_no_libera_con_ventas_abiertas(self, mesas, ventas, mesa, producto):
        """Antes se liberaba sin comprobar nada, dejando ventas huerfanas."""
        ventas.crear_venta(_venta_en_mesa(producto, mesa.id), usuario_id=1, empresa_id=1)
        with pytest.raises(ValueError, match="venta"):
            mesas.liberar_mesa(mesa.id)

    def test_forzar_permite_liberar(self, mesas, ventas, mesa, producto):
        ventas.crear_venta(_venta_en_mesa(producto, mesa.id), usuario_id=1, empresa_id=1)
        assert mesas.liberar_mesa(mesa.id, forzar=True).estado == "libre"

    def test_pagar_libera_la_mesa(self, mesas, ventas, mesa, producto):
        v = ventas.crear_venta(_venta_en_mesa(producto, mesa.id), usuario_id=1, empresa_id=1)
        ventas.procesar_pago(v.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO, monto=v.total),
                             empresa_id=1)
        assert mesa.estado == "libre"
        assert mesa.fecha_apertura is None


class TestReservas:
    def test_la_reserva_se_persiste(self, mesas, mesa, db_session):
        """El esquema existia desde el principio, pero los datos se descartaban."""
        r = mesas.reservar(mesa.id, ReservarMesa(
            cliente_nombre="Ana Gomez", telefono="3001234567", personas=2))
        assert db_session.get(ReservaMesa, r.id) is not None
        assert r.cliente_nombre == "Ana Gomez"
        assert mesa.estado == "reservada"

    def test_no_reserva_mas_personas_que_capacidad(self, mesas, mesa):
        with pytest.raises(ValueError, match="admite"):
            mesas.reservar(mesa.id, ReservarMesa(
                cliente_nombre="Grupo", personas=mesa.capacidad + 10))

    def test_no_reserva_mesa_ocupada(self, mesas, mesa):
        mesas.ocupar_mesa(mesa.id, venta_id=1)
        with pytest.raises(ValueError, match="ocupada"):
            mesas.reservar(mesa.id, ReservarMesa(cliente_nombre="Luis", personas=1))

    def test_cancelar_reserva_libera_la_mesa(self, mesas, mesa):
        r = mesas.reservar(mesa.id, ReservarMesa(cliente_nombre="Ana", personas=2))
        mesas.cancelar_reserva(r.id)
        assert mesa.estado == "libre"

    def test_mesa_reservada_puede_ocuparse(self, mesas, mesa):
        mesas.reservar(mesa.id, ReservarMesa(cliente_nombre="Ana", personas=2))
        assert mesas.ocupar_mesa(mesa.id, venta_id=1).estado == "ocupada"


class TestUnirYTransferir:
    def test_unir_mesas(self, mesas, mesa, db_session):
        otra = db_session.query(Mesa).filter(Mesa.id != mesa.id).first()
        otra.estado = "libre"
        otra.mesa_padre_id = None
        db_session.commit()

        mesas.unir_mesas(mesa.id, [otra.id])
        assert otra.mesa_padre_id == mesa.id
        assert otra.estado == "ocupada"
        assert mesa.estado == "ocupada"

    def test_no_unir_consigo_misma(self, mesas, mesa):
        with pytest.raises(ValueError, match="consigo misma"):
            mesas.unir_mesas(mesa.id, [mesa.id])

    def test_separar_deshace_la_union(self, mesas, mesa, db_session):
        otra = db_session.query(Mesa).filter(Mesa.id != mesa.id).first()
        otra.estado = "libre"
        otra.mesa_padre_id = None
        db_session.commit()

        mesas.unir_mesas(mesa.id, [otra.id])
        mesas.separar_mesas(mesa.id)
        assert otra.mesa_padre_id is None
        assert otra.estado == "libre"

    def test_transferir_venta_a_otra_mesa(self, mesas, ventas, mesa, producto, db_session):
        destino = db_session.query(Mesa).filter(Mesa.id != mesa.id).first()
        db_session.query(Venta).filter(
            Venta.mesa_id == destino.id,
            Venta.estado.in_(["abierta", "suspendida"]),
        ).update({"estado": "cancelada"}, synchronize_session=False)
        destino.estado = "libre"
        db_session.commit()

        v = ventas.crear_venta(_venta_en_mesa(producto, mesa.id), usuario_id=1, empresa_id=1)
        mesas.transferir_venta(v.id, destino.id)

        assert v.mesa_id == destino.id
        assert destino.estado == "ocupada"
        assert mesa.estado == "libre"  # la de origen queda libre

    def test_no_transferir_venta_cerrada(self, mesas, ventas, mesa, producto, db_session):
        destino = db_session.query(Mesa).filter(Mesa.id != mesa.id).first()
        v = ventas.crear_venta(_venta_en_mesa(producto, mesa.id), usuario_id=1, empresa_id=1)
        ventas.procesar_pago(v.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO, monto=v.total),
                             empresa_id=1)
        with pytest.raises(ValueError, match="transferir"):
            mesas.transferir_venta(v.id, destino.id)
