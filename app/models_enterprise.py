"""
Modelos Enterprise para sincronización en tiempo real y multi-tenancy avanzado
FASE 5: Infrastructure for Real-time Synchronization
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, JSON, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
import uuid

# ============================================================================
# TABLA ASOCIATIVA PARA M2M: Rol <-> Permiso
# ============================================================================
rol_permiso_association = Table(
    'rol_permisos',
    Base.metadata,
    Column('rol_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permiso_id', Integer, ForeignKey('permisos.id'), primary_key=True)
)

# ============================================================================
# SUCURSAL (MULTI-TENANCY MEJORADO)
# ============================================================================
class Sucursal(Base):
    """
    Representa una sucursal/locación de un restaurante.
    Permite que múltiples restaurantes funcionen en la misma plataforma.
    
    Ejemplo:
    - Empresa: "Mi Café Premium"
      - Sucursal 1: Centro (3 meseros, 10 mesas)
      - Sucursal 2: Mall (5 meseros, 20 mesas)
      - Sucursal 3: Aeropuerto (2 meseros, 5 mesas)
    """
    __tablename__ = "sucursales"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)  # SUC001, SUC002
    direccion: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pais: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitud: Mapped[float] = mapped_column(nullable=True)
    longitud: Mapped[float] = mapped_column(nullable=True)
    
    # Configuración
    zona_horaria: Mapped[str] = mapped_column(String(50), default="America/Bogota")
    idioma: Mapped[str] = mapped_column(String(10), default="es")
    moneda: Mapped[str] = mapped_column(String(5), default="COP")
    
    # Estados y metadata
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Configuración KDS/Impresoras
    config_kds: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {estaciones: [...], formato_impresora: ...}
    
    # Audit
    creado_por: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    conexiones_activas: Mapped[list["ConexionWebSocket"]] = relationship(back_populates="sucursal")


# ============================================================================
# ROLES - Control de Acceso Basado en Roles (RBAC)
# ============================================================================
class Rol(Base):
    """
    Define roles predefinidos del sistema.
    Cada rol tiene permisos específicos.
    
    Roles incluidos por defecto:
    - Administrador: Control total
    - Gerente: Operaciones, reportes, personal
    - Cajero: Caja, cobros, cierre
    - Mesero: Toma de pedidos, cobro en mesa
    - Cocinero: Visualización de comandas
    - Bartender: Comandas de bar
    - Chef: Comandas de cocina
    """
    __tablename__ = "roles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255))
    nivel_acceso: Mapped[int] = mapped_column(Integer, default=0)  # 0=mínimo, 100=máximo
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    es_predefinido: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relaciones
    permisos: Mapped[list["Permiso"]] = relationship(
        secondary=rol_permiso_association,
        back_populates="roles"
    )
    usuarios: Mapped[list["UsuarioRol"]] = relationship(back_populates="rol")


# ============================================================================
# PERMISOS - Control Granular
# ============================================================================
class Permiso(Base):
    """
    Permisos granulares del sistema.
    Se asignan a roles y se evalúan en cada acción.
    
    Ejemplos:
    - ventas.crear
    - ventas.editar
    - ventas.eliminar
    - caja.abrir
    - caja.cerrar
    - reportes.ver
    - usuarios.gestionar
    """
    __tablename__ = "permisos"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(80), unique=True)  # ej: "ventas.crear"
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[Optional[str]] = mapped_column(String(255))
    categoria: Mapped[str] = mapped_column(String(50))  # ventas, caja, usuarios, reportes
    
    # Relaciones
    roles: Mapped[list["Rol"]] = relationship(
        secondary=rol_permiso_association,
        back_populates="permisos"
    )


# ============================================================================
# USUARIO-ROL (Soporte para múltiples roles por usuario)
# ============================================================================
class UsuarioRol(Base):
    """
    Relación M2M entre Usuarios y Roles.
    Permite que un usuario tenga múltiples roles en diferentes contextos.
    
    Ejemplo:
    - Usuario: Carlos
      - Rol: Mesero en Sucursal 1
      - Rol: Cajero en Sucursal 2
    """
    __tablename__ = "usuario_roles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    sucursal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sucursales.id"))
    
    # Validez temporal
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_expiracion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    usuario: Mapped["Usuario"] = relationship()
    rol: Mapped[Rol] = relationship(back_populates="usuarios")


# ============================================================================
# CONEXIÓN WEBSOCKET - Rastreo de conexiones activas
# ============================================================================
class ConexionWebSocket(Base):
    """
    Rastrea conexiones WebSocket activas en tiempo real.
    Permite saber qué usuarios están conectados y en qué dispositivo.
    
    Uso:
    - Sincronización de cambios en tiempo real
    - Notificaciones push
    - Broadcast de eventos
    - Auditoría de conexiones
    """
    __tablename__ = "conexiones_websocket"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Usuario y ubicación
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"), nullable=False)
    
    # Información del cliente
    dispositivo: Mapped[str] = mapped_column(String(50))  # web, app_mesero, kds, cajero
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    direccion_ip: Mapped[str] = mapped_column(String(45))  # IPv4 o IPv6
    
    # Estados
    conectado: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_conexion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_ultima_actividad: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_desconexion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    sucursal: Mapped[Sucursal] = relationship(back_populates="conexiones_activas")


# ============================================================================
# EVENTO DE SINCRONIZACIÓN - Auditoría de cambios
# ============================================================================
class EventoSincronizacion(Base):
    """
    Registra cada cambio en el sistema para sincronización.
    Permite que otros clientes WebSocket se enteren de cambios.
    
    Ejemplo:
    - Usuario: Mesero (Juan)
    - Evento: venta.creada
    - Datos: {venta_id: 123, mesa_id: 5, total: 45000}
    - Destinatarios: [cajero, gerente, kds]
    """
    __tablename__ = "eventos_sincronizacion"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Información del evento
    tipo_evento: Mapped[str] = mapped_column(String(50))  # venta.creada, mesa.cambio_estado, etc
    entidad: Mapped[str] = mapped_column(String(50))  # venta, mesa, comanda
    entidad_id: Mapped[int] = mapped_column(Integer)
    accion: Mapped[str] = mapped_column(String(20))  # crear, actualizar, eliminar
    
    # Datos
    datos_anteriores: Mapped[Optional[dict]] = mapped_column(JSON)
    datos_nuevos: Mapped[dict] = mapped_column(JSON)
    
    # Contexto
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"))
    
    # Sincronización
    fecha_evento: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    sincronizado: Mapped[bool] = mapped_column(Boolean, default=False)
    dispositivos_notificados: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
