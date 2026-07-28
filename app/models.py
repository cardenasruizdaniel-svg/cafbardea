from datetime import datetime, date, time, timedelta, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, Numeric, DateTime, Date, Time, ForeignKey, Boolean, Text, JSON, Table
from sqlalchemy import true as sa_true, false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
import uuid


# Zona horaria de Colombia (UTC-5, sin horario de verano). Se usa para las
# marcaciones de asistencia: registrar la hora local real, no UTC, evita que
# una entrada a las 8am se guarde como la 1pm.
TZ_COLOMBIA = timezone(timedelta(hours=-5))


def hora_colombia() -> datetime:
    """Hora actual en Colombia, sin tzinfo (naive) para guardar en SQLite."""
    return datetime.now(TZ_COLOMBIA).replace(tzinfo=None)


def fecha_colombia():
    """Fecha actual en Colombia. Usar en reportes en vez de date.today(),
    que devuelve la fecha UTC y de noche (hora Colombia) adelanta un dia."""
    return datetime.now(TZ_COLOMBIA).date()

class Empresa(Base):
    __tablename__ = "empresas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    nit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    color_primario: Mapped[str] = mapped_column(String(7), default="#b45309", server_default="#b45309")
    color_secundario: Mapped[str] = mapped_column(String(7), default="#fef3c7", server_default="#fef3c7")
    moneda: Mapped[str] = mapped_column(String(5), default="COP", server_default="COP")
    direccion: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    prefijo_factura: Mapped[str] = mapped_column(String(12), default="POS", server_default="POS")
    consecutivo_factura: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    impuesto_porcentaje: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0, server_default="0")
    tipo_persona: Mapped[str] = mapped_column(String(20), default="juridica", server_default="juridica")
    tipo_sociedad: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    regimen_tributario: Mapped[str] = mapped_column(String(30), default="ordinario", server_default="ordinario")
    facturador_electronico: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sa_false())
    proveedor_tecnologico: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    modo_electronico: Mapped[str] = mapped_column(String(15), default="pruebas", server_default="pruebas")
    prefijo_nomina: Mapped[str] = mapped_column(String(12), default="NE", server_default="NE")
    consecutivo_nomina: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    software_nomina_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # Politica de inventario: si es True se permite vender sin existencias,
    # el stock queda en negativo y se registra una alerta.
    permitir_stock_negativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=sa_true())

class Zona(Base):
    __tablename__ = "zonas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    nombre: Mapped[str] = mapped_column(String(80))
    orden: Mapped[int] = mapped_column(Integer, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    mesas: Mapped[list["Mesa"]] = relationship(back_populates="zona")

class Mesa(Base):
    """Mesa del salon.

    Estados validos: libre | ocupada | reservada | limpieza | mantenimiento.
    El dominio de mesas usaba "disponible" mientras el resto del sistema
    escribia "libre", de modo que el plano nunca reflejaba la realidad.
    """
    __tablename__ = "mesas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    zona_id: Mapped[int] = mapped_column(ForeignKey("zonas.id"))
    nombre: Mapped[str] = mapped_column(String(40))
    capacidad: Mapped[int] = mapped_column(Integer, default=4)
    posicion_x: Mapped[int] = mapped_column(Integer, default=0)
    posicion_y: Mapped[int] = mapped_column(Integer, default=0)
    forma: Mapped[str] = mapped_column(String(15), default="redonda")
    # Tamano de la mesa en el plano (px). Permite mesas mas grandes o pequenas.
    ancho: Mapped[int] = mapped_column(Integer, default=64, server_default="64")
    alto: Mapped[int] = mapped_column(Integer, default=64, server_default="64")
    estado: Mapped[str] = mapped_column(String(20), default="libre")

    # --- Datos operativos del servicio en curso ---
    # Sin estos campos era imposible saber cuanto lleva ocupada una mesa,
    # cuantos comensales hay o quien la atiende.
    fecha_apertura: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    mesero_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    comensales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mesa_padre_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mesas.id"), nullable=True)

    zona: Mapped[Zona] = relationship(back_populates="mesas")

    def minutos_ocupada(self) -> Optional[int]:
        """Minutos transcurridos desde la apertura del servicio."""
        if not self.fecha_apertura:
            return None
        delta = hora_colombia() - self.fecha_apertura
        return int(delta.total_seconds() // 60)


class ReservaMesa(Base):
    """Reserva de una mesa.

    El esquema `ReservarMesa` existia en la API desde el principio, pero
    ninguna ruta lo usaba: los datos del cliente se descartaban.
    """
    __tablename__ = "reservas_mesa"
    id: Mapped[int] = mapped_column(primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"))
    cliente_nombre: Mapped[str] = mapped_column(String(100))
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    personas: Mapped[int] = mapped_column(Integer, default=1)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    notas: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)

class Impresora(Base):
    """Impresora configurable del negocio (cocina, barra, caja, etc.).

    'destino' identifica fisicamente la impresora. Para impresoras de red suele
    ser una IP o nombre de cola; para la impresora local del equipo, un valor
    como 'local'. El sistema no imprime directamente al hardware desde aqui
    (eso depende del sistema operativo y drivers del cliente); guarda a que
    impresora corresponde cada comanda para que el cliente de impresion la envie
    al destino correcto.
    """
    __tablename__ = "impresoras"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    nombre: Mapped[str] = mapped_column(String(80))  # ej: "Cocina caliente"
    destino: Mapped[str] = mapped_column(String(120), default="local")
    # tipo de conexion: local | red | usb  (informativo para el cliente)
    tipo_conexion: Mapped[str] = mapped_column(String(15), default="local")
    # Impresora por defecto: recibe lo que no tiene destino resuelto.
    es_por_defecto: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_false())
    activa: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=sa_true())


