"""
Rutas (Endpoints) para módulo Productos - FASE 2
Gestión de catálogo, búsqueda y stock
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from .schemas import (
    ProductoCreate, ProductoResponse, ProductoUpdate,
    CategoriaCreate, CategoriaResponse, ResultadoBusquedaResponse,
    FiltroBusqueda, ProductoSimplificadoResponse,
    EstadisticasProductos, TipoProducto, EstadoProducto
)
from .services import ProductoService
from app.config import logger

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

router = APIRouter(
    prefix="/productos",
    tags=["productos"],
    responses={
        401: {"description": "No autenticado"},
        404: {"description": "No encontrado"},
        422: {"description": "Validación fallida"}
    }
)

# ============================================================================
# CREAR PRODUCTO
# ============================================================================

@router.post(
    "",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo producto"
)
def crear_producto(
    producto_data: ProductoCreate,
    db: Session = Depends(get_db)
):
    """Crear nuevo producto en catálogo"""
    try:
        service = ProductoService(db)
        producto = service.crear_producto(producto_data)
        
        logger.info(f"Producto {producto.nombre} creado - ${producto.precio_venta}")
        return producto
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creando producto: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creando producto")

# ============================================================================
# OBTENER PRODUCTO
# ============================================================================

@router.get(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Obtener producto por ID"
)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    """Obtener información completa del producto"""
    service = ProductoService(db)
    producto = service.obtener_producto(producto_id)
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return producto

# ============================================================================
# BUSCAR PRODUCTOS
# ============================================================================

@router.get(
    "/buscar/avanzado",
    response_model=ResultadoBusquedaResponse,
    summary="Búsqueda avanzada de productos"
)
def buscar_productos(
    q: Optional[str] = Query(None, max_length=100, description="Buscar por nombre/código"),
    categoria_id: Optional[int] = None,
    tipo: Optional[TipoProducto] = None,
    precio_minimo: Optional[float] = None,
    precio_maximo: Optional[float] = None,
    en_stock: Optional[bool] = None,
    ordenar_por: str = Query("nombre", pattern="^(nombre|precio|existencias)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Búsqueda avanzada con múltiples filtros
    
    Parámetros:
    - `q`: Buscar por nombre o código
    - `categoria_id`: Filtrar por categoría
    - `tipo`: bebida, comida, postre, acompanamiento, promocion
    - `precio_minimo/maximo`: Rango de precio
    - `en_stock`: Solo productos con existencia > 0
    - `ordenar_por`: nombre, precio, existencias
    """
    from decimal import Decimal
    
    filtro = FiltroBusqueda(
        q=q,
        categoria_id=categoria_id,
        tipo=tipo,
        precio_minimo=Decimal(str(precio_minimo)) if precio_minimo else None,
        precio_maximo=Decimal(str(precio_maximo)) if precio_maximo else None,
        en_stock=en_stock,
        limit=limit,
        offset=offset,
        ordenar_por=ordenar_por
    )
    
    service = ProductoService(db)
    productos, total = service.buscar_productos(filtro)
    
    return ResultadoBusquedaResponse(
        productos=[
            ProductoSimplificadoResponse(
                id=p.id,
                codigo=p.codigo,
                nombre=p.nombre,
                precio_venta=p.precio_venta,
                existencias=p.existencias,
                imagen_url=p.imagen_url,
                categoria=p.categoria.nombre if p.categoria else "Sin categoría",
                en_favoritos=False
            )
            for p in productos
        ],
        total=total,
        limit=limit,
        offset=offset
    )

# ============================================================================
# LISTAR POR CATEGORÍA
# ============================================================================

@router.get(
    "/categoria/{categoria_id}",
    response_model=List[ProductoSimplificadoResponse],
    summary="Listar productos por categoría"
)
def listar_por_categoria(
    categoria_id: int,
    db: Session = Depends(get_db)
):
    """Obtener todos los productos de una categoría"""
    service = ProductoService(db)
    productos = service.listar_por_categoria(categoria_id)
    
    return [
        ProductoSimplificadoResponse(
            id=p.id,
            codigo=p.codigo,
            nombre=p.nombre,
            precio_venta=p.precio_venta,
            existencias=p.existencias,
            imagen_url=p.imagen_url,
            categoria=p.categoria.nombre if p.categoria else "Sin categoría",
            en_favoritos=False
        )
        for p in productos
    ]

# ============================================================================
# ACTUALIZAR PRODUCTO
# ============================================================================

@router.patch(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Actualizar producto"
)
def actualizar_producto(
    producto_id: int,
    producto_data: ProductoUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar información del producto"""
    try:
        service = ProductoService(db)
        producto = service.actualizar_producto(producto_id, producto_data)
        
        logger.info(f"Producto {producto.nombre} actualizado")
        return producto
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

# ============================================================================
# GESTIÓN DE STOCK
# ============================================================================

@router.post(
    "/{producto_id}/stock/decrementar",
    response_model=ProductoResponse,
    summary="Decrementar stock (venta)"
)
def decrementar_stock(
    producto_id: int,
    cantidad: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Decrementar stock por venta"""
    try:
        service = ProductoService(db)
        producto = service.decrementar_stock(producto_id, cantidad)
        
        logger.info(f"Stock decrementado: {producto.nombre} -{cantidad}")
        return producto
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post(
    "/{producto_id}/stock/incrementar",
    response_model=ProductoResponse,
    summary="Incrementar stock"
)
def incrementar_stock(
    producto_id: int,
    cantidad: int = Query(..., gt=0),
    razon: str = Query("Compra"),
    db: Session = Depends(get_db)
):
    """Incrementar stock (compra, devolución)"""
    try:
        service = ProductoService(db)
        producto = service.incrementar_stock(producto_id, cantidad, razon)
        
        logger.info(f"Stock incrementado: {producto.nombre} +{cantidad} ({razon})")
        return producto
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

# ============================================================================
# PRODUCTOS BAJO STOCK
# ============================================================================

@router.get(
    "/alertas/bajo-stock",
    response_model=List[ProductoResponse],
    summary="Productos bajo stock"
)
def obtener_bajo_stock(db: Session = Depends(get_db)):
    """Obtener productos por debajo del mínimo"""
    service = ProductoService(db)
    productos = service.obtener_productos_bajo_stock()
    
    logger.info(f"Alerta: {len(productos)} productos bajo stock")
    return productos

# ============================================================================
# ESTADÍSTICAS
# ============================================================================

@router.get(
    "/reportes/estadisticas",
    response_model=EstadisticasProductos,
    summary="Estadísticas del catálogo"
)
def obtener_estadisticas(db: Session = Depends(get_db)):
    """Obtener estadísticas completas del catálogo"""
    service = ProductoService(db)
    stats = service.obtener_estadisticas()
    
    return EstadisticasProductos(
        total_productos=stats["total_productos"],
        productos_activos=stats["productos_activos"],
        productos_sin_stock=stats["productos_sin_stock"],
        valor_inventario=stats["valor_inventario"],
        categorias=stats["categorias"],
        productos_por_tipo=stats["productos_por_tipo"]
    )

# ============================================================================
# CATÁLOGOS (Enumeraciones)
# ============================================================================

@router.get(
    "/catalogo/tipos",
    response_model=List[str],
    summary="Tipos de producto disponibles"
)
def obtener_tipos():
    """Tipos válidos para un producto"""
    return ["venta", "insumo", "elaborado"]

@router.get(
    "/catalogo/estados",
    response_model=List[str],
    summary="Estados de producto"
)
def obtener_estados():
    """Estados válidos para un producto"""
    return ["activo", "inactivo"]
