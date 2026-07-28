"""Paso 30: sincroniza columnas de tablas base con el modelo actual.

Contexto del bug: la migracion 0001 crea las tablas con Base.metadata.create_all,
que refleja el modelo del momento y NO modifica tablas ya existentes. Si una base
de produccion (PostgreSQL en Render) se creo con una version antigua del modelo,
tablas como 'zonas' pueden carecer de columnas que el codigo nuevo espera
(empresa_id, orden, activa). Entonces INSERT INTO zonas (...) falla con 500 en
Postgres, aunque en SQLite local funcione.

Esta migracion agrega, de forma idempotente y compatible con SQLite y Postgres,
las columnas que el modelo necesita en las tablas base. Solo agrega lo que falte.
"""
import sqlalchemy as sa
from alembic import op

revision = "0015_sincronizar_columnas_base"
down_revision = "0014_pedidos_cliente"
branch_labels = None
depends_on = None


def _cols(tabla):
    insp = sa.inspect(op.get_bind())
    if tabla not in insp.get_table_names():
        return None  # la tabla no existe (se creara por create_all si aplica)
    return {c["name"] for c in insp.get_columns(tabla)}


def _add(tabla, nombre, tipo, server_default=None):
    """Agrega una columna si la tabla existe y la columna falta."""
    cols = _cols(tabla)
    if cols is None or nombre in cols:
        return
    col = sa.Column(nombre, tipo, server_default=server_default)
    op.add_column(tabla, col)


def upgrade() -> None:
    # zonas: el modelo espera empresa_id, orden, activa
    _add("zonas", "empresa_id", sa.Integer(), server_default="1")
    _add("zonas", "orden", sa.Integer(), server_default="0")
    _add("zonas", "activa", sa.Boolean(), server_default=sa.true())

    # mesas: columnas que fueron creciendo (posicion, forma, tamano, estado)
    _add("mesas", "empresa_id", sa.Integer(), server_default="1")
    _add("mesas", "posicion_x", sa.Integer(), server_default="0")
    _add("mesas", "posicion_y", sa.Integer(), server_default="0")
    _add("mesas", "forma", sa.String(15), server_default="redonda")
    _add("mesas", "ancho", sa.Integer(), server_default="64")
    _add("mesas", "alto", sa.Integer(), server_default="64")
    _add("mesas", "estado", sa.String(20), server_default="libre")

    # categorias: el modelo actual solo tiene id y nombre; nada que agregar,
    # pero se deja el hook por si un esquema viejo carecia de algo.

    # productos: enlaces de impresion (por si 0011 no alcanzo a una base vieja)
    _add("productos", "grupo_impresion_id", sa.Integer())
    _add("productos", "impresora_id", sa.Integer())


def downgrade() -> None:
    # No se revierte: solo agrega columnas ausentes para reparar esquemas viejos.
    # Quitarlas podria romper datos existentes. Operacion de reparacion, no
    # reversible de forma segura.
    pass
