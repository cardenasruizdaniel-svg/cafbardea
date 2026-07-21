"""
Inicializador de Base de Datos Enterprise
Crea las tablas y datos iniciales para FASE 5
"""
import logging
from sqlalchemy.orm import Session
from .database import engine, Base
from .models_enterprise import (
    Sucursal, Rol, Permiso, UsuarioRol, ConexionWebSocket, EventoSincronizacion
)
from .services.rbac_service import RolService

logger = logging.getLogger(__name__)


def crear_tablas_enterprise() -> None:
    """Crea todas las tablas de los nuevos modelos Enterprise"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tablas Enterprise creadas exitosamente")
    except Exception as e:
        logger.error(f"Error creando tablas Enterprise: {e}")


def inicializar_datos_enterprise(db: Session) -> None:
    """
    Inicializa los datos de configuración Enterprise:
    - Roles predefinidos
    - Permisos del sistema
    - Sucursal por defecto
    """
    try:
        # Crear roles y permisos
        rol_service = RolService(db)
        rol_service.crear_roles_predefinidos()
        
        logger.info("✓ Datos Enterprise inicializados")
        
    except Exception as e:
        logger.error(f"Error inicializando datos Enterprise: {e}")


def setup_enterprise_database() -> None:
    """Ejecuta setup completo de base de datos Enterprise"""
    logger.info("🚀 Inicializando infraestructura Enterprise...")
    
    # 1. Crear tablas
    crear_tablas_enterprise()
    
    # 2. Inicializar datos
    from .database import SessionLocal
    db = SessionLocal()
    try:
        inicializar_datos_enterprise(db)
    finally:
        db.close()
    
    logger.info("✅ Infraestructura Enterprise lista")
