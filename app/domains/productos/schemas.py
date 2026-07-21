"""
Schemas Pydantic para el módulo de Productos - FASE 2
Define validaciones y estructuras para catálogo de productos
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from decimal import Decimal
from enum import Enum


class EstadoProducto(str, Enum):
    """Estados de producto basados en atributo activo"""
    ACTIVO = "activo"
    INACTIVO = "inactivo"


class TipoProducto(str, Enum):
    """Tipos de producto en sistema"""
    VENTA = "venta"
    INSUMO = "insumo"
    ELABORADO = "elaborado"


# ============================================================================
# SCHEMAS DE ENTRADA (Input)
# ============================================================================

class CategoriaCreate(BaseModel):
    """Crear categoría de productos"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nombre": "Cafetería",
            "descripcion": "Bebidas de café premium",
            "orden": 1
        }
    })
    
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    orden: int = Field(default=1, ge=1)


class ProductoCreate(BaseModel):
    """Crear nuevo producto"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "categoria_id": 1,
            "codigo": "CAF-001",
            "nombre": "Capuchino",
            "precio_venta": "8500.00",
            "costo": "2400.00",
            "existencias": 50,
            "stock_minimo": 10,
            "tipo": "venta"
        }
    })
    
    categoria_id: int = Field(..., gt=0)
    codigo: str = Field(..., min_length=1, max_length=40)
    nombre: str = Field(..., min_length=1, max_length=120)
    precio_venta: Decimal = Field(..., gt=0)
    costo: Decimal = Field(..., ge=0)
    existencias: Decimal = Field(default=Decimal("0"), ge=0)
    stock_minimo: Decimal = Field(default=Decimal("0"), ge=0)
    tipo: str = Field(default="venta", description="venta, insumo, elaborado")
    
    @field_validator('precio_venta', 'costo', 'existencias', 'stock_minimo', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class ProductoUpdate(BaseModel):
    """Actualizar producto"""
    nombre: Optional[str] = None
    precio_venta: Optional[Decimal] = None
    costo: Optional[Decimal] = None
    existencias: Optional[Decimal] = None
    stock_minimo: Optional[Decimal] = None
    activo: Optional[bool] = None
    tipo: Optional[str] = None


class AgregarAFavoritos(BaseModel):
    """Agregar producto a favoritos"""
    producto_id: int = Field(..., gt=0)
    alias: Optional[str] = Field(None, max_length=100, description="Nombre personalizado")


# ============================================================================
# SCHEMAS DE SALIDA (Response)
# ============================================================================

class CategoriaResponse(BaseModel):
    """Respuesta: Categoría"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    nombre: str
    descripcion: Optional[str]
    orden: int
    productos_count: int


class ProductoResponse(BaseModel):
    """Respuesta: Producto completo"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "categoria_id": 1,
                "codigo": "CAF-001",
                "nombre": "Capuchino",
                "precio_venta": "8500.00",
                "costo": "2400.00",
                "existencias": "45.000",
                "activo": True,
                "tipo": "venta"
            }
        }
    )
    
    id: int
    categoria_id: Optional[int]
    codigo: str
    nombre: str
    precio_venta: Decimal
    costo: Decimal
    existencias: Decimal
    stock_minimo: Decimal
    tipo: str
    activo: bool


class ProductoSimplificadoResponse(BaseModel):
    """Respuesta: Producto para menú/POS"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    codigo: str
    nombre: str
    precio_venta: Decimal
    existencias: Decimal
    categoria: str
    activo: bool
    tipo: str


class ResultadoBusquedaResponse(BaseModel):
    """Respuesta: Resultado de búsqueda de productos"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "productos": [],
            "total": 0,
            "limit": 50,
            "offset": 0
        }
    })
    
    productos: List[ProductoSimplificadoResponse]
    total: int
    limit: int
    offset: int


class FavoritoResponse(BaseModel):
    """Respuesta: Producto en favoritos"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    producto_id: int
    producto_nombre: str
    alias: Optional[str]
    precio_venta: Decimal
    es_favorito: bool = True


# ============================================================================
# SCHEMAS DE BÚSQUEDA
# ============================================================================

class FiltroBusqueda(BaseModel):
    """Filtros para búsqueda de productos"""
    q: Optional[str] = Field(None, max_length=100, description="Búsqueda por nombre/código")
    categoria_id: Optional[int] = None
    tipo: Optional[str] = None
    activo: Optional[bool] = True
    precio_minimo: Optional[Decimal] = None
    precio_maximo: Optional[Decimal] = None
    en_stock: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    ordenar_por: str = Field(default="nombre", description="nombre | precio | existencias")


class EstadisticasProductos(BaseModel):
    """Estadísticas de productos"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total_productos": 50,
            "productos_activos": 48,
            "productos_sin_stock": 2,
            "valor_inventario": "250000.00",
            "productos_mas_vendidos": [],
            "categorias": 5
        }
    })
    
    total_productos: int
    productos_activos: int
    productos_sin_stock: int
    valor_inventario: Decimal
    categorias: int
    productos_por_tipo: dict
