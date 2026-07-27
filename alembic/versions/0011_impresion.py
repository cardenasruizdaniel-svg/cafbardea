"""Paso 21: impresoras y grupos de impresion.

Crea las tablas de impresoras y grupos, y agrega a 'productos' los enlaces de
impresion (impresora especifica y grupo). Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0011_impresion"
down_revision = "0010_empleado_usuario"
branch_labels = None
depends_on = None


def _tablas():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _cols(tabla):
    insp = sa.inspect(op.get_bind())
    if tabla not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(tabla)}


def upgrade() -> None:
    tablas = _tablas()

    if "impresoras" not in tablas:
        op.create_table(
            "impresoras",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), server_default="1"),
            sa.Column("nombre", sa.String(80), nullable=False),
            sa.Column("destino", sa.String(120), server_default="local"),
            sa.Column("tipo_conexion", sa.String(15), server_default="local"),
            sa.Column("es_por_defecto", sa.Boolean(), server_default=sa.false()),
            sa.Column("activa", sa.Boolean(), server_default=sa.true()),
        )

    if "grupos_impresion" not in tablas:
        op.create_table(
            "grupos_impresion",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), server_default="1"),
            sa.Column("nombre", sa.String(80), nullable=False),
            sa.Column("impresora_id", sa.Integer(),
                      sa.ForeignKey("impresoras.id")),
            sa.Column("activo", sa.Boolean(), server_default=sa.true()),
        )

    prod = _cols("productos")
    if prod:
        if "grupo_impresion_id" not in prod:
            op.add_column("productos", sa.Column(
                "grupo_impresion_id", sa.Integer(),
                sa.ForeignKey("grupos_impresion.id")))
        if "impresora_id" not in prod:
            op.add_column("productos", sa.Column(
                "impresora_id", sa.Integer(), sa.ForeignKey("impresoras.id")))


def downgrade() -> None:
    # En SQLite, quitar columnas con FK requiere batch (recrea la tabla).
    prod = _cols("productos")
    with op.batch_alter_table("productos") as batch:
        if "impresora_id" in prod:
            batch.drop_column("impresora_id")
        if "grupo_impresion_id" in prod:
            batch.drop_column("grupo_impresion_id")
    for t in ("grupos_impresion", "impresoras"):
        if t in _tablas():
            op.drop_table(t)
