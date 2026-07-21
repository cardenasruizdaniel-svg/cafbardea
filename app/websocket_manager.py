"""
WebSocket Manager para sincronización en tiempo real
FASE 5: Real-time Synchronization Engine
"""
from typing import Dict, Set, Callable, Any
from datetime import datetime, timezone
import logging
import json
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class MensajeWS:
    """Estructura estándar de mensajes WebSocket"""
    tipo: str  # evento, comando, respuesta, notificacion
    evento: str  # venta.creada, mesa.actualizada, etc
    datos: dict
    timestamp: datetime = None
    remitente_id: int = None
    destinatario_id: int = None
    sucursal_id: int = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_json(self) -> str:
        """Convierte a JSON para envío"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data, default=str)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Crea desde diccionario"""
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ConnectionManager:
    """
    Gestiona conexiones WebSocket activas.
    
    Características:
    - Rastreo de usuarios conectados
    - Broadcast de mensajes
    - Envío a dispositivos específicos
    - Sincronización por sucursal
    """
    
    def __init__(self):
        # Dict[sucursal_id][usuario_id] = {socket_id: websocket}
        self.active_connections: Dict[int, Dict[int, Dict[str, Any]]] = {}
        self.user_devices: Dict[int, Dict[str, str]] = {}  # usuario_id -> {socket_id: dispositivo}
        self.locks: Dict[int] = {}  # Locks por sucursal para thread-safety
    
    async def connect(self, sucursal_id: int, usuario_id: int, websocket, socket_id: str, dispositivo: str):
        """Registra una nueva conexión WebSocket"""
        if sucursal_id not in self.locks:
            self.locks[sucursal_id] = asyncio.Lock()
        
        async with self.locks[sucursal_id]:
            if sucursal_id not in self.active_connections:
                self.active_connections[sucursal_id] = {}
            
            if usuario_id not in self.active_connections[sucursal_id]:
                self.active_connections[sucursal_id][usuario_id] = {}
            
            # Almacenar conexión
            self.active_connections[sucursal_id][usuario_id][socket_id] = {
                'websocket': websocket,
                'dispositivo': dispositivo,
                'conectado_en': datetime.now(timezone.utc)
            }
            
            # Rastrear dispositivo
            if usuario_id not in self.user_devices:
                self.user_devices[usuario_id] = {}
            self.user_devices[usuario_id][socket_id] = dispositivo
            
            logger.info(f"✓ Conexión establecida: Usuario {usuario_id}, Sucursal {sucursal_id}, Dispositivo {dispositivo}")
    
    async def disconnect(self, sucursal_id: int, usuario_id: int, socket_id: str):
        """Desconecta un usuario"""
        if sucursal_id not in self.locks:
            self.locks[sucursal_id] = asyncio.Lock()
        
        async with self.locks[sucursal_id]:
            try:
                if (sucursal_id in self.active_connections and 
                    usuario_id in self.active_connections[sucursal_id] and 
                    socket_id in self.active_connections[sucursal_id][usuario_id]):
                    
                    del self.active_connections[sucursal_id][usuario_id][socket_id]
                    
                    # Limpiar si no hay más conexiones
                    if not self.active_connections[sucursal_id][usuario_id]:
                        del self.active_connections[sucursal_id][usuario_id]
                    if not self.active_connections[sucursal_id]:
                        del self.active_connections[sucursal_id]
                
                if usuario_id in self.user_devices and socket_id in self.user_devices[usuario_id]:
                    del self.user_devices[usuario_id][socket_id]
                
                logger.info(f"✓ Desconexión: Usuario {usuario_id}, Sucursal {sucursal_id}")
            except Exception as e:
                logger.error(f"Error desconectando: {e}")
    
    async def broadcast_sucursal(self, sucursal_id: int, mensaje: MensajeWS):
        """Envía un mensaje a todos los usuarios conectados en una sucursal"""
        if sucursal_id not in self.active_connections:
            return
        
        desconectados = []
        
        for usuario_id, sockets in self.active_connections[sucursal_id].items():
            for socket_id, conexion in sockets.items():
                try:
                    await conexion['websocket'].send_text(mensaje.to_json())
                except Exception as e:
                    logger.error(f"Error enviando broadcast: {e}")
                    desconectados.append((socket_id, usuario_id))
        
        # Limpiar conexiones rotas
        for socket_id, usuario_id in desconectados:
            await self.disconnect(sucursal_id, usuario_id, socket_id)
    
    async def broadcast_dispositivo(self, sucursal_id: int, dispositivo: str, mensaje: MensajeWS):
        """Envía un mensaje a un tipo de dispositivo específico"""
        if sucursal_id not in self.active_connections:
            return
        
        desconectados = []
        
        for usuario_id, sockets in self.active_connections[sucursal_id].items():
            for socket_id, conexion in sockets.items():
                if conexion['dispositivo'] == dispositivo:
                    try:
                        await conexion['websocket'].send_text(mensaje.to_json())
                    except Exception as e:
                        logger.error(f"Error enviando a {dispositivo}: {e}")
                        desconectados.append((socket_id, usuario_id))
        
        for socket_id, usuario_id in desconectados:
            await self.disconnect(sucursal_id, usuario_id, socket_id)
    
    async def send_to_user(self, sucursal_id: int, usuario_id: int, mensaje: MensajeWS):
        """Envía un mensaje a un usuario específico en todas sus conexiones"""
        if (sucursal_id not in self.active_connections or 
            usuario_id not in self.active_connections[sucursal_id]):
            logger.warning(f"Usuario {usuario_id} no conectado en sucursal {sucursal_id}")
            return
        
        desconectados = []
        sockets = self.active_connections[sucursal_id][usuario_id]
        
        for socket_id, conexion in sockets.items():
            try:
                await conexion['websocket'].send_text(mensaje.to_json())
            except Exception as e:
                logger.error(f"Error enviando a usuario {usuario_id}: {e}")
                desconectados.append(socket_id)
        
        for socket_id in desconectados:
            await self.disconnect(sucursal_id, usuario_id, socket_id)
    
    async def send_to_dispositivos(self, sucursal_id: int, dispositivos: list, mensaje: MensajeWS):
        """Envía un mensaje a dispositivos específicos"""
        if sucursal_id not in self.active_connections:
            return
        
        for dispositivo in dispositivos:
            await self.broadcast_dispositivo(sucursal_id, dispositivo, mensaje)
    
    def get_usuarios_conectados(self, sucursal_id: int) -> Dict[int, str]:
        """Retorna {usuario_id: dispositivo} conectados en una sucursal"""
        if sucursal_id not in self.active_connections:
            return {}
        
        usuarios = {}
        for usuario_id, sockets in self.active_connections[sucursal_id].items():
            if sockets:
                # Tomar el primer dispositivo como referencia
                dispositivo = list(sockets.values())[0]['dispositivo']
                usuarios[usuario_id] = dispositivo
        
        return usuarios
    
    def get_conexiones_stats(self) -> dict:
        """Retorna estadísticas de conexiones"""
        total_conexiones = sum(
            len(sockets)
            for sucursal in self.active_connections.values()
            for sockets in sucursal.values()
        )
        
        total_usuarios = sum(
            len(usuarios)
            for usuarios in self.active_connections.values()
        )
        
        return {
            'total_conexiones': total_conexiones,
            'total_usuarios_conectados': total_usuarios,
            'sucursales_activas': len(self.active_connections)
        }


