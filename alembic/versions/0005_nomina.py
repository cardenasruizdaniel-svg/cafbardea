"""Paso 12: dominio de Nomina (Colombia).

Amplia parametros de nomina (todos los factores legales configurables),
empleados (datos de nomina), periodos y liquidaciones (desglose completo:
devengados, deducciones, IBC, aportes patronales y provisiones) y crea la
tabla de novedades. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_nomina"
down_revision = "0004_produccion"
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
    # --- parametros_nomina: todos los factores legales configurables ---
    for col in [
        sa.Column("fsp_pct", sa.Numeric(7, 4), server_default="1"),
        sa.Column("fsp_smmlv_desde", sa.Numeric(7, 2), server_default="4"),
        sa.Column("salud_empleador_pct", sa.Numeric(7, 4), server_default="8.5"),
        sa.Column("pension_empleador_pct", sa.Numeric(7, 4), server_default="12"),
        sa.Column("arl_pct", sa.Numeric(7, 4), server_default="0.522"),
        sa.Column("caja_pct", sa.Numeric(7, 4), server_default="4"),
        sa.Column("icbf_pct", sa.Numeric(7, 4), server_default="3"),
        sa.Column("sena_pct", sa.Numeric(7, 4), server_default="2"),
        sa.Column("exoneracion_smmlv", sa.Numeric(7, 2), server_default="10"),
        sa.Column("recargo_nocturno_pct", sa.Numeric(7, 4), server_default="35"),
        sa.Column("hora_extra_diurna_pct", sa.Numeric(7, 4), server_default="25"),
        sa.Column("hora_extra_nocturna_pct", sa.Numeric(7, 4), server_default="75"),
        sa.Column("recargo_dominical_pct", sa.Numeric(7, 4), server_default="75"),
        sa.Column("hora_extra_diurna_dominical_pct", sa.Numeric(7, 4), server_default="100"),
        sa.Column("hora_extra_nocturna_dominical_pct", sa.Numeric(7, 4), server_default="150"),
        sa.Column("horas_mensuales", sa.Numeric(7, 2), server_default="230"),
        sa.Column("prima_pct", sa.Numeric(7, 4), server_default="8.33"),
        sa.Column("cesantias_pct", sa.Numeric(7, 4), server_default="8.33"),
        sa.Column("intereses_cesantias_pct", sa.Numeric(7, 4), server_default="12"),
        sa.Column("vacaciones_pct", sa.Numeric(7, 4), server_default="4.17"),
        sa.Column("factor_integral_prestacional", sa.Numeric(7, 4), server_default="30"),
        sa.Column("integral_min_smmlv", sa.Numeric(7, 2), server_default="13"),
    ]:
        _add("parametros_nomina", col)

    # Normalizar porcentajes de empleado que pudieran haber quedado como
    # fraccion (0.04) en lugar de entero (4). Solo si son menores a 1.
    op.execute("UPDATE parametros_nomina SET salud_empleado_pct = 4 "
               "WHERE salud_empleado_pct < 1")
    op.execute("UPDATE parametros_nomina SET pension_empleado_pct = 4 "
               "WHERE pension_empleado_pct < 1")

    # --- empleados: datos de nomina ---
    for col in [
        sa.Column("empresa_id", sa.Integer(), server_default="1"),
        sa.Column("tipo_salario", sa.String(15), server_default="ordinario"),
        sa.Column("caja_compensacion", sa.String(100)),
        sa.Column("nivel_riesgo_arl", sa.Integer(), server_default="1"),
        sa.Column("auxilio_transporte", sa.Boolean(), server_default=sa.true()),
        sa.Column("fecha_retiro", sa.Date()),
        sa.Column("cuenta_bancaria", sa.String(40)),
        sa.Column("banco", sa.String(80)),
    ]:
        _add("empleados", col)

    # --- periodos_nomina: empresa y totales ---
    for col in [
        sa.Column("empresa_id", sa.Integer(), server_default="1"),
        sa.Column("total_devengado", sa.Numeric(16, 2), server_default="0"),
        sa.Column("total_deducido", sa.Numeric(16, 2), server_default="0"),
        sa.Column("total_neto", sa.Numeric(16, 2), server_default="0"),
        sa.Column("total_aportes_empleador", sa.Numeric(16, 2), server_default="0"),
    ]:
        _add("periodos_nomina", col)

    # --- liquidaciones_nomina: desglose completo ---
    for col in [
        sa.Column("tipo_salario", sa.String(15), server_default="ordinario"),
        sa.Column("sueldo", sa.Numeric(14, 2), server_default="0"),
        sa.Column("auxilio_transporte", sa.Numeric(14, 2), server_default="0"),
        sa.Column("horas_extra", sa.Numeric(14, 2), server_default="0"),
        sa.Column("recargos", sa.Numeric(14, 2), server_default="0"),
        sa.Column("comisiones", sa.Numeric(14, 2), server_default="0"),
        sa.Column("bonificaciones", sa.Numeric(14, 2), server_default="0"),
        sa.Column("otros_devengados", sa.Numeric(14, 2), server_default="0"),
        sa.Column("salud_empleado", sa.Numeric(14, 2), server_default="0"),
        sa.Column("pension_empleado", sa.Numeric(14, 2), server_default="0"),
        sa.Column("fondo_solidaridad", sa.Numeric(14, 2), server_default="0"),
        sa.Column("retencion_fuente", sa.Numeric(14, 2), server_default="0"),
        sa.Column("otras_deducciones", sa.Numeric(14, 2), server_default="0"),
        sa.Column("ibc", sa.Numeric(14, 2), server_default="0"),
        sa.Column("salud_empleador", sa.Numeric(14, 2), server_default="0"),
        sa.Column("pension_empleador", sa.Numeric(14, 2), server_default="0"),
        sa.Column("arl_empleador", sa.Numeric(14, 2), server_default="0"),
        sa.Column("caja_empleador", sa.Numeric(14, 2), server_default="0"),
        sa.Column("icbf_empleador", sa.Numeric(14, 2), server_default="0"),
        sa.Column("sena_empleador", sa.Numeric(14, 2), server_default="0"),
        sa.Column("total_aportes_empleador", sa.Numeric(14, 2), server_default="0"),
        sa.Column("prov_prima", sa.Numeric(14, 2), server_default="0"),
        sa.Column("prov_cesantias", sa.Numeric(14, 2), server_default="0"),
        sa.Column("prov_intereses_cesantias", sa.Numeric(14, 2), server_default="0"),
        sa.Column("prov_vacaciones", sa.Numeric(14, 2), server_default="0"),
        sa.Column("total_provisiones", sa.Numeric(14, 2), server_default="0"),
    ]:
        _add("liquidaciones_nomina", col)

    # --- novedades_nomina: tabla nueva ---
    if not _hay_tabla("novedades_nomina"):
        op.create_table(
            "novedades_nomina",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), server_default="1"),
            sa.Column("empleado_id", sa.Integer(), nullable=False),
            sa.Column("periodo_id", sa.Integer()),
            sa.Column("fecha", sa.Date()),
            sa.Column("tipo", sa.String(35), nullable=False),
            sa.Column("cantidad", sa.Numeric(10, 2), server_default="0"),
            sa.Column("valor", sa.Numeric(14, 2), server_default="0"),
            sa.Column("constitutivo_salario", sa.Boolean(), server_default=sa.true()),
            sa.Column("descripcion", sa.String(250)),
            sa.Column("aplicada", sa.Boolean(), server_default=sa.false()),
        )


def downgrade() -> None:
    if _hay_tabla("novedades_nomina"):
        op.drop_table("novedades_nomina")
    for c in ["tipo_salario", "sueldo", "auxilio_transporte", "horas_extra",
              "recargos", "comisiones", "bonificaciones", "otros_devengados",
              "salud_empleado", "pension_empleado", "fondo_solidaridad",
              "retencion_fuente", "otras_deducciones", "ibc", "salud_empleador",
              "pension_empleador", "arl_empleador", "caja_empleador",
              "icbf_empleador", "sena_empleador", "total_aportes_empleador",
              "prov_prima", "prov_cesantias", "prov_intereses_cesantias",
              "prov_vacaciones", "total_provisiones"]:
        _drop("liquidaciones_nomina", c)
    for c in ["empresa_id", "total_devengado", "total_deducido", "total_neto",
              "total_aportes_empleador"]:
        _drop("periodos_nomina", c)
    for c in ["empresa_id", "tipo_salario", "caja_compensacion",
              "nivel_riesgo_arl", "auxilio_transporte", "fecha_retiro",
              "cuenta_bancaria", "banco"]:
        _drop("empleados", c)
    for c in ["fsp_pct", "fsp_smmlv_desde", "salud_empleador_pct",
              "pension_empleador_pct", "arl_pct", "caja_pct", "icbf_pct",
              "sena_pct", "exoneracion_smmlv", "recargo_nocturno_pct",
              "hora_extra_diurna_pct", "hora_extra_nocturna_pct",
              "recargo_dominical_pct", "hora_extra_diurna_dominical_pct",
              "hora_extra_nocturna_dominical_pct", "horas_mensuales",
              "prima_pct", "cesantias_pct", "intereses_cesantias_pct",
              "vacaciones_pct", "factor_integral_prestacional",
              "integral_min_smmlv"]:
        _drop("parametros_nomina", c)
