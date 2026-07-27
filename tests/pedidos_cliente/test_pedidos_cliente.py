"""App de cliente: autoservicio y pedido en mesa, con gestion del personal."""
import pytest

from app.models import Producto, Mesa, PedidoCliente
from app.domains.pedidos_cliente.services import PedidoClienteService


def _prod(db):
    return db.query(Producto).filter(Producto.precio_venta > 0).first()


class TestServicio:
    def test_crear_autoservicio(self, db_session):
        p = _prod(db_session)
        svc = PedidoClienteService(db_session)
        ped = svc.crear_pedido(tipo="autoservicio", nombre_cliente="Ana",
                               items=[{"producto_id": p.id, "cantidad": 2}])
        db_session.commit()
        assert ped.estado == "pendiente"
        assert ped.total == p.precio_venta * 2
        assert len(ped.lineas) == 1

    def test_autoservicio_exige_nombre(self, db_session):
        p = _prod(db_session)
        svc = PedidoClienteService(db_session)
        with pytest.raises(ValueError):
            svc.crear_pedido(tipo="autoservicio", nombre_cliente="",
                             items=[{"producto_id": p.id, "cantidad": 1}])

    def test_mesa_exige_mesa(self, db_session):
        p = _prod(db_session)
        svc = PedidoClienteService(db_session)
        with pytest.raises(ValueError):
            svc.crear_pedido(tipo="mesa",
                             items=[{"producto_id": p.id, "cantidad": 1}])

    def test_aceptar_mesa_genera_venta(self, db_session):
        p = _prod(db_session)
        mesa = db_session.query(Mesa).first()
        svc = PedidoClienteService(db_session)
        ped = svc.crear_pedido(tipo="mesa", mesa_id=mesa.id,
                               items=[{"producto_id": p.id, "cantidad": 1}])
        db_session.commit()
        ped = svc.aceptar_pedido(ped.id, usuario_id=1)
        db_session.commit()
        assert ped.estado == "aceptado"
        assert ped.venta_id is not None

    def test_rechazar_mesa(self, db_session):
        p = _prod(db_session)
        mesa = db_session.query(Mesa).first()
        svc = PedidoClienteService(db_session)
        ped = svc.crear_pedido(tipo="mesa", mesa_id=mesa.id,
                               items=[{"producto_id": p.id, "cantidad": 1}])
        db_session.commit()
        ped = svc.rechazar_pedido(ped.id, motivo="Agotado")
        db_session.commit()
        assert ped.estado == "rechazado"
        assert ped.motivo_rechazo == "Agotado"

    def test_no_reprocesa(self, db_session):
        p = _prod(db_session)
        mesa = db_session.query(Mesa).first()
        svc = PedidoClienteService(db_session)
        ped = svc.crear_pedido(tipo="mesa", mesa_id=mesa.id,
                               items=[{"producto_id": p.id, "cantidad": 1}])
        db_session.commit()
        svc.rechazar_pedido(ped.id)
        db_session.commit()
        with pytest.raises(ValueError):
            svc.aceptar_pedido(ped.id)

    def test_cobrar_autoservicio_genera_venta(self, db_session):
        p = _prod(db_session)
        svc = PedidoClienteService(db_session)
        ped = svc.crear_pedido(tipo="autoservicio", nombre_cliente="Luis",
                               items=[{"producto_id": p.id, "cantidad": 1}])
        db_session.commit()
        venta = svc.cobrar_autoservicio(ped.id, usuario_id=1)
        db_session.commit()
        assert venta.estado == "abierta"
        assert ped.estado == "entregado"
        assert "Luis" in (venta.observacion or "")


class TestAPIPublica:
    def test_carta_publica_sin_login(self, client):
        r = client.get("/api/cliente/carta")
        assert r.status_code == 200
        assert len(r.json()["productos"]) > 0

    def test_crear_pedido_sin_login(self, client, db_session):
        p = _prod(db_session)
        r = client.post("/api/cliente/pedido", json={
            "tipo": "autoservicio", "nombre_cliente": "Web",
            "items": [{"producto_id": p.id, "cantidad": 1}]})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_pagina_cliente_carga(self, client):
        r = client.get("/cliente")
        assert r.status_code == 200

    def test_pendientes_requiere_login(self, client):
        r = client.get("/api/cliente/pendientes")
        assert r.status_code == 401


class TestGestion:
    def test_personal_ve_y_acepta(self, client_autenticado, db_session):
        p = _prod(db_session)
        mesa = db_session.query(Mesa).first()
        # crear pedido via servicio
        svc = PedidoClienteService(db_session)
        ped = svc.crear_pedido(tipo="mesa", mesa_id=mesa.id,
                               items=[{"producto_id": p.id, "cantidad": 1}])
        db_session.commit()
        # aceptar via API
        r = client_autenticado.post(f"/api/cliente/pedido/{ped.id}/aceptar")
        assert r.status_code == 200
        assert r.json()["venta_id"] is not None

    def test_vista_pendientes_carga(self, client_autenticado):
        r = client_autenticado.get("/pedidos-pendientes")
        assert r.status_code == 200
