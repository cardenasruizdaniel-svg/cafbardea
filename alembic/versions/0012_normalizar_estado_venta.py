"""Paso 22: normaliza el estado de ventas cobradas.

Antes, el servicio de ventas dejaba las ventas cobradas en estado 'cerrada',
pero los reportes, el dashboard y la caja consultan 'pagada'. Resultado: las
ventas cobradas por esa via no aparecian en ningun reporte. Se unifico el codigo
a 'pagada'; esta migracion normaliza los datos ya existentes. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0012_normalizar_estado_venta"
down_revision = "0011_impresion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "ventas" in sa.inspect(bind).get_table_names():
        # Las ventas 'cerrada' eran ventas cobradas -> pasan a 'pagada'.
        bind.execute(sa.text(
            "UPDATE ventas SET estado='pagada' WHERE estado='cerrada'"))


def downgrade() -> None:
    # No se revierte: 'pagada' es el estado canonico y no se puede distinguir
    # cuales eran 'cerrada' originalmente. Operacion de datos no reversible.
    pass
