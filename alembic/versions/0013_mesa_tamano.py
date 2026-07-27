"""Paso 24: tamano configurable de mesas (editor visual).

Agrega ancho y alto a las mesas para el editor de plano profesional.
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_mesa_tamano"
down_revision = "0012_normalizar_estado_venta"
branch_labels = None
depends_on = None


def _cols(tabla):
    insp = sa.inspect(op.get_bind())
    if tabla not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(tabla)}


def upgrade() -> None:
    cols = _cols("mesas")
    if cols:
        if "ancho" not in cols:
            op.add_column("mesas", sa.Column("ancho", sa.Integer(),
                                             server_default="64"))
        if "alto" not in cols:
            op.add_column("mesas", sa.Column("alto", sa.Integer(),
                                             server_default="64"))


def downgrade() -> None:
    for col in ("ancho", "alto"):
        if col in _cols("mesas"):
            op.drop_column("mesas", col)
