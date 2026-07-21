"""
Tests para FASE 7: Mobile API Endpoints
Valida autenticación JWT y endpoints REST para móviles
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import Usuario, Empresa, Empleado, Mesa, Producto, Categoria, Zona
from app.services.jwt_service import JWTService, TokenBlacklist
from passlib.context import CryptContext
import uuid

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create fresh in-memory engine per test"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def TestingSessionLocal(test_engine):
    """Create session factory per test"""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db_override(TestingSessionLocal):
    """Setup dependency override for each test"""
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
    """Get a test database session"""
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture
def client(setup_db_override):
    """Cliente HTTP de prueba"""
    return TestClient(app)


@pytest.fixture
def mobile_user(test_db):
    """Crea usuario mesero para testing"""
    empresa = test_db.query(Empresa).first()
    if not empresa:
        empresa = Empresa(nombre="Test Empresa", nit="900.000.000-0")
        test_db.add(empresa)
        test_db.flush()
    
    empleado = Empleado(
        nombre="Mesero Test",
        documento="1234567890",
        cargo="Mesero",
        salario=1000000
    )
    test_db.add(empleado)
    test_db.flush()
    
    usuario = Usuario(
        empleado_id=empleado.id,
        empresa_id=empresa.id,
        usuario="mesero_test",
        password_hash=passwords.hash("MeseroTest123*"),
        rol="mesero",
        activo=True
    )
    test_db.add(usuario)
    test_db.commit()
    
    return usuario


@pytest.fixture
def valid_jwt_token(mobile_user):
    """Genera JWT token válido para testing"""
    return JWTService.create_token(
        usuario_id=mobile_user.id,
        sucursal_id=mobile_user.empresa_id,
        dispositivo="app_mesero",
        device_id=str(uuid.uuid4())
    )


# ============================================================================
# TESTS DE AUTENTICACIÓN JWT
# ============================================================================

class TestMobileAuth:
    """Tests de autenticación y JWT"""
    
    def test_jwt_creation(self, mobile_user):
        """JWT token se crea correctamente"""
        token = JWTService.create_token(
            usuario_id=mobile_user.id,
            sucursal_id=mobile_user.empresa_id
        )
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20
    
    def test_jwt_verification(self, mobile_user):
        """JWT token se verifica correctamente"""
        token = JWTService.create_token(
            usuario_id=mobile_user.id,
            sucursal_id=mobile_user.empresa_id
        )
        payload = JWTService.verify_token(token)
        assert payload is not None
        assert payload["usuario_id"] == mobile_user.id
        assert payload["sucursal_id"] == mobile_user.empresa_id
    
    def test_jwt_invalid_token(self):
        """Token inválido retorna None"""
        payload = JWTService.verify_token("invalid_token_123")
        assert payload is None
    
    def test_jwt_token_structure(self, mobile_user):
        """JWT token contiene campos requeridos"""
        device_id = str(uuid.uuid4())
        token = JWTService.create_token(
            usuario_id=mobile_user.id,
            sucursal_id=mobile_user.empresa_id,
            device_id=device_id
        )
        payload = JWTService.verify_token(token)
        
        assert payload["usuario_id"] == mobile_user.id
        assert payload["sucursal_id"] == mobile_user.empresa_id
        assert payload["dispositivo"] == "app_mesero"
        assert payload["device_id"] == device_id
        assert "exp" in payload
        assert "iat" in payload
    
    def test_token_blacklist(self, valid_jwt_token):
        """Token se puede añadir a blacklist"""
        assert not TokenBlacklist.is_blacklisted(valid_jwt_token)
        TokenBlacklist.add(valid_jwt_token)
        assert TokenBlacklist.is_blacklisted(valid_jwt_token)
        TokenBlacklist.clear()
    
    def test_login_endpoint_success(self, client, test_db):
        """Login exitoso retorna JWT token"""
        # Crear usuario
        empresa = test_db.query(Empresa).first()
        if not empresa:
            empresa = Empresa(nombre="Test", nit="900.000.000-0")
            test_db.add(empresa)
            test_db.flush()
        
        empleado = Empleado(nombre="Test", documento="123", cargo="Mesero", salario=1000000)
        test_db.add(empleado)
        test_db.flush()
        
        usuario = Usuario(
            empleado_id=empleado.id,
            empresa_id=empresa.id,
            usuario="testuser",
            password_hash=passwords.hash("Test123*"),
            rol="mesero",
            activo=True
        )
        test_db.add(usuario)
        test_db.commit()
        
        # Hacer login
        response = client.post("/api/v1/mobile/auth/login", json={
            "usuario": "testuser",
            "password": "Test123*",
            "device_id": str(uuid.uuid4())
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["usuario_id"] == usuario.id
        assert data["rol"] == "mesero"
    
    def test_login_invalid_credentials(self, client):
        """Login con credenciales inválidas falla"""
        response = client.post("/api/v1/mobile/auth/login", json={
            "usuario": "noexist",
            "password": "wrong",
            "device_id": str(uuid.uuid4())
        })
        assert response.status_code == 401
    
    def test_logout_endpoint(self, client, valid_jwt_token):
        """Logout revoca el token"""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.post(
            "/api/v1/mobile/auth/logout",
            headers=headers
        )
        assert response.status_code == 200
        assert TokenBlacklist.is_blacklisted(valid_jwt_token)
        TokenBlacklist.clear()


# ============================================================================
# TESTS DE ENDPOINTS DE DATOS
# ============================================================================

class TestMobileDataEndpoints:
    """Tests de endpoints para obtener datos"""
    
    def test_get_mesas_requires_auth(self, client):
        """GET /mesas requiere JWT token"""
        response = client.get("/api/v1/mobile/mesas")
        assert response.status_code == 401
    
    def test_get_mesas_with_token(self, client, valid_jwt_token, test_db, mobile_user):
        """GET /mesas con token válido"""
        # Crear zona y mesa de prueba
        zona = Zona(nombre="Zona Principal")
        test_db.add(zona)
        test_db.flush()
        
        mesa = Mesa(
            nombre="M1",
            empresa_id=mobile_user.empresa_id,
            zona_id=zona.id,
            capacidad=4,
            estado="libre"
        )
        test_db.add(mesa)
        test_db.commit()
        
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.get("/api/v1/mobile/mesas", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "numero" in data[0]
        assert "estado" in data[0]
    
    def test_get_productos_with_token(self, client, valid_jwt_token, test_db, mobile_user):
        """GET /productos con token válido"""
        # Crear categoria y producto
        categoria = Categoria(nombre="Bebidas")
        test_db.add(categoria)
        test_db.flush()
        
        producto = Producto(
            categoria_id=categoria.id,
            codigo="TEST-001",
            nombre="Café Test",
            precio_venta=5000,
            costo=1500,
            existencias=20,
            empresa_id=mobile_user.empresa_id,
            activo=True
        )
        test_db.add(producto)
        test_db.commit()
        
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.get("/api/v1/mobile/productos", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(p["codigo"] == "TEST-001" for p in data)
    
    def test_get_productos_requires_auth(self, client):
        """GET /productos requiere JWT token"""
        response = client.get("/api/v1/mobile/productos")
        assert response.status_code == 401


# ============================================================================
# TESTS DE OPERACIONES (CREAR, PAGAR)
# ============================================================================

class TestMobileOperations:
    """Tests de operaciones de comanda"""
    
    def test_crear_comanda(self, client, valid_jwt_token, test_db, mobile_user):
        """Crear comanda exitosamente"""
        # Setup: crear zona, mesa y producto
        zona = Zona(nombre="Zona Principal")
        test_db.add(zona)
        test_db.flush()
        
        mesa = Mesa(
            nombre="M1",
            empresa_id=mobile_user.empresa_id,
            zona_id=zona.id,
            capacidad=4,
            estado="libre"
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
            empresa_id=mobile_user.empresa_id,
            activo=True
        )
        test_db.add(producto)
        test_db.commit()
        
        # Crear comanda
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        payload = {
            "mesa_id": mesa.id,
            "productos": [
                {
                    "producto_id": producto.id,
                    "cantidad": 2,
                    "notas": "Sin azúcar"
                }
            ]
        }
        
        response = client.post(
            "/api/v1/mobile/comandas",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "venta_id" in data
        assert data["estado"] == "abierta"
        assert len(data["productos"]) == 1
    
    def test_agregar_producto_a_comanda(self, client, valid_jwt_token, test_db, mobile_user):
        """Agregar producto a comanda existente"""
        # Este test requeriría crear primero una comanda
        # Simplificado por ahora
        pass
    
    def test_pagar_comanda(self, client, valid_jwt_token, test_db, mobile_user):
        """Pagar comanda"""
        # Este test requeriría crear y obtener venta_id
        # Simplificado por ahora
        pass


# ============================================================================
# TESTS DE SEGURIDAD
# ============================================================================

class TestSecurityMobile:
    """Tests de seguridad para Mobile API"""
    
    def test_bearer_token_required(self, client):
        """Endpoints requieren Bearer token"""
        response = client.get("/api/v1/mobile/mesas")
        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"] or "token" in response.json()["detail"].lower()
    
    def test_invalid_bearer_format(self, client):
        """Formato inválido de Bearer token"""
        headers = {"Authorization": "InvalidFormat token123"}
        response = client.get("/api/v1/mobile/mesas", headers=headers)
        assert response.status_code == 401
    
    def test_expired_token_denied(self, client, mobile_user, test_db):
        """Token expirado es rechazado"""
        # Crear token con expiración en el pasado
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        
        SECRET = "test-secret"
        expired_payload = {
            "usuario_id": mobile_user.id,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)
        }
        expired_token = jwt.encode(expired_payload, SECRET, algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/mobile/mesas", headers=headers)
        # Debería fallar o retornar 401
        assert response.status_code in [401, 422]
    
    def test_blacklisted_token_denied(self, client, valid_jwt_token, mobile_user):
        """Token en blacklist es rechazado"""
        TokenBlacklist.add(valid_jwt_token)
        
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}
        response = client.get("/api/v1/mobile/mesas", headers=headers)
        assert response.status_code == 401
        
        TokenBlacklist.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
