"""
Service Layer para Mesas - Gestión de floor plan y estados
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models import Mesa, Zona, Venta
from .schemas import MesaCreate, MesaUpdate, CambiarEstadoMesa, EstadoMesa, ReservarMesa
from app.config import logger


class MesaService:
    """Servicio de lógica de negocio para mesas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # CREAR MESA
    # ========================================================================
    
    def crear_mesa(self, mesa_data: MesaCreate, empresa_id: int) -> Mesa:
        """
        Crear nueva mesa en zona
        
        Args:
            mesa_data: Datos de la mesa
            empresa_id: ID de empresa
            
        Returns:
            Mesa creada
        """
        try:
            # Validar zona existe
            zona = self.db.get(Zona, mesa_data.zona_id)
            if not zona:
                raise ValueError(f"Zona {mesa_data.zona_id} no encontrada")
            
            # Crear mesa
            mesa = Mesa(
                zona_id=mesa_data.zona_id,
                nombre=mesa_data.nombre,
                capacidad=mesa_data.capacidad,
                posicion_x=mesa_data.posicion_x,
                posicion_y=mesa_data.posicion_y,
                forma=mesa_data.forma.value if hasattr(mesa_data.forma, 'value') else mesa_data.forma,
                estado="disponible"
            )
            
            self.db.add(mesa)
            self.db.commit()
            
            self.logger.info(f"Mesa {mesa.nombre} creada en zona {zona.nombre}")
            return mesa
            
        except ValueError as e:
            self.db.rollback()
            self.logger.warning(f"Error creando mesa: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error inesperado creando mesa: {str(e)}")
            raise
    
    # ========================================================================
    # CONSULTAR MESAS
    # ========================================================================
    
    def obtener_mesa(self, mesa_id: int) -> Optional[Mesa]:
        """Obtener mesa por ID"""
        return self.db.get(Mesa, mesa_id)
    
    def listar_mesas_por_zona(self, zona_id: int, limit: int = 100) -> List[Mesa]:
        """Listar mesas de una zona"""
        return self.db.query(Mesa) \
            .filter(Mesa.zona_id == zona_id) \
            .order_by(Mesa.nombre) \
            .limit(limit) \
            .all()
    
    def obtener_floor_plan(self) -> dict:
        """Obtener plano completo con todas las zonas y mesas"""
        zonas = self.db.query(Zona).order_by(Zona.orden).all()
        
        estadisticas = {
            "total_mesas": 0,
            "mesas_disponibles": 0,
            "mesas_ocupadas": 0,
            "ocupacion_porcentaje": 0
        }
        
        for zona in zonas:
            mesas = zona.mesas
            estadisticas["total_mesas"] += len(mesas)
            estadisticas["mesas_disponibles"] += len([m for m in mesas if m.estado == "disponible"])
            estadisticas["mesas_ocupadas"] += len([m for m in mesas if m.estado == "ocupada"])
        
        if estadisticas["total_mesas"] > 0:
            estadisticas["ocupacion_porcentaje"] = int(
                (estadisticas["mesas_ocupadas"] / estadisticas["total_mesas"]) * 100
            )
        
        return {
            "zonas": zonas,
            "estadisticas": estadisticas
        }
    
    # ========================================================================
    # ACTUALIZAR MESA
    # ========================================================================
    
    def actualizar_mesa(self, mesa_id: int, mesa_data: MesaUpdate) -> Mesa:
        """Actualizar información de mesa"""
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")
        
        # Actualizar solo campos que vienen
        if mesa_data.nombre:
            mesa.nombre = mesa_data.nombre
        if mesa_data.capacidad:
            mesa.capacidad = mesa_data.capacidad
        if mesa_data.posicion_x is not None:
            mesa.posicion_x = mesa_data.posicion_x
        if mesa_data.posicion_y is not None:
            mesa.posicion_y = mesa_data.posicion_y
        if mesa_data.forma:
            mesa.forma = mesa_data.forma.value if hasattr(mesa_data.forma, 'value') else mesa_data.forma
        if mesa_data.estado:
            mesa.estado = mesa_data.estado.value if hasattr(mesa_data.estado, 'value') else mesa_data.estado
        
        self.db.commit()
        self.logger.info(f"Mesa {mesa.nombre} actualizada")
        
        return mesa
    
    # ========================================================================
    # CAMBIAR ESTADO
    # ========================================================================
    
    def cambiar_estado(self, mesa_id: int, cambio: CambiarEstadoMesa) -> Mesa:
        """Cambiar estado de mesa"""
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")
        
        estado_anterior = mesa.estado
        mesa.estado = cambio.estado.value if hasattr(cambio.estado, 'value') else cambio.estado
        
        self.db.commit()
        
        self.logger.info(
            f"Mesa {mesa.nombre}: {estado_anterior} → {mesa.estado}" +
            (f" ({cambio.motivo})" if cambio.motivo else "")
        )
        
        return mesa
    
    def ocupar_mesa(self, mesa_id: int, venta_id: int) -> Mesa:
        """Marcar mesa como ocupada por una venta"""
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")
        
        if mesa.estado != "disponible":
            raise ValueError(f"Mesa {mesa.nombre} no está disponible (estado: {mesa.estado})")
        
        mesa.estado = "ocupada"
        self.db.commit()
        
        self.logger.info(f"Mesa {mesa.nombre} ocupada (venta {venta_id})")
        return mesa
    
    def liberar_mesa(self, mesa_id: int) -> Mesa:
        """Liberar mesa (cambiar a disponible)"""
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")
        
        mesa.estado = "disponible"
        self.db.commit()
        
        self.logger.info(f"Mesa {mesa.nombre} liberada")
        return mesa
    
    def marcar_limpieza(self, mesa_id: int) -> Mesa:
        """Marcar mesa en limpieza"""
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")
        
        mesa.estado = "limpieza"
        self.db.commit()
        
        self.logger.info(f"Mesa {mesa.nombre} en limpieza")
        return mesa
    
    # ========================================================================
    # ESTADÍSTICAS
    # ========================================================================
    
    def obtener_estadisticas(self) -> dict:
        """Obtener estadísticas de ocupación"""
        total = self.db.query(func.count(Mesa.id)).scalar() or 0
        
        estados = self.db.query(
            Mesa.estado,
            func.count(Mesa.id)
        ).group_by(Mesa.estado).all()
        
        estado_dict = {estado: count for estado, count in estados}
        
        disponibles = estado_dict.get("disponible", 0)
        ocupadas = estado_dict.get("ocupada", 0)
        
        return {
            "total_mesas": total,
            "disponibles": disponibles,
            "ocupadas": ocupadas,
            "en_limpieza": estado_dict.get("limpieza", 0),
            "reservadas": estado_dict.get("reservada", 0),
            "mantenimiento": estado_dict.get("mantenimiento", 0),
            "ocupacion_porcentaje": int((ocupadas / total * 100)) if total > 0 else 0,
            "por_estado": estado_dict
        }
    
    def obtener_mesas_disponibles(self, capacidad_minima: int = 1) -> List[Mesa]:
        """Obtener mesas disponibles con capacidad mínima"""
        return self.db.query(Mesa) \
            .filter(
                and_(
                    Mesa.estado == "disponible",
                    Mesa.capacidad >= capacidad_minima
                )
            ) \
            .order_by(Mesa.capacidad) \
            .all()
