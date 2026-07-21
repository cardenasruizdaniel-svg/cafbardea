"""
Service Layer para Productos - Gestión de catálogo
"""

import logging
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from app.models import Producto, Categoria
from .schemas import ProductoCreate, ProductoUpdate, FiltroBusqueda
from app.config import logger


class ProductoService:
    """Servicio de lógica de negocio para productos"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # CREAR PRODUCTO
    # ========================================================================
    
    def crear_producto(self, producto_data: ProductoCreate) -> Producto:
        """
        Crear nuevo producto
        
        Args:
            producto_data: Datos del producto
            
        Returns:
            Producto creado
        """
        try:
            # Validar categoría existe
            categoria = self.db.get(Categoria, producto_data.categoria_id)
            if not categoria:
                raise ValueError(f"Categoría {producto_data.categoria_id} no existe")
            
            # Validar código único
            existente = self.db.query(Producto) \
                .filter(Producto.codigo == producto_data.codigo) \
                .first()
            if existente:
                raise ValueError(f"Código {producto_data.codigo} ya existe")
            
            # Validar margen
            if producto_data.precio_venta <= producto_data.costo:
                self.logger.warning(
                    f"Margen negativo: {producto_data.nombre} "
                    f"(venta: {producto_data.precio_venta}, costo: {producto_data.costo})"
                )
            
            # Crear producto
            producto = Producto(
                categoria_id=producto_data.categoria_id,
                codigo=producto_data.codigo,
                nombre=producto_data.nombre,
                descripcion=producto_data.descripcion,
                precio_venta=producto_data.precio_venta,
                costo=producto_data.costo,
                existencias=producto_data.existencias,
                stock_minimo=producto_data.stock_minimo
            )
            
            self.db.add(producto)
            self.db.commit()
            
            self.logger.info(f"Producto {producto.nombre} creado - Precio: {producto.precio_venta}")
            return producto
            
        except ValueError as e:
            self.db.rollback()
            self.logger.warning(f"Error creando producto: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error inesperado: {str(e)}")
            raise
    
    # ========================================================================
    # CONSULTAR PRODUCTOS
    # ========================================================================
    
    def obtener_producto(self, producto_id: int) -> Optional[Producto]:
        """Obtener producto por ID"""
        return self.db.get(Producto, producto_id)
    
    def obtener_por_codigo(self, codigo: str) -> Optional[Producto]:
        """Obtener producto por código"""
        return self.db.query(Producto) \
            .filter(Producto.codigo == codigo) \
            .first()
    
    def buscar_productos(self, filtro: FiltroBusqueda) -> tuple[List[Producto], int]:
        """
        Búsqueda avanzada de productos
        
        Returns:
            Tupla (productos, total)
        """
        query = self.db.query(Producto)
        
        # Filtros básicos
        if filtro.q:
            query = query.filter(
                or_(
                    Producto.nombre.ilike(f"%{filtro.q}%"),
                    Producto.codigo.ilike(f"%{filtro.q}%")
                )
            )
        
        if filtro.categoria_id:
            query = query.filter(Producto.categoria_id == filtro.categoria_id)
        
        if filtro.tipo:
            query = query.filter(Producto.tipo == filtro.tipo)
        
        # Filtro activo
        if filtro.activo is not None:
            query = query.filter(Producto.activo == filtro.activo)
        
        # Filtro de rango de precio
        if filtro.precio_minimo:
            query = query.filter(Producto.precio_venta >= filtro.precio_minimo)
        if filtro.precio_maximo:
            query = query.filter(Producto.precio_venta <= filtro.precio_maximo)
        
        # Stock
        if filtro.en_stock:
            query = query.filter(Producto.existencias > 0)
        
        # Contar total
        total = query.count()
        
        # Ordenamiento
        if filtro.ordenar_por == "precio":
            query = query.order_by(Producto.precio_venta)
        elif filtro.ordenar_por == "existencias":
            query = query.order_by(Producto.existencias.desc())
        else:  # default: nombre
            query = query.order_by(Producto.nombre)
        
        # Paginación
        productos = query.offset(filtro.offset).limit(filtro.limit).all()
        
        return productos, total
    
    def listar_por_categoria(self, categoria_id: int, limit: int = 100) -> List[Producto]:
        """Listar productos de una categoría"""
        return self.db.query(Producto) \
            .filter(Producto.categoria_id == categoria_id) \
            .order_by(Producto.nombre) \
            .limit(limit) \
            .all()
    
    # ========================================================================
    # ACTUALIZAR PRODUCTO
    # ========================================================================
    
    def actualizar_producto(self, producto_id: int, producto_data: ProductoUpdate) -> Producto:
        """Actualizar producto"""
        producto = self.obtener_producto(producto_id)
        if not producto:
            raise ValueError(f"Producto {producto_id} no encontrado")
        
        if producto_data.nombre:
            producto.nombre = producto_data.nombre
        if producto_data.precio_venta:
            producto.precio_venta = producto_data.precio_venta
        if producto_data.costo is not None:
            producto.costo = producto_data.costo
        if producto_data.existencias is not None:
            producto.existencias = producto_data.existencias
        if producto_data.stock_minimo is not None:
            producto.stock_minimo = producto_data.stock_minimo
        if producto_data.activo is not None:
            producto.activo = producto_data.activo
        if producto_data.tipo:
            producto.tipo = producto_data.tipo
        
        self.db.commit()
        self.logger.info(f"Producto {producto.nombre} actualizado")
        
        return producto
    
    # ========================================================================
    # GESTIÓN DE STOCK
    # ========================================================================
    
    def decrementar_stock(self, producto_id: int, cantidad: int) -> Producto:
        """Decrementar stock (venta)"""
        producto = self.obtener_producto(producto_id)
        if not producto:
            raise ValueError(f"Producto {producto_id} no encontrado")
        
        if producto.existencias < cantidad:
            raise ValueError(
                f"Stock insuficiente: {producto.nombre} "
                f"({producto.existencias} < {cantidad})"
            )
        
        producto.existencias -= cantidad
        self.db.commit()
        
        self.logger.info(f"Stock {producto.nombre}: -{cantidad} (nuevo: {producto.existencias})")
        return producto
    
    def incrementar_stock(self, producto_id: int, cantidad: int, razon: str = "Compra") -> Producto:
        """Incrementar stock (compra, devolución)"""
        producto = self.obtener_producto(producto_id)
        if not producto:
            raise ValueError(f"Producto {producto_id} no encontrado")
        
        producto.existencias += cantidad
        self.db.commit()
        
        self.logger.info(
            f"Stock {producto.nombre}: +{cantidad} ({razon}) "
            f"(nuevo: {producto.existencias})"
        )
        return producto
    
    def obtener_productos_bajo_stock(self) -> List[Producto]:
        """Obtener productos por debajo del mínimo"""
        return self.db.query(Producto) \
            .filter(Producto.existencias <= Producto.stock_minimo) \
            .order_by(Producto.existencias) \
            .all()
    
    # ========================================================================
    # ESTADÍSTICAS
    # ========================================================================
    
    def obtener_estadisticas(self) -> dict:
        """Obtener estadísticas de catálogo"""
        total = self.db.query(func.count(Producto.id)).scalar() or 0
        activos = self.db.query(func.count(Producto.id)) \
            .filter(Producto.estado == "activo") \
            .scalar() or 0
        sin_stock = self.db.query(func.count(Producto.id)) \
            .filter(Producto.existencias == 0) \
            .scalar() or 0
        
        # Valor total del inventario
        valor_inventario = self.db.query(
            func.sum(Producto.costo * Producto.existencias)
        ).scalar() or Decimal("0")
        
        # Productos por tipo
        por_tipo = self.db.query(
            Producto.tipo,
            func.count(Producto.id)
        ).group_by(Producto.tipo).all()
        
        return {
            "total_productos": total,
            "productos_activos": activos,
            "productos_sin_stock": sin_stock,
            "valor_inventario": valor_inventario,
            "categorias": self.db.query(func.count(Categoria.id)).scalar() or 0,
            "productos_por_tipo": {tipo: count for tipo, count in por_tipo}
        }
    
    def obtener_productos_populares(self, limite: int = 10) -> List[Producto]:
        """Obtener productos más vendidos (placeholder para futuro)"""
        return self.db.query(Producto) \
            .filter(Producto.estado == "activo") \
            .order_by(Producto.precio_venta.desc()) \
            .limit(limite) \
            .all()
