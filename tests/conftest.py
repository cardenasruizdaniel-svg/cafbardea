"""
Configuración compartida para tests - pytest
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from decimal import Decimal
import os

# Usar BD en memoria para tests
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_db_engine():
    """Crear engine para tests"""
    from app.database import Base
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
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
            rol="administrador"
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
    
    yield db
    db.close()


@pytest.fixture
def client(db_session):
    """Cliente FastAPI para testing"""
    from app.main import app
    from app.database import get_db
    
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()
