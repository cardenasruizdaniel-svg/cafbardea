"""Reglas de negocio de Inventario.

Cada prueba corresponde a un defecto observado ejecutando el codigo antes
de corregirlo.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domains.inventario.services import InventarioService
from app.models import AlertaStock, Empresa, ExistenciaBodega, Lote, MovimientoInventario, Producto


@pytest.fixture
def inv(db_session):
    return InventarioService(db_session)


@pytest.fixture
def producto(db_session):
    p = db_session.query(Producto).filter(Producto.activo == True).first()
    p.existencias = Decimal("10")
    p.costo = Decimal("1000")
    p.stock_minimo = Decimal("5")
    db_session.commit()
    return p


class TestCostoPromedio:
    def test_entrada_recalcula_promedio_ponderado(self, inv, producto, db_session):
        """Antes: /inventario/movimiento guardaba el costo y lo ignoraba.

        10 unidades a $1.000 + 10 a $2.000 debe dar promedio $1.500.
        """
        inv.registrar_movimiento(producto.id, "entrada", Decimal("10"),
                                 costo_unitario=Decimal("2000"))
        db_session.commit()
        db_session.refresh(producto)
        assert producto.costo == Decimal("1500")
        assert producto.existencias == Decimal("20")

    def test_salida_no_altera_el_costo(self, inv, producto, db_session):
        inv.registrar_movimiento(producto.id, "salida", Decimal("5"))
        db_session.commit()
        db_session.refresh(producto)
        assert producto.costo == Decimal("1000")
        assert producto.existencias == Decimal("5")

    def test_entrada_sin_costo_conserva_el_promedio(self, inv, producto, db_session):
        inv.registrar_movimiento(producto.id, "entrada", Decimal("10"))
        db_session.commit()
        db_session.refresh(producto)
        assert producto.costo == Decimal("1000")


class TestValidaciones:
    def test_salida_mayor_al_stock_se_bloquea_si_la_empresa_lo_prohibe(
            self, inv, producto, db_session):
        """Antes: existencias 2, salida de 100 -> -98 sin validacion alguna."""
        empresa = db_session.get(Empresa, 1)
        empresa.permitir_stock_negativo = False
        db_session.commit()
        try:
            with pytest.raises(ValueError, match="Stock insuficiente"):
                inv.registrar_movimiento(producto.id, "salida", Decimal("100"))
        finally:
            empresa.permitir_stock_negativo = True
            db_session.commit()

    def test_salida_negativa_permitida_genera_alerta(self, inv, producto, db_session):
        empresa = db_session.get(Empresa, 1)
        empresa.permitir_stock_negativo = True
        db_session.commit()

        inv.registrar_movimiento(producto.id, "salida", Decimal("30"),
                                 referencia="PRUEBA-NEG")
        db_session.commit()
        db_session.refresh(producto)
        assert producto.existencias == Decimal("-20")

        alerta = db_session.query(AlertaStock).filter_by(
            producto_id=producto.id, tipo="negativo").first()
        assert alerta is not None

    def test_cantidad_cero_o_negativa_se_rechaza(self, inv, producto):
        with pytest.raises(ValueError, match="mayor que cero"):
            inv.registrar_movimiento(producto.id, "entrada", Decimal("0"))
        with pytest.raises(ValueError, match="mayor que cero"):
            inv.registrar_movimiento(producto.id, "salida", Decimal("-5"))

    def test_tipo_invalido_se_rechaza(self, inv, producto):
        with pytest.raises(ValueError, match="no valido"):
            inv.registrar_movimiento(producto.id, "cualquier_cosa", Decimal("1"))

    def test_bajo_minimo_genera_alerta(self, inv, producto, db_session):
        inv.registrar_movimiento(producto.id, "salida", Decimal("6"))
        db_session.commit()
        alerta = db_session.query(AlertaStock).filter_by(
            producto_id=producto.id, tipo="bajo_minimo").first()
        assert alerta is not None


class TestKardex:
    def test_kardex_registra_saldos(self, inv, producto, db_session):
        """Antes no existia kardex: cero menciones en todo el codigo."""
        inv.registrar_movimiento(producto.id, "entrada", Decimal("10"),
                                 costo_unitario=Decimal("2000"), referencia="E1")
        inv.registrar_movimiento(producto.id, "salida", Decimal("5"), referencia="S1")
        db_session.commit()

        filas = inv.kardex(producto.id)
        assert len(filas) >= 2
        entrada = [f for f in filas if f["referencia"] == "E1"][0]
        salida = [f for f in filas if f["referencia"] == "S1"][0]

        assert entrada["entrada"] == Decimal("10")
        assert entrada["saldo"] == Decimal("20")
        assert entrada["costo_promedio"] == Decimal("1500")
        assert salida["salida"] == Decimal("5")
        assert salida["saldo"] == Decimal("15")

    def test_kardex_calcula_valor_del_saldo(self, inv, producto, db_session):
        inv.registrar_movimiento(producto.id, "entrada", Decimal("10"),
                                 costo_unitario=Decimal("2000"))
        db_session.commit()
        ultima = inv.kardex(producto.id)[-1]
        assert ultima["valor_saldo"] == Decimal("20") * Decimal("1500")


class TestBodegas:
    def test_se_crea_bodega_principal_automaticamente(self, inv, db_session):
        b = inv.bodega_principal(1)
        db_session.commit()
        assert b.es_principal is True

    def test_movimiento_actualiza_existencia_por_bodega(self, inv, producto, db_session):
        b = inv.bodega_principal(1)
        db_session.commit()
        antes = inv.existencia_en(producto.id, b.id)
        inv.registrar_movimiento(producto.id, "entrada", Decimal("7"), bodega_id=b.id)
        db_session.commit()
        assert inv.existencia_en(producto.id, b.id) == antes + Decimal("7")

    def test_traslado_mueve_entre_bodegas_sin_alterar_total(self, inv, producto, db_session):
        origen = inv.bodega_principal(1)
        destino = inv.crear_bodega("COCINA", "Cocina")
        inv.registrar_movimiento(producto.id, "entrada", Decimal("20"), bodega_id=origen.id)
        db_session.commit()
        total_antes = producto.existencias

        inv.trasladar(producto.id, origen.id, destino.id, Decimal("8"))
        db_session.commit()
        db_session.refresh(producto)

        assert inv.existencia_en(producto.id, destino.id) == Decimal("8")
        assert producto.existencias == total_antes  # el total no cambia

    def test_traslado_sin_stock_en_origen_se_rechaza(self, inv, producto, db_session):
        origen = inv.bodega_principal(1)
        destino = inv.crear_bodega("BARRA", "Barra")
        db_session.commit()
        with pytest.raises(ValueError, match="disponibles"):
            inv.trasladar(producto.id, origen.id, destino.id, Decimal("99999"))

    def test_traslado_a_la_misma_bodega_se_rechaza(self, inv, producto, db_session):
        b = inv.bodega_principal(1)
        db_session.commit()
        with pytest.raises(ValueError, match="no pueden ser la misma"):
            inv.trasladar(producto.id, b.id, b.id, Decimal("1"))


class TestLotesYVencimientos:
    def test_crear_lote_ingresa_stock(self, inv, producto, db_session):
        antes = producto.existencias
        lote = inv.crear_lote(producto.id, "L-001", Decimal("12"),
                              costo_unitario=Decimal("1200"),
                              fecha_vencimiento=date.today() + timedelta(days=10))
        db_session.commit()
        db_session.refresh(producto)
        assert producto.existencias == antes + Decimal("12")
        assert lote.cantidad_disponible == Decimal("12")

    def test_detecta_lotes_por_vencer(self, inv, producto, db_session):
        inv.crear_lote(producto.id, "L-PRONTO", Decimal("5"),
                       fecha_vencimiento=date.today() + timedelta(days=3))
        inv.crear_lote(producto.id, "L-LEJANO", Decimal("5"),
                       fecha_vencimiento=date.today() + timedelta(days=300))
        db_session.commit()
        codigos = [l.codigo for l in inv.lotes_por_vencer(dias=30)]
        assert "L-PRONTO" in codigos
        assert "L-LEJANO" not in codigos

    def test_detecta_lotes_vencidos(self, inv, producto, db_session):
        inv.crear_lote(producto.id, "L-VENCIDO", Decimal("4"),
                       fecha_vencimiento=date.today() - timedelta(days=1))
        db_session.commit()
        assert "L-VENCIDO" in [l.codigo for l in inv.lotes_vencidos()]

    def test_lote_sin_vencimiento_no_aparece_como_proximo(self, inv, producto, db_session):
        inv.crear_lote(producto.id, "L-SIN-FECHA", Decimal("3"))
        db_session.commit()
        assert "L-SIN-FECHA" not in [l.codigo for l in inv.lotes_por_vencer(dias=365)]


class TestAlertas:
    def test_las_alertas_se_pueden_consultar(self, inv, producto, db_session):
        """Ventas ya las generaba, pero ninguna vista las leia."""
        inv.registrar_movimiento(producto.id, "salida", Decimal("50"))
        db_session.commit()
        assert len(inv.alertas_pendientes()) >= 1


class TestValoracion:
    def test_valor_inventario_usa_costo_promedio(self, inv, producto, db_session):
        inv.registrar_movimiento(producto.id, "entrada", Decimal("10"),
                                 costo_unitario=Decimal("2000"))
        db_session.commit()
        assert inv.valor_inventario(1) > 0
