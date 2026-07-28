"""Paso 31: impresion incremental de comandas del mesero.

Agrega a detalle_ventas las columnas para rastrear que lineas ya fueron
comandadas (enviadas a impresion), de modo que al comandar de nuevo solo se
impriman los productos nuevos. Idempotente y compatible con SQLite y PostgreSQL.
"""
import sqlalchemy as sa
from alembic import op

revision = "0016_detalle_comandado"
down_revision = "0015_sincronizar_columnas_base"
branch_labels = None
depends_on = None


def _cols(tabla):
    insp = sa.inspect(op.get_bind())
    if tabla not in insp.get_table_names():
        return None
    return {c["name"] for c in insp.get_columns(tabla)}


def upgrade() -> None:
    cols = _cols("detalle_ventas")
    if cols is None:
        return
    if "comandado" not in cols:
        op.add_column("detalle_ventas", sa.Column(
            "comandado", sa.Boolean(), server_default=sa.false(),
            nullable=False))
    if "comandado_en" not in cols:
        op.add_column("detalle_ventas", sa.Column(
            "comandado_en", sa.DateTime(), nullable=True))


def downgrade() -> None:
    cols = _cols("detalle_ventas")
    if cols is None:
        return
    with op.batch_alter_table("detalle_ventas") as batch:
        if "comandado_en" in cols:
            batch.drop_column("comandado_en")
        if "comandado" in cols:
            batch.drop_column("comandado")