class GrupoImpresion(Base):
    """Grupo de productos para efectos de impresion, aparte de las categorias.

    Permite agrupar productos por donde se preparan (p. ej. 'Bebidas frias' ->
    barra) independientemente de como esten categorizados para la venta.
    """
    __tablename__ = "grupos_impresion"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    nombre: Mapped[str] = mapped_column(String(80))
    # Impresora del grupo (segundo nivel de la cascada).
    impresora_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("impresoras.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=sa_true())


class PedidoCliente(Base):
    """Pedido hecho por el cliente desde la app de cliente (autoservicio o mesa).

    Es un pedido PREVIO a la venta: existe mientras espera atencion.
      - autoservicio: el cliente ordena con su nombre; llega a caja como comanda
        pendiente de pago; paga en caja al recoger.
      - mesa: el cliente ordena desde la mesa; queda pendiente hasta que un mesero
        lo acepte (se convierte en comanda/venta) o lo rechace.

    Estados:
      pendiente  -> recien creado, esperando (caja o mesero)
      aceptado   -> el mesero lo acepto (mesa) y se genero la venta
      rechazado  -> el mesero lo rechazo (mesa)
      entregado  -> autoservicio pagado/entregado en caja
      cancelado  -> anulado
    """
    __tablename__ = "pedidos_cliente"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    # tipo: 'autoservicio' o 'mesa'
    tipo: Mapped[str] = mapped_column(String(15), default="autoservicio")
    # nombre que el cliente escribe (autoservicio) o referencia
    nombre_cliente: Mapped[str] = mapped_column(String(80), default="")
    # mesa asociada (solo pedidos de tipo mesa)
    mesa_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("mesas.id"), nullable=True)
    estado: Mapped[str] = mapped_column(String(15), default="pendiente")
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    atendido: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # venta generada al aceptar (mesa) o cobrar (autoservicio)
    venta_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ventas.id"), nullable=True)
    # motivo si se rechaza
    motivo_rechazo: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    lineas: Mapped[list["PedidoClienteLinea"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan")


class PedidoClienteLinea(Base):
    """Linea de un pedido de cliente (producto + cantidad)."""
    __tablename__ = "pedidos_cliente_lineas"
    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(
        ForeignKey("pedidos_cliente.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id"), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    nota: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    pedido: Mapped["PedidoCliente"] = relationship(back_populates="lineas")
    producto: Mapped["Producto"] = relationship()


class Categoria(Base):
    __tablename__ = "categorias"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)

class Producto(Base):
    __tablename__ = "productos"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    categoria_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categorias.id"), nullable=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(20), default="venta") # venta, insumo, elaborado
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    costo: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    existencias: Mapped[Decimal] = mapped_column(Numeric(14,3), default=0)
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(14,3), default=0)
    # Tarifa de IVA del producto (Colombia: 0, 5 o 19). Es el valor por defecto
    # al comprar o vender; puede ajustarse en cada factura.
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # --- Impresion (Paso 21) ---
    # Grupo de impresion del producto (segundo nivel de la cascada).
    grupo_impresion_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("grupos_impresion.id"), nullable=True)
    # Impresora especifica del producto (primer nivel; sobrescribe al grupo).
    impresora_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("impresoras.id"), nullable=True)

class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    documento: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    cupo_credito: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    saldo_cartera: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

class AbonoCartera(Base):
    __tablename__ = "abonos_cartera"
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    valor: Mapped[Decimal] = mapped_column(Numeric(14,2))
    medio_pago: Mapped[str] = mapped_column(String(40), default="efectivo")
    observacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)

