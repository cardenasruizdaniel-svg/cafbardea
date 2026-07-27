"""Reglas de negocio del dominio Produccion.

Cada prueba corresponde a un defecto observado ejecutando el codigo real.
"""
from decimal import Decimal

import pytest

from app.domains.produccion.services import ProduccionService
from app.models import (
    ConsumoProduccion, MovimientoInventario, OrdenProduccion, Producto, Receta,
)


@pytest.fixture
def svc(db_session):
    return ProduccionService(db_session)


_contador = [0]

def _nuevo_producto(db_session, nombre, tipo, existencias, costo):
    from app.models import Categoria
    cat = db_session.query(Categoria).first()
    _contador[0] += 1
    p = Producto(empresa_id=1, categoria_id=cat.id if cat else None,
                 codigo=f"TEST-{nombre}-{_contador[0]}", nombre=nombre, tipo=tipo,
                 precio_venta=Decimal("0"), costo=Decimal(str(costo)),
                 existencias=Decimal(str(existencias)), stock_minimo=Decimal("0"),
                 activo=True)
    db_session.add(p); db_session.commit()
    return p


@pytest.fixture
def insumos(db_session):
    """Dos insumos con existencias y costo conocidos."""
    harina = _nuevo_producto(db_session, "Harina", "insumo", 100, 2000)
    agua = _nuevo_producto(db_session, "Agua", "insumo", 200, 500)
    return harina, agua


@pytest.fixture
def elaborado(db_session):
    """Un producto que sera el resultado de la produccion."""
    return _nuevo_producto(db_session, "Masa", "elaborado", 0, 0)


@pytest.fixture
def receta(db_session, svc, elaborado, insumos):
    harina, agua = insumos
    r = svc.crear_receta(elaborado.id, rendimiento=Decimal("10"))
    svc.agregar_insumo(r.id, harina.id, Decimal("5"))          # 5 harina
    svc.agregar_insumo(r.id, agua.id, Decimal("2"), merma_porcentaje=Decimal("10"))  # 2 agua + 10%
    db_session.commit()
    return r


class TestCosteo:
    def test_costear_receta_sin_ejecutar(self, svc, receta, db_session):
        """Antes no se podia saber el costo de un elaborado hasta producirlo."""
        c = svc.costear_receta(receta.id, lotes=Decimal("1"))
        # 5 harina * 2000 = 10000; 2 agua * 1.10 * 500 = 1100 -> 11100 / 10 unid
        assert c["costo_insumos"] == Decimal("11100.00")
        assert c["unidades"] == Decimal("10")
        assert c["costo_unitario"] == Decimal("1110.00")

    def test_costeo_incluye_merma(self, svc, receta):
        c = svc.costear_receta(receta.id)
        agua = [l for l in c["lineas"] if l["rol"] == "insumo"][1]
        assert agua["cantidad"] == Decimal("2.200")  # 2 + 10%


class TestEjecucion:
    def test_ejecutar_consume_y_produce_por_kardex(self, svc, receta, insumos,
                                                   elaborado, db_session):
        """Antes consumir_receta restaba a mano, sin pasar por el kardex."""
        harina, agua = insumos
        orden = svc.ejecutar(receta.id, Decimal("2"), usuario_id=1)  # 2 lotes
        db_session.commit()

        db_session.refresh(harina); db_session.refresh(agua); db_session.refresh(elaborado)
        assert harina.existencias == Decimal("90")   # 100 - 5*2
        assert agua.existencias == Decimal("195.6")  # 200 - 2*2*1.10
        assert elaborado.existencias == Decimal("20")  # 10 * 2

        # El consumo aparece en el kardex CON saldos
        from app.domains.inventario.services import InventarioService
        kardex = InventarioService(db_session).kardex(harina.id)
        consumo = [f for f in kardex if f["referencia"] == orden.numero]
        assert consumo and consumo[0]["salida"] == Decimal("10")

    def test_costo_del_elaborado_es_correcto(self, svc, receta, elaborado, db_session):
        svc.ejecutar(receta.id, Decimal("1"), usuario_id=1)
        db_session.commit()
        db_session.refresh(elaborado)
        assert elaborado.costo == Decimal("1110.00")

    def test_merma_queda_registrada(self, svc, receta, db_session):
        """Antes la merma solo inflaba el consumo, sin dejar rastro."""
        orden = svc.ejecutar(receta.id, Decimal("1"), usuario_id=1)
        db_session.commit()
        # agua: base 2, merma 0.2, a $500 = $100 de merma
        assert orden.merma_valor == Decimal("100.00")
        consumos = db_session.query(ConsumoProduccion).filter_by(orden_id=orden.id).all()
        agua_consumo = [c for c in consumos if c.cantidad_merma > 0]
        assert agua_consumo and agua_consumo[0].cantidad_merma == Decimal("0.200")

    def test_inventario_insuficiente_se_bloquea(self, svc, receta, insumos, db_session):
        harina, _ = insumos
        harina.existencias = Decimal("3")  # se necesitan 5
        db_session.commit()
        with pytest.raises(ValueError, match="insuficiente"):
            svc.ejecutar(receta.id, Decimal("1"))

    def test_no_ejecuta_receta_de_venta(self, svc, elaborado, db_session):
        r = svc.crear_receta(elaborado.id, tipo_receta="venta")
        db_session.commit()
        with pytest.raises(ValueError, match="produccion"):
            svc.ejecutar(r.id, Decimal("1"))

    def test_lotes_cero_se_rechaza(self, svc, receta):
        with pytest.raises(ValueError, match="mayores que cero"):
            svc.ejecutar(receta.id, Decimal("0"))


