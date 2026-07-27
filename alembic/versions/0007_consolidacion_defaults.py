"""Paso 15: consolidacion. Server-defaults en columnas NOT NULL de empresas.

Las columnas NOT NULL de 'empresas' tenian default en Python (via ORM) pero no
en la base. Un INSERT SQL directo (restauracion, carga masiva) fallaba. Esta
migracion agrega server_default a nivel de BD para que la tabla sea robusta
independientemente de como se inserte. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_consolidacion_defaults"
down_revision = "0006_asistencia"
branch_labels = None
depends_on = None


# columna -> valor por defecto a nivel de servidor
DEFAULTS = {
    "color_primario": "#b45309",
    "color_secundario": "#fef3c7",
    "moneda": "COP",
    "prefijo_factura": "POS",
    "consecutivo_factura": "1",
    "impuesto_porcentaje": "0",
    "tipo_persona": "juridica",
    "regimen_tributario": "ordinario",
    "facturador_electronico": "0",
    "modo_electronico": "pruebas",
    "prefijo_nomina": "NE",
    "consecutivo_nomina": "1",
    "permitir_stock_negativo": "1",
}


def _cols(tabla):
    insp = sa.inspect(op.get_bind())
    if tabla not in insp.get_table_names():
        return {}
    return {c["name"]: c for c in insp.get_columns(tabla)}


def upgrade() -> None:
    cols = _cols("empresas")
    if not cols:
        return
    # En SQLite, alterar defaults requiere batch (recrea la tabla). Solo se
    # tocan las columnas que existen y aun no tienen server_default.
    faltantes = {
        nombre: valor for nombre, valor in DEFAULTS.items()
        if nombre in cols and cols[nombre].get("default") is None
    }
    if not faltantes:
        return
    with op.batch_alter_table("empresas") as batch:
        for nombre, valor in faltantes.items():
            batch.alter_column(nombre, server_default=valor)


def downgrade() -> None:
    cols = _cols("empresas")
    if not cols:
        return
    with op.batch_alter_table("empresas") as batch:
        for nombre in DEFAULTS:
            if nombre in cols:
                batch.alter_column(nombre, server_default=None)
