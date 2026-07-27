"""Paso 10: dominio de Produccion.

Amplia recetas, ordenes de produccion y anade el registro de consumos.
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_produccion"
down_revision = "0003_compras_aprovisionamiento"
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _hay_tabla(n):
    return n in _insp().get_table_names()


def _hay_col(t, c):
    return _hay_tabla(t) and c in {x["name"] for x in _insp().get_columns(t)}


def _add(t, col):
    if _hay_tabla(t) and not _hay_col(t, col.name):
        op.add_column(t, col)


def _drop(t, c):
    if _hay_col(t, c):
        with op.batch_alter_table(t) as b:
            b.drop_column(c)


def upgrade() -> None:
    _add("recetas", sa.Column("activa", sa.Boolean(), server_default=sa.true()))
    _add("receta_detalles", sa.Column("rol", sa.String(15), server_default="insumo"))
    _add("receta_detalles", sa.Column("valor_aprovechable", sa.Numeric(14, 2),
                                      server_default="0"))

    for col in [
        sa.Column("empresa_id", sa.Integer(), server_default="1"),
        sa.Column("numero", sa.String(30)),
        sa.Column("costo_insumos", sa.Numeric(14, 2), server_default="0"),
        sa.Column("valor_aprovechables", sa.Numeric(14, 2), server_default="0"),
        sa.Column("merma_valor", sa.Numeric(14, 2), server_default="0"),
        sa.Column("estado", sa.String(20), server_default="confirmada"),
        sa.Column("bodega_id", sa.Integer()),
        sa.Column("usuario_id", sa.Integer()),
        sa.Column("observaciones", sa.String(400)),
        sa.Column("motivo_anulacion", sa.String(250)),
        sa.Column("fecha_anulacion", sa.DateTime()),
    ]:
        _add("ordenes_produccion", col)

    op.execute("UPDATE ordenes_produccion SET estado = 'confirmada' WHERE estado IS NULL")

    if not _hay_tabla("consumos_produccion"):
        op.create_table(
            "consumos_produccion",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("orden_id", sa.Integer(), sa.ForeignKey("ordenes_produccion.id"), nullable=False),
            sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
            sa.Column("rol", sa.String(15), server_default="insumo"),
            sa.Column("cantidad_base", sa.Numeric(14, 3), server_default="0"),
            sa.Column("cantidad_merma", sa.Numeric(14, 3), server_default="0"),
            sa.Column("cantidad_total", sa.Numeric(14, 3), nullable=False),
            sa.Column("costo_unitario", sa.Numeric(14, 2), server_default="0"),
            sa.Column("costo_total", sa.Numeric(14, 2), server_default="0"))


def downgrade() -> None:
    if _hay_tabla("consumos_produccion"):
        op.drop_table("consumos_produccion")
    for c in ("empresa_id", "numero", "costo_insumos", "valor_aprovechables",
              "merma_valor", "estado", "bodega_id", "usuario_id",
              "observaciones", "motivo_anulacion", "fecha_anulacion"):
        _drop("ordenes_produccion", c)
    _drop("receta_detalles", "rol")
    _drop("receta_detalles", "valor_aprovechable")
    _drop("recetas", "activa")
