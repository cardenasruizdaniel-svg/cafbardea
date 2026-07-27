"""Rediseño de escritorio: el tema claro se carga en las páginas del sistema."""


class TestTemaEscritorio:
    def test_css_tema_se_sirve(self, client_autenticado):
        r = client_autenticado.get("/static/css/tema-escritorio.css")
        assert r.status_code == 200
        assert "e-brand" in r.text  # variable del tema

    def test_paginas_referencian_tema(self, client_autenticado):
        for ruta in ["/dashboard", "/productos", "/informes"]:
            r = client_autenticado.get(ruta)
            assert r.status_code == 200
            assert "tema-escritorio.css" in r.text

    def test_ancho_aprovechado(self, client_autenticado):
        # El tema define un contenedor mas ancho para escritorio.
        r = client_autenticado.get("/static/css/tema-escritorio.css")
        assert "1800px" in r.text


class TestSinFranjaOscura:
    """El tema claro debe eliminar el fondo oscuro del app-container (franja azul)."""

    def test_tema_neutraliza_app_container(self, client_autenticado):
        r = client_autenticado.get("/static/css/tema-escritorio.css")
        # el tema debe forzar el fondo claro en app-container y body
        assert ".app-container" in r.text
        assert "background-image: none" in r.text

    def test_tema_cubre_header_oscuro(self, client_autenticado):
        r = client_autenticado.get("/static/css/tema-escritorio.css")
        assert ".header" in r.text
