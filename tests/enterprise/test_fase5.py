"""
Tests para FASE 5: Infraestructura Enterprise
Prueba WebSocket, Multi-tenancy y RBAC
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import Usuario, Empresa
from app.models_enterprise import Sucursal, Rol, Permiso, UsuarioRol
from app.websocket_manager import connection_manager, MensajeWS
from app.services.rbac_service import PermisosService, RolService
from datetime import datetime
import uuid


# ============================================================================
# FIXTURES
# ============================================================================
@pytest.fixture(scope="function")
def test_db():
    """Base de datos de prueba en memoria"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    return db


@pytest.fixture
def client(test_db):
    """Cliente HTTP de prueba"""
    return TestClient(app)


@pytest.fixture
def usuario_test(test_db):
    """Crea un usuario de prueba"""
    empresa = Empresa(nombre="Empresa Test", nit="123456789")
    test_db.add(empresa)
    test_db.commit()
    
    usuario = Usuario(
        usuario="test_user",
        password_hash="hashed_password",
        empresa_id=empresa.id,
        rol="administrador"
    )
    test_db.add(usuario)
    test_db.commit()
    return usuario


# ============================================================================
# TESTS DE RBAC
# ============================================================================
class TestRBAC:
    """Tests del sistema RBAC"""
    
    def test_crear_permisos_del_sistema(self, test_db):
        """Verifica que se crean los permisos predefinidos"""
        rol_service = RolService(test_db)
        rol_service.crear_permisos_del_sistema()
        
        permisos = test_db.query(Permiso).all()
        assert len(permisos) > 0
        
        # Verificar permisos específicos
        codigos = [p.codigo for p in permisos]
        assert "ventas.crear" in codigos
        assert "caja.abrir" in codigos
        assert "admin.*" in codigos
    
    def test_crear_roles_predefinidos(self, test_db):
        """Verifica que se crean los roles predefinidos"""
        rol_service = RolService(test_db)
        rol_service.crear_roles_predefinidos()
        
        roles = test_db.query(Rol).all()
        assert len(roles) > 0
        
        nombres_roles = [r.nombre for r in roles]
        assert "administrador" in nombres_roles
        assert "mesero" in nombres_roles
        assert "cocinero" in nombres_roles
    
    def test_permisos_service_tiene_permiso(self, test_db, usuario_test):
        """Verifica validación de permisos"""
        rol_service = RolService(test_db)
        rol_service.crear_roles_predefinidos()
        
        # Obtener rol administrador
        rol_admin = test_db.query(Rol).filter(Rol.nombre == "administrador").first()
        assert rol_admin is not None
        
        # Asignar rol al usuario
        usuario_rol = UsuarioRol(
            usuario_id=usuario_test.id,
            rol_id=rol_admin.id,
            activo=True
        )
        test_db.add(usuario_rol)
        test_db.commit()
        
        # Verificar permisos
        permisos_service = PermisosService(test_db)
        assert permisos_service.tiene_permiso(usuario_test.id, "admin.*")
    
    def test_permisos_comodin(self, test_db, usuario_test):
        """Verifica que los permisos comodín (*) funcionan"""
        rol_service = RolService(test_db)
        rol_service.crear_roles_predefinidos()
        
        # Crear rol con permisos comodín
        permisos = test_db.query(Permiso).filter(
            Permiso.codigo.in_(["ventas.crear", "ventas.editar"])
        ).all()
        
        rol_ventas = Rol(
            nombre="vendedor",
            permisos=permisos,
            es_predefinido=False
        )
        test_db.add(rol_ventas)
        test_db.commit()
        
        # Asignar rol
        usuario_rol = UsuarioRol(
            usuario_id=usuario_test.id,
            rol_id=rol_ventas.id,
            activo=True
        )
        test_db.add(usuario_rol)
        test_db.commit()
        
        # Verificar
        permisos_service = PermisosService(test_db)
        assert permisos_service.tiene_permiso(usuario_test.id, "ventas.crear")
        assert permisos_service.tiene_permiso(usuario_test.id, "ventas.editar")
        assert not permisos_service.tiene_permiso(usuario_test.id, "caja.abrir")


