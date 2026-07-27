"""Paso 9: dominio de Compras y aprovisionamiento.

Anade las tablas del ciclo de compras (solicitudes, cotizaciones, ordenes,
recepciones y detalle de factura) y los campos fiscales de la cabecera de
compra, mas datos comerciales del proveedor y el IVA por producto.

Idempotente: comprueba antes de crear.
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_compras_aprovisionamiento"
down_revision = "0002_inventario_mesas_pagos"
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
    # -- Columnas nuevas ----------------------------------------------------
    _add("productos", sa.Column("iva_porcentaje", sa.Numeric(6, 3),
                                nullable=True, server_default="0"))

    for col in [
        sa.Column("direccion", sa.String(200)),
        sa.Column("ciudad", sa.String(100)),
        sa.Column("contacto", sa.String(120)),
        sa.Column("dias_credito", sa.Integer(), server_default="0"),
        sa.Column("activo", sa.Boolean(), server_default=sa.true()),
        sa.Column("observaciones", sa.String(400)),
    ]:
        _add("proveedores", col)

    for col in [
        sa.Column("empresa_id", sa.Integer(), server_default="1"),
        sa.Column("usuario_id", sa.Integer()),
        sa.Column("orden_compra_id", sa.Integer()),
        sa.Column("bodega_id", sa.Integer()),
        sa.Column("estado", sa.String(20), server_default="confirmada"),
        sa.Column("subtotal", sa.Numeric(14, 2), server_default="0"),
        sa.Column("descuento", sa.Numeric(14, 2), server_default="0"),
        sa.Column("iva", sa.Numeric(14, 2), server_default="0"),
        sa.Column("retencion_fuente", sa.Numeric(14, 2), server_default="0"),
        sa.Column("retencion_iva", sa.Numeric(14, 2), server_default="0"),
        sa.Column("total", sa.Numeric(14, 2), server_default="0"),
        sa.Column("forma_pago", sa.String(20), server_default="contado"),
        sa.Column("fecha_vencimiento", sa.Date()),
        sa.Column("motivo_anulacion", sa.String(250)),
        sa.Column("fecha_anulacion", sa.DateTime()),
        sa.Column("observaciones", sa.String(500)),
    ]:
        _add("compras", col)

    # Las compras historicas quedan como 'confirmada' y con total = valor
    op.execute("UPDATE compras SET estado = 'confirmada' WHERE estado IS NULL")
    op.execute("UPDATE compras SET total = valor WHERE total IS NULL OR total = 0")

    # -- Tablas nuevas ------------------------------------------------------
    def crea(nombre, *cols):
        if not _hay_tabla(nombre):
            op.create_table(nombre, *cols)

    crea("detalle_compras",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("compra_id", sa.Integer(), sa.ForeignKey("compras.id"), nullable=False),
         sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
         sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
         sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=False),
         sa.Column("descuento_porcentaje", sa.Numeric(6, 3), server_default="0"),
         sa.Column("iva_porcentaje", sa.Numeric(6, 3), server_default="0"),
         sa.Column("lote_codigo", sa.String(60)),
         sa.Column("fecha_vencimiento", sa.Date()))

    crea("solicitudes_compra",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("empresa_id", sa.Integer(), server_default="1"),
         sa.Column("numero", sa.String(30), unique=True, nullable=False),
         sa.Column("fecha", sa.Date()),
         sa.Column("solicitante_id", sa.Integer()),
         sa.Column("justificacion", sa.String(400)),
         sa.Column("estado", sa.String(20), server_default="pendiente"),
         sa.Column("aprobada_por_id", sa.Integer()),
         sa.Column("fecha_aprobacion", sa.DateTime()),
         sa.Column("motivo_rechazo", sa.String(250)))

    crea("detalle_solicitudes",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("solicitud_id", sa.Integer(), sa.ForeignKey("solicitudes_compra.id"), nullable=False),
         sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
         sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
         sa.Column("observacion", sa.String(250)))

    crea("cotizaciones",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("empresa_id", sa.Integer(), server_default="1"),
         sa.Column("solicitud_id", sa.Integer(), sa.ForeignKey("solicitudes_compra.id")),
         sa.Column("proveedor_id", sa.Integer(), sa.ForeignKey("proveedores.id"), nullable=False),
         sa.Column("numero", sa.String(30), nullable=False),
         sa.Column("fecha", sa.Date()),
         sa.Column("validez_dias", sa.Integer(), server_default="15"),
         sa.Column("dias_entrega", sa.Integer(), server_default="0"),
         sa.Column("forma_pago", sa.String(20), server_default="contado"),
         sa.Column("estado", sa.String(20), server_default="recibida"),
         sa.Column("subtotal", sa.Numeric(14, 2), server_default="0"),
         sa.Column("iva", sa.Numeric(14, 2), server_default="0"),
         sa.Column("total", sa.Numeric(14, 2), server_default="0"),
         sa.Column("observaciones", sa.String(400)))

    crea("detalle_cotizaciones",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("cotizacion_id", sa.Integer(), sa.ForeignKey("cotizaciones.id"), nullable=False),
         sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
         sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
         sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=False),
         sa.Column("iva_porcentaje", sa.Numeric(6, 3), server_default="0"))

    crea("ordenes_compra",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("empresa_id", sa.Integer(), server_default="1"),
         sa.Column("numero", sa.String(30), unique=True, nullable=False),
         sa.Column("proveedor_id", sa.Integer(), sa.ForeignKey("proveedores.id"), nullable=False),
         sa.Column("cotizacion_id", sa.Integer()),
         sa.Column("solicitud_id", sa.Integer()),
         sa.Column("fecha", sa.Date()),
         sa.Column("fecha_entrega_esperada", sa.Date()),
         sa.Column("estado", sa.String(20), server_default="borrador"),
         sa.Column("forma_pago", sa.String(20), server_default="contado"),
         sa.Column("subtotal", sa.Numeric(14, 2), server_default="0"),
         sa.Column("iva", sa.Numeric(14, 2), server_default="0"),
         sa.Column("total", sa.Numeric(14, 2), server_default="0"),
         sa.Column("usuario_id", sa.Integer()),
         sa.Column("observaciones", sa.String(500)),
         sa.Column("motivo_anulacion", sa.String(250)))

    crea("detalle_ordenes",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("orden_id", sa.Integer(), sa.ForeignKey("ordenes_compra.id"), nullable=False),
         sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
         sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
         sa.Column("cantidad_recibida", sa.Numeric(14, 3), server_default="0"),
         sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=False),
         sa.Column("iva_porcentaje", sa.Numeric(6, 3), server_default="0"))

    crea("recepciones",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("empresa_id", sa.Integer(), server_default="1"),
         sa.Column("numero", sa.String(30), unique=True, nullable=False),
         sa.Column("orden_id", sa.Integer(), sa.ForeignKey("ordenes_compra.id")),
         sa.Column("compra_id", sa.Integer(), sa.ForeignKey("compras.id")),
         sa.Column("bodega_id", sa.Integer()),
         sa.Column("fecha", sa.DateTime()),
         sa.Column("remision", sa.String(60)),
         sa.Column("usuario_id", sa.Integer()),
         sa.Column("observaciones", sa.String(400)))

    crea("detalle_recepciones",
         sa.Column("id", sa.Integer(), primary_key=True),
         sa.Column("recepcion_id", sa.Integer(), sa.ForeignKey("recepciones.id"), nullable=False),
         sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
         sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
         sa.Column("costo_unitario", sa.Numeric(14, 2), server_default="0"),
         sa.Column("lote_codigo", sa.String(60)),
         sa.Column("fecha_vencimiento", sa.Date()))


def downgrade() -> None:
    for t in ("detalle_recepciones", "recepciones", "detalle_ordenes",
              "ordenes_compra", "detalle_cotizaciones", "cotizaciones",
              "detalle_solicitudes", "solicitudes_compra", "detalle_compras"):
        if _hay_tabla(t):
            op.drop_table(t)

    for c in ("empresa_id", "usuario_id", "orden_compra_id", "bodega_id",
              "estado", "subtotal", "descuento", "iva", "retencion_fuente",
              "retencion_iva", "total", "forma_pago", "fecha_vencimiento",
              "motivo_anulacion", "fecha_anulacion", "observaciones"):
        _drop("compras", c)
    for c in ("direccion", "ciudad", "contacto", "dias_credito", "activo",
              "observaciones"):
        _drop("proveedores", c)
    _drop("productos", "iva_porcentaje")