class Venta(Base):
    __tablename__ = "ventas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    mesa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mesas.id"), nullable=True)
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="abierta")
    total: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medio_pago: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    propina: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    impuesto: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    empleado_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    numero_factura: Mapped[Optional[str]] = mapped_column(String(40), unique=True, nullable=True)
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    canal: Mapped[str] = mapped_column(String(20), default="mesa")
    cargo_envio: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    detalles: Mapped[list["DetalleVenta"]] = relationship(back_populates="venta", cascade="all, delete-orphan")

    # Relaciones de solo lectura usadas por la capa de API.
    # `routes.py` accedia a venta.usuario / venta.cliente / venta.mesa sin que
    # estuvieran declaradas -> AttributeError al listar ventas.
    usuario: Mapped[Optional["Usuario"]] = relationship(lazy="selectin")
    cliente: Mapped[Optional["Cliente"]] = relationship(lazy="selectin")
    mesa: Mapped[Optional["Mesa"]] = relationship(lazy="selectin")

    # --- Alias de compatibilidad con VentaResponse ---
    # El esquema de la API usa nombres que el modelo no tiene. Se exponen
    # como propiedades derivadas para no requerir migracion de esquema.
    # Mapeo: canal -> tipo_venta, observacion -> observaciones,
    #        fecha -> fecha_creacion, zona via mesa.
    _CANAL_A_TIPO = {
        "mesa": "en_mesa",
        "en_mesa": "en_mesa",
        "llevar": "para_llevar",
        "para_llevar": "para_llevar",
        "domicilio": "domicilio",
        "mostrador": "mostrador",
    }

    @property
    def tipo_venta(self) -> str:
        return self._CANAL_A_TIPO.get(self.canal, "mostrador")

    @property
    def zona_id(self) -> Optional[int]:
        mesa = getattr(self, "mesa", None)
        return getattr(mesa, "zona_id", None) if mesa else None

    @property
    def observaciones(self) -> Optional[str]:
        return self.observacion

    @property
    def referencia_externa(self) -> Optional[str]:
        return self.numero_factura

    @property
    def fecha_creacion(self) -> datetime:
        return self.fecha

class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"
    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12,3))
    precio: Mapped[Decimal] = mapped_column(Numeric(14,2))
    nota: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    estado_cocina: Mapped[str] = mapped_column(String(20), default="pendiente")
    # Marca si esta linea ya fue enviada a impresion (comandada). Permite la
    # impresion incremental: al comandar, solo se imprimen las lineas nuevas
    # (comandado=False) y luego se marcan como comandadas.
    comandado: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_false())
    comandado_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    venta: Mapped[Venta] = relationship(back_populates="detalles")

    # --- Alias de compatibilidad con DetalleVentaResponse ---
    # El esquema de la API espera `subtotal` y `observaciones`; el modelo
    # almacena `nota` y calcula el subtotal. Sin estas propiedades la API
    # fallaba con ResponseValidationError.
    @property
    def subtotal(self) -> Decimal:
        return (self.cantidad or Decimal("0")) * (self.precio or Decimal("0"))

    @property
    def observaciones(self) -> Optional[str]:
        return self.nota

class MovimientoInventario(Base):
    """Movimiento de inventario. Es la fuente de verdad del kardex.

    Se agregaron los saldos y costos resultantes para poder reconstruir el
    kardex sin recalcular toda la historia en cada consulta, y para que el
    valor del inventario sea auditable hacia atras.
    """
    __tablename__ = "movimientos_inventario"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia, index=True)
    tipo: Mapped[str] = mapped_column(String(25))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14,3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    referencia: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # --- Kardex ---
    bodega_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bodegas.id"), nullable=True)
    lote_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lotes.id"), nullable=True)
    saldo_anterior: Mapped[Decimal] = mapped_column(Numeric(14,3), default=0)
    saldo_posterior: Mapped[Decimal] = mapped_column(Numeric(14,3), default=0)
    costo_promedio_anterior: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    costo_promedio_posterior: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    observacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)

