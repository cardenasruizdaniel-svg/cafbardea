"""Gestión de roles desde la UI: crear, editar permisos, eliminar, proteger admin."""
import pytest

from app.services.rbac_service import RolService


class TestGestionRolesServicio:
    def test_crear_rol_con_modulos(self, db_session):
        s = RolService(db_session)
        rol = s.crear_rol("Supervisor", nivel_acceso=50,
                          modulos=["dashboard", "caja"])
        db_session.commit()
        assert s.puede_modulo("Supervisor", "caja") is True
        assert s.puede_modulo("Supervisor", "nomina") is False

    def test_no_crea_super_admin_desde_ui(self, db_session):
        s = RolService(db_session)
        rol = s.crear_rol("CasiAdmin", nivel_acceso=500, modulos=[])
        db_session.commit()
        # el nivel se topa en 99; no se convierte en super admin.
        assert rol.nivel_acceso < 100

    def test_actualizar_permisos(self, db_session):
        s = RolService(db_session)
        rol = s.crear_rol("Editor", nivel_acceso=40, modulos=["caja"])
        db_session.commit()
        s.actualizar_permisos_modulo(rol.id, ["inventario", "informes"])
        db_session.commit()
        assert s.puede_modulo("Editor", "caja") is False
        assert s.puede_modulo("Editor", "inventario") is True

    def test_no_edita_super_admin(self, db_session):
        s = RolService(db_session)
        admin = s.rol_por_nombre_flexible("administrador")
        with pytest.raises(ValueError):
            s.actualizar_permisos_modulo(admin.id, [])

    def test_no_elimina_super_admin(self, db_session):
        s = RolService(db_session)
        admin = s.rol_por_nombre_flexible("administrador")
        with pytest.raises(ValueError):
            s.eliminar_rol(admin.id)

    def test_no_elimina_rol_en_uso(self, db_session):
        from app.models import Usuario
        from passlib.context import CryptContext
        s = RolService(db_session)
        rol = s.crear_rol("Temporal", nivel_acceso=30, modulos=[])
        db_session.commit()
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(usuario="conrol", password_hash=pwd.hash("x"),
                               rol="Temporal", activo=True))
        db_session.commit()
        with pytest.raises(ValueError):
            s.eliminar_rol(rol.id)

    def test_elimina_rol_libre(self, db_session):
        s = RolService(db_session)
        rol = s.crear_rol("Descartable", nivel_acceso=30, modulos=[])
        db_session.commit()
        rid = rol.id
        s.eliminar_rol(rid)
        db_session.commit()
        from app.models_enterprise import Rol
        assert db_session.get(Rol, rid) is None


class TestGestionRolesHTTP:
    def test_vista_roles_admin(self, client_autenticado):
        r = client_autenticado.get("/roles")
        assert r.status_code == 200

    def test_crear_rol_por_http(self, client_autenticado, db_session):
        r = client_autenticado.post(
            "/roles",
            data={"nombre": "SupHTTP", "nivel_acceso": "50",
                  "modulos": ["dashboard", "caja"]},
            follow_redirects=False)
        assert r.status_code == 303
        assert RolService(db_session).puede_modulo("SupHTTP", "caja") is True

    def test_mesero_no_accede_a_roles(self, client, db_session):
        from app.models import Usuario
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_session.add(Usuario(usuario="mesero_r", password_hash=pwd.hash("Test123*"),
                               rol="mesero", activo=True, acceso_web=True))
        db_session.commit()
        client.post("/login", data={"usuario": "mesero_r", "password": "Test123*"})
        r = client.get("/roles", follow_redirects=False)
        assert r.status_code == 403
