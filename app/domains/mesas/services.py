"""
Service Layer para Mesas - Gestión de floor plan y estados
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from datetime import datetime
from decimal import Decimal

from app.models import hora_colombia, Mesa, Zona, Venta, ReservaMesa
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
            
            forma_val = mesa_data.forma.value if hasattr(mesa_data.forma, 'value') else mesa_data.forma
            ancho = getattr(mesa_data, 'ancho', None) or (96 if forma_val == "rectangular" else 64)
            alto = getattr(mesa_data, 'alto', None) or (56 if forma_val == "rectangular" else 64)

            # Crear mesa
            mesa = Mesa(
                empresa_id=empresa_id,
                zona_id=mesa_data.zona_id,
                nombre=mesa_data.nombre,
                capacidad=mesa_data.capacidad,
                posicion_x=mesa_data.posicion_x,
                posicion_y=mesa_data.posicion_y,
                forma=forma_val,
                ancho=ancho,
                alto=alto,
                estado="libre"
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
            estadisticas["mesas_disponibles"] += len([m for m in mesas if m.estado == "libre"])
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
    
    def ocupar_mesa(self, mesa_id: int, venta_id: int,
                    mesero_id: int = None, comensales: int = None) -> Mesa:
        """Marcar mesa como ocupada e iniciar el servicio.

        Registra la hora de apertura, el mesero y los comensales: antes solo
        cambiaba el estado, por lo que no se podia saber cuanto llevaba
        ocupada ni quien la atendia.
        """
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")

        if mesa.estado not in ("libre", "reservada"):
            raise ValueError(f"Mesa {mesa.nombre} no esta disponible (estado: {mesa.estado})")

        if comensales is not None and comensales > mesa.capacidad:
            raise ValueError(
                f"Mesa {mesa.nombre} admite {mesa.capacidad} personas, se solicitaron {comensales}"
            )

        mesa.estado = "ocupada"
        mesa.fecha_apertura = hora_colombia()
        mesa.mesero_id = mesero_id
        mesa.comensales = comensales
        self.db.commit()

        self.logger.info("Mesa %s ocupada (venta %s)", mesa.nombre, venta_id)
        return mesa
    
    def liberar_mesa(self, mesa_id: int, forzar: bool = False) -> Mesa:
        """Liberar mesa y cerrar el servicio.

        No permite liberar una mesa con ventas abiertas encima salvo que se
        indique `forzar`: antes se liberaba sin comprobar nada, dejando ventas
        huerfanas sin mesa visible.
        """
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")

        if not forzar:
            abiertas = self.db.query(Venta).filter(
                Venta.mesa_id == mesa_id,
                Venta.estado.in_(["abierta", "suspendida"]),
            ).count()
            if abiertas:
                raise ValueError(
                    f"Mesa {mesa.nombre} tiene {abiertas} venta(s) abierta(s); "
                    "cierre la cuenta antes de liberarla"
                )

        mesa.estado = "libre"
        mesa.fecha_apertura = None
        mesa.mesero_id = None
        mesa.comensales = None
        self.db.commit()

        self.logger.info("Mesa %s liberada", mesa.nombre)
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
        
        disponibles = estado_dict.get("libre", 0)
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
                    Mesa.estado == "libre",
                    Mesa.capacidad >= capacidad_minima
                )
            ) \
            .order_by(Mesa.capacidad) \
            .all()

    # ========================================================================
    # DATOS OPERATIVOS DEL SERVICIO
    # ========================================================================

    def consumo_actual(self, mesa_id: int) -> Decimal:
        """Consumo acumulado de las ventas abiertas en la mesa."""
        total = self.db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.mesa_id == mesa_id,
            Venta.estado.in_(["abierta", "suspendida"]),
        ).scalar()
        return Decimal(str(total or 0))

    def detalle_mesa(self, mesa_id: int) -> dict:
        """Estado completo de la mesa para el plano de salon.

        Reune lo que antes no existia: tiempo ocupada, consumo acumulado,
        mesero y comensales.
        """
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")

        ventas_abiertas = self.db.query(Venta).filter(
            Venta.mesa_id == mesa_id,
            Venta.estado.in_(["abierta", "suspendida"]),
        ).all()

        mesero = None
        if mesa.mesero_id:
            from app.models import Usuario
            u = self.db.get(Usuario, mesa.mesero_id)
            mesero = u.usuario if u else None

        return {
            "id": mesa.id,
            "nombre": mesa.nombre,
            "estado": mesa.estado,
            "capacidad": mesa.capacidad,
            "comensales": mesa.comensales,
            "mesero": mesero,
            "minutos_ocupada": mesa.minutos_ocupada(),
            "consumo": self.consumo_actual(mesa_id),
            "ventas_abiertas": len(ventas_abiertas),
            "posicion_x": mesa.posicion_x,
            "posicion_y": mesa.posicion_y,
            "forma": mesa.forma,
            "zona_id": mesa.zona_id,
        }

    # ========================================================================
    # RESERVAS
    # ========================================================================

    def reservar(self, mesa_id: int, datos) -> ReservaMesa:
        """Registrar una reserva.

        El esquema `ReservarMesa` existia en la API pero ninguna ruta lo
        usaba: los datos del cliente se descartaban.
        """
        mesa = self.obtener_mesa(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} no encontrada")
        if mesa.estado == "ocupada":
            raise ValueError(f"Mesa {mesa.nombre} esta ocupada")
        if datos.personas > mesa.capacidad:
            raise ValueError(
                f"Mesa {mesa.nombre} admite {mesa.capacidad} personas, "
                f"se solicitaron {datos.personas}"
            )

        reserva = ReservaMesa(
            mesa_id=mesa_id,
            cliente_nombre=datos.cliente_nombre,
            telefono=getattr(datos, "telefono", None),
            personas=datos.personas,
            fecha_hora=getattr(datos, "fecha_hora", None) or hora_colombia(),
            notas=getattr(datos, "notas", None),
        )
        self.db.add(reserva)
        mesa.estado = "reservada"
        self.db.commit()
        self.logger.info("Mesa %s reservada para %s", mesa.nombre, datos.cliente_nombre)
        return reserva

    def cancelar_reserva(self, reserva_id: int) -> ReservaMesa:
        reserva = self.db.get(ReservaMesa, reserva_id)
        if not reserva:
            raise ValueError(f"Reserva {reserva_id} no encontrada")
        reserva.estado = "cancelada"
        mesa = self.obtener_mesa(reserva.mesa_id)
        if mesa and mesa.estado == "reservada":
            mesa.estado = "libre"
        self.db.commit()
        return reserva

    def reservas_activas(self, mesa_id: int = None) -> list:
        q = self.db.query(ReservaMesa).filter(ReservaMesa.estado == "pendiente")
        if mesa_id:
            q = q.filter(ReservaMesa.mesa_id == mesa_id)
        return q.order_by(ReservaMesa.fecha_hora).all()

    # ========================================================================
    # UNIR Y TRANSFERIR
    # ========================================================================

    def unir_mesas(self, mesa_principal_id: int, mesa_ids: list) -> Mesa:
        """Unir mesas para un mismo grupo.

        Las secundarias quedan vinculadas a la principal y pasan a 'ocupada'.
        """
        principal = self.obtener_mesa(mesa_principal_id)
        if not principal:
            raise ValueError(f"Mesa {mesa_principal_id} no encontrada")

        capacidad_total = principal.capacidad
        for mid in mesa_ids:
            if mid == mesa_principal_id:
                raise ValueError("No se puede unir una mesa consigo misma")
            m = self.obtener_mesa(mid)
            if not m:
                raise ValueError(f"Mesa {mid} no encontrada")
            if m.estado == "ocupada" and m.mesa_padre_id != mesa_principal_id:
                raise ValueError(f"Mesa {m.nombre} ya esta ocupada")
            m.mesa_padre_id = mesa_principal_id
            m.estado = "ocupada"
            capacidad_total += m.capacidad

        if principal.estado == "libre":
            principal.estado = "ocupada"
            principal.fecha_apertura = hora_colombia()

        self.db.commit()
        self.logger.info("Mesas %s unidas a %s (capacidad %s)",
                         mesa_ids, principal.nombre, capacidad_total)
        return principal

    def separar_mesas(self, mesa_principal_id: int) -> list:
        """Deshacer una union."""
        hijas = self.db.query(Mesa).filter(Mesa.mesa_padre_id == mesa_principal_id).all()
        for m in hijas:
            m.mesa_padre_id = None
            m.estado = "libre"
            m.fecha_apertura = None
        self.db.commit()
        return hijas

    def transferir_venta(self, venta_id: int, mesa_destino_id: int) -> Venta:
        """Mover una cuenta abierta a otra mesa."""
        venta = self.db.get(Venta, venta_id)
        if not venta:
            raise ValueError(f"Venta {venta_id} no encontrada")
        if venta.estado not in ("abierta", "suspendida"):
            raise ValueError(f"No se puede transferir una venta {venta.estado}")

        destino = self.obtener_mesa(mesa_destino_id)
        if not destino:
            raise ValueError(f"Mesa {mesa_destino_id} no encontrada")

        origen_id = venta.mesa_id
        venta.mesa_id = mesa_destino_id

        if destino.estado == "libre":
            destino.estado = "ocupada"
            destino.fecha_apertura = hora_colombia()

        # Liberar la mesa de origen si ya no le quedan cuentas
        if origen_id:
            restantes = self.db.query(Venta).filter(
                Venta.mesa_id == origen_id,
                Venta.estado.in_(["abierta", "suspendida"]),
                Venta.id != venta_id,
            ).count()
            if restantes == 0:
                origen = self.obtener_mesa(origen_id)
                if origen:
                    origen.estado = "libre"
                    origen.fecha_apertura = None
                    origen.mesero_id = None
                    origen.comensales = None

        self.db.commit()
        self.logger.info("Venta %s transferida a mesa %s", venta_id, destino.nombre)
        return venta
