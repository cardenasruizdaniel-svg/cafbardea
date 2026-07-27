"""Impresión: cascada de resolución producto -> grupo -> por defecto."""
import pytest

from app.domains.impresion.services import ImpresionService
from app.models import Producto, GrupoImpresion, Impresora


@pytest.fixture
def svc(db_session):
    return ImpresionService(db_session)


@pytest.fixture
def setup_impresoras(db_session, svc):
    cocina = svc.crear_impresora("Cocina", "192.168.1.50", "red")
    barra = svc.crear_impresora("Barra", "192.168.1.51", "red")
    defecto = svc.crear_impresora("Caja", "local", "local", es_por_defecto=True)
    db_session.commit()
    grupo = svc.crear_grupo("Bebidas", impresora_id=barra.id)
    db_session.commit()
    return {"cocina": cocina, "barra": barra, "defecto": defecto, "grupo": grupo}


def _producto(db, **kw):
    import uuid
    p = Producto(codigo=uuid.uuid4().hex[:8], nombre=kw.pop("nombre", "P"),
                 precio_venta=1000, **kw)
    db.add(p)
    db.commit()
    return p


class TestCascada:
    def test_nivel1_impresora_del_producto(self, svc, setup_impresoras, db_session):
        p = _producto(db_session, impresora_id=setup_impresoras["cocina"].id)
        assert svc.resolver_impresora(p).nombre == "Cocina"

    def test_nivel2_impresora_del_grupo(self, svc, setup_impresoras, db_session):
        p = _producto(db_session, grupo_impresion_id=setup_impresoras["grupo"].id)
        assert svc.resolver_impresora(p).nombre == "Barra"

    def test_nivel3_por_defecto(self, svc, setup_impresoras, db_session):
        p = _producto(db_session)  # sin nada
        assert svc.resolver_impresora(p).nombre == "Caja"

    def test_producto_gana_sobre_grupo(self, svc, setup_impresoras, db_session):
        # Si el producto tiene impresora propia Y grupo, gana la del producto.
        p = _producto(db_session,
                      impresora_id=setup_impresoras["cocina"].id,
                      grupo_impresion_id=setup_impresoras["grupo"].id)
        assert svc.resolver_impresora(p).nombre == "Cocina"

    def test_sin_defecto_devuelve_none(self, svc, db_session):
        # Sin impresora por defecto configurada, un producto pelado no resuelve.
        db_session.query(Impresora).delete()
        db_session.commit()
        p = _producto(db_session)
        assert svc.resolver_impresora(p) is None


class TestAgrupacion:
    def test_agrupa_por_impresora(self, svc, setup_impresoras, db_session):
        p1 = _producto(db_session, nombre="Bandeja",
                       impresora_id=setup_impresoras["cocina"].id)
        p2 = _producto(db_session, nombre="Jugo",
                       grupo_impresion_id=setup_impresoras["grupo"].id)
        grupos = svc.agrupar_comanda([(p1, 2), (p2, 1)])
        assert "Cocina" in grupos
        assert "Barra" in grupos
        assert grupos["Cocina"]["lineas"][0]["cantidad"] == 2

    def test_sin_destino_va_a_grupo_especial(self, svc, db_session):
        # Sin impresoras configuradas, va a SIN_DESTINO.
        db_session.query(Impresora).delete()
        db_session.commit()
        p = _producto(db_session, nombre="Huerfano")
        grupos = svc.agrupar_comanda([(p, 1)])
        assert "SIN_DESTINO" in grupos


class TestGestion:
    def test_solo_una_por_defecto(self, svc, db_session):
        a = svc.crear_impresora("A", es_por_defecto=True)
        b = svc.crear_impresora("B", es_por_defecto=True)
        db_session.commit()
        db_session.refresh(a)
        # Al marcar B por defecto, A deja de serlo.
        assert b.es_por_defecto is True
        assert a.es_por_defecto is False

    def test_nombre_obligatorio(self, svc):
        with pytest.raises(ValueError):
            svc.crear_impresora("")
