"""Paso 18: auditoria.

Crea la tabla de registros de auditoria (append-only): quien hizo que, cuando,
desde donde, con el estado antes y despues. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_auditoria"
down_revision = "0008_rbac"
branch_labels = None
depends_on = None


def _tablas():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "registros_auditoria" not in _tablas():
        op.create_table(
            "registros_auditoria",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), server_default="1"),
            sa.Column("fecha_hora", sa.DateTime()),
            sa.Column("usuario_id", sa.Integer()),
            sa.Column("usuario_nombre", sa.String(80)),
            sa.Column("rol", sa.String(40)),
            sa.Column("ip", sa.String(45)),
            sa.Column("accion", sa.String(20), nullable=False),
            sa.Column("modulo", sa.String(40)),
            sa.Column("entidad", sa.String(40)),
            sa.Column("entidad_id", sa.String(40)),
            sa.Column("descripcion", sa.String(300)),
            sa.Column("valor_anterior", sa.Text()),
            sa.Column("valor_nuevo", sa.Text()),
            sa.Column("resultado", sa.String(10), server_default="exito"),
        )
        op.create_index("ix_auditoria_fecha", "registros_auditoria",
                        ["fecha_hora"])
        op.create_index("ix_auditoria_accion", "registros_auditoria",
                        ["accion"])


def downgrade() -> None:
    if "registros_auditoria" in _tablas():
        op.drop_table("registros_auditoria")
