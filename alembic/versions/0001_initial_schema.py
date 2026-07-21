"""Esquema inicial de CafeNexus.

Esta migración de arranque crea las tablas definidas por SQLAlchemy. Las siguientes
migraciones deben generarse con `alembic revision --autogenerate -m "descripcion"`.
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
