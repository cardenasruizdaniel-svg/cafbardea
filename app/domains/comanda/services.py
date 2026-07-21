"""
Service layer para Comanda (Kitchen Management) - FASE 3
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models import Comanda, Venta, DetalleVenta, Mesa
from .schemas import ComandaCreate, ComandaUpdate, CambiarEstadoComanda

logger = logging.getLogger(__name__)


class ComandaService:
    """Servicio de gestión de comandas (kitchen management)"""

    def __init__(self, db: Session):
        self.db = db
        logger.debug("ComandaService inicializado")

    def crear_comanda(self, comanda_data: ComandaCreate) -> Comanda:
        """Crear nueva comanda"""
        # Validar que venta existe
        venta = self.db.query(Venta).filter(Venta.id == comanda_data.venta_id).first()
        if not venta:
            logger.error(f"Venta {comanda_data.venta_id} no existe")
            raise ValueError(f"Venta {comanda_data.venta_id} no existe")

        comanda = Comanda(
            venta_id=comanda_data.venta_id,
            mesa_id=comanda_data.mesa_id,
            estado="pendiente",
            prioridad=comanda_data.prioridad,
            notas=comanda_data.notas,
            fecha_creacion=datetime.utcnow()
        )
        
        self.db.add(comanda)
        self.db.commit()
        self.db.refresh(comanda)
        
        logger.info(f"Comanda {comanda.id} creada para venta {comanda_data.venta_id}")
        return comanda

    def obtener_comanda(self, comanda_id: int) -> Optional[Comanda]:
        """Obtener comanda por ID"""
        comanda = self.db.query(Comanda).filter(Comanda.id == comanda_id).first()
        if not comanda:
            logger.warning(f"Comanda {comanda_id} no encontrada")
        return comanda

    def listar_comandas_por_estado(self, estado: str) -> List[Comanda]:
        """Listar comandas por estado"""
        comandas = self.db.query(Comanda).filter(
            Comanda.estado == estado
        ).order_by(Comanda.fecha_creacion.desc()).all()
        
        logger.debug(f"Encontradas {len(comandas)} comandas en estado {estado}")
        return comandas

    def obtener_comandas_pendientes(self) -> List[Comanda]:
        """Obtener todas las comandas pendientes (no entregadas)"""
        comandas = self.db.query(Comanda).filter(
            Comanda.estado.in_(["pendiente", "preparando"])
        ).order_by(
            Comanda.prioridad,
            Comanda.fecha_creacion
        ).all()
        
        return comandas

    def cambiar_estado(
        self,
        comanda_id: int,
        cambio: CambiarEstadoComanda
    ) -> Comanda:
        """Cambiar estado de comanda"""
        comanda = self.obtener_comanda(comanda_id)
        if not comanda:
            logger.error(f"Comanda {comanda_id} no existe")
            raise ValueError(f"Comanda {comanda_id} no existe")

        estado_anterior = comanda.estado
        comanda.estado = cambio.estado
        
        # Registrar timestamp de entrega si se marca como lista o entregada
        if cambio.estado in ["lista", "entregada"]:
            comanda.fecha_entrega = datetime.utcnow()
        
        if cambio.notas:
            comanda.notas = (comanda.notas or "") + f"\n[{datetime.utcnow().isoformat()}] {cambio.notas}"
        
        self.db.commit()
        self.db.refresh(comanda)
        
        logger.info(
            f"Comanda {comanda_id} cambió de {estado_anterior} a {cambio.estado}"
        )
        return comanda

    def aumentar_prioridad(self, comanda_id: int) -> Comanda:
        """Aumentar prioridad de comanda"""
        comanda = self.obtener_comanda(comanda_id)
        if not comanda:
            raise ValueError(f"Comanda {comanda_id} no existe")

        prioridad_mapping = {
            "normal": "alta",
            "alta": "urgente",
            "urgente": "urgente"
        }
        
        comanda.prioridad = prioridad_mapping.get(comanda.prioridad, "normal")
        self.db.commit()
        self.db.refresh(comanda)
        
        logger.info(f"Prioridad de comanda {comanda_id} aumentada a {comanda.prioridad}")
        return comanda

    def obtener_lista_espera(self) -> List[Dict]:
        """Obtener lista de espera (comandas pendientes con tiempo de espera)"""
        ahora = datetime.utcnow()
        
        comandas = self.db.query(Comanda).filter(
            Comanda.estado.in_(["pendiente", "preparando"])
        ).order_by(
            Comanda.prioridad,
            Comanda.fecha_creacion
        ).all()

        lista = []
        for comanda in comandas:
            tiempo_espera = (ahora - comanda.fecha_creacion).total_seconds() / 60
            lista.append({
                "id": comanda.id,
                "venta_id": comanda.venta_id,
                "mesa_id": comanda.mesa_id,
                "estado": comanda.estado,
                "prioridad": comanda.prioridad,
                "tiempo_espera_minutos": int(tiempo_espera),
                "notas": comanda.notas
            })
        
        return lista

    def obtener_estadisticas(self) -> Dict:
        """Obtener estadísticas de comandas"""
        total = self.db.query(func.count(Comanda.id)).scalar() or 0
        
        # Contar por estado
        por_estado = {}
        for estado in ["pendiente", "preparando", "lista", "entregada", "cancelada"]:
            count = self.db.query(func.count(Comanda.id)).filter(
                Comanda.estado == estado
            ).scalar() or 0
            por_estado[estado] = count

        # Contar por prioridad
        por_prioridad = {}
        for prioridad in ["normal", "alta", "urgente"]:
            count = self.db.query(func.count(Comanda.id)).filter(
                Comanda.prioridad == prioridad
            ).scalar() or 0
            por_prioridad[prioridad] = count

        # Calcular tiempo promedio
        tiempo_promedio = None
        entregadas = self.db.query(Comanda).filter(
            Comanda.estado == "entregada",
            Comanda.fecha_entrega.isnot(None)
        ).all()
        
        if entregadas:
            tiempos = []
            for cmd in entregadas:
                if cmd.fecha_entrega:
                    td = (cmd.fecha_entrega - cmd.fecha_creacion).total_seconds() / 60
                    tiempos.append(td)
            if tiempos:
                tiempo_promedio = Decimal(sum(tiempos) / len(tiempos))

        return {
            "total_comandas": total,
            "por_estado": por_estado,
            "por_prioridad": por_prioridad,
            "tiempo_promedio_minutos": tiempo_promedio,
            "comandas_pendientes": por_estado.get("pendiente", 0),
            "comandas_en_cocina": por_estado.get("preparando", 0)
        }

    def obtener_tiempo_promedio_preparacion(self) -> Optional[Decimal]:
        """Obtener tiempo promedio de preparación en minutos"""
        entregadas = self.db.query(Comanda).filter(
            Comanda.estado == "entregada",
            Comanda.fecha_entrega.isnot(None)
        ).all()

        if not entregadas:
            return None

        tiempos = []
        for comanda in entregadas:
            if comanda.fecha_entrega:
                td = (comanda.fecha_entrega - comanda.fecha_creacion).total_seconds() / 60
                tiempos.append(td)

        if tiempos:
            return Decimal(sum(tiempos) / len(tiempos))
        
        return None

    def obtener_comandas_por_mesa(self, mesa_id: int) -> List[Comanda]:
        """Obtener comandas asociadas a una mesa"""
        comandas = self.db.query(Comanda).filter(
            Comanda.mesa_id == mesa_id
        ).order_by(Comanda.fecha_creacion.desc()).all()
        
        return comandas

    def obtener_detalles_comanda(self, comanda_id: int) -> Dict:
        """Obtener comanda con detalles de items"""
        comanda = self.obtener_comanda(comanda_id)
        if not comanda:
            return None

        # Obtener detalles de venta
        detalles = self.db.query(DetalleVenta).filter(
            DetalleVenta.venta_id == comanda.venta_id
        ).all()

        items = []
        for detalle in detalles:
            items.append({
                "id": detalle.id,
                "producto": detalle.producto_id,
                "cantidad": float(detalle.cantidad),
                "estado_cocina": detalle.estado_cocina,
                "nota": detalle.nota
            })

        return {
            "id": comanda.id,
            "venta_id": comanda.venta_id,
            "mesa_id": comanda.mesa_id,
            "estado": comanda.estado,
            "prioridad": comanda.prioridad,
            "fecha_creacion": comanda.fecha_creacion,
            "fecha_entrega": comanda.fecha_entrega,
            "notas": comanda.notas,
            "items": items
        }
