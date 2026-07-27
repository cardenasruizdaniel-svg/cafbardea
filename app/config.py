"""Configuracion central de CafBarDLA.

Orden critico: el logging se configura ANTES de cualquier uso de `logger`.
El bug original invocaba logger.warning() en la linea 23 mientras que
logger se definia en la linea 32 -> NameError en tiempo de import,
lo que impedia el arranque de toda la aplicacion.
"""
import logging
import os
import secrets
import sys
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# 1. LOGGING PRIMERO. Nada por encima de este bloque puede usar `logger`.
# ---------------------------------------------------------------------------
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("cafbardla")


# ---------------------------------------------------------------------------
# 2. SETTINGS
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    # Entorno: "development" | "production"
    environment: str = "development"

    database_url: str = "sqlite:///./cafbardla.db"

    # Sin valor por defecto utilizable. En produccion es obligatorio via .env
    secret_key: str = ""
    jwt_secret_key: str = ""

    app_name: str = "CafBarDLA"
    auto_create_schema: bool = True

    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"

    # Origenes CORS validos, separados por coma. Deben incluir el esquema.
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"

    log_level: str = "INFO"
    log_file: Optional[str] = "logs/cafbardla.log"

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 3600
    rate_limit_login_requests: int = 10
    rate_limit_login_period: int = 300

    csrf_enabled: bool = True
    hsts_enabled: bool = False  # activar solo bajo HTTPS (produccion tras TLS)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()


# ---------------------------------------------------------------------------
# 3. VALIDACION DE ARRANQUE
#    En produccion: fallar de inmediato. En desarrollo: avisar y continuar.
# ---------------------------------------------------------------------------
def _fail(mensaje: str) -> None:
    """Aborta el arranque en produccion; advierte en desarrollo."""
    if settings.is_production:
        logger.critical("ARRANQUE ABORTADO: %s", mensaje)
        raise RuntimeError(mensaje)
    logger.warning("%s (tolerado en entorno de desarrollo)", mensaje)


if not settings.secret_key:
    _fail("SECRET_KEY no esta definida. Configurela en el archivo .env")
    settings.secret_key = secrets.token_urlsafe(48)
    logger.warning(
        "SECRET_KEY generada de forma efimera. Las sesiones se invalidaran "
        "en cada reinicio. Solo valido para desarrollo local."
    )

if not settings.jwt_secret_key:
    _fail("JWT_SECRET_KEY no esta definida. Configurela en el archivo .env")
    settings.jwt_secret_key = secrets.token_urlsafe(48)
    logger.warning("JWT_SECRET_KEY generada de forma efimera (solo desarrollo).")

if settings.database_url.startswith("sqlite"):
    if settings.is_production:
        _fail("SQLite no es admisible en produccion. Configure PostgreSQL en DATABASE_URL")
    else:
        logger.info("Usando SQLite para desarrollo local.")

if settings.is_production and not settings.session_cookie_secure:
    _fail("SESSION_COOKIE_SECURE debe ser true en produccion (cookies solo por HTTPS)")

logger.info(
    "Configuracion cargada | entorno=%s | motor_bd=%s",
    settings.environment,
    settings.database_url.split(":", 1)[0],
)
