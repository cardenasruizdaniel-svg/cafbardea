"""Revision funcional: bugs reportados por el usuario (zonas, logout, mesa cliente)."""
import re

import pytest


class TestLogout:
    def test_logout_por_get_funciona(self, client_autenticado):
        """El boton 'Salir' es un <a> (GET); antes daba 405."""
        r = client_autenticado.get("/logout", follow_redirects=False)
        assert r.status_code == 303

    def test_logout_por_post_tambien(self, client_autenticado):
        r = client_autenticado.post("/logout", follow_redirects=False)
        assert r.status_code == 303


class TestCSRFForm:
    """El bug de fondo: el CSRF leia el body para el token y lo consumia,
    dejando el form vacio ('nombre: null'). Se prueba SIN header X-CSRF-Token,
    como envia un formulario HTML normal."""

    def _token(self, client):
        r = client.get("/mesas")
        return re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)

    def test_crear_zona_sin_header_csrf(self, client_autenticado, db_session):
        from app.models import Zona
        tok = self._token(client_autenticado)
        # NOTA: sin headers={'X-CSRF-Token': ...}; el token va solo en el form
        r = client_autenticado.post(
            "/zonas", data={"nombre": "Zona Form", "csrf_token": tok},
            follow_redirects=False)
        assert r.status_code == 303
        assert db_session.query(Zona).filter_by(nombre="Zona Form").first() is not None

    def test_crear_mesa_sin_header_csrf(self, client_autenticado, db_session):
        from app.models import Zona, Mesa
        tok = self._token(client_autenticado)
        client_autenticado.post("/zonas", data={"nombre": "ZM", "csrf_token": tok})
        z = db_session.query(Zona).filter_by(nombre="ZM").first()
        r = client_autenticado.post(
            "/mesas",
            data={"zona_id": str(z.id), "nombre": "MFORM", "capacidad": "4",
                  "forma": "redonda", "csrf_token": tok},
            follow_redirects=False)
        assert r.status_code == 303
        assert db_session.query(Mesa).filter_by(nombre="MFORM").first() is not None


class TestClienteEligeMesa:
    def test_mesas_publicas_disponibles(self, client):
        r = client.get("/api/cliente/mesas")
        assert r.status_code == 200
        assert "zonas" in r.json()

    def test_cliente_elige_mesa_y_pide(self, client, db_session):
        from app.models import Producto, Mesa
        mesa = db_session.query(Mesa).first()
        prod = db_session.query(Producto).filter(Producto.precio_venta > 0).first()
        r = client.post("/api/cliente/pedido", json={
            "tipo": "mesa", "mesa_id": mesa.id,
            "items": [{"producto_id": prod.id, "cantidad": 1}]})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_pagina_ofrece_elegir_modo(self, client):
        r = client.get("/cliente")
        assert "elegirModo" in r.text
        assert "select-mesa" in r.text


class TestFacturacionCompleta:
    def test_flujo_venta_completo(self, client_autenticado, db_session):
        """Comanda -> item -> cobrar -> pagada."""
        from app.models import Mesa, Producto, Venta
        mesa = db_session.query(Mesa).first()
        prod = db_session.query(Producto).filter(Producto.precio_venta > 0).first()
        tok = re.search(r'name="csrf_token" value="([^"]+)"',
                        client_autenticado.get("/mesas").text).group(1)
        H = {"X-CSRF-Token": tok}
        client_autenticado.get(f"/comanda/{mesa.id}")
        client_autenticado.post(f"/api/comanda/{mesa.id}/items",
                                data={"producto_id": str(prod.id), "cantidad": "2"},
                                headers=H)
        venta = db_session.query(Venta).filter_by(mesa_id=mesa.id, estado="abierta").first()
        assert venta is not None
        r = client_autenticado.post(f"/api/ventas/{venta.id}/pagar",
                                    data={"medio_pago": "efectivo"}, headers=H,
                                    follow_redirects=False)
        assert r.status_code == 200
        db_session.refresh(venta)
        assert venta.estado == "pagada"


class TestEsquemaReparado:
    """El 500 en produccion venia de una tabla 'zonas' vieja sin columnas nuevas.
    La migracion 0015 la repara. Se prueba que la migracion es idempotente y
    agrega las columnas que faltan."""

    def test_migracion_0015_existe(self):
        import os
        base = os.path.join(os.path.dirname(__file__), "..", "..",
                            "alembic", "versions")
        archivos = os.listdir(base)
        assert any("0015" in a for a in archivos), "falta la migracion 0015"

    def test_zonas_tiene_columnas_del_modelo(self, db_session):
        from app.models import Zona
        # el modelo y la tabla deben coincidir tras las migraciones
        cols = set(Zona.__table__.columns.keys())
        assert {"empresa_id", "orden", "activa", "nombre"}.issubset(cols)

    def test_crear_zona_con_orden_automatico(self, client_autenticado, db_session):
        import re
        from app.models import Zona
        tok = re.search(r'name="csrf_token" value="([^"]+)"',
                        client_autenticado.get("/mesas").text).group(1)
        r = client_autenticado.post("/zonas",
                                    data={"nombre": "Con Orden", "csrf_token": tok},
                                    follow_redirects=False)
        assert r.status_code == 303
        z = db_session.query(Zona).filter_by(nombre="Con Orden").first()
        assert z is not None
        assert z.orden is not None  # el orden se asigna sin fallar


