from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.config import settings
from app.database import Base
# Importar TODOS los modulos de modelos para que Base.metadata los registre.
# Antes solo se importaba `models`, de modo que Alembic no veia las 7 tablas
# de models_enterprise (sucursales, roles, permisos, usuario_roles,
# conexiones_websocket, eventos_sincronizacion, rol_permisos) y una
# autogeneracion las habria marcado para BORRAR.
from app import models  # noqa: F401
from app import models_enterprise  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