class Receta(Base):
    """Formula para producir o vender un producto.

    tipo_receta: "produccion" genera un producto elaborado; "venta" descuenta
    insumos al vender un producto terminado.
    """
    __tablename__ = "recetas"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), unique=True)
    rendimiento: Mapped[Decimal] = mapped_column(Numeric(12,3), default=1)
    instrucciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo_receta: Mapped[str] = mapped_column(String(20), default="produccion")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    detalles: Mapped[list["RecetaDetalle"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin")
    producto: Mapped["Producto"] = relationship(lazy="selectin")

class RecetaDetalle(Base):
    """Insumo o subproducto de una receta.

    rol = "insumo": se consume (resta inventario, suma al costo).
    rol = "aprovechable": es un subproducto que la produccion GENERA
          (ej: huesos al despresar). Ingresa al inventario y su valor se
          DESCUENTA del costo del producto principal, abaratandolo.
    """
    __tablename__ = "receta_detalles"
    id: Mapped[int] = mapped_column(primary_key=True)
    receta_id: Mapped[int] = mapped_column(ForeignKey("recetas.id"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12,3))
    merma_porcentaje: Mapped[Decimal] = mapped_column(Numeric(7,4), default=0)
    rol: Mapped[str] = mapped_column(String(15), default="insumo")
    # Valor unitario del aprovechable (para descontarlo del costo principal)
    valor_aprovechable: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    insumo: Mapped["Producto"] = relationship(lazy="selectin")

class OrdenProduccion(Base):
    """Ejecucion de una receta.

    Antes no tenia estado, usuario ni empresa, y su ejecucion no pasaba por
    el kardex. Ahora es rastreable y anulable.
    """
    __tablename__ = "ordenes_produccion"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    receta_id: Mapped[int] = mapped_column(ForeignKey("recetas.id"))
    numero: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    lotes: Mapped[Decimal] = mapped_column(Numeric(12,3))
    unidades_producidas: Mapped[Decimal] = mapped_column(Numeric(12,3))
    costo_insumos: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    valor_aprovechables: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    costo_total: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    merma_valor: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    # borrador | confirmada | anulada
    estado: Mapped[str] = mapped_column(String(20), default="confirmada")
    bodega_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bodegas.id"), nullable=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    fecha_anulacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    receta: Mapped["Receta"] = relationship(lazy="selectin")


class ConsumoProduccion(Base):
    """Registro de cada insumo consumido o aprovechable generado.

    Da trazabilidad completa: que ordenes consumieron cada insumo y cuanta
    merma real hubo, algo imposible antes porque no se guardaba el detalle.
    """
    __tablename__ = "consumos_produccion"
    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("ordenes_produccion.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    rol: Mapped[str] = mapped_column(String(15), default="insumo")  # insumo | aprovechable | merma
    cantidad_base: Mapped[Decimal] = mapped_column(Numeric(14,3), default=0)
    cantidad_merma: Mapped[Decimal] = mapped_column(Numeric(14,3), default=0)
    cantidad_total: Mapped[Decimal] = mapped_column(Numeric(14,3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    costo_total: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

class SesionCaja(Base):
    __tablename__ = "sesiones_caja"
    id: Mapped[int] = mapped_column(primary_key=True)
    apertura: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    cierre: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    base_inicial: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    efectivo_declarado: Mapped[Optional[Decimal]] = mapped_column(Numeric(14,2), nullable=True)
    observacion_cierre: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class Domicilio(Base):
    __tablename__ = "domicilios"
    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"), unique=True)
    direccion: Mapped[str] = mapped_column(String(220))
    barrio: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contacto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    repartidor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    estado: Mapped[str] = mapped_column(String(25), default="recibido")

class Gasto(Base):
    __tablename__ = "gastos"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    concepto: Mapped[str] = mapped_column(String(150))
    categoria: Mapped[str] = mapped_column(String(80))
    valor: Mapped[Decimal] = mapped_column(Numeric(14,2))
    proveedor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

class Empleado(Base):
    __tablename__ = "empleados"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    documento: Mapped[str] = mapped_column(String(40), unique=True)
    cargo: Mapped[str] = mapped_column(String(80))
    salario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    tipo_documento: Mapped[str] = mapped_column(String(10), default="CC")
    fecha_ingreso: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tipo_contrato: Mapped[str] = mapped_column(String(30), default="indefinido")
    eps: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pension: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    arl: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # --- Datos de nomina ---
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    # ordinario | integral
    tipo_salario: Mapped[str] = mapped_column(String(15), default="ordinario")
    caja_compensacion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nivel_riesgo_arl: Mapped[int] = mapped_column(Integer, default=1)  # I..V
    auxilio_transporte: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_retiro: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cuenta_bancaria: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    banco: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # --- Foto y estructura para reconocimiento facial (Paso 20) ---
    # La foto se guarda como ruta a un archivo en disco (no en la BD).
    foto: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Vector/codificacion facial para futuro motor de reconocimiento. Se deja
    # el campo listo; el motor de comparacion no se implementa aqui (requiere
    # libreria de vision y hardware de camara). Guardado como JSON/base64.
    codificacion_facial: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Consentimiento del empleado para tratar su dato biometrico (Ley 1581 de
    # 2012, habeas data). Sin consentimiento no se debe capturar el rostro.
    consentimiento_biometrico: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_consentimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

class ParametrosNomina(Base):
    """Parametros legales de nomina, versionados por fecha de vigencia.

    TODO es configurable para adaptarse a cambios de ley sin tocar codigo.
    Los valores por defecto corresponden a Colombia 2026. Al cambiar la ley,
    se crea un registro nuevo con otra vigencia_desde; el calculo usa el
    vigente en la fecha del periodo.
    """
    __tablename__ = "parametros_nomina"
    id: Mapped[int] = mapped_column(primary_key=True)
    vigencia_desde: Mapped[date] = mapped_column(Date, default=date.today)
    salario_minimo: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    auxilio_transporte: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    # El auxilio se paga si el salario es <= este tope (2 SMMLV por defecto)
    tope_auxilio_transporte: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    # --- Aportes del empleado (deducciones) ---
    salud_empleado_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=4)
    pension_empleado_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=4)
    fsp_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=1)  # fondo solidaridad
    fsp_smmlv_desde: Mapped[Decimal] = mapped_column(Numeric(7,2), default=4)  # aplica desde 4 SMMLV

    # --- Aportes del empleador ---
    salud_empleador_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default="8.5")
    pension_empleador_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=12)
    arl_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default="0.522")  # riesgo I
    caja_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=4)
    icbf_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=3)
    sena_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=2)
    # Exoneracion Ley 1607: empleados que ganan < 10 SMMLV no causan
    # salud-empleador, ICBF ni SENA (para personas juridicas).
    exoneracion_smmlv: Mapped[Decimal] = mapped_column(Numeric(7,2), default=10)

    # --- Recargos y horas extra (factores sobre el valor hora ordinaria) ---
    recargo_nocturno_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=35)
    hora_extra_diurna_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=25)
    hora_extra_nocturna_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=75)
    recargo_dominical_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=75)
    hora_extra_diurna_dominical_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=100)
    hora_extra_nocturna_dominical_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=150)
    horas_mensuales: Mapped[Decimal] = mapped_column(Numeric(7,2), default=230)  # jornada legal

    # --- Provisiones de prestaciones (porcentaje sobre base) ---
    prima_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default="8.33")
    cesantias_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default="8.33")
    intereses_cesantias_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=12)  # anual sobre cesantias
    vacaciones_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default="4.17")

    # --- Salario integral ---
    factor_integral_prestacional: Mapped[Decimal] = mapped_column(Numeric(7,4), default=30)  # 30% factor
    integral_min_smmlv: Mapped[Decimal] = mapped_column(Numeric(7,2), default=13)  # 13 SMMLV minimo

    @property
    def base_salud_pension_pct(self) -> Decimal:
        return self.salud_empleado_pct + self.pension_empleado_pct

