"""Paso 14: control de asistencia.

Amplia la tabla de turnos (horas calculadas, tipo de jornada, receso, tardanza,
vinculo con la novedad de nomina), crea la tabla de marcaciones y la de turnos
programados. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_asistencia"
down_revision = "0005_nomina"
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
    # --- turnos: columnas nuevas ---
    for col in [
        sa.Column("empresa_id", sa.Integer(), server_default="1"),
        sa.Column("programado_id", sa.Integer()),
        sa.Column("horas_trabajadas", sa.Numeric(6, 2), server_default="0"),
        sa.Column("horas_ordinarias", sa.Numeric(6, 2), server_default="0"),
        sa.Column("horas_nocturnas", sa.Numeric(6, 2), server_default="0"),
        sa.Column("horas_dominicales", sa.Numeric(6, 2), server_default="0"),
        sa.Column("horas_extra_diurna", sa.Numeric(6, 2), server_default="0"),
        sa.Column("horas_extra_nocturna", sa.Numeric(6, 2), server_default="0"),
        sa.Column("horas_receso", sa.Numeric(6, 2), server_default="0"),
        sa.Column("minutos_tardanza", sa.Integer(), server_default="0"),
        sa.Column("estado", sa.String(15), server_default="abierto"),
        sa.Column("notas", sa.String(250)),
        sa.Column("novedad_generada_id", sa.Integer()),
    ]:
        _add("turnos", col)

    # Los turnos viejos que tenian salida se marcan como cerrados.
    if _hay_col("turnos", "estado") and _hay_col("turnos", "salida"):
        op.execute("UPDATE turnos SET estado = 'cerrado' "
                   "WHERE salida IS NOT NULL AND (estado IS NULL OR estado = 'abierto')")

    # --- marcaciones: tabla nueva ---
    if not _hay_tabla("marcaciones"):
        op.create_table(
            "marcaciones",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("turno_id", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(20), nullable=False),
            sa.Column("momento", sa.DateTime()),
            sa.Column("origen", sa.String(20), server_default="manual"),
        )

    # --- turnos_programados: tabla nueva ---
    if not _hay_tabla("turnos_programados"):
        op.create_table(
            "turnos_programados",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), server_default="1"),
            sa.Column("empleado_id", sa.Integer(), nullable=False),
            sa.Column("fecha", sa.Date(), nullable=False),
            sa.Column("hora_entrada", sa.Time(), nullable=False),
            sa.Column("hora_salida", sa.Time(), nullable=False),
            sa.Column("tolerancia_min", sa.Integer(), server_default="5"),
            sa.Column("estado", sa.String(15), server_default="programado"),
        )


def downgrade() -> None:
    if _hay_tabla("marcaciones"):
        op.drop_table("marcaciones")
    if _hay_tabla("turnos_programados"):
        op.drop_table("turnos_programados")
    for c in ["empresa_id", "programado_id", "horas_trabajadas",
              "horas_ordinarias", "horas_nocturnas", "horas_dominicales",
              "horas_extra_diurna", "horas_extra_nocturna", "horas_receso",
              "minutos_tardanza", "estado", "notas", "novedad_generada_id"]:
        _drop("turnos", c)
