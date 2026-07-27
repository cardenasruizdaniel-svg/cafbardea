"""Paso 25: app de cliente (pedidos de autoservicio y mesa).

Crea las tablas de pedidos de cliente y sus lineas. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0014_pedidos_cliente"
down_revision = "0013_mesa_tamano"
branch_labels = None
depends_on = None


def _tablas():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tablas = _tablas()
    if "pedidos_cliente" not in tablas:
        op.create_table(
            "pedidos_cliente",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), server_default="1"),
            sa.Column("tipo", sa.String(15), server_default="autoservicio"),
            sa.Column("nombre_cliente", sa.String(80), server_default=""),
            sa.Column("mesa_id", sa.Integer()),
            sa.Column("estado", sa.String(15), server_default="pendiente"),
            sa.Column("total", sa.Numeric(14, 2), server_default="0"),
            sa.Column("observacion", sa.Text()),
            sa.Column("creado", sa.DateTime()),
            sa.Column("atendido", sa.DateTime()),
            sa.Column("venta_id", sa.Integer()),
            sa.Column("motivo_rechazo", sa.String(200)),
        )
    if "pedidos_cliente_lineas" not in tablas:
        op.create_table(
            "pedidos_cliente_lineas",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pedido_id", sa.Integer(), nullable=False),
            sa.Column("producto_id", sa.Integer(), nullable=False),
            sa.Column("cantidad", sa.Numeric(10, 2), server_default="1"),
            sa.Column("precio_unitario", sa.Numeric(14, 2), server_default="0"),
            sa.Column("nota", sa.String(200)),
        )


def downgrade() -> None:
    for t in ("pedidos_cliente_lineas", "pedidos_cliente"):
        if t in _tablas():
            op.drop_table(t)
