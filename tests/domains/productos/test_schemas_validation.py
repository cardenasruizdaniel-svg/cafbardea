"""
Tests para validación de schemas de Productos
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from app.domains.productos.schemas import (
    ProductoCreate, ProductoUpdate, CategoriaCreate,
    EstadoProducto, TipoProducto, FiltroBusqueda
)


class TestEstadoProductoEnum:
    """Tests para enum EstadoProducto"""
    
    def test_estados_validos(self):
        """Verificar todos los estados válidos"""
        assert EstadoProducto.ACTIVO.value == "activo"
        assert EstadoProducto.INACTIVO.value == "inactivo"


class TestTipoProductoEnum:
    """Tests para enum TipoProducto"""
    
    def test_tipos_validos(self):
        """Verificar todos los tipos válidos"""
        assert TipoProducto.VENTA.value == "venta"
        assert TipoProducto.INSUMO.value == "insumo"
        assert TipoProducto.ELABORADO.value == "elaborado"


class TestCategoriaCreate:
    """Tests para schema CategoriaCreate"""
    
    def test_crear_categoria_valida(self):
        """Crear categoría con datos válidos"""
        cat = CategoriaCreate(
            nombre="Bebidas Calientes",
            descripcion="Cafés y tés premium",
            orden=1
        )
        assert cat.nombre == "Bebidas Calientes"
        assert cat.orden == 1
    
    def test_nombre_requerido(self):
        """nombre es requerido"""
        with pytest.raises(ValidationError):
            CategoriaCreate()
    
    def test_nombre_vacio_invalido(self):
        """nombre vacío es inválido"""
        with pytest.raises(ValidationError):
            CategoriaCreate(nombre="")
    
    def test_defaults(self):
        """Verificar valores por defecto"""
        cat = CategoriaCreate(nombre="Bebidas")
        assert cat.descripcion is None
        assert cat.orden == 1


class TestProductoCreate:
    """Tests para schema ProductoCreate"""
    
    def test_crear_producto_valido(self):
        """Crear producto con datos válidos"""
        prod = ProductoCreate(
            categoria_id=1,
            codigo="CAF-001",
            nombre="Capuchino",
            precio_venta=8500,
            costo=2400,
            existencias=50
        )
        assert prod.codigo == "CAF-001"
        assert prod.nombre == "Capuchino"
        assert isinstance(prod.precio_venta, Decimal)
        assert isinstance(prod.costo, Decimal)
    
    def test_categoria_id_requerido(self):
        """categoria_id es requerido"""
        with pytest.raises(ValidationError):
            ProductoCreate(codigo="A1", nombre="Producto")
    
    def test_codigo_requerido(self):
        """código es requerido"""
        with pytest.raises(ValidationError):
            ProductoCreate(categoria_id=1, nombre="Producto")
    
    def test_nombre_requerido(self):
        """nombre es requerido"""
        with pytest.raises(ValidationError):
            ProductoCreate(categoria_id=1, codigo="A1")
    
    def test_precio_venta_requerido(self):
        """precio_venta es requerido"""
        with pytest.raises(ValidationError):
            ProductoCreate(
                categoria_id=1, codigo="A1", nombre="P",
                costo=100
            )
    
    def test_precio_venta_positivo(self):
        """precio_venta debe ser > 0"""
        with pytest.raises(ValidationError):
            ProductoCreate(
                categoria_id=1, codigo="A1", nombre="P",
                precio_venta=0, costo=100
            )
    
    def test_costo_no_negativo(self):
        """costo no puede ser negativo"""
        with pytest.raises(ValidationError):
            ProductoCreate(
                categoria_id=1, codigo="A1", nombre="P",
                precio_venta=100, costo=-10
            )
    
    def test_decimal_conversion_desde_string(self):
        """Convertir string a Decimal"""
        prod = ProductoCreate(
            categoria_id=1, codigo="A1", nombre="P",
            precio_venta="8500.50",
            costo="2400.25"
        )
        assert prod.precio_venta == Decimal("8500.50")
        assert prod.costo == Decimal("2400.25")
    
    def test_decimal_conversion_desde_float(self):
        """Convertir float a Decimal"""
        prod = ProductoCreate(
            categoria_id=1, codigo="A1", nombre="P",
            precio_venta=8500.50,
            costo=2400.25
        )
        assert isinstance(prod.precio_venta, Decimal)
        assert isinstance(prod.costo, Decimal)
    
    def test_existencias_default(self):
        """Existencias por defecto es 0"""
        prod = ProductoCreate(
            categoria_id=1, codigo="A1", nombre="P",
            precio_venta=100, costo=50
        )
        assert prod.existencias == 0
    
    def test_stock_minimo_default(self):
        """Stock mínimo por defecto es 0"""
        prod = ProductoCreate(
            categoria_id=1, codigo="A1", nombre="P",
            precio_venta=100, costo=50
        )
        assert prod.stock_minimo == Decimal("0")
    
    def test_tipo_default(self):
        """Tipo por defecto es venta"""
        prod = ProductoCreate(
            categoria_id=1, codigo="A1", nombre="P",
            precio_venta=100, costo=50
        )
        assert prod.tipo == "venta"


class TestProductoUpdate:
    """Tests para schema ProductoUpdate"""
    
    def test_todos_campos_opcionales(self):
        """Todos los campos son opcionales"""
        update = ProductoUpdate()
        assert update.nombre is None
        assert update.precio_venta is None
        assert update.activo is None
    
    def test_actualizar_precio(self):
        """Actualizar solo precio"""
        update = ProductoUpdate(precio_venta=9000)
        assert update.precio_venta == 9000
        assert update.nombre is None
    
    def test_actualizar_multiples_campos(self):
        """Actualizar múltiples campos"""
        update = ProductoUpdate(
            nombre="Capuchino Premium",
            precio_venta=12000,
            activo=True
        )
        assert update.nombre == "Capuchino Premium"
        assert update.precio_venta == 12000


class TestFiltroBusqueda:
    """Tests para schema FiltroBusqueda"""
    
    def test_filtro_vacio(self):
        """Crear filtro vacío con defaults"""
        filtro = FiltroBusqueda()
        assert filtro.q is None
        assert filtro.categoria_id is None
        assert filtro.limit == 50
        assert filtro.offset == 0
        assert filtro.ordenar_por == "nombre"
        assert filtro.activo is True
    
    def test_filtro_con_busqueda(self):
        """Filtro con búsqueda por texto"""
        filtro = FiltroBusqueda(q="café")
        assert filtro.q == "café"
    
    def test_paginacion(self):
        """Filtro con paginación"""
        filtro = FiltroBusqueda(limit=100, offset=50)
        assert filtro.limit == 100
        assert filtro.offset == 50
    
    def test_ordenamiento_valido(self):
        """Verificar ordenamientos válidos"""
        f1 = FiltroBusqueda(ordenar_por="nombre")
        f2 = FiltroBusqueda(ordenar_por="precio")
        f3 = FiltroBusqueda(ordenar_por="existencias")
        
        assert f1.ordenar_por == "nombre"
        assert f2.ordenar_por == "precio"
        assert f3.ordenar_por == "existencias"
    
    def test_limit_maximo(self):
        """Limit máximo validado"""
        filtro = FiltroBusqueda(limit=1000)
        assert filtro.limit == 1000
        
        with pytest.raises(ValidationError):
            FiltroBusqueda(limit=1001)
    
    def test_limit_minimo(self):
        """Limit mínimo es 1"""
        with pytest.raises(ValidationError):
            FiltroBusqueda(limit=0)
