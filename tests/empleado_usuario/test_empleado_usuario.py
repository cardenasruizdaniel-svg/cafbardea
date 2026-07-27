"""Empleado-Usuario unificado: asignación de usuario y permisos de acceso."""
import pytest

from app.models import Empleado, Usuario


@pytest.fixture
def empleado(db_session):
    import uuid
    doc = uuid.uuid4().hex[:10]
    e = Empleado(nombre="Test Emp", documento=doc, cargo="Mesero",
                 empresa_id=1)
    db_session.add(e)
    db_session.commit()
    return e


class TestAsignarUsuario:
    def test_crea_usuario_con_acceso_web(self, client_autenticado, empleado, db_session):
        r = client_autenticado.post(
            f"/empleados/{empleado.id}/usuario",
            data={"usuario": "empweb", "password": "Clave123*",
                  "rol": "mesero", "acceso_web": "on"},
            follow_redirects=False)
        assert r.status_code == 303
        db_session.expire_all()
        u = db_session.query(Usuario).filter_by(usuario="empweb").first()
        assert u is not None
        assert u.empleado_id == empleado.id
        assert u.acceso_web is True
        assert u.acceso_app_pedidos is False

    def test_usuario_solo_turnos_sin_accesos(self, client_autenticado, empleado, db_session):
        # Sin marcar casillas -> sin acceso a ninguna app.
        r = client_autenticado.post(
            f"/empleados/{empleado.id}/usuario",
            data={"usuario": "empturnos", "password": "Clave123*",
                  "rol": "cocina"},
            follow_redirects=False)
        assert r.status_code == 303
        db_session.expire_all()
        u = db_session.query(Usuario).filter_by(usuario="empturnos").first()
        assert u.acceso_web is False
        assert u.acceso_app_pedidos is False

    def test_actualiza_usuario_existente(self, client_autenticado, empleado, db_session):
        # crear
        client_autenticado.post(
            f"/empleados/{empleado.id}/usuario",
            data={"usuario": "empupd", "password": "Clave123*",
                  "rol": "mesero", "acceso_web": "on"})
        # actualizar: quitar acceso web, cambiar rol
        r = client_autenticado.post(
            f"/empleados/{empleado.id}/usuario",
            data={"usuario": "empupd", "rol": "gerente",
                  "acceso_app_pedidos": "on"},
            follow_redirects=False)
        assert r.status_code == 303
        db_session.expire_all()
        us = db_session.query(Usuario).filter_by(empleado_id=empleado.id).all()
        assert len(us) == 1  # no duplica
        assert us[0].rol == "gerente"
        assert us[0].acceso_web is False
        assert us[0].acceso_app_pedidos is True

    def test_usuario_duplicado_rechazado(self, client_autenticado, empleado, db_session):
        client_autenticado.post(
            f"/empleados/{empleado.id}/usuario",
            data={"usuario": "repetido", "password": "Clave123*", "rol": "mesero"})
        # otro empleado
        e2 = Empleado(nombre="Otro", documento=__import__("uuid").uuid4().hex[:10], cargo="Caja", empresa_id=1)
        db_session.add(e2)
        db_session.commit()
        r = client_autenticado.post(
            f"/empleados/{e2.id}/usuario",
            data={"usuario": "repetido", "password": "Otra123*", "rol": "cajero"},
            follow_redirects=False)
        assert r.status_code == 400


class TestAccesoWeb:
    def test_usuario_sin_acceso_web_no_ingresa(self, client, empleado, db_session):
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(
            empleado_id=empleado.id, usuario="noweb",
            password_hash=pwd.hash("Clave123*"), rol="cocina",
            activo=True, acceso_web=False, acceso_app_pedidos=False))
        db_session.commit()
        r = client.post("/login", data={"usuario": "noweb",
                                        "password": "Clave123*"},
                        follow_redirects=False)
        assert r.status_code == 403

    def test_usuario_con_acceso_web_ingresa(self, client, empleado, db_session):
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(
            empleado_id=empleado.id, usuario="siweb",
            password_hash=pwd.hash("Clave123*"), rol="administrador",
            activo=True, acceso_web=True))
        db_session.commit()
        r = client.post("/login", data={"usuario": "siweb",
                                        "password": "Clave123*"},
                        follow_redirects=False)
        assert r.status_code == 303  # entra
