"""
FASE 10 - Dashboard KPI Tests
Suite de tests para endpoints de KPI en tiempo real
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.models import (
    Empresa, Empleado, Usuario, Zona, Mesa, Categoria,
    Producto, Venta, DetalleVenta
)
from passlib.context import CryptContext
from app.models import fecha_colombia

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def TestingSessionLocal(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def setup_db_override(TestingSessionLocal):
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
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(setup_db_override):
    return TestClient(app)


@pytest.fixture(scope="function")
def client_autenticado(client, test_db):
    """Cliente de pruebas con sesion iniciada.

    Cerrado el bypass de autenticacion del middleware, los endpoints
    protegidos exigen sesion. Se siembra un usuario y se inicia sesion.
    """
    from app.models import Usuario, Empleado
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not test_db.query(Usuario).filter(Usuario.usuario == "testuser").first():
        emp = Empleado(nombre="Test Admin", documento="TEST-AUTH-001",
                       cargo="Administrador", salario=0)
        test_db.add(emp)
        test_db.flush()
        test_db.add(Usuario(empleado_id=emp.id, empresa_id=1, usuario="testuser",
                            password_hash=pwd.hash("Test123*"), rol="administrador"))
        test_db.commit()

    resp = client.post("/login",
                       data={"usuario": "testuser", "password": "Test123*"},
                       follow_redirects=False)
    assert resp.status_code == 303, f"login de prueba fallo: {resp.status_code}"
    return client


@pytest.fixture(scope="function")
def datos_dashboard(test_db):
    """Crea dataset completo: empresa, mesas, productos, ventas de hoy."""
    empresa = Empresa(nombre="Test Dashboard", nit="900.222.333-4")
    test_db.add(empresa)
    test_db.flush()

    empleado = Empleado(nombre="Mesero KPI", documento="555666777", cargo="Mesero", salario=1200000)
    test_db.add(empleado)
    test_db.flush()

    usuario = Usuario(
        empleado_id=empleado.id,
        empresa_id=empresa.id,
        usuario="mesero_kpi",
        password_hash=passwords.hash("Pass123*"),
        rol="mesero",
        activo=True
    )
    test_db.add(usuario)
    test_db.flush()

    zona = Zona(nombre="Salón", empresa_id=empresa.id)
    test_db.add(zona)
    test_db.flush()

    mesa1 = Mesa(nombre="M1", empresa_id=empresa.id, zona_id=zona.id, capacidad=4, estado="ocupada")
    mesa2 = Mesa(nombre="M2", empresa_id=empresa.id, zona_id=zona.id, capacidad=2, estado="libre")
    mesa3 = Mesa(nombre="M3", empresa_id=empresa.id, zona_id=zona.id, capacidad=4, estado="libre")
    test_db.add_all([mesa1, mesa2, mesa3])
    test_db.flush()

    cat_cafe = Categoria(nombre="Cafetería")
    cat_comida = Categoria(nombre="Comidas")
    test_db.add_all([cat_cafe, cat_comida])
    test_db.flush()

    prod1 = Producto(
        empresa_id=empresa.id, categoria_id=cat_cafe.id,
        codigo="C001", nombre="Capuchino",
        precio_venta=Decimal("8500"), costo=Decimal("2500"),
        existencias=Decimal("5"), stock_minimo=Decimal("10"),  # bajo mínimo
        activo=True
    )
    prod2 = Producto(
        empresa_id=empresa.id, categoria_id=cat_comida.id,
        codigo="F001", nombre="Croissant",
        precio_venta=Decimal("7000"), costo=Decimal("2000"),
        existencias=Decimal("30"), stock_minimo=Decimal("5"),
        activo=True
    )
    test_db.add_all([prod1, prod2])
    test_db.flush()

    # Dos ventas pagadas hoy
    for i, (p, mesa) in enumerate([(prod1, mesa1), (prod2, mesa1)]):
        venta = Venta(
            empresa_id=empresa.id, usuario_id=usuario.id,
            mesa_id=mesa.id, estado="pagada", medio_pago="efectivo",
            subtotal=p.precio_venta, impuesto=Decimal("0"),
            descuento=Decimal("0"), propina=Decimal("0"),
            total=p.precio_venta
        )
        test_db.add(venta)
        test_db.flush()
        test_db.add(DetalleVenta(
            venta_id=venta.id, producto_id=p.id,
            cantidad=Decimal("1"), precio=p.precio_venta,
            costo_unitario=p.costo
        ))

    test_db.commit()
    return {"empresa": empresa, "mesa1": mesa1, "prod1": prod1, "prod2": prod2}


# ============================================================================
# Tests - KPIs
# ============================================================================

class TestKPIEndpoint:
    """Tests para GET /api/v1/dashboard/kpis"""

    def test_kpis_estructura_completa(self, client_autenticado, setup_db_override):
        """Responde con todos los campos requeridos"""
        response = client_autenticado.get("/api/v1/dashboard/kpis")
        assert response.status_code == 200
        data = response.json()

        campos_requeridos = [
            "fecha", "hora_actualizacion",
            "ingresos_hoy", "transacciones_hoy", "ticket_promedio_hoy",
            "mesas_ocupadas", "mesas_totales", "ocupacion_pct", "alertas_stock",
            "vs_ayer", "vs_semana_pasada"
        ]
        for campo in campos_requeridos:
            assert campo in data, f"Falta campo: {campo}"

    def test_kpis_comparativa_estructura(self, client_autenticado, setup_db_override):
        """Comparativas tienen los campos correctos"""
        response = client_autenticado.get("/api/v1/dashboard/kpis")
        assert response.status_code == 200
        data = response.json()

        for comp in ["vs_ayer", "vs_semana_pasada"]:
            assert "valor_actual" in data[comp]
            assert "valor_anterior" in data[comp]
            assert "variacion_pct" in data[comp]
            assert "tendencia" in data[comp]
            assert data[comp]["tendencia"] in ["sube", "baja", "igual"]

    def test_kpis_sin_ventas(self, client_autenticado, setup_db_override):
        """Sin ventas, ingresos = 0 y ticket = 0"""
        response = client_autenticado.get("/api/v1/dashboard/kpis")
        assert response.status_code == 200
        data = response.json()
        assert data["ingresos_hoy"] == 0.0
        assert data["transacciones_hoy"] == 0
        assert data["ticket_promedio_hoy"] == 0.0

    def test_kpis_con_ventas(self, client_autenticado, datos_dashboard):
        """Con ventas refleja totales correctos"""
        response = client_autenticado.get("/api/v1/dashboard/kpis")
        assert response.status_code == 200
        data = response.json()
        assert data["ingresos_hoy"] == 8500.0 + 7000.0
        assert data["transacciones_hoy"] == 2
        assert data["ticket_promedio_hoy"] == (8500.0 + 7000.0) / 2

    def test_kpis_mesas_ocupacion(self, client_autenticado, datos_dashboard):
        """Ocupa 1 de 3 mesas → 33.3%"""
        response = client_autenticado.get("/api/v1/dashboard/kpis")
        assert response.status_code == 200
        data = response.json()
        assert data["mesas_totales"] == 3
        assert data["mesas_ocupadas"] == 1
        assert data["ocupacion_pct"] == pytest.approx(33.3, rel=0.01)

    def test_kpis_alertas_stock(self, client_autenticado, datos_dashboard):
        """Producto con stock bajo aparece en alertas"""
        response = client_autenticado.get("/api/v1/dashboard/kpis")
        assert response.status_code == 200
        data = response.json()
        assert data["alertas_stock"] >= 1  # prod1 tiene existencias < mínimo


# ============================================================================
# Tests - Ventas por hora
# ============================================================================

class TestVentasPorHora:
    """Tests para GET /api/v1/dashboard/ventas-por-hora"""

    def test_estructura_respuesta(self, client_autenticado, setup_db_override):
        """Retorna lista con las 24 horas del dia"""
        response = client_autenticado.get("/api/v1/dashboard/ventas-por-hora")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 24 horas: el rango 7-23 dejaba fuera las ventas de madrugada
        assert len(data) == 24

    def test_campos_por_hora(self, client_autenticado, setup_db_override):
        """Cada entrada tiene hora, label, total y transacciones"""
        response = client_autenticado.get("/api/v1/dashboard/ventas-por-hora")
        assert response.status_code == 200
        for item in response.json():
            assert "hora" in item
            assert "label" in item
            assert "total" in item
            assert "transacciones" in item

    def test_formato_label(self, client_autenticado, setup_db_override):
        """Labels tienen formato HH:00"""
        response = client_autenticado.get("/api/v1/dashboard/ventas-por-hora")
        for item in response.json():
            assert item["label"].endswith(":00")
            assert len(item["label"]) == 5

    def test_ventas_por_hora_con_datos(self, client_autenticado, datos_dashboard):
        """La hora de creación de ventas tiene total > 0"""
        response = client_autenticado.get("/api/v1/dashboard/ventas-por-hora")
        assert response.status_code == 200
        data = response.json()
        total_dia = sum(h["total"] for h in data)
        assert total_dia == pytest.approx(8500.0 + 7000.0)

    def test_filtro_dia(self, client_autenticado, datos_dashboard):
        """Parámetro dia filtra por fecha"""
        ayer = (fecha_colombia() - timedelta(days=1)).isoformat()
        response = client_autenticado.get(f"/api/v1/dashboard/ventas-por-hora?dia={ayer}")
        assert response.status_code == 200
        data = response.json()
        total_ayer = sum(h["total"] for h in data)
        assert total_ayer == 0.0  # no hay ventas de ayer


# ============================================================================
# Tests - Top Productos
# ============================================================================

class TestTopProductos:
    """Tests para GET /api/v1/dashboard/top-productos"""

    def test_sin_ventas_lista_vacia(self, client_autenticado, setup_db_override):
        """Sin ventas retorna lista vacía"""
        response = client_autenticado.get("/api/v1/dashboard/top-productos")
        assert response.status_code == 200
        assert response.json() == []

    def test_con_ventas_retorna_productos(self, client_autenticado, datos_dashboard):
        """Con ventas retorna productos ordenados por ingresos"""
        response = client_autenticado.get("/api/v1/dashboard/top-productos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["nombre"] == "Capuchino"  # 8500 > 7000
        assert data[0]["ingresos"] == 8500.0

    def test_limite_funciona(self, client_autenticado, datos_dashboard):
        """Parámetro limite respetado"""
        response = client_autenticado.get("/api/v1/dashboard/top-productos?limite=1")
        assert response.status_code == 200
        assert len(response.json()) <= 1

    def test_campos_requeridos(self, client_autenticado, datos_dashboard):
        """Cada entrada tiene nombre, cantidad e ingresos"""
        response = client_autenticado.get("/api/v1/dashboard/top-productos")
        for item in response.json():
            assert "nombre" in item
            assert "cantidad" in item
            assert "ingresos" in item


# ============================================================================
# Tests - Categorías
# ============================================================================

class TestCategorias:
    """Tests para GET /api/v1/dashboard/categorias"""

    def test_sin_ventas_lista_vacia(self, client_autenticado, setup_db_override):
        """Sin ventas retorna lista vacía"""
        response = client_autenticado.get("/api/v1/dashboard/categorias")
        assert response.status_code == 200
        assert response.json() == []

    def test_con_ventas_retorna_categorias(self, client_autenticado, datos_dashboard):
        """Con ventas retorna categorías con porcentajes"""
        response = client_autenticado.get("/api/v1/dashboard/categorias")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        total_pct = sum(c["porcentaje"] for c in data)
        assert total_pct == pytest.approx(100.0, rel=0.01)

    def test_campos_requeridos(self, client_autenticado, datos_dashboard):
        """Cada entrada tiene categoria, ingresos y porcentaje"""
        response = client_autenticado.get("/api/v1/dashboard/categorias")
        for item in response.json():
            assert "categoria" in item
            assert "ingresos" in item
            assert "porcentaje" in item
            assert 0 <= item["porcentaje"] <= 100


# ============================================================================
# Tests - Estado Mesas
# ============================================================================

class TestEstadoMesas:
    """Tests para GET /api/v1/dashboard/mesas"""

    def test_sin_mesas_ceros(self, client_autenticado, setup_db_override):
        """Sin mesas, todos los contadores en 0"""
        response = client_autenticado.get("/api/v1/dashboard/mesas")
        assert response.status_code == 200
        data = response.json()
        assert data["totales"] == 0
        assert data["ocupadas"] == 0
        assert data["libres"] == 0
        assert data["ocupacion_pct"] == 0.0

    def test_con_mesas_cuenta_correcta(self, client_autenticado, datos_dashboard):
        """1 ocupada de 3 → totales correctos"""
        response = client_autenticado.get("/api/v1/dashboard/mesas")
        assert response.status_code == 200
        data = response.json()
        assert data["totales"] == 3
        assert data["ocupadas"] == 1
        assert data["libres"] == 2
        assert data["ocupacion_pct"] == pytest.approx(33.3, rel=0.01)

    def test_campos_requeridos(self, client_autenticado, setup_db_override):
        """Respuesta incluye todos los campos"""
        response = client_autenticado.get("/api/v1/dashboard/mesas")
        assert response.status_code == 200
        data = response.json()
        for campo in ["libres", "ocupadas", "reservadas", "totales", "ocupacion_pct"]:
            assert campo in data
