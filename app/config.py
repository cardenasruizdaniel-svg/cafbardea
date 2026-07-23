from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
from typing import Optional

class Settings(BaseSettings):
    database_url: str = "sqlite:///./cafbardla.db"
    secret_key: str = "MUST_CHANGE_IN_PRODUCTION"
    app_name: str = "CafBarDLA"
    auto_create_schema: bool = True
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/cafbardla.log"
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 3600
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()

if settings.secret_key == "MUST_CHANGE_IN_PRODUCTION":
    logger.warning("SECRET_KEY sigue con el valor por defecto; cámbiala antes de usar producción.")

if settings.database_url.startswith("sqlite"):
    logger.warning("DATABASE_URL está usando SQLite; para Render debe apuntar a PostgreSQL.")

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
