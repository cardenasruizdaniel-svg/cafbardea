"""
Configuración compartida para tests - pytest
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from decimal import Decimal
import os

# En pruebas se desactiva el rate limiting: todos los tests corren desde la
# misma IP (testclient) y hacen login repetido, lo que dispararia el limite de
# fuerza bruta y haria fallar el setup. La proteccion CSRF SI queda activa y se
# ejercita a traves del cliente de pruebas.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# Usar BD en memoria para tests
# Archivo temporal en vez de ":memory:".
# Con SQLite en memoria cada conexion abre una base VACIA distinta, por lo que
# el usuario sembrado no era visible para la conexion que atendia /login.
import tempfile as _tempfile, os as _os
_TEST_DB_PATH = _os.path.join(_tempfile.gettempdir(), "cafbardla_tests.db")
TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"

@pytest.fixture(scope="session")
def test_db_engine():
    """Crear engine para tests"""
    from app.database import Base
    # Importar los modelos para que queden registrados en Base.metadata
    # antes de create_all; si no, no se crea ninguna tabla.
    import app.models  # noqa: F401
    import app.models_enterprise  # noqa: F401
    if _os.path.exists(_TEST_DB_PATH):
        _os.remove(_TEST_DB_PATH)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_db_engine):
    """Sesión de DB para cada test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestingSessionLocal()
    
    # Seed básico
    from app.models import Empresa, Usuario, Empleado, Zona, Mesa, Categoria, Producto
    from passlib.context import CryptContext
    
    passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    if db.query(Empresa).count() == 0:
        # Crear empresa
        empresa = Empresa(nombre="Test Café", nit="999.999.999-9")
        db.add(empresa)
        db.flush()
        
        # Crear empleado y usuario
        empleado = Empleado(
            nombre="Test Admin",
            documento="TEST-001",
            cargo="Administrador",
            salario=0
        )
        db.add(empleado)
        db.flush()
        
        usuario = Usuario(
            empleado_id=empleado.id,
            usuario="testuser",
            password_hash=passwords.hash("Test123*"),
            rol="administrador",
            activo=True,
            acceso_web=True
        )
        db.add(usuario)
        
        # Crear zonas
        salon = Zona(nombre="Salón", orden=1)
        terraza = Zona(nombre="Terraza", orden=2)
        db.add_all([salon, terraza])
        db.flush()
        
        # Crear mesas
        mesa1 = Mesa(zona_id=salon.id, nombre="M1", capacidad=4, posicion_x=10, posicion_y=10)
        mesa2 = Mesa(zona_id=salon.id, nombre="M2", capacidad=2, posicion_x=30, posicion_y=20)
        db.add_all([mesa1, mesa2])
        db.flush()
        
        # Crear categorías
        cafe = Categoria(nombre="Cafetería")
        comida = Categoria(nombre="Comidas")
        db.add_all([cafe, comida])
        db.flush()
        
        # Crear productos
        capuchino = Producto(
            categoria_id=cafe.id,
            codigo="CAF-001",
            nombre="Capuchino",
            precio_venta=Decimal("8500"),
            costo=Decimal("2400"),
            existencias=50,
            stock_minimo=10
        )
        
        latte = Producto(
            categoria_id=cafe.id,
            codigo="CAF-002",
            nombre="Latte",
            precio_venta=Decimal("9000"),
            costo=Decimal("2700"),
            existencias=40,
            stock_minimo=10
        )
        
        croissant = Producto(
            categoria_id=comida.id,
            codigo="COM-001",
            nombre="Croissant",
            precio_venta=Decimal("7000"),
            costo=Decimal("2500"),
            existencias=20,
            stock_minimo=5
        )
        
        db.add_all([capuchino, latte, croissant])
        db.commit()

    # Sembrar RBAC (roles y permisos) para que la autorizacion por modulo
    # funcione en las pruebas igual que en produccion.
    try:
        from app.services.rbac_service import inicializar_rbac
        from app.models_enterprise import Rol
        if db.query(Rol).count() == 0:
            inicializar_rbac(db)
            db.commit()
    except Exception:
        db.rollback()

    yield db
    db.close()


@pytest.fixture
def client(db_session):
    """Cliente FastAPI para testing.

    Envuelve el POST/PUT/PATCH/DELETE para adjuntar automaticamente el token
    CSRF en la cabecera X-CSRF-Token, tomandolo de la sesion. Asi las pruebas
    ejercitan el flujo real (con proteccion CSRF activa) sin tener que extraer
    el token de cada formulario.
    """
    from app.main import app
    from app.database import get_db

    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db

    import re as _re

    class ClienteCSRF(TestClient):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._csrf = None

        def _asegurar_token(self):
            for ruta in ("/empleados", "/dashboard", "/login"):
                r = super().get(ruta)
                m = _re.search(r'name="csrf_token" value="([^"]+)"', r.text)
                if m:
                    self._csrf = m.group(1)
                    return self._csrf
            return self._csrf

        def request(self, method, url, **kwargs):
            if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
                token = self._asegurar_token()
                if token:
                    headers = dict(kwargs.get("headers") or {})
                    headers["X-CSRF-Token"] = token
                    kwargs["headers"] = headers
                    data = kwargs.get("data")
                    if isinstance(data, dict) and "csrf_token" not in data:
                        data_copy = dict(data)
                        data_copy["csrf_token"] = token
                        kwargs["data"] = data_copy
            return super().request(method, url, **kwargs)

    yield ClienteCSRF(app)

    app.dependency_overrides.clear()

@pytest.fixture
def client_autenticado(client):
    """Cliente con sesion iniciada.

    Antes, el middleware listaba casi todas las rutas como publicas, de modo
    que los tests pasaban sin autenticarse. Cerrado ese bypass, las pruebas
    de endpoints protegidos deben iniciar sesion de forma explicita.
    """
    resp = client.post(
        "/login",
        data={"usuario": "testuser", "password": "Test123*"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, f"login de prueba fallo: {resp.status_code}"
    return client

