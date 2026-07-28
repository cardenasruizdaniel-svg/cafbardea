"""Modulo del mesero: plano propio, toma de pedidos, impresion incremental,
y la regla de que el mesero no puede cobrar."""
import re

import pytest

from app.models import Mesa, Producto, Venta, DetalleVenta
from app.domains.impresion.services import ImpresionService
from app.domains.ventas.services import VentaService
from app.domains.ventas.schemas import VentaCreate, DetalleVentaCreate, TipoVenta


def _prod(db, n=1):
    return db.query(Producto).filter(Producto.precio_venta > 0).limit(n).all()


class TestImpresionIncremental:
    def _venta_mesa(self, db, items):
        mesa = db.query(Mesa).first()
        detalles = [DetalleVentaCreate(producto_id=p.id, cantidad=c,
                                       precio=p.precio_venta) for p, c in items]
        v = VentaService(db).crear_venta(
            VentaCreate(tipo_venta=TipoVenta.EN_MESA, mesa_id=mesa.id,
                        detalles=detalles), usuario_id=1, empresa_id=1)
        db.commit()
        return v

    def test_primera_comanda_imprime_todo(self, db_session):
        prods = _prod(db_session, 2)
        v = self._venta_mesa(db_session, [(prods[0], 2), (prods[1], 1)])
        r = ImpresionService(db_session).comandar_venta(v.id)
        db_session.commit()
        assert r["primera"] is True
        assert r["nuevas"] == 2

    def test_recomandar_solo_lo_nuevo(self, db_session):
        prods = _prod(db_session, 2)
        v = self._venta_mesa(db_session, [(prods[0], 1)])
        ImpresionService(db_session).comandar_venta(v.id)
        db_session.commit()
        # agregar otro producto
        db_session.add(DetalleVenta(venta_id=v.id, producto_id=prods[1].id,
                                    cantidad=3, precio=prods[1].precio_venta))
        db_session.commit()
        r = ImpresionService(db_session).comandar_venta(v.id)
        db_session.commit()
        assert r["primera"] is False
        assert r["nuevas"] == 1  # solo el nuevo

    def test_comandar_sin_cambios_no_imprime(self, db_session):
        prods = _prod(db_session, 1)
        v = self._venta_mesa(db_session, [(prods[0], 1)])
        svc = ImpresionService(db_session)
        svc.comandar_venta(v.id)
        db_session.commit()
        r = svc.comandar_venta(v.id)
        db_session.commit()
        assert r["nuevas"] == 0


class TestModuloMesero:
    def _login_mesero(self, client, db_session):
        from app.models import Usuario
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if not db_session.query(Usuario).filter_by(usuario="mesero_t").first():
            db_session.add(Usuario(usuario="mesero_t",
                                   password_hash=pwd.hash("Test123*"),
                                   rol="mesero", activo=True, acceso_web=True))
            db_session.commit()
        client.post("/login", data={"usuario": "mesero_t", "password": "Test123*"})

    def test_plano_mesero_es_propio(self, client, db_session):
        self._login_mesero(client, db_session)
        r = client.get("/mobile/mesas")
        assert r.status_code == 200
        assert "Toca una mesa" in r.text  # su propia interfaz, no la web

    def test_mesero_toma_pedido_y_comanda(self, client, db_session):
        self._login_mesero(client, db_session)
        # usar una mesa sin venta abierta para aislar el conteo
        from app.models import Venta
        mesas = db_session.query(Mesa).all()
        mesa = None
        for m in mesas:
            abierta = db_session.query(Venta).filter_by(
                mesa_id=m.id, estado="abierta").first()
            if not abierta:
                mesa = m
                break
        assert mesa is not None, "no hay mesa libre para la prueba"
        prod = _prod(db_session, 1)[0]
        r = client.post(f"/api/mesero/mesa/{mesa.id}/agregar",
                        json={"producto_id": prod.id, "cantidad": 2})
        assert r.status_code == 200
        r = client.post(f"/api/mesero/mesa/{mesa.id}/comandar")
        assert r.status_code == 200
        d = r.json()
        assert d["primera"] is True
        assert d["nuevas"] >= 1  # al menos el producto que agregamos

    def test_mesero_sin_sesion_bloqueado(self, client):
        r = client.post("/api/mesero/mesa/1/comandar")
        assert r.status_code == 401


class TestMeseroNoCobra:
    def test_pagar_exige_rol_caja(self, db_session):
        """La regla de negocio: el mesero NO puede cobrar."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from app.main import exigir_rol
        req = MagicMock()
        req.session = {"rol": "mesero"}
        with pytest.raises(HTTPException):
            exigir_rol(req, "cajero", "gerente")
        # cajero si puede
        req.session = {"rol": "cajero"}
        exigir_rol(req, "cajero", "gerente")  # no lanza
