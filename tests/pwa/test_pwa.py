"""PWA: manifest, service worker y pagina offline.

Estos recursos deben ser publicos (el navegador los pide antes de la sesion)
y servirse con los tipos correctos, sin romper el control de acceso del resto.
"""
import json


class TestRecursosPublicos:
    def test_manifest_es_publico(self, client):
        r = client.get("/manifest.webmanifest")
        assert r.status_code == 200
        assert "manifest" in r.headers["content-type"]
        data = json.loads(r.content)
        assert data["name"] == "CafBarDLA"
        assert data["display"] == "standalone"
        assert len(data["icons"]) >= 6

    def test_service_worker_es_publico(self, client):
        r = client.get("/sw.js")
        assert r.status_code == 200
        assert "javascript" in r.headers["content-type"]
        # Debe permitir scope raiz para interceptar navegaciones.
        assert r.headers.get("service-worker-allowed") == "/"

    def test_service_worker_sin_cache_http(self, client):
        r = client.get("/sw.js")
        assert "no-cache" in r.headers.get("cache-control", "")

    def test_offline_es_publico(self, client):
        r = client.get("/offline")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_iconos_existen(self, client):
        for size in (192, 512):
            r = client.get(f"/static/icons/icon-{size}.png")
            assert r.status_code == 200
            assert r.headers["content-type"] == "image/png"


class TestNoRompeSeguridad:
    def test_rutas_privadas_siguen_protegidas(self, client):
        # El dashboard sin sesion debe redirigir a login, no exponerse.
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code in (302, 303, 307)

    def test_manifest_no_expone_datos(self, client):
        # El manifest es estatico: no debe filtrar nada de negocio.
        r = client.get("/manifest.webmanifest")
        cuerpo = r.content.decode().lower()
        assert "password" not in cuerpo
        assert "secret" not in cuerpo


class TestServiceWorkerContenido:
    """Verifica reglas clave del SW leyendo el archivo servido."""

    def test_sw_no_cachea_post_ni_navegacion_autenticada(self, client):
        sw = client.get("/sw.js").content.decode()
        # Solo intercepta GET.
        assert 'req.method !== "GET"' in sw
        # Las navegaciones van a la red primero (network-first), no cache-first.
        assert "navigate" in sw
        # No se precachea ninguna ruta de navegacion autenticada. Se comprueba
        # que no aparezcan como entradas del array de precache (entre comillas).
        assert '"/dashboard"' not in sw
        assert '"/mesas"' not in sw
        assert '"/caja"' not in sw