class EventBroadcaster:
    """
    Gestor de eventos para brodacast de cambios.
    
    Eventos estándar:
    - venta.creada, venta.actualizada, venta.pagada
    - comanda.creada, comanda.actualizada, comanda.lista
    - mesa.actualizada, mesa.cambio_estado
    - usuario.conectado, usuario.desconectado
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self.cm = connection_manager
        self.event_handlers: Dict[str, list] = {}
    
    def on(self, evento: str) -> Callable:
        """Decorador para registrar handlers de eventos"""
        def registrar_handler(handler: Callable):
            if evento not in self.event_handlers:
                self.event_handlers[evento] = []
            self.event_handlers[evento].append(handler)
            return handler
        return registrar_handler
    
    async def emit(self, evento: str, datos: dict, contexto: dict):
        """Emite un evento y ejecuta handlers registrados"""
        logger.info(f"📢 Evento: {evento} | Datos: {datos}")
        
        # Ejecutar handlers registrados
        if evento in self.event_handlers:
            for handler in self.event_handlers[evento]:
                try:
                    await handler(evento, datos, contexto)
                except Exception as e:
                    logger.error(f"Error en handler de {evento}: {e}")
    
    async def broadcast_evento(self, sucursal_id: int, evento: str, datos: dict, 
                               dispositivos_destino: list = None, usuario_remitente: int = None):
        """Brodacsta un evento a través de WebSocket"""
        mensaje = MensajeWS(
            tipo='evento',
            evento=evento,
            datos=datos,
            sucursal_id=sucursal_id,
            remitente_id=usuario_remitente
        )
        
        if dispositivos_destino:
            await self.cm.send_to_dispositivos(sucursal_id, dispositivos_destino, mensaje)
        else:
            await self.cm.broadcast_sucursal(sucursal_id, mensaje)


# Instancia global
connection_manager = ConnectionManager()
event_broadcaster = EventBroadcaster(connection_manager)