class PeriodoNomina(Base):
    __tablename__ = "periodos_nomina"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    periodicidad: Mapped[str] = mapped_column(String(20), default="mensual")
    # borrador | liquidado | cerrado | anulado
    estado: Mapped[str] = mapped_column(String(20), default="borrador")
    total_devengado: Mapped[Decimal] = mapped_column(Numeric(16,2), default=0)
    total_deducido: Mapped[Decimal] = mapped_column(Numeric(16,2), default=0)
    total_neto: Mapped[Decimal] = mapped_column(Numeric(16,2), default=0)
    total_aportes_empleador: Mapped[Decimal] = mapped_column(Numeric(16,2), default=0)

class LiquidacionNomina(Base):
    """Desprendible de un empleado en un periodo, con desglose completo.

    Antes solo tenia salario_base, devengados, deducciones y neto: no separaba
    horas extra, recargos, provisiones ni aportes patronales, por lo que era
    imposible cumplir la legislacion o generar un desprendible legal.
    """
    __tablename__ = "liquidaciones_nomina"
    id: Mapped[int] = mapped_column(primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos_nomina.id"))
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    dias_liquidados: Mapped[Decimal] = mapped_column(Numeric(7,2), default=30)
    tipo_salario: Mapped[str] = mapped_column(String(15), default="ordinario")
    salario_base: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    # --- Devengados ---
    sueldo: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    auxilio_transporte: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    horas_extra: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    recargos: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    comisiones: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    bonificaciones: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    otros_devengados: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    devengados: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    # --- Deducciones ---
    salud_empleado: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    pension_empleado: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    fondo_solidaridad: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    retencion_fuente: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    otras_deducciones: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    deducciones: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    neto: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    # --- Base para aportes y provisiones (salario + variables constitutivas) ---
    ibc: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)  # ingreso base cotizacion

    # --- Aportes del empleador (no se descuentan al empleado) ---
    salud_empleador: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    pension_empleador: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    arl_empleador: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    caja_empleador: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    icbf_empleador: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    sena_empleador: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    total_aportes_empleador: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    # --- Provisiones de prestaciones ---
    prov_prima: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    prov_cesantias: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    prov_intereses_cesantias: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    prov_vacaciones: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    total_provisiones: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    estado_electronico: Mapped[str] = mapped_column(String(25), default="pendiente")
    consecutivo_electronico: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    cune: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    empleado: Mapped["Empleado"] = relationship(lazy="selectin")

    @property
    def costo_total_empleador(self) -> Decimal:
        """Lo que le cuesta el empleado a la empresa: neto + aportes + provisiones."""
        return ((self.devengados or Decimal("0"))
                + (self.total_aportes_empleador or Decimal("0"))
                + (self.total_provisiones or Decimal("0")))


