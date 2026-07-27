"""Modo offline de la app de cliente y enlaces a apps (solo admin)."""
import pytest

from app.models import Usuario


class TestServiceWorkerCliente:
    def test_sw_cliente_se_sirve(self, client):
        r = client.get("/sw-cliente.js")
        assert r.status_code == 200
        assert "javascript" in r.headers.get("content-type", "")

    def test_sw_cliente_scope_header(self, client):
        r = client.get("/sw-cliente.js")
        assert r.headers.get("service-worker-allowed") == "/cliente"

    def test_pagina_cliente_registra_sw(self, client):
        r = client.get("/cliente")
        assert "/sw-cliente.js" in r.text

    def test_pagina_cliente_tiene_cola_offline(self, client):
        r = client.get("/cliente")
        # la logica de cola offline y cache de carta debe estar presente
        assert "cola_pedidos" in r.text
        assert "carta_cache" in r.text
        assert "procesarCola" in r.text


class TestEnlacesApps:
    def test_admin_ve_seccion_apps(self, client_autenticado):
        r = client_autenticado.get("/dashboard")
        assert "Apps (revisar)" in r.text
        assert "App de cliente" in r.text
        assert "App de meseros" in r.text

    def test_mesero_no_ve_seccion_apps(self, client, db_session):
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(usuario="mesero_apps", password_hash=pwd.hash("Test123*"),
                               rol="mesero", activo=True, acceso_web=True))
        db_session.commit()
        client.post("/login", data={"usuario": "mesero_apps", "password": "Test123*"})
        r = client.get("/dashboard")
        assert "Apps (revisar)" not in r.text