# ============================================================================
# TESTS DE SUCURSAL
# ============================================================================
class TestSucursal:
    """Tests de multi-tenancy con sucursales"""
    
    def test_crear_sucursal(self, test_db):
        """Verifica creación de sucursal"""
        empresa = Empresa(nombre="Test Corp", nit="999999999")
        test_db.add(empresa)
        test_db.commit()
        
        sucursal = Sucursal(
            empresa_id=empresa.id,
            nombre="Sucursal Centro",
            codigo="SUC001",
            direccion="Calle 1 #123",
            telefono="1234567890",
            ciudad="Bogotá",
            pais="Colombia"
        )
        test_db.add(sucursal)
        test_db.commit()
        
        sucursal_recuperada = test_db.query(Sucursal).filter(
            Sucursal.codigo == "SUC001"
        ).first()
        
        assert sucursal_recuperada is not None
        assert sucursal_recuperada.nombre == "Sucursal Centro"
        assert len(sucursal_recuperada.uuid) > 0
    
    def test_multiples_sucursales_por_empresa(self, test_db):
        """Verifica que una empresa puede tener múltiples sucursales"""
        empresa = Empresa(nombre="Cadena Grande", nit="111111111")
        test_db.add(empresa)
        test_db.commit()
        
        sucursales = []
        for i in range(3):
            sucursal = Sucursal(
                empresa_id=empresa.id,
                nombre=f"Sucursal {i+1}",
                codigo=f"SUC{i+1:03d}",
                ciudad=f"Ciudad {i+1}",
                pais="Colombia"
            )
            sucursales.append(sucursal)
            test_db.add(sucursal)
        
        test_db.commit()
        
        sucursales_recuperadas = test_db.query(Sucursal).filter(
            Sucursal.empresa_id == empresa.id
        ).all()
        
        assert len(sucursales_recuperadas) == 3


# ============================================================================
# TESTS DE WEBSOCKET
# ============================================================================
class TestWebSocket:
    """Tests de sincronización WebSocket"""
    
    @pytest.mark.asyncio
    async def test_mensaje_ws_creation(self):
        """Verifica creación de mensajes WebSocket"""
        mensaje = MensajeWS(
            tipo="evento",
            evento="venta.creada",
            datos={"venta_id": 123, "total": 45000},
            sucursal_id=1,
            remitente_id=1
        )
        
        assert mensaje.tipo == "evento"
        assert mensaje.evento == "venta.creada"
        assert mensaje.datos["venta_id"] == 123
        
        # Verificar conversión a JSON
        json_str = mensaje.to_json()
        assert "venta.creada" in json_str
        assert "123" in json_str
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect(self):
        """Verifica conexión al manager"""
        from unittest.mock import AsyncMock
        
        mock_ws = AsyncMock()
        await connection_manager.connect(
            sucursal_id=2,
            usuario_id=2,
            websocket=mock_ws,
            socket_id="test-socket-connect",
            dispositivo="web"
        )
        
        # Verificar que se registró
        usuarios = connection_manager.get_usuarios_conectados(2)
        assert 2 in usuarios
    
    @pytest.mark.asyncio
    async def test_connection_manager_disconnect(self):
        """Verifica desconexión del manager"""
        from unittest.mock import AsyncMock
        
        mock_ws = AsyncMock()
        socket_id = "test-socket-disconnect"
        
        await connection_manager.connect(3, 3, mock_ws, socket_id, "web")
        assert 3 in connection_manager.get_usuarios_conectados(3)
        
        await connection_manager.disconnect(3, 3, socket_id)
        assert 3 not in connection_manager.get_usuarios_conectados(3)
    
    def test_connection_manager_stats(self):
        """Verifica estadísticas de conexiones"""
        stats = connection_manager.get_conexiones_stats()
        
        assert "total_conexiones" in stats
        assert "total_usuarios_conectados" in stats
        assert "sucursales_activas" in stats
        assert stats["total_conexiones"] >= 0


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================
class TestIntegracion:
    """Tests de integración entre componentes"""
    
    def test_usuario_con_multiples_roles_en_sucursales(self, test_db):
        """Verifica que un usuario puede tener roles en múltiples sucursales"""
        empresa = Empresa(nombre="Test", nit="123456")
        test_db.add(empresa)
        test_db.commit()
        
        # Crear sucursales
        suc1 = Sucursal(empresa_id=empresa.id, nombre="Suc1", codigo="SUC1", pais="Colombia")
        suc2 = Sucursal(empresa_id=empresa.id, nombre="Suc2", codigo="SUC2", pais="Colombia")
        test_db.add_all([suc1, suc2])
        test_db.commit()
        
        # Crear usuario
        usuario = Usuario(usuario="gerente", password_hash="pwd", empresa_id=empresa.id)
        test_db.add(usuario)
        test_db.commit()
        
        # Crear roles
        rol_service = RolService(test_db)
        rol_service.crear_roles_predefinidos()
        
        gerente_rol = test_db.query(Rol).filter(Rol.nombre == "gerente").first()
        mesero_rol = test_db.query(Rol).filter(Rol.nombre == "mesero").first()
        
        # Asignar roles en diferentes sucursales
        ur1 = UsuarioRol(usuario_id=usuario.id, rol_id=gerente_rol.id, sucursal_id=suc1.id, activo=True)
        ur2 = UsuarioRol(usuario_id=usuario.id, rol_id=mesero_rol.id, sucursal_id=suc2.id, activo=True)
        
        test_db.add_all([ur1, ur2])
        test_db.commit()
        
        # Verificar
        usuarios_roles = test_db.query(UsuarioRol).filter(
            UsuarioRol.usuario_id == usuario.id
        ).all()
        
        assert len(usuarios_roles) == 2
        assert usuarios_roles[0].sucursal_id == suc1.id
        assert usuarios_roles[1].sucursal_id == suc2.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
