"""
Módulo Productos - Gestión de catálogo
"""

from .routes import router
from .services import ProductoService
from .schemas import (
    ProductoCreate, ProductoResponse, ProductoUpdate,
    CategoriaCreate, CategoriaResponse, EstadoProducto,
    TipoProducto, FiltroBusqueda, EstadisticasProductos,
    ResultadoBusquedaResponse, ProductoSimplificadoResponse,
    FavoritoResponse
)

__all__ = [
    "router",
    "ProductoService",
    "ProductoCreate",
    "ProductoResponse",
    "ProductoUpdate",
    "CategoriaCreate",
    "CategoriaResponse",
    "EstadoProducto",
    "TipoProducto",
    "FiltroBusqueda",
    "EstadisticasProductos",
    "ResultadoBusquedaResponse",
    "ProductoSimplificadoResponse",
    "FavoritoResponse"
]