class TestAprovechables:
    def test_aprovechable_abarata_el_principal(self, svc, elaborado, insumos, db_session):
        """Un subproducto valorizado descuenta del costo del producto final."""
        harina, agua = insumos
        aprov = _nuevo_producto(db_session, "Huesos", "insumo", 0, 0)

        r = svc.crear_receta(elaborado.id, rendimiento=Decimal("10"))
        svc.agregar_insumo(r.id, harina.id, Decimal("5"))   # 5*2000 = 10000
        svc.agregar_aprovechable(r.id, aprov.id, Decimal("2"), Decimal("500"))  # -1000
        db_session.commit()

        orden = svc.ejecutar(r.id, Decimal("1"), usuario_id=1)
        db_session.commit()
        db_session.refresh(elaborado); db_session.refresh(aprov)

        # costo neto = 10000 - 1000 = 9000 / 10 = 900
        assert orden.valor_aprovechables == Decimal("1000.00")
        assert elaborado.costo == Decimal("900.00")
        assert aprov.existencias == Decimal("2")  # el aprovechable ingreso


class TestAnulacion:
    def test_anular_revierte_todo(self, svc, receta, insumos, elaborado, db_session):
        """Antes no existia: una produccion mal hecha no tenia retorno."""
        harina, agua = insumos
        orden = svc.ejecutar(receta.id, Decimal("2"), usuario_id=1)
        db_session.commit()
        db_session.refresh(harina)
        assert harina.existencias == Decimal("90")

        svc.anular(orden.id, "Error en la formula", usuario_id=1)
        db_session.commit()
        db_session.refresh(harina); db_session.refresh(agua); db_session.refresh(elaborado)

        assert orden.estado == "anulada"
        assert harina.existencias == Decimal("100")  # insumo devuelto
        assert agua.existencias == Decimal("200")
        assert elaborado.existencias == Decimal("0")  # producto retirado

    def test_anular_exige_motivo(self, svc, receta, db_session):
        orden = svc.ejecutar(receta.id, Decimal("1"))
        db_session.commit()
        with pytest.raises(ValueError, match="motivo"):
            svc.anular(orden.id, "")

    def test_no_anular_si_el_producto_ya_se_consumio(self, svc, receta,
                                                     elaborado, db_session):
        orden = svc.ejecutar(receta.id, Decimal("1"))
        db_session.commit()
        elaborado.existencias = Decimal("2")  # se vendio parte
        db_session.commit()
        with pytest.raises(ValueError, match="ya se consumio"):
            svc.anular(orden.id, "Tardio")

    def test_no_anular_dos_veces(self, svc, receta, db_session):
        orden = svc.ejecutar(receta.id, Decimal("1"))
        db_session.commit()
        svc.anular(orden.id, "Primera")
        db_session.commit()
        with pytest.raises(ValueError, match="ya esta anulada"):
            svc.anular(orden.id, "Segunda")


class TestRecetas:
    def test_no_duplica_receta(self, svc, elaborado, db_session):
        svc.crear_receta(elaborado.id)
        db_session.commit()
        with pytest.raises(ValueError, match="ya tiene receta"):
            svc.crear_receta(elaborado.id)

    def test_insumo_no_puede_ser_el_mismo_producto(self, svc, elaborado, db_session):
        r = svc.crear_receta(elaborado.id)
        db_session.commit()
        with pytest.raises(ValueError, match="propia receta"):
            svc.agregar_insumo(r.id, elaborado.id, Decimal("1"))


class TestIndicadores:
    def test_indicadores(self, svc, receta, db_session):
        svc.ejecutar(receta.id, Decimal("1"), usuario_id=1)
        db_session.commit()
        ind = svc.indicadores()
        assert ind["ordenes"] >= 1
        assert ind["costo_producido"] > 0
        assert ind["merma_valor"] >= 0