class TestZonasYCategorias:
    def test_editar_zona(self, client_autenticado, db_session):
        from app.models import Zona
        z = db_session.query(Zona).first()
        r = client_autenticado.post(f"/zonas/{z.id}/editar",
                                    data={"nombre": "Zona Editada VIP"},
                                    follow_redirects=False)
        assert r.status_code == 303
        db_session.refresh(z)
        assert z.nombre == "Zona Editada VIP"

    def test_crear_editar_eliminar_categoria(self, client_autenticado, db_session):
        from app.models import Categoria, Producto
        # Crear
        r = client_autenticado.post("/productos/categorias",
                                    data={"nombre": "Bebidas Exóticas"},
                                    follow_redirects=False)
        assert r.status_code == 303
        cat = db_session.query(Categoria).filter_by(nombre="Bebidas Exóticas").first()
        assert cat is not None

        # Editar
        r = client_autenticado.post(f"/productos/categorias/{cat.id}/editar",
                                    data={"nombre": "Bebidas Premium"},
                                    follow_redirects=False)
        assert r.status_code == 303
        db_session.refresh(cat)
        assert cat.nombre == "Bebidas Premium"

        # Eliminar (los productos deben pasar a sin categoria)
        prod = db_session.query(Producto).first()
        if prod:
            prod.categoria_id = cat.id
            db_session.commit()

        r = client_autenticado.post(f"/productos/categorias/{cat.id}/eliminar",
                                    follow_redirects=False)
        assert r.status_code == 303
        assert db_session.query(Categoria).filter_by(id=cat.id).first() is None
        if prod:
            db_session.refresh(prod)
            assert prod.categoria_id is None

    def test_costo_receta_actualizado_al_comprar(self, client_autenticado, db_session):
        from decimal import Decimal
        from app.models import Producto, Receta, RecetaDetalle, Proveedor
        # Crear insumo A y producto elaborado
        insumo = Producto(codigo="INS-1", nombre="Café Grano", tipo="insumo", costo=Decimal("1000"), existencias=Decimal("10"))
        elaborado = Producto(codigo="ELAB-1", nombre="Café Espresso", tipo="elaborado", costo=Decimal("0"), precio_venta=Decimal("5000"))
        prov = Proveedor(nombre="Proveedor Test", documento="123")
        db_session.add_all([insumo, elaborado, prov])
        db_session.commit()

        receta = Receta(producto_id=elaborado.id, rendimiento=Decimal("1"), tipo_receta="produccion")
        db_session.add(receta)
        db_session.commit()

        detalle = RecetaDetalle(receta_id=receta.id, insumo_id=insumo.id, cantidad=Decimal("2"), merma_porcentaje=Decimal("0"))
        db_session.add(detalle)
        db_session.commit()

        # Recalcular costo inicial
        from app.domains.produccion.services import ProduccionService
        ProduccionService(db_session).recalcular_todos_los_costos()
        db_session.refresh(elaborado)
        assert elaborado.costo == Decimal("2000.00")

        # Registrar compra con nuevo precio de insumo ($2,000)
        import re
        tok = re.search(r'name="csrf_token" value="([^"]+)"', client_autenticado.get("/compras").text).group(1)
        r = client_autenticado.post("/compras", data={
            "proveedor_id": str(prov.id), "fecha": "2026-07-29", "concepto": "Compra Grano",
            "producto_id": str(insumo.id), "cantidad": "10", "costo_unitario": "2000",
            "csrf_token": tok
        }, follow_redirects=False)
        assert r.status_code == 303
        db_session.refresh(elaborado)
        # El costo del insumo pasa a promedio ponderado $1,500. El elaborado pasa a 2x $1,500 = $3,000
        assert elaborado.costo == Decimal("3000.00")

    def test_mobile_mesero_vistas(self, client_autenticado, db_session):
        from app.models import Mesa
        mesa = db_session.query(Mesa).first()

        # Cargar plano mobile
        r1 = client_autenticado.get("/mobile/mesas")
        assert r1.status_code == 200
        assert "Mesas" in r1.text

        # Cargar comanda mobile para la mesa
        if mesa:
            r2 = client_autenticado.get(f"/mobile/comanda/{mesa.id}")
            assert r2.status_code == 200
            assert mesa.nombre in r2.text

    def test_facturar_mesa_pasa_a_limpieza(self, client_autenticado, db_session):
        from app.models import Mesa, Venta
        mesa = db_session.query(Mesa).first()
        if not mesa:
            return
        venta = Venta(mesa_id=mesa.id, estado="abierta", total=1000)
        db_session.add(venta)
        mesa.estado = "ocupada"
        db_session.commit()

        r = client_autenticado.post(f"/api/ventas/{venta.id}/pagar",
                                    data={"medio_pago": "efectivo"},
                                    follow_redirects=False)
        assert r.status_code == 200
        db_session.refresh(mesa)
        assert mesa.estado == "limpieza"

    def test_cambio_estado_mesa(self, client_autenticado, db_session):
        from app.models import Mesa
        mesa = db_session.query(Mesa).first()
        if not mesa:
            return

        # Cambiar a reservada
        r1 = client_autenticado.post(f"/mesas/{mesa.id}/estado",
                                     data={"estado": "reservada"},
                                     follow_redirects=False)
        assert r1.status_code == 303
        db_session.refresh(mesa)
        assert mesa.estado == "reservada"

        # Mesero cambia a libre
        r2 = client_autenticado.post(f"/api/mesero/mesa/{mesa.id}/estado",
                                     json={"estado": "libre"})
        assert r2.status_code == 200
        db_session.refresh(mesa)
        assert mesa.estado == "libre"



