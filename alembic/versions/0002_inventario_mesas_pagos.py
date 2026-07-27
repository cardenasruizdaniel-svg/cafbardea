"""Pasos 4-6: pagos de venta, kardex de inventario, bodegas, lotes y mesas.

Escrita a mano en vez de autogenerada. La autogeneracion producia 1.500 lineas
de ruido (recreacion de tablas por diferencias de NOT NULL y claves foraneas
que SQLite no expresa igual que SQLAlchemy). Esta version aplica UNICAMENTE
los cambios reales de los pasos 4, 5 y 6.

Cambios:
  - ventas   : tabla `pagos_venta` (monto recibido, aplicado y cambio)
  - inventario: `alertas_stock`, `bodegas`, `existencias_bodega`, `lotes`
                y campos de kardex en `movimientos_inventario`
  - mesas    : `reservas_mesa` y datos operativos del servicio
  - empresas : politica `permitir_stock_negativo`

Es idempotente: comprueba lo existente antes de crear, de modo que puede
aplicarse sobre una base que ya arranco con `auto_create_schema=True`.
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_inventario_mesas_pagos"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Utilidades de idempotencia
# ---------------------------------------------------------------------------
def _inspector():
    return sa.inspect(op.get_bind())


def _hay_tabla(nombre: str) -> bool:
    return nombre in _inspector().get_table_names()


def _hay_columna(tabla: str, columna: str) -> bool:
    if not _hay_tabla(tabla):
        return False
    return columna in {c["name"] for c in _inspector().get_columns(tabla)}


def _add_column(tabla: str, columna: sa.Column) -> None:
    if _hay_tabla(tabla) and not _hay_columna(tabla, columna.name):
        op.add_column(tabla, columna)


def _drop_column(tabla: str, columna: str) -> None:
    if _hay_columna(tabla, columna):
        with op.batch_alter_table(tabla) as batch:
            batch.drop_column(columna)


# ---------------------------------------------------------------------------
def upgrade() -> None:
    # -- Politica de inventario ---------------------------------------------
    _add_column("empresas", sa.Column(
        "permitir_stock_negativo", sa.Boolean(), nullable=True,
        server_default=sa.true()))

    # -- Mesas: datos operativos del servicio -------------------------------
    _add_column("mesas", sa.Column("fecha_apertura", sa.DateTime(), nullable=True))
    _add_column("mesas", sa.Column("mesero_id", sa.Integer(), nullable=True))
    _add_column("mesas", sa.Column("comensales", sa.Integer(), nullable=True))
    _add_column("mesas", sa.Column("mesa_padre_id", sa.Integer(), nullable=True))

    # El dominio de mesas usaba "disponible" mientras el resto del sistema
    # escribia "libre". Se normalizan los datos existentes.
    op.execute("UPDATE mesas SET estado = 'libre' WHERE estado = 'disponible'")

    # -- Kardex en movimientos de inventario --------------------------------
    _add_column("movimientos_inventario", sa.Column("bodega_id", sa.Integer(), nullable=True))
    _add_column("movimientos_inventario", sa.Column("lote_id", sa.Integer(), nullable=True))
    _add_column("movimientos_inventario", sa.Column(
        "saldo_anterior", sa.Numeric(14, 3), nullable=True, server_default="0"))
    _add_column("movimientos_inventario", sa.Column(
        "saldo_posterior", sa.Numeric(14, 3), nullable=True, server_default="0"))
    _add_column("movimientos_inventario", sa.Column(
        "costo_promedio_anterior", sa.Numeric(14, 2), nullable=True, server_default="0"))
    _add_column("movimientos_inventario", sa.Column(
        "costo_promedio_posterior", sa.Numeric(14, 2), nullable=True, server_default="0"))
    _add_column("movimientos_inventario", sa.Column("usuario_id", sa.Integer(), nullable=True))
    _add_column("movimientos_inventario", sa.Column("observacion", sa.String(250), nullable=True))

    # -- Pagos de venta -----------------------------------------------------
    if not _hay_tabla("pagos_venta"):
        op.create_table(
            "pagos_venta",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("venta_id", sa.Integer(), sa.ForeignKey("ventas.id"), nullable=False),
            sa.Column("tipo_pago", sa.String(30), nullable=False),
            sa.Column("monto_recibido", sa.Numeric(14, 2), nullable=False),
            sa.Column("monto_aplicado", sa.Numeric(14, 2), nullable=False),
            sa.Column("cambio", sa.Numeric(14, 2), nullable=True, server_default="0"),
            sa.Column("referencia", sa.String(100), nullable=True),
            sa.Column("fecha", sa.DateTime(), nullable=True),
            sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        )

    # -- Alertas de stock ---------------------------------------------------
    if not _hay_tabla("alertas_stock"):
        op.create_table(
            "alertas_stock",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
            sa.Column("tipo", sa.String(30), nullable=False),
            sa.Column("existencia_resultante", sa.Numeric(14, 3), nullable=False),
            sa.Column("cantidad_solicitada", sa.Numeric(14, 3), nullable=True, server_default="0"),
            sa.Column("referencia", sa.String(120), nullable=True),
            sa.Column("fecha", sa.DateTime(), nullable=True),
            sa.Column("atendida", sa.Boolean(), nullable=True, server_default=sa.false()),
        )

    # -- Bodegas ------------------------------------------------------------
    if not _hay_tabla("bodegas"):
        op.create_table(
            "bodegas",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=True),
            sa.Column("codigo", sa.String(20), nullable=False, unique=True),
            sa.Column("nombre", sa.String(100), nullable=False),
            sa.Column("ubicacion", sa.String(150), nullable=True),
            sa.Column("es_principal", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("activa", sa.Boolean(), nullable=True, server_default=sa.true()),
        )

    if not _hay_tabla("lotes"):
        op.create_table(
            "lotes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
            sa.Column("bodega_id", sa.Integer(), sa.ForeignKey("bodegas.id"), nullable=False),
            sa.Column("codigo", sa.String(60), nullable=False),
            sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
            sa.Column("fecha_ingreso", sa.Date(), nullable=True),
            sa.Column("cantidad_inicial", sa.Numeric(14, 3), nullable=True, server_default="0"),
            sa.Column("cantidad_disponible", sa.Numeric(14, 3), nullable=True, server_default="0"),
            sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True, server_default="0"),
            sa.Column("activo", sa.Boolean(), nullable=True, server_default=sa.true()),
        )

    if not _hay_tabla("existencias_bodega"):
        op.create_table(
            "existencias_bodega",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
            sa.Column("bodega_id", sa.Integer(), sa.ForeignKey("bodegas.id"), nullable=False),
            sa.Column("cantidad", sa.Numeric(14, 3), nullable=True, server_default="0"),
        )

    # -- Reservas de mesa ---------------------------------------------------
    if not _hay_tabla("reservas_mesa"):
        op.create_table(
            "reservas_mesa",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("mesa_id", sa.Integer(), sa.ForeignKey("mesas.id"), nullable=False),
            sa.Column("cliente_nombre", sa.String(100), nullable=False),
            sa.Column("telefono", sa.String(20), nullable=True),
            sa.Column("personas", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("fecha_hora", sa.DateTime(), nullable=True),
            sa.Column("notas", sa.String(500), nullable=True),
            sa.Column("estado", sa.String(20), nullable=True, server_default="pendiente"),
            sa.Column("creada_en", sa.DateTime(), nullable=True),
        )

    # -- Bodega principal y migracion de existencias ------------------------
    # Las existencias historicas viven en productos.existencias sin bodega.
    # Se crea la bodega principal y se vuelca ahi el saldo actual, de modo que
    # el detalle por ubicacion cuadre con el total consolidado.
    conn = op.get_bind()
    existe = conn.execute(sa.text(
        "SELECT id FROM bodegas WHERE codigo = 'PRINCIPAL'")).fetchone()
    if not existe:
        conn.execute(sa.text(
            "INSERT INTO bodegas (empresa_id, codigo, nombre, es_principal, activa) "
            "VALUES (1, 'PRINCIPAL', 'Bodega principal', 1, 1)"))
    bodega_id = conn.execute(sa.text(
        "SELECT id FROM bodegas WHERE codigo = 'PRINCIPAL'")).scalar()

    ya_hay = conn.execute(sa.text("SELECT COUNT(*) FROM existencias_bodega")).scalar()
    if not ya_hay:
        conn.execute(sa.text(
            "INSERT INTO existencias_bodega (producto_id, bodega_id, cantidad) "
            "SELECT id, :b, COALESCE(existencias, 0) FROM productos"), {"b": bodega_id})

    # Los movimientos historicos no tienen bodega: se asignan a la principal.
    conn.execute(sa.text(
        "UPDATE movimientos_inventario SET bodega_id = :b WHERE bodega_id IS NULL"),
        {"b": bodega_id})


# ---------------------------------------------------------------------------
def downgrade() -> None:
    for tabla in ("reservas_mesa", "existencias_bodega", "lotes",
                  "bodegas", "alertas_stock", "pagos_venta"):
        if _hay_tabla(tabla):
            op.drop_table(tabla)

    for col in ("bodega_id", "lote_id", "saldo_anterior", "saldo_posterior",
                "costo_promedio_anterior", "costo_promedio_posterior",
                "usuario_id", "observacion"):
        _drop_column("movimientos_inventario", col)

    for col in ("fecha_apertura", "mesero_id", "comensales", "mesa_padre_id"):
        _drop_column("mesas", col)

    _drop_column("empresas", "permitir_stock_negativo")
