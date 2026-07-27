"""Blindaje HTTP: cabeceras de seguridad, CSRF y rate limiting."""
import re

import pytest


class TestСabecerasSeguridad:
    def test_headers_presentes_en_login(self, client):
        r = client.get("/login")
        h = r.headers
        assert "content-security-policy" in h
        assert h["x-frame-options"] == "DENY"
        assert h["x-content-type-options"] == "nosniff"
        assert h["referrer-policy"] == "same-origin"
        assert "permissions-policy" in h

    def test_csp_restringe_origenes(self, client):
        r = client.get("/login")
        csp = r.headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

    def test_headers_en_toda_respuesta(self, client):
        # Incluso un 404 debe traer las cabeceras.
        r = client.get("/ruta-inexistente-xyz")
        assert "x-frame-options" in r.headers


class TestCSRF:
    def _token(self, client):
        r = client.get("/login")
        m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
        return m.group(1) if m else None

    def test_post_sin_token_rechazado(self, client_autenticado):
        # Peticion con token explicitamente invalido en header y form.
        # Se salta el wrapper llamando al request base de TestClient.
        from starlette.testclient import TestClient
        r = TestClient.request(
            client_autenticado, "POST", "/clientes",
            data={"nombre": "X", "documento": "1", "csrf_token": "malo"},
            headers={"X-CSRF-Token": "malo"},
            follow_redirects=False)
        assert r.status_code == 403

    def test_login_exento_de_csrf(self, client):
        # El login no debe exigir CSRF (aun no hay sesion).
        r = client.post("/login",
                        data={"usuario": "noexiste", "password": "x"},
                        follow_redirects=False)
        # No es 403 por CSRF; es redirect (credenciales invalidas) o 200.
        assert r.status_code != 403

    def test_get_no_requiere_csrf(self, client_autenticado):
        r = client_autenticado.get("/empleados")
        assert r.status_code == 200


class TestRateLimit:
    def test_rate_limit_desactivado_en_tests(self, client):
        # En el entorno de pruebas el rate limit esta apagado; multiples
        # peticiones no deben producir 429.
        for _ in range(15):
            r = client.get("/login")
            assert r.status_code != 429


class TestRateLimitUnitario:
    """Prueba la ventana deslizante directamente, sin depender del entorno."""

    def test_ventana_bloquea_tras_limite(self):
        from app.security.rate_limit import _Ventana
        v = _Ventana()
        # 3 permitidos, el 4o bloqueado en la misma ventana.
        assert v.permitido("k", 3, 60)
        assert v.permitido("k", 3, 60)
        assert v.permitido("k", 3, 60)
        assert not v.permitido("k", 3, 60)

    def test_claves_independientes(self):
        from app.security.rate_limit import _Ventana
        v = _Ventana()
        assert v.permitido("ip1", 1, 60)
        assert not v.permitido("ip1", 1, 60)
        # otra IP no se ve afectada
        assert v.permitido("ip2", 1, 60)
