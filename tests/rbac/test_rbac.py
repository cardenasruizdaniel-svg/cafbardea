"""RBAC: control de acceso por modulo, parametrizable en base de datos."""
import pytest

from app.services.rbac_service import RolService, inicializar_rbac
from app.models_enterprise import Rol


@pytest.fixture
def svc(db_session):
    # El fixture ya siembra RBAC; devolver el servicio.
    return RolService(db_session)


class TestResolucionPermisos:
    def test_super_admin_puede_todo(self, svc):
        for m in ("nomina", "inventario", "configuracion", "caja", "usuarios"):
            assert svc.puede_modulo("administrador", m) is True

    def test_super_admin_detectado(self, svc):
        assert svc.es_super_admin("administrador") is True
        assert svc.es_super_admin("mesero") is False

    def test_mesero_acceso_limitado(self, svc):
        assert svc.puede_modulo("mesero", "mesas") is True
        assert svc.puede_modulo("mesero", "caja") is True
        assert svc.puede_modulo("mesero", "nomina") is False
        assert svc.puede_modulo("mesero", "inventario") is False

    def test_cajero_no_entra_a_inventario(self, svc):
        assert svc.puede_modulo("cajero", "caja") is True
        assert svc.puede_modulo("cajero", "inventario") is False

    def test_resolucion_case_insensitive(self, svc):
        # El Usuario.rol puede venir capitalizado o no.
        assert svc.puede_modulo("Administrador", "nomina") is True
        assert svc.puede_modulo("MESERO", "mesas") is True

    def test_rol_inexistente_no_puede(self, svc):
        assert svc.puede_modulo("rol_fantasma", "mesas") is False


class TestParametrizacion:
    def test_permisos_modulo_de_mesero(self, svc):
        permisos = svc.permisos_modulo_de("mesero")
        assert "mesas" in permisos
        assert "nomina" not in permisos

    def test_roles_tienen_nivel(self, db_session):
        admin = db_session.query(Rol).filter(Rol.nombre == "administrador").first()
        assert admin.nivel_acceso >= 100
        mesero = db_session.query(Rol).filter(Rol.nombre == "mesero").first()
        assert mesero.nivel_acceso < 100


class TestAccesoPorModuloHTTP:
    def test_admin_entra_a_nomina(self, client_autenticado):
        # El usuario de prueba es administrador.
        r = client_autenticado.get("/nomina")
        assert r.status_code == 200

    def test_endpoint_sin_permiso_da_403(self, client, db_session):
        # Crear un usuario mesero e iniciar sesion con el.
        from app.models import Usuario
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(usuario="mesero_test",
                               password_hash=pwd.hash("Test123*"),
                               rol="mesero", activo=True))
        db_session.commit()
        client.post("/login", data={"usuario": "mesero_test",
                                    "password": "Test123*"})
        r = client.get("/nomina", follow_redirects=False)
        assert r.status_code == 403
