"""Paso 20: empleado-usuario unificado + estructura de foto/biometria.

Agrega a 'empleados' los campos de foto y estructura para reconocimiento facial
(consentimiento incluido), y a 'usuarios' los permisos de acceso por canal
(web / app de pedidos). Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_empleado_usuario"
down_revision = "0009_auditoria"
branch_labels = None
depends_on = None


def _cols(tabla):
    insp = sa.inspect(op.get_bind())
    if tabla not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(tabla)}


def upgrade() -> None:
    emp = _cols("empleados")
    if emp:
        if "foto" not in emp:
            op.add_column("empleados", sa.Column("foto", sa.String(255)))
        if "codificacion_facial" not in emp:
            op.add_column("empleados",
                          sa.Column("codificacion_facial", sa.Text()))
        if "consentimiento_biometrico" not in emp:
            op.add_column("empleados", sa.Column(
                "consentimiento_biometrico", sa.Boolean(),
                server_default=sa.false()))
        if "fecha_consentimiento" not in emp:
            op.add_column("empleados",
                          sa.Column("fecha_consentimiento", sa.Date()))

    usu = _cols("usuarios")
    if usu:
        if "acceso_web" not in usu:
            op.add_column("usuarios", sa.Column(
                "acceso_web", sa.Boolean(), server_default=sa.true()))
        if "acceso_app_pedidos" not in usu:
            op.add_column("usuarios", sa.Column(
                "acceso_app_pedidos", sa.Boolean(), server_default=sa.false()))


def downgrade() -> None:
    for col in ("acceso_web", "acceso_app_pedidos"):
        if col in _cols("usuarios"):
            op.drop_column("usuarios", col)
    for col in ("foto", "codificacion_facial", "consentimiento_biometrico",
                "fecha_consentimiento"):
        if col in _cols("empleados"):
            op.drop_column("empleados", col)
