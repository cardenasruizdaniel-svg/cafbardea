"""Auditoría: registro de acciones, ocultamiento de datos sensibles y accesos."""
import json

import pytest

from app.domains.auditoria.services import AuditoriaService, _serializar
from app.models import RegistroAuditoria


@pytest.fixture
def svc(db_session):
    return AuditoriaService(db_session)


class TestRegistro:
    def test_registra_accion_basica(self, svc, db_session):
        r = svc.registrar(accion="crear", modulo="caja", entidad="Venta",
                          entidad_id=5, descripcion="Test")
        db_session.commit()
        assert r is not None
        assert r.accion == "crear"
        assert r.entidad_id == "5"

    def test_accion_invalida_se_normaliza(self, svc, db_session):
        r = svc.registrar(accion="inventar_accion")
        db_session.commit()
        assert r.accion == "otro"

    def test_captura_antes_y_despues(self, svc, db_session):
        r = svc.registrar(accion="editar", antes={"estado": "abierta"},
                          despues={"estado": "anulada"})
        db_session.commit()
        assert "abierta" in r.valor_anterior
        assert "anulada" in r.valor_nuevo


class TestDatosSensibles:
    def test_oculta_password(self):
        s = _serializar({"usuario": "ana", "password": "secreta123"})
        data = json.loads(s)
        assert data["usuario"] == "ana"
        assert data["password"] == "***"

    def test_oculta_varios_campos(self):
        s = _serializar({"password_hash": "x", "token": "y", "csrf_token": "z",
                         "nombre": "visible"})
        data = json.loads(s)
        assert data["password_hash"] == "***"
        assert data["token"] == "***"
        assert data["csrf_token"] == "***"
        assert data["nombre"] == "visible"


class TestNoRompeOperacion:
    def test_registro_no_lanza_excepcion(self, db_session):
        # Aun con datos raros, registrar nunca debe propagar excepcion.
        svc = AuditoriaService(db_session)
        r = svc.registrar(accion="crear", antes=object())  # no serializable
        # No lanza; devuelve el registro o None.
        assert r is None or isinstance(r, RegistroAuditoria)


class TestConsulta:
    def test_filtra_por_accion(self, svc, db_session):
        svc.registrar(accion="acceso", descripcion="login")
        svc.registrar(accion="anular", descripcion="anulacion")
        db_session.commit()
        solo_acceso = svc.listar(accion="acceso")
        assert all(r.accion == "acceso" for r in solo_acceso)


class TestAuditoriaHTTP:
    def test_login_exitoso_se_audita(self, client, db_session):
        from app.models import Usuario
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(usuario="audit_user",
                               password_hash=pwd.hash("Test123*"),
                               rol="administrador", activo=True))
        db_session.commit()
        client.post("/login", data={"usuario": "audit_user",
                                    "password": "Test123*"})
        registros = db_session.query(RegistroAuditoria).filter_by(
            accion="acceso", resultado="exito").all()
        assert any(r.usuario_nombre == "audit_user" for r in registros)

    def test_login_fallido_se_audita(self, client, db_session):
        client.post("/login", data={"usuario": "noexiste",
                                    "password": "malo"})
        registros = db_session.query(RegistroAuditoria).filter_by(
            accion="acceso", resultado="error").all()
        assert len(registros) >= 1
