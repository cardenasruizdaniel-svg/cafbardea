"""Paso 17: RBAC (roles y permisos parametrizables).

Crea las tablas de roles, permisos y sus asignaciones. Estas tablas ya estaban
definidas en los modelos enterprise pero no se creaban en bases existentes.
Idempotente: solo crea lo que falte. Los datos (roles y permisos) los siembra
inicializar_rbac(), no la migracion.
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_rbac"
down_revision = "0007_consolidacion_defaults"
branch_labels = None
depends_on = None


def _tablas():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existentes = _tablas()

    if "roles" not in existentes:
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nombre", sa.String(50), nullable=False, unique=True),
            sa.Column("descripcion", sa.String(255)),
            sa.Column("nivel_acceso", sa.Integer(), server_default="0"),
            sa.Column("activo", sa.Boolean(), server_default=sa.true()),
            sa.Column("es_predefinido", sa.Boolean(), server_default=sa.false()),
        )

    if "permisos" not in existentes:
        op.create_table(
            "permisos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("codigo", sa.String(80), nullable=False, unique=True),
            sa.Column("nombre", sa.String(120), nullable=False),
            sa.Column("descripcion", sa.String(255)),
            sa.Column("categoria", sa.String(50), nullable=False),
        )

    if "rol_permisos" not in existentes:
        op.create_table(
            "rol_permisos",
            sa.Column("rol_id", sa.Integer(), sa.ForeignKey("roles.id"),
                      primary_key=True),
            sa.Column("permiso_id", sa.Integer(), sa.ForeignKey("permisos.id"),
                      primary_key=True),
        )

    if "usuario_roles" not in existentes:
        op.create_table(
            "usuario_roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("usuario_id", sa.Integer(),
                      sa.ForeignKey("usuarios.id"), nullable=False),
            sa.Column("rol_id", sa.Integer(),
                      sa.ForeignKey("roles.id"), nullable=False),
            sa.Column("sucursal_id", sa.Integer()),
            sa.Column("activo", sa.Boolean(), server_default=sa.true()),
            sa.Column("fecha_asignacion", sa.DateTime()),
            sa.Column("fecha_expiracion", sa.DateTime()),
        )


def downgrade() -> None:
    for t in ("usuario_roles", "rol_permisos", "permisos", "roles"):
        if t in _tablas():
            op.drop_table(t)
