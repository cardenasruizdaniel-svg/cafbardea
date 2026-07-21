"""
FASE 9 - Reportes Ejecutivos API Tests
Suite de tests para endpoints de reportes
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
def datos_base(test_db):
    """Crea empresa, zona, mesa, producto y una venta pagada para pruebas."""
    empresa = Empresa(nombre="Test Café", nit="900.111.222-3")
    test_db.add(empresa)
    test_db.flush()

    empleado = Empleado(nombre="Mesero Demo", documento="111222333", cargo="Mesero", salario=1200000)
    test_db.add(empleado)
    test_db.flush()

    usuario = Usuario(
        empleado_id=empleado.id,
        empresa_id=empresa.id,
        usuario="mesero1",
        password_hash=passwords.hash("Pass123*"),
        rol="mesero",
        activo=True
    )
    test_db.add(usuario)
    test_db.flush()

    zona = Zona(nombre="Salón", empresa_id=empresa.id)
    test_db.add(zona)
    test_db.flush()

    mesa = Mesa(nombre="M1", empresa_id=empresa.id, zona_id=zona.id, capacidad=4)
    test_db.add(mesa)
    test_db.flush()

    cat = Categoria(nombre="Bebidas")
    test_db.add(cat)
    test_db.flush()

    producto = Producto(
        empresa_id=empresa.id,
        categoria_id=cat.id,
        codigo="CAF-001",
        nombre="Capuchino",
        precio_venta=Decimal("8500"),
        costo=Decimal("2500"),
        existencias=Decimal("50"),
        stock_minimo=Decimal("10"),
        activo=True
    )
    test_db.add(producto)
    test_db.flush()

    # Venta pagada de hoy
    venta = Venta(
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        mesa_id=mesa.id,
        estado="pagada",
        medio_pago="efectivo",
        subtotal=Decimal("8500"),
        impuesto=Decimal("680"),
        descuento=Decimal("0"),
        propina=Decimal("500"),
        total=Decimal("9680")
    )
    test_db.add(venta)
    test_db.flush()

    detalle = DetalleVenta(
        venta_id=venta.id,
        producto_id=producto.id,
        cantidad=Decimal("1"),
        precio=Decimal("8500"),
        costo_unitario=Decimal("2500"),
        estado_cocina="entregado"
    )
    test_db.add(detalle)
    test_db.commit()

    return {
        "empresa": empresa,
        "usuario": usuario,
        "empleado": empleado,
        "mesa": mesa,
        "producto": producto,
        "venta": venta,
        "detalle": detalle
    }


# ============================================================================
# Tests - Ventas
# ============================================================================

class TestReporteVentas:
    """Tests para GET /api/v1/reportes/ventas"""

    def test_reporte_ventas_vacio(self, client, setup_db_override):
        """Sin datos retorna estructura vacía con totales cero"""
        response = client.get("/api/v1/reportes/ventas")
        assert response.status_code == 200
        data = response.json()
        assert data["total_ventas"] == 0.0
        assert data["cantidad_transacciones"] == 0
        assert data["ticket_promedio"] == 0.0
        assert isinstance(data["ventas_por_dia"], list)
        assert isinstance(data["ventas_por_medio_pago"], list)

    def test_reporte_ventas_con_datos(self, client, datos_base):
        """Con una venta retorna el total correcto"""
        hoy = date.today().isoformat()
        response = client.get(f"/api/v1/reportes/ventas?desde={hoy}&hasta={hoy}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_ventas"] == 9680.0
        assert data["cantidad_transacciones"] == 1
        assert data["ticket_promedio"] == 9680.0

    def test_reporte_ventas_periodo(self, client, datos_base):
        """Filtro por período funciona"""
        hace_30 = (date.today() - timedelta(days=30)).isoformat()
        hoy = date.today().isoformat()
        response = client.get(f"/api/v1/reportes/ventas?desde={hace_30}&hasta={hoy}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_ventas"] >= 0

    def test_reporte_ventas_medio_pago(self, client, datos_base):
        """Incluye desglose por medio de pago"""
        hoy = date.today().isoformat()
        response = client.get(f"/api/v1/reportes/ventas?desde={hoy}&hasta={hoy}")
        assert response.status_code == 200
        data = response.json()
        medios = {m["medio"]: m["total"] for m in data["ventas_por_medio_pago"]}
        assert "efectivo" in medios
        assert medios["efectivo"] == 9680.0

    def test_reporte_ventas_defaults(self, client, datos_base):
        """Sin parámetros usa últimos 30 días"""
        response = client.get("/api/v1/reportes/ventas")
        assert response.status_code == 200
        data = response.json()
        assert "periodo_desde" in data
        assert "periodo_hasta" in data


# ============================================================================
# Tests - Productos
# ============================================================================

class TestReporteProductos:
    """Tests para GET /api/v1/reportes/productos"""

    def test_reporte_productos_vacio(self, client, setup_db_override):
        """Sin ventas retorna lista vacía"""
        response = client.get("/api/v1/reportes/productos")
        assert response.status_code == 200
        assert response.json() == []

    def test_reporte_productos_con_ventas(self, client, datos_base):
        """Con venta retorna producto con métricas"""
        hoy = date.today().isoformat()
        response = client.get(f"/api/v1/reportes/productos?desde={hoy}&hasta={hoy}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        prod = data[0]
        assert prod["codigo"] == "CAF-001"
        assert prod["ingresos"] == 8500.0
        assert prod["costo_total"] == 2500.0
        assert prod["margen_bruto"] == 6000.0
        assert prod["margen_porcentaje"] == pytest.approx(70.59, rel=0.01)

    def test_reporte_productos_limite(self, client, datos_base):
        """Parámetro limite funciona"""
        response = client.get("/api/v1/reportes/productos?limite=5")
        assert response.status_code == 200
        assert len(response.json()) <= 5

    def test_reporte_productos_limite_invalido(self, client, setup_db_override):
        """Limite inválido devuelve error 422"""
        response = client.get("/api/v1/reportes/productos?limite=0")
        assert response.status_code == 422


# ============================================================================
# Tests - Meseros
# ============================================================================

class TestReporteMeseros:
    """Tests para GET /api/v1/reportes/meseros"""

    def test_reporte_meseros_vacio(self, client, setup_db_override):
        """Sin ventas retorna lista vacía"""
        response = client.get("/api/v1/reportes/meseros")
        assert response.status_code == 200
        assert response.json() == []

    def test_reporte_meseros_con_ventas(self, client, datos_base):
        """Con ventas retorna estadísticas del mesero"""
        hoy = date.today().isoformat()
        response = client.get(f"/api/v1/reportes/meseros?desde={hoy}&hasta={hoy}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mesero = data[0]
        assert mesero["nombre"] == "Mesero Demo"
        assert mesero["ventas_cerradas"] == 1
        assert mesero["total_ventas"] == 9680.0
        assert mesero["propinas"] == 500.0


# ============================================================================
# Tests - Rentabilidad
# ============================================================================

class TestReporteRentabilidad:
    """Tests para GET /api/v1/reportes/rentabilidad"""

    def test_rentabilidad_vacia(self, client, setup_db_override):
        """Sin ventas todos los valores son 0"""
        response = client.get("/api/v1/reportes/rentabilidad")
        assert response.status_code == 200
        data = response.json()
        assert data["ingresos_totales"] == 0.0
        assert data["costo_ventas"] == 0.0
        assert data["margen_bruto"] == 0.0
        assert data["margen_bruto_pct"] == 0.0

    def test_rentabilidad_con_ventas(self, client, datos_base):
        """Calcula margen bruto correctamente"""
        hoy = date.today().isoformat()
        response = client.get(f"/api/v1/reportes/rentabilidad?desde={hoy}&hasta={hoy}")
        assert response.status_code == 200
        data = response.json()
        assert data["ingresos_totales"] == 9680.0
        assert data["costo_ventas"] == 2500.0
        assert data["margen_bruto"] == 7180.0
        assert data["margen_bruto_pct"] > 0

    def test_rentabilidad_incluye_descuentos_propinas(self, client, datos_base):
        """El resultado neto incluye descuentos y propinas"""
        hoy = date.today().isoformat()
        response = client.get(f"/api/v1/reportes/rentabilidad?desde={hoy}&hasta={hoy}")
        assert response.status_code == 200
        data = response.json()
        assert data["descuentos"] == 0.0
        assert data["propinas"] == 500.0
        assert "resultado_neto" in data


# ============================================================================
# Tests - Inventario
# ============================================================================

class TestReporteInventario:
    """Tests para GET /api/v1/reportes/inventario"""

    def test_inventario_vacio(self, client, setup_db_override):
        """Sin productos retorna lista vacía"""
        response = client.get("/api/v1/reportes/inventario")
        assert response.status_code == 200
        assert response.json() == []

    def test_inventario_con_productos(self, client, datos_base):
        """Con producto retorna análisis correcto"""
        response = client.get("/api/v1/reportes/inventario")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        item = data[0]
        assert item["codigo"] == "CAF-001"
        assert item["existencias"] == 50.0
        assert item["estado"] == "ok"
        assert item["categoria_abc"] in ["A", "B", "C"]
        assert item["valor_inventario"] == 50.0 * 2500.0

    def test_inventario_solo_bajos(self, client, test_db, datos_base):
        """Filtro solo_bajos excluye productos con stock ok"""
        response = client.get("/api/v1/reportes/inventario?solo_bajos=true")
        assert response.status_code == 200
        # El producto tiene 50 existencias y mínimo 10 → estado ok → no aparece
        assert response.json() == []

    def test_inventario_stock_bajo(self, client, test_db, datos_base):
        """Producto con stock bajo aparece en filtro"""
        # Bajar existencias por debajo del mínimo
        prod = datos_base["producto"]
        prod.existencias = Decimal("5")  # minimo es 10
        test_db.commit()

        response = client.get("/api/v1/reportes/inventario?solo_bajos=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["estado"] in ["bajo", "critico"]


# ============================================================================
# Tests - Exportar Excel
# ============================================================================

class TestExportarReporte:
    """Tests para GET /api/v1/reportes/exportar"""

    def test_exportar_ventas(self, client, datos_base):
        """Exporta ventas a Excel"""
        response = client.get("/api/v1/reportes/exportar?tipo=ventas")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]
        assert response.headers["content-disposition"].startswith('attachment; filename="reporte_ventas_')

    def test_exportar_productos(self, client, datos_base):
        """Exporta productos a Excel"""
        response = client.get("/api/v1/reportes/exportar?tipo=productos")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]

    def test_exportar_inventario(self, client, datos_base):
        """Exporta inventario a Excel"""
        response = client.get("/api/v1/reportes/exportar?tipo=inventario")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]

    def test_exportar_meseros(self, client, datos_base):
        """Exporta meseros a Excel"""
        response = client.get("/api/v1/reportes/exportar?tipo=meseros")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]

    def test_exportar_tipo_invalido(self, client, setup_db_override):
        """Tipo inválido retorna 400"""
        response = client.get("/api/v1/reportes/exportar?tipo=invalido")
        assert response.status_code == 400

    def test_exportar_sin_tipo(self, client, setup_db_override):
        """Sin parámetro tipo retorna 422"""
        response = client.get("/api/v1/reportes/exportar")
        assert response.status_code == 422
