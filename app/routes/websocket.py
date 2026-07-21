"""
Rutas WebSocket para sincronización en tiempo real
FASE 5: Real-time Communication Endpoints
"""
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..websocket_manager import (
    connection_manager, event_broadcaster, MensajeWS
)
from ..models import Usuario
from ..models_enterprise import ConexionWebSocket, EventoSincronizacion

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

# ============================================================================
# ENDPOINT WEBSOCKET PRINCIPAL
# ============================================================================
@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """
    WebSocket principal para sincronización en tiempo real.
    
    Formato del token: {usuario_id}:{sucursal_id}:{dispositivo}
    Ejemplo: 1:1:web
    
    Dispositivos soportados:
    - web: POS Web
    - app_mesero: App para Meseros
    - kds: Kitchen Display System
    - cajero: Terminal de caja
    """
    
    socket_id = str(uuid.uuid4())
    usuario_id = None
    sucursal_id = None
    dispositivo = None
    
    try:
        # Validar y parsear token
        try:
            partes = token.split(':')
            if len(partes) != 3:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                logger.warning(f"Token inválido: {token}")
                return
            
            usuario_id = int(partes[0])
            sucursal_id = int(partes[1])
            dispositivo = partes[2]
            
            # Verificar que el usuario existe
            usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))
            if not usuario:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                logger.warning(f"Usuario {usuario_id} no encontrado")
                return
            
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning(f"Token mal formado: {token}")
            return
        
        # Aceptar conexión
        await websocket.accept()
        logger.info(f"✓ WebSocket conectado: Usuario {usuario_id}, Sucursal {sucursal_id}, Dispositivo {dispositivo}")
        
        # Registrar conexión
        await connection_manager.connect(sucursal_id, usuario_id, websocket, socket_id, dispositivo)
        
        # Registrar en BD
        conexion_ws = ConexionWebSocket(
            uuid=socket_id,
            usuario_id=usuario_id,
            sucursal_id=sucursal_id,
            dispositivo=dispositivo,
            user_agent=websocket.headers.get("user-agent", "unknown"),
            direccion_ip=websocket.client.host if websocket.client else "unknown"
        )
        db.add(conexion_ws)
        db.commit()
        
        # Notificar a otros usuarios
        await event_broadcaster.broadcast_evento(
            sucursal_id=sucursal_id,
            evento='usuario.conectado',
            datos={'usuario_id': usuario_id, 'dispositivo': dispositivo},
            usuario_remitente=usuario_id
        )
        
        # Escuchar mensajes
        while True:
            data = await websocket.receive_text()
            
            try:
                mensaje = MensajeWS.from_dict(eval(data))  # JSON parse
                
                logger.debug(f"Mensaje recibido: {mensaje.evento}")
                
                # Procesar según tipo de evento
                await procesar_evento_ws(
                    evento=mensaje.evento,
                    datos=mensaje.datos,
                    usuario_id=usuario_id,
                    sucursal_id=sucursal_id,
                    dispositivo=dispositivo,
                    db=db
                )
                
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}")
    
    except WebSocketDisconnect:
        logger.info(f"✓ WebSocket desconectado: Usuario {usuario_id}")
        
        if usuario_id and sucursal_id:
            # Desconectar
            await connection_manager.disconnect(sucursal_id, usuario_id, socket_id)
            
            # Actualizar en BD
            conexion = db.query(ConexionWebSocket).filter(
                ConexionWebSocket.uuid == socket_id
            ).first()
            if conexion:
                conexion.conectado = False
                conexion.fecha_desconexion = datetime.utcnow()
                db.commit()
            
            # Notificar a otros
            await event_broadcaster.broadcast_evento(
                sucursal_id=sucursal_id,
                evento='usuario.desconectado',
                datos={'usuario_id': usuario_id},
                usuario_remitente=usuario_id
            )
    
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        await websocket.close(code=status.WS_1011_SERVER_ERROR)


# ============================================================================
# PROCESADOR DE EVENTOS
# ============================================================================
async def procesar_evento_ws(evento: str, datos: dict, usuario_id: int, 
                             sucursal_id: int, dispositivo: str, db: Session) -> None:
    """
    Procesa eventos recibidos por WebSocket.
    
    Eventos soportados:
    - venta.actualizar
    - mesa.cambio_estado
    - comanda.estado
    - etc.
    """
    
    try:
        # Registrar evento
        evento_sync = EventoSincronizacion(
            uuid=str(uuid.uuid4()),
            tipo_evento=evento,
            entidad=evento.split('.')[0],
            entidad_id=datos.get('id', 0),
            accion=evento.split('.')[1] if '.' in evento else 'actualizar',
            datos_nuevos=datos,
            usuario_id=usuario_id,
            sucursal_id=sucursal_id
        )
        db.add(evento_sync)
        db.commit()
        
        # Brodacast según tipo de dispositivo
        if evento.startswith('mesa.'):
            # Notificar a: web, app_mesero, kds
            await event_broadcaster.broadcast_evento(
                sucursal_id=sucursal_id,
                evento=evento,
                datos=datos,
                dispositivos_destino=['web', 'app_mesero', 'kds'],
                usuario_remitente=usuario_id
            )
        
        elif evento.startswith('comanda.'):
            # Notificar a: app_mesero, kds, web
            await event_broadcaster.broadcast_evento(
                sucursal_id=sucursal_id,
                evento=evento,
                datos=datos,
                dispositivos_destino=['app_mesero', 'kds', 'web'],
                usuario_remitente=usuario_id
            )
        
        elif evento.startswith('caja.'):
            # Notificar solo a cajero y gerente
            await event_broadcaster.broadcast_evento(
                sucursal_id=sucursal_id,
                evento=evento,
                datos=datos,
                dispositivos_destino=['web'],  # Solo web para caja
                usuario_remitente=usuario_id
            )
        
        else:
            # Broadcast general
            await event_broadcaster.broadcast_evento(
                sucursal_id=sucursal_id,
                evento=evento,
                datos=datos,
                usuario_remitente=usuario_id
            )
        
        logger.info(f"✓ Evento procesado: {evento} (Usuario: {usuario_id})")
    
    except Exception as e:
        logger.error(f"Error procesando evento {evento}: {e}")


# ============================================================================
# ENDPOINTS REST PARA OBTENER ESTADO
# ============================================================================
@router.get("/api/v1/websocket/status")
async def websocket_status(db: Session = Depends(get_db)):
    """Obtiene estado de conexiones WebSocket activas"""
    stats = connection_manager.get_conexiones_stats()
    return {
        'estado': 'activo',
        'timestamp': datetime.utcnow(),
        **stats
    }


@router.get("/api/v1/websocket/usuarios-conectados/{sucursal_id}")
async def usuarios_conectados(sucursal_id: int, db: Session = Depends(get_db)):
    """Obtiene lista de usuarios conectados en una sucursal"""
    usuarios = connection_manager.get_usuarios_conectados(sucursal_id)
    return {
        'sucursal_id': sucursal_id,
        'usuarios_conectados': usuarios,
        'total': len(usuarios)
    }
