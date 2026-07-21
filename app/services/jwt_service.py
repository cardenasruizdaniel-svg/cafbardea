"""
JWT Service para Autenticación Mobile
FASE 7: Mobile API Endpoints

Gestiona tokens JWT para la app mesero y otros clientes móviles.
Token format: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
"""
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from typing import Optional, Dict
import os
import logging

logger = logging.getLogger(__name__)


class JWTService:
    """Servicio de JWT para autenticación mobile"""
    
    # Configuración
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "tu-clave-secreta-fase7-cafbardla-2024")
    ALGORITHM = "HS256"
    TOKEN_EXPIRE_HOURS = 24
    
    @classmethod
    def create_token(
        cls,
        usuario_id: int,
        sucursal_id: int,
        dispositivo: str = "app_mesero",
        device_id: Optional[str] = None,
        additional_claims: Optional[Dict] = None
    ) -> str:
        """
        Crea un JWT token para dispositivo mobile
        
        Args:
            usuario_id: ID del usuario
            sucursal_id: ID de la sucursal
            dispositivo: Tipo de dispositivo (app_mesero, kds, cajero)
            device_id: ID único del dispositivo (UUID)
            additional_claims: Claims adicionales a incluir
        
        Returns:
            Token JWT encodificado
        """
        try:
            expire = datetime.now(timezone.utc) + timedelta(hours=cls.TOKEN_EXPIRE_HOURS)
            
            payload = {
                "sub": f"{usuario_id}:app_mesero",  # Subject format consistente
                "usuario_id": usuario_id,
                "sucursal_id": sucursal_id,
                "dispositivo": dispositivo,
                "device_id": device_id,
                "exp": expire,
                "iat": datetime.now(timezone.utc)
            }
            
            # Añadir claims adicionales si se proporcionan
            if additional_claims:
                payload.update(additional_claims)
            
            token = jwt.encode(
                payload,
                cls.SECRET_KEY,
                algorithm=cls.ALGORITHM
            )
            
            logger.info(f"✅ Token JWT creado para usuario {usuario_id} en sucursal {sucursal_id}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Error creando JWT token: {str(e)}")
            raise
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict]:
        """
        Verifica y decodifica un JWT token
        
        Args:
            token: Token JWT a verificar
        
        Returns:
            Payload decodificado o None si es inválido
        """
        try:
            payload = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
            logger.debug(f"✅ Token JWT verificado para usuario {payload.get('usuario_id')}")
            return payload
            
        except JWTError as e:
            logger.warning(f"⚠️ Token JWT inválido o expirado: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error verificando token JWT: {str(e)}")
            return None
    
    @classmethod
    def get_user_from_token(cls, token: str) -> Optional[Dict]:
        """
        Extrae información del usuario desde un token
        
        Returns:
            Dict con usuario_id, sucursal_id, dispositivo, device_id
        """
        payload = cls.verify_token(token)
        if not payload:
            return None
        
        return {
            "usuario_id": payload.get("usuario_id"),
            "sucursal_id": payload.get("sucursal_id"),
            "dispositivo": payload.get("dispositivo"),
            "device_id": payload.get("device_id"),
            "exp": payload.get("exp")
        }
    
    @classmethod
    def is_token_expired(cls, token: str) -> bool:
        """Verifica si un token está expirado"""
        payload = cls.verify_token(token)
        if not payload:
            return True
        
        exp = payload.get("exp")
        if not exp:
            return True
        
        return datetime.utcfromtimestamp(exp) < datetime.utcnow()
    
    @classmethod
    def refresh_token(cls, token: str, device_id: Optional[str] = None) -> Optional[str]:
        """
        Refresca un token JWT existente
        
        Args:
            token: Token actual
            device_id: Nuevo device_id si cambió
        
        Returns:
            Nuevo token o None si no se puede refrescar
        """
        payload = cls.verify_token(token)
        if not payload:
            logger.warning("❌ No se puede refrescar token inválido")
            return None
        
        # Crear nuevo token con la misma información
        new_device_id = device_id or payload.get("device_id")
        
        return cls.create_token(
            usuario_id=payload.get("usuario_id"),
            sucursal_id=payload.get("sucursal_id"),
            dispositivo=payload.get("dispositivo", "app_mesero"),
            device_id=new_device_id
        )


class TokenBlacklist:
    """
    Mantiene lista negra de tokens revocados
    En producción usar Redis para persistencia
    """
    
    _blacklist = set()
    
    @classmethod
    def add(cls, token: str):
        """Añade token a lista negra"""
        cls._blacklist.add(token)
        logger.info(f"🚫 Token añadido a blacklist")
    
    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """Verifica si token está en blacklist"""
        return token in cls._blacklist
    
    @classmethod
    def clear(cls):
        """Limpia lista negra (para testing)"""
        cls._blacklist.clear()
    
    @classmethod
    def size(cls) -> int:
        """Retorna tamaño de blacklist"""
        return len(cls._blacklist)


# Inicialización
logger.info("🔐 JWT Service cargado - FASE 7 Mobile Auth")
