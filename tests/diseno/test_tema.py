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