class NovedadNomina(Base):
    """Novedad de un empleado en un periodo: horas extra, recargos,
    incapacidades, licencias, bonificaciones, comisiones, prestamos, etc.

    Antes no existia: no habia forma de registrar nada mas alla del salario fijo.
    """
    __tablename__ = "novedades_nomina"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    periodo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("periodos_nomina.id"), nullable=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    # Tipos: he_diurna, he_nocturna, he_dominical_diurna, he_dominical_nocturna,
    #        recargo_nocturno, recargo_dominical, incapacidad_eg, incapacidad_at,
    #        licencia_mp, licencia_no_remunerada, bonificacion, comision,
    #        prestamo, embargo, otro_devengado, otra_deduccion
    tipo: Mapped[str] = mapped_column(String(35))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)  # horas o dias
    valor: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)  # para montos fijos
    constitutivo_salario: Mapped[bool] = mapped_column(Boolean, default=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    aplicada: Mapped[bool] = mapped_column(Boolean, default=False)
    empleado: Mapped["Empleado"] = relationship(lazy="selectin")

class Proveedor(Base):
    __tablename__ = "proveedores"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    tipo_documento: Mapped[str] = mapped_column(String(10), default="NIT")
    documento: Mapped[str] = mapped_column(String(40))
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    obligado_facturar: Mapped[bool] = mapped_column(Boolean, default=True)

    # Datos comerciales: antes el proveedor solo tenia nombre, documento,
    # telefono y correo, insuficiente para gestionar aprovisionamiento.
    direccion: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contacto: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    dias_credito: Mapped[int] = mapped_column(Integer, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    observaciones: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)

class Compra(Base):
    __tablename__ = "compras"
    id: Mapped[int] = mapped_column(primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"))
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    concepto: Mapped[str] = mapped_column(String(200))
    valor: Mapped[Decimal] = mapped_column(Numeric(14,2))
    numero_documento: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    es_documento_soporte: Mapped[bool] = mapped_column(Boolean, default=False)
    estado_electronico: Mapped[str] = mapped_column(String(30), default="no_aplica")
    cuds: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    # --- Campos heredados: una compra admitia UN solo producto. Se conservan
    # por compatibilidad con datos existentes, pero el detalle real vive en
    # DetalleCompra. No usar en codigo nuevo.
    producto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("productos.id"), nullable=True)
    cantidad: Mapped[Optional[Decimal]] = mapped_column(Numeric(14,3), nullable=True)
    costo_unitario: Mapped[Optional[Decimal]] = mapped_column(Numeric(14,2), nullable=True)

    # --- Cabecera fiscal y de control ---
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    orden_compra_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ordenes_compra.id"), nullable=True)
    bodega_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bodegas.id"), nullable=True)

    # borrador | confirmada | anulada
    estado: Mapped[str] = mapped_column(String(20), default="borrador")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    iva: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    retencion_fuente: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    retencion_iva: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)

    forma_pago: Mapped[str] = mapped_column(String(20), default="contado")  # contado | credito
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    fecha_anulacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    detalles: Mapped[list["DetalleCompra"]] = relationship(
        back_populates="compra", cascade="all, delete-orphan")
    proveedor: Mapped["Proveedor"] = relationship(lazy="selectin")


class DetalleCompra(Base):
    """Linea de una factura de compra.

    Antes no existia: la tabla `compras` tenia `producto_id`, `cantidad` y
    `costo_unitario` en singular, de modo que una factura de 10 articulos
    exigia 10 filas independientes sin nada que las agrupara.
    """
    __tablename__ = "detalle_compras"
    id: Mapped[int] = mapped_column(primary_key=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compras.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14,3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2))
    descuento_porcentaje: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0)
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0)
    lote_codigo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    compra: Mapped["Compra"] = relationship(back_populates="detalles")

    @property
    def subtotal_bruto(self) -> Decimal:
        return (self.cantidad or Decimal("0")) * (self.costo_unitario or Decimal("0"))

    @property
    def valor_descuento(self) -> Decimal:
        return (self.subtotal_bruto * (self.descuento_porcentaje or Decimal("0")) / Decimal("100"))

    @property
    def subtotal(self) -> Decimal:
        return self.subtotal_bruto - self.valor_descuento

    @property
    def valor_iva(self) -> Decimal:
        return (self.subtotal * (self.iva_porcentaje or Decimal("0")) / Decimal("100"))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.valor_iva

