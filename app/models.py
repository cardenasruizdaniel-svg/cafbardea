from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, Numeric, DateTime, Date, ForeignKey, Boolean, Text, JSON, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
import uuid

class Empresa(Base):
    __tablename__ = "empresas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    nit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    color_primario: Mapped[str] = mapped_column(String(7), default="#b45309")
    color_secundario: Mapped[str] = mapped_column(String(7), default="#fef3c7")
    moneda: Mapped[str] = mapped_column(String(5), default="COP")
    direccion: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    prefijo_factura: Mapped[str] = mapped_column(String(12), default="POS")
    consecutivo_factura: Mapped[int] = mapped_column(Integer, default=1)
    impuesto_porcentaje: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0)
    tipo_persona: Mapped[str] = mapped_column(String(20), default="juridica")
    tipo_sociedad: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    regimen_tributario: Mapped[str] = mapped_column(String(30), default="ordinario")
    facturador_electronico: Mapped[bool] = mapped_column(Boolean, default=False)
    proveedor_tecnologico: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    modo_electronico: Mapped[str] = mapped_column(String(15), default="pruebas")
    prefijo_nomina: Mapped[str] = mapped_column(String(12), default="NE")
    consecutivo_nomina: Mapped[int] = mapped_column(Integer, default=1)
    software_nomina_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

class Zona(Base):
    __tablename__ = "zonas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    nombre: Mapped[str] = mapped_column(String(80))
    orden: Mapped[int] = mapped_column(Integer, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    mesas: Mapped[list["Mesa"]] = relationship(back_populates="zona")

class Mesa(Base):
    __tablename__ = "mesas"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    zona_id: Mapped[int] = mapped_column(ForeignKey("zonas.id"))
    nombre: Mapped[str] = mapped_column(String(40))
    capacidad: Mapped[int] = mapped_column(Integer, default=4)
    posicion_x: Mapped[int] = mapped_column(Integer, default=0)
    posicion_y: Mapped[int] = mapped_column(Integer, default=0)
    forma: Mapped[str] = mapped_column(String(15), default="redonda")
    estado: Mapped[str] = mapped_column(String(20), default="libre")
    zona: Mapped[Zona] = relationship(back_populates="mesas")

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
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

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
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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

class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"
    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12,3))
    precio: Mapped[Decimal] = mapped_column(Numeric(14,2))
    nota: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    estado_cocina: Mapped[str] = mapped_column(String(20), default="pendiente")
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    venta: Mapped[Venta] = relationship(back_populates="detalles")

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tipo: Mapped[str] = mapped_column(String(25))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14,3))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    referencia: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

class Receta(Base):
    __tablename__ = "recetas"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), unique=True)
    rendimiento: Mapped[Decimal] = mapped_column(Numeric(12,3), default=1)
    instrucciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo_receta: Mapped[str] = mapped_column(String(20), default="produccion")
    detalles: Mapped[list["RecetaDetalle"]] = relationship(cascade="all, delete-orphan")

class RecetaDetalle(Base):
    __tablename__ = "receta_detalles"
    id: Mapped[int] = mapped_column(primary_key=True)
    receta_id: Mapped[int] = mapped_column(ForeignKey("recetas.id"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12,3))
    merma_porcentaje: Mapped[Decimal] = mapped_column(Numeric(7,4), default=0)

class OrdenProduccion(Base):
    __tablename__ = "ordenes_produccion"
    id: Mapped[int] = mapped_column(primary_key=True)
    receta_id: Mapped[int] = mapped_column(ForeignKey("recetas.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    lotes: Mapped[Decimal] = mapped_column(Numeric(12,3))
    unidades_producidas: Mapped[Decimal] = mapped_column(Numeric(12,3))
    costo_total: Mapped[Decimal] = mapped_column(Numeric(14,2))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2))

class SesionCaja(Base):
    __tablename__ = "sesiones_caja"
    id: Mapped[int] = mapped_column(primary_key=True)
    apertura: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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

class ParametrosNomina(Base):
    __tablename__ = "parametros_nomina"
    id: Mapped[int] = mapped_column(primary_key=True)
    vigencia_desde: Mapped[date] = mapped_column(Date, default=date.today)
    salario_minimo: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    auxilio_transporte: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    tope_auxilio_transporte: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    salud_empleado_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=0)
    pension_empleado_pct: Mapped[Decimal] = mapped_column(Numeric(7,4), default=0)

class PeriodoNomina(Base):
    __tablename__ = "periodos_nomina"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    periodicidad: Mapped[str] = mapped_column(String(20), default="mensual")
    estado: Mapped[str] = mapped_column(String(20), default="borrador")

class LiquidacionNomina(Base):
    __tablename__ = "liquidaciones_nomina"
    id: Mapped[int] = mapped_column(primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos_nomina.id"))
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    dias_liquidados: Mapped[Decimal] = mapped_column(Numeric(7,2), default=30)
    salario_base: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    devengados: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    deducciones: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    neto: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    estado_electronico: Mapped[str] = mapped_column(String(25), default="pendiente_configuracion")
    consecutivo_electronico: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    cune: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

class Proveedor(Base):
    __tablename__ = "proveedores"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    tipo_documento: Mapped[str] = mapped_column(String(10), default="NIT")
    documento: Mapped[str] = mapped_column(String(40))
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    obligado_facturar: Mapped[bool] = mapped_column(Boolean, default=True)

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
    producto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("productos.id"), nullable=True)
    cantidad: Mapped[Optional[Decimal]] = mapped_column(Numeric(14,3), nullable=True)
    costo_unitario: Mapped[Optional[Decimal]] = mapped_column(Numeric(14,2), nullable=True)

class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), default=1)
    usuario: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(30), default="mesero")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    
    def verificar_password(self, password: str) -> bool:
        """Verifica si la contraseña coincide con el hash"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.password_hash)

class Comanda(Base):
    __tablename__ = "comandas"
    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente, preparando, lista, entregada
    prioridad: Mapped[str] = mapped_column(String(15), default="normal")  # normal, alta, urgente
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_entrega: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mesa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mesas.id"), nullable=True)

class Turno(Base):
    __tablename__ = "turnos"
    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    entrada: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    salida: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
