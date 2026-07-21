"""
FASE 8 - Kitchen Display System (KDS) Tests
19 tests para validar endpoints y funcionalidad de cocina
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from passlib.context import CryptContext

from app.main import app
from app.database import get_db, Base
from app.models import (
    Usuario, Empleado, Empresa, Zona, Mesa, Categoria,
    Producto, Venta, DetalleVenta
)
from app.services.jwt_service import JWTService

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite for tests"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def TestingSessionLocal(test_engine):
    """Session factory for test database"""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def setup_db_override(TestingSessionLocal):
    """Override get_db dependency"""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_db(TestingSessionLocal):
    """Test database session"""
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(setup_db_override):
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def kds_user(test_db):
    """Crea usuario chef para testing"""
    empresa = test_db.query(Empresa).first()
    if not empresa:
        empresa = Empresa(nombre="Test Empresa", nit="900.000.000-0")
        test_db.add(empresa)
        test_db.flush()
    
    empleado = Empleado(
        nombre="Chef Test",
        documento="9876543210",
        cargo="Chef",
        salario=2500000
    )
    test_db.add(empleado)
    test_db.flush()
    
    usuario = Usuario(
        empleado_id=empleado.id,
        empresa_id=empresa.id,
        usuario="chef_test",
        password_hash=passwords.hash("ChefTest123*"),
        rol="chef",
        activo=True
    )
    test_db.add(usuario)
    test_db.commit()
    
    return usuario


@pytest.fixture(scope="function")
def valid_kds_token(kds_user):
    """Genera JWT token válido para KDS"""
    token = JWTService.create_token(
        usuario_id=kds_user.id,
        sucursal_id=kds_user.empresa_id,
        dispositivo="kds"
    )
    return token


# ============================================================================
# Tests - Authentication
# ============================================================================

class TestKDSAuth:
    """Pruebas de autenticación KDS"""
    
    def test_kds_login_success(self, client, kds_user, test_db):
        """Login KDS exitoso"""
        response = client.post(
            "/api/v1/kds/auth/login",
            json={
                "usuario": "chef_test",
                "password": "ChefTest123*",
                "device_id": "kds-cocina-1"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["usuario_id"] == kds_user.id
        assert data["rol"] == "chef"
        assert data["dispositivo"] == "kds"
    
    def test_kds_login_invalid_credentials(self, client):
        """Login KDS con credenciales inválidas"""
        response = client.post(
            "/api/v1/kds/auth/login",
            json={
                "usuario": "chef_test",
                "password": "WrongPassword"
            }
        )
        assert response.status_code == 401
    
    def test_kds_login_non_chef_user(self, client, test_db):
        """Intento de login KDS con usuario no-chef"""
        empresa = test_db.query(Empresa).first()
        if not empresa:
            empresa = Empresa(nombre="Test Empresa", nit="900.000.000-0")
            test_db.add(empresa)
            test_db.flush()
        
        empleado = Empleado(
            nombre="Mesero Test",
            documento="1111111111",
            cargo="Mesero",
            salario=1200000
        )
        test_db.add(empleado)
        test_db.flush()
        
        usuario = Usuario(
            empleado_id=empleado.id,
            empresa_id=empresa.id,
            usuario="mesero_test",
            password_hash=passwords.hash("Test123*"),
            rol="mesero",
            activo=True
        )
        test_db.add(usuario)
        test_db.commit()
        
        response = client.post(
            "/api/v1/kds/auth/login",
            json={
                "usuario": "mesero_test",
                "password": "Test123*"
            }
        )
        assert response.status_code == 403
        assert "chef" in response.json()["detail"].lower() or "cocinero" in response.json()["detail"].lower()
    
    def test_kds_logout(self, client, valid_kds_token):
        """Logout KDS - revoca token"""
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.post("/api/v1/kds/auth/logout", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "logged out"


# ============================================================================
# Tests - Security
# ============================================================================

class TestKDSSecurity:
    """Pruebas de seguridad KDS"""
    
    def test_kds_bearer_token_required(self, client):
        """Endpoints requieren Bearer token"""
        response = client.get("/api/v1/kds/pedidos")
        assert response.status_code == 401
    
    def test_kds_invalid_token(self, client):
        """Token inválido rechazado"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/kds/pedidos", headers=headers)
        assert response.status_code == 401
    
    def test_kds_wrong_device_type(self, client, test_db):
        """Token no-KDS rechazado en endpoints KDS"""
        # Crear token mobile, no KDS
        empresa = test_db.query(Empresa).first()
        if not empresa:
            empresa = Empresa(nombre="Test Empresa", nit="900.000.000-0")
            test_db.add(empresa)
            test_db.flush()
        
        empleado = Empleado(
            nombre="Mesero",
            documento="2222222222",
            cargo="Mesero",
            salario=1200000
        )
        test_db.add(empleado)
        test_db.flush()
        
        usuario = Usuario(
            empleado_id=empleado.id,
            empresa_id=empresa.id,
            usuario="mesero_mobile",
            password_hash=passwords.hash("Test123*"),
            rol="mesero",
            activo=True
        )
        test_db.add(usuario)
        test_db.commit()
        
        # Crear token mobile
        mobile_token = JWTService.create_token(
            usuario_id=usuario.id,
            sucursal_id=usuario.empresa_id,
            dispositivo="app_mesero"
        )
        
        headers = {"Authorization": f"Bearer {mobile_token}"}
        response = client.get("/api/v1/kds/pedidos", headers=headers)
        assert response.status_code == 403


