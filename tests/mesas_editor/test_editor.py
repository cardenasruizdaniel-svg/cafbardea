"""Editor de mesas: crear con forma, mover, redimensionar, eliminar, permisos."""
import pytest

from app.models import Zona, Mesa


@pytest.fixture
def zona(db_session):
    z = Zona(nombre="Zona Test", orden=99)
    db_session.add(z)
    db_session.commit()
    return z


class TestCrearMesa:
    def test_crea_con_forma_y_tamano(self, client_autenticado, zona, db_session):
        r = client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "T-1", "capacidad": "6",
            "forma": "rectangular"}, follow_redirects=False)
        assert r.status_code == 303
        m = db_session.query(Mesa).filter_by(nombre="T-1").first()
        assert m.forma == "rectangular"
        assert m.ancho == 96 and m.alto == 56

    def test_posicion_escalonada(self, client_autenticado, zona, db_session):
        # Dos mesas nuevas no deben quedar en la misma posicion.
        client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "E-1", "capacidad": "4"})
        client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "E-2", "capacidad": "4"})
        m1 = db_session.query(Mesa).filter_by(nombre="E-1").first()
        m2 = db_session.query(Mesa).filter_by(nombre="E-2").first()
        assert (m1.posicion_x, m1.posicion_y) != (m2.posicion_x, m2.posicion_y)

    def test_crear_mesa_sin_zona_id(self, client_autenticado, db_session):
        r = client_autenticado.post("/mesas", data={"nombre": "Mesa AutoZona", "capacidad": "4"}, follow_redirects=False)
        assert r.status_code == 303
        m = db_session.query(Mesa).filter_by(nombre="Mesa AutoZona").first()
        assert m is not None
        assert m.zona_id is not None



class TestLayout:
    def test_mover_mesa(self, client_autenticado, zona, db_session):
        client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "M-1", "capacidad": "4"})
        m = db_session.query(Mesa).filter_by(nombre="M-1").first()
        r = client_autenticado.post(f"/mesas/{m.id}/layout",
                                    json={"posicion_x": 55, "posicion_y": 33})
        assert r.status_code == 200
        db_session.refresh(m)
        assert m.posicion_x == 55 and m.posicion_y == 33

    def test_cambiar_forma_y_tamano(self, client_autenticado, zona, db_session):
        client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "F-1", "capacidad": "4"})
        m = db_session.query(Mesa).filter_by(nombre="F-1").first()
        r = client_autenticado.post(f"/mesas/{m.id}/layout",
                                    json={"forma": "cuadrada", "ancho": 120, "alto": 120})
        assert r.status_code == 200
        db_session.refresh(m)
        assert m.forma == "cuadrada" and m.ancho == 120

    def test_limites_de_tamano(self, client_autenticado, zona, db_session):
        client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "L-1", "capacidad": "4"})
        m = db_session.query(Mesa).filter_by(nombre="L-1").first()
        # Un tamano exagerado se topa en el limite.
        client_autenticado.post(f"/mesas/{m.id}/layout", json={"ancho": 9999})
        db_session.refresh(m)
        assert m.ancho <= 240


class TestEliminar:
    def test_eliminar_mesa_libre(self, client_autenticado, zona, db_session):
        client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "D-1", "capacidad": "4"})
        m = db_session.query(Mesa).filter_by(nombre="D-1").first()
        mid = m.id
        r = client_autenticado.post(f"/mesas/{mid}/eliminar", follow_redirects=False)
        assert r.status_code == 303
        assert db_session.get(Mesa, mid) is None

    def test_no_elimina_zona_con_mesas(self, client_autenticado, zona, db_session):
        client_autenticado.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "Z-1", "capacidad": "4"})
        r = client_autenticado.post(f"/zonas/{zona.id}/eliminar",
                                    follow_redirects=False)
        assert r.status_code == 400


class TestPermisos:
    def test_mesero_no_crea_mesa(self, client, zona, db_session):
        from app.models import Usuario
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(usuario="mesero_e", password_hash=pwd.hash("Test123*"),
                               rol="mesero", activo=True, acceso_web=True))
        db_session.commit()
        client.post("/login", data={"usuario": "mesero_e", "password": "Test123*"})
        r = client.post("/mesas", data={
            "zona_id": str(zona.id), "nombre": "X", "capacidad": "4"},
            follow_redirects=False)
        assert r.status_code == 403