class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    usuario: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(30), default="mesero")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # --- Permisos de acceso por canal (Paso 20) ---
    # Determinan a donde puede entrar este usuario. Un empleado puede tener
    # usuario solo para marcar entrada/salida y no acceder a ningun sistema:
    # en ese caso ambos van en False.
    acceso_web: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=sa_true())
    acceso_app_pedidos: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_false())
    
    def verificar_password(self, password: str) -> bool:
        """Verifica si la contraseña coincide con el hash"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.password_hash)


class RegistroAuditoria(Base):
    """Registro de auditoria: quien hizo que, cuando, desde donde.

    Guarda cada accion relevante del sistema (cambios de datos, accesos y
    accesos denegados) con el contexto que exige una auditoria seria: usuario,
    fecha/hora (local), IP, accion, modulo, registro afectado y el estado antes
    y despues del cambio.

    Es un registro append-only: no se edita ni se borra desde la aplicacion.
    """
    __tablename__ = "registros_auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)

    # Quien
    usuario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True)
    usuario_nombre: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    rol: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4/IPv6

    # Que
    # acceso | acceso_denegado | crear | editar | anular | eliminar | otro
    accion: Mapped[str] = mapped_column(String(20))
    modulo: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    entidad: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    entidad_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Antes / despues (JSON serializado; nunca datos sensibles como contrasenas)
    valor_anterior: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_nuevo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resultado: exito | error
    resultado: Mapped[str] = mapped_column(String(10), default="exito")


class Comanda(Base):
    __tablename__ = "comandas"
    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente, preparando, lista, entregada
    prioridad: Mapped[str] = mapped_column(String(15), default="normal")  # normal, alta, urgente
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    fecha_entrega: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mesa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mesas.id"), nullable=True)

class Turno(Base):
    """Marcacion de asistencia de un empleado: entrada y salida reales.

    Antes solo tenia entrada y salida (con utcnow, que en Colombia corre las
    horas 5h). Ahora registra las horas trabajadas ya desglosadas (ordinarias,
    nocturnas, dominicales/festivas y extra) para poder alimentar la nomina.
    Las horas se calculan al cerrar el turno.
    """
    __tablename__ = "turnos"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    entrada: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    salida: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Turno programado (opcional): permite medir tardanzas y ausencias.
    programado_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("turnos_programados.id"), nullable=True)

    # Horas calculadas al cerrar (desglosadas para la nomina).
    horas_trabajadas: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    horas_ordinarias: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    horas_nocturnas: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    horas_dominicales: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    horas_extra_diurna: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    horas_extra_nocturna: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)

    minutos_tardanza: Mapped[int] = mapped_column(Integer, default=0)
    horas_receso: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    # abierto | en_receso | cerrado | anulado
    estado: Mapped[str] = mapped_column(String(15), default="abierto")
    notas: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    # Novedad de nomina generada por las horas extra de este turno (si hubo).
    novedad_generada_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("novedades_nomina.id"), nullable=True)

    empleado: Mapped["Empleado"] = relationship(lazy="selectin")
    marcaciones: Mapped[list["Marcacion"]] = relationship(
        back_populates="turno", cascade="all, delete-orphan", lazy="selectin")


class TurnoProgramado(Base):
    """Horario planeado de un empleado para un dia: la hora a la que se espera
    que entre y salga. Sirve para medir tardanzas y ausencias.
    """
    __tablename__ = "turnos_programados"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    fecha: Mapped[date] = mapped_column(Date)
    hora_entrada: Mapped[time] = mapped_column(Time)
    hora_salida: Mapped[time] = mapped_column(Time)
    # Tolerancia en minutos antes de contar tardanza.
    tolerancia_min: Mapped[int] = mapped_column(Integer, default=5)
    estado: Mapped[str] = mapped_column(String(15), default="programado")
    empleado: Mapped["Empleado"] = relationship(lazy="selectin")

class Marcacion(Base):
    """Cada evento de marcacion dentro de un turno.

    Un turno se compone de varias marcaciones: la entrada, las salidas y
    regresos de receso, y la salida final. El tiempo entre 'salida_receso' y
    'regreso_receso' NO cuenta como trabajado y se descuenta del total.
    """
    __tablename__ = "marcaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    turno_id: Mapped[int] = mapped_column(ForeignKey("turnos.id"))
    # entrada | salida_receso | regreso_receso | salida
    tipo: Mapped[str] = mapped_column(String(20))
    momento: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    origen: Mapped[str] = mapped_column(String(20), default="manual")
    turno: Mapped["Turno"] = relationship(back_populates="marcaciones")

class PagoVenta(Base):
    """Pago aplicado a una venta.

    Antes el pago no se persistia: solo se marcaba la venta como cerrada y se
    guardaba el medio de pago. No quedaba registro del monto recibido ni del
    cambio, lo que hacia imposible cuadrar la caja o soportar pagos mixtos.
    """
    __tablename__ = "pagos_venta"
    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"))
    tipo_pago: Mapped[str] = mapped_column(String(30))
    monto_recibido: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    monto_aplicado: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cambio: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    referencia: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class AlertaStock(Base):
    """Alerta por existencias en negativo o bajo minimo."""
    __tablename__ = "alertas_stock"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    tipo: Mapped[str] = mapped_column(String(30))  # negativo | bajo_minimo
    existencia_resultante: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    cantidad_solicitada: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    referencia: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    atendida: Mapped[bool] = mapped_column(Boolean, default=False)

# ============================================================================
# INVENTARIO: bodegas, lotes y existencias por ubicacion
# ============================================================================

class Bodega(Base):
    """Almacen o punto de existencias.

    Antes el stock vivia en un unico campo `Producto.existencias`, sin
    posibilidad de separar cocina, barra o bodega principal.
    """
    __tablename__ = "bodegas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    ubicacion: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Lote(Base):
    """Lote de un producto con su fecha de vencimiento.

    Imprescindible en alimentos: permite trazabilidad y control de caducidad.
    """
    __tablename__ = "lotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id"))
    codigo: Mapped[str] = mapped_column(String(60))
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_ingreso: Mapped[date] = mapped_column(Date, default=date.today)
    cantidad_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    cantidad_disponible: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def vencido(self) -> bool:
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < date.today())

    def dias_para_vencer(self) -> Optional[int]:
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - date.today()).days


class ExistenciaBodega(Base):
    """Existencia de un producto en una bodega concreta.

    `Producto.existencias` se conserva como total consolidado para no romper
    el codigo actual; esta tabla es el detalle por ubicacion.
    """
    __tablename__ = "existencias_bodega"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)


# ============================================================================
# APROVISIONAMIENTO: solicitudes, cotizaciones, ordenes y recepciones
# ============================================================================

class SolicitudCompra(Base):
    """Necesidad de compra detectada por un area o por stock bajo minimo."""
    __tablename__ = "solicitudes_compra"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    numero: Mapped[str] = mapped_column(String(30), unique=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    solicitante_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    justificacion: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    # pendiente | aprobada | rechazada | cotizada | ordenada | cancelada
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    aprobada_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    fecha_aprobacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    motivo_rechazo: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    detalles: Mapped[list["DetalleSolicitud"]] = relationship(
        back_populates="solicitud", cascade="all, delete-orphan")


class DetalleSolicitud(Base):
    __tablename__ = "detalle_solicitudes"
    id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes_compra.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14,3))
    observacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    solicitud: Mapped["SolicitudCompra"] = relationship(back_populates="detalles")


class Cotizacion(Base):
    """Oferta de un proveedor para una solicitud.

    Varias cotizaciones sobre la misma solicitud permiten comparar precios,
    plazos y condiciones antes de emitir la orden.
    """
    __tablename__ = "cotizaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    solicitud_id: Mapped[Optional[int]] = mapped_column(ForeignKey("solicitudes_compra.id"), nullable=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"))
    numero: Mapped[str] = mapped_column(String(30))
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    validez_dias: Mapped[int] = mapped_column(Integer, default=15)
    dias_entrega: Mapped[int] = mapped_column(Integer, default=0)
    forma_pago: Mapped[str] = mapped_column(String(20), default="contado")
    # recibida | seleccionada | descartada
    estado: Mapped[str] = mapped_column(String(20), default="recibida")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    iva: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    observaciones: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    detalles: Mapped[list["DetalleCotizacion"]] = relationship(
        back_populates="cotizacion", cascade="all, delete-orphan")
    proveedor: Mapped["Proveedor"] = relationship(lazy="selectin")


class DetalleCotizacion(Base):
    __tablename__ = "detalle_cotizaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    cotizacion_id: Mapped[int] = mapped_column(ForeignKey("cotizaciones.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14,3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2))
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0)
    cotizacion: Mapped["Cotizacion"] = relationship(back_populates="detalles")


class OrdenCompra(Base):
    """Compromiso formal de compra con un proveedor.

    Permite recepciones parciales: cada DetalleOrden lleva la cantidad pedida
    y la recibida acumulada.
    """
    __tablename__ = "ordenes_compra"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    numero: Mapped[str] = mapped_column(String(30), unique=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"))
    cotizacion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cotizaciones.id"), nullable=True)
    solicitud_id: Mapped[Optional[int]] = mapped_column(ForeignKey("solicitudes_compra.id"), nullable=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    fecha_entrega_esperada: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # borrador | emitida | parcial | recibida | cerrada | anulada
    estado: Mapped[str] = mapped_column(String(20), default="borrador")
    forma_pago: Mapped[str] = mapped_column(String(20), default="contado")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    iva: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    detalles: Mapped[list["DetalleOrden"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan")
    proveedor: Mapped["Proveedor"] = relationship(lazy="selectin")

    @property
    def porcentaje_recibido(self) -> Decimal:
        pedido = sum((d.cantidad or Decimal("0") for d in self.detalles), Decimal("0"))
        if pedido <= 0:
            return Decimal("0")
        recibido = sum((d.cantidad_recibida or Decimal("0") for d in self.detalles), Decimal("0"))
        return (recibido / pedido * Decimal("100")).quantize(Decimal("0.01"))


class DetalleOrden(Base):
    __tablename__ = "detalle_ordenes"
    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("ordenes_compra.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14,3))
    cantidad_recibida: Mapped[Decimal] = mapped_column(Numeric(14,3), default=0)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2))
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0)
    orden: Mapped["OrdenCompra"] = relationship(back_populates="detalles")

    @property
    def pendiente(self) -> Decimal:
        return (self.cantidad or Decimal("0")) - (self.cantidad_recibida or Decimal("0"))


class Recepcion(Base):
    """Entrada fisica de mercancia contra una orden de compra."""
    __tablename__ = "recepciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    numero: Mapped[str] = mapped_column(String(30), unique=True)
    orden_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ordenes_compra.id"), nullable=True)
    compra_id: Mapped[Optional[int]] = mapped_column(ForeignKey("compras.id"), nullable=True)
    bodega_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bodegas.id"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=hora_colombia)
    remision: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    detalles: Mapped[list["DetalleRecepcion"]] = relationship(
        back_populates="recepcion", cascade="all, delete-orphan")


class DetalleRecepcion(Base):
    __tablename__ = "detalle_recepciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    recepcion_id: Mapped[int] = mapped_column(ForeignKey("recepciones.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14,3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    lote_codigo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    recepcion: Mapped["Recepcion"] = relationship(back_populates="detalles")