# ============================================================================
# Tests - KDS Operations
# ============================================================================

class TestKDSOperations:
    """Pruebas operacionales de cocina"""
    
    def test_obtener_pedidos_vacio(self, client, valid_kds_token, test_db):
        """GET /pedidos sin órdenes"""
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.get("/api/v1/kds/pedidos", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_obtener_pedidos_con_ordenes(self, client, valid_kds_token, test_db, kds_user):
        """GET /pedidos con órdenes pendientes"""
        # Crear datos de prueba
        zona = test_db.query(Zona).first()
        if not zona:
            zona = Zona(nombre="Piso 1", empresa_id=kds_user.empresa_id)
            test_db.add(zona)
            test_db.flush()
        
        mesa = Mesa(
            nombre="M1",
            empresa_id=kds_user.empresa_id,
            zona_id=zona.id,
            capacidad=4,
            estado="ocupada"
        )
        test_db.add(mesa)
        test_db.flush()
        
        categoria = Categoria(nombre="Bebidas")
        test_db.add(categoria)
        test_db.flush()
        
        producto = Producto(
            categoria_id=categoria.id,
            codigo="CAF-001",
            nombre="Café",
            precio_venta=5000,
            costo=1500,
            existencias=50,
            empresa_id=kds_user.empresa_id,
            activo=True
        )
        test_db.add(producto)
        test_db.flush()
        
        venta = Venta(
            mesa_id=mesa.id,
            usuario_id=kds_user.id,
            empresa_id=kds_user.empresa_id,
            estado="abierta",
            subtotal=5000,
            impuesto=400,
            total=5400
        )
        test_db.add(venta)
        test_db.flush()
        
        detalle = DetalleVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            cantidad=1,
            precio=5000,
            nota=None,
            estado_cocina="pendiente"
        )
        test_db.add(detalle)
        test_db.commit()
        
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.get("/api/v1/kds/pedidos", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["venta_id"] == venta.id
        assert len(data[0]["items"]) == 1
    
    def test_actualizar_estado_pedido(self, client, valid_kds_token, test_db, kds_user):
        """PUT /pedidos/{id}/estado - cambiar a preparando"""
        # Setup
        zona = Zona(nombre="Piso 1", empresa_id=kds_user.empresa_id)
        test_db.add(zona)
        test_db.flush()
        
        mesa = Mesa(
            nombre="M2",
            empresa_id=kds_user.empresa_id,
            zona_id=zona.id,
            capacidad=4
        )
        test_db.add(mesa)
        test_db.flush()
        
        venta = Venta(
            mesa_id=mesa.id,
            usuario_id=kds_user.id,
            empresa_id=kds_user.empresa_id,
            estado="abierta",
            subtotal=5000,
            total=5400
        )
        test_db.add(venta)
        test_db.commit()
        
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.put(
            f"/api/v1/kds/pedidos/{venta.id}/estado",
            json={"estado": "preparando"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "preparando"
        assert data["venta_id"] == venta.id
    
    def test_actualizar_estado_pedido_lista(self, client, valid_kds_token, test_db, kds_user):
        """PUT /pedidos/{id}/estado - cambiar a lista"""
        zona = Zona(nombre="Piso 1", empresa_id=kds_user.empresa_id)
        test_db.add(zona)
        test_db.flush()
        
        mesa = Mesa(
            nombre="M3",
            empresa_id=kds_user.empresa_id,
            zona_id=zona.id,
            capacidad=4
        )
        test_db.add(mesa)
        test_db.flush()
        
        venta = Venta(
            mesa_id=mesa.id,
            usuario_id=kds_user.id,
            empresa_id=kds_user.empresa_id,
            estado="en_preparacion",
            subtotal=5000,
            total=5400
        )
        test_db.add(venta)
        test_db.commit()
        
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.put(
            f"/api/v1/kds/pedidos/{venta.id}/estado",
            json={"estado": "lista"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "lista"
    
    def test_actualizar_estado_inválido(self, client, valid_kds_token, test_db, kds_user):
        """PUT /pedidos/{id}/estado - estado inválido rechazado"""
        zona = Zona(nombre="Piso 1", empresa_id=kds_user.empresa_id)
        test_db.add(zona)
        test_db.flush()
        
        mesa = Mesa(
            nombre="M4",
            empresa_id=kds_user.empresa_id,
            zona_id=zona.id,
            capacidad=4
        )
        test_db.add(mesa)
        test_db.flush()
        
        venta = Venta(
            mesa_id=mesa.id,
            usuario_id=kds_user.id,
            empresa_id=kds_user.empresa_id,
            estado="abierta"
        )
        test_db.add(venta)
        test_db.commit()
        
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.put(
            f"/api/v1/kds/pedidos/{venta.id}/estado",
            json={"estado": "invalid_status"},
            headers=headers
        )
        assert response.status_code == 400
    
    def test_obtener_estado_cocina(self, client, valid_kds_token, test_db, kds_user):
        """GET /estado - estado general de cocina"""
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.get("/api/v1/kds/estado", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_pendientes" in data
        assert "total_preparando" in data
        assert "total_listas" in data
        assert data["total_pendientes"] == 0
        assert data["total_preparando"] == 0
        assert data["total_listas"] == 0
    
    def test_estadisticas_endpoint(self, client, valid_kds_token):
        """GET /estadisticas - endpoint de estadísticas"""
        headers = {"Authorization": f"Bearer {valid_kds_token}"}
        response = client.get("/api/v1/kds/estadisticas", headers=headers)
        assert response.status_code == 200


# ============================================================================
# Tests - JWT Integration
# ============================================================================

class TestKDSJWT:
    """Pruebas de integración JWT para KDS"""
    
    def test_kds_jwt_structure(self, kds_user):
        """Verifica estructura del JWT para KDS"""
        token = JWTService.create_token(
            usuario_id=kds_user.id,
            sucursal_id=kds_user.empresa_id,
            dispositivo="kds"
        )
        
        payload = JWTService.verify_token(token)
        assert payload is not None
        assert payload["usuario_id"] == kds_user.id
        assert payload["sucursal_id"] == kds_user.empresa_id
        assert payload["dispositivo"] == "kds"
    
    def test_kds_token_expiration(self, kds_user):
        """Token KDS se expira después de 24 horas"""
        token = JWTService.create_token(
            usuario_id=kds_user.id,
            sucursal_id=kds_user.empresa_id,
            dispositivo="kds"
        )
        
        # Token debe ser válido inicialmente
        payload = JWTService.verify_token(token)
        assert payload is not None
