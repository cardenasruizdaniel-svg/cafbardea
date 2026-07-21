"""
Schemas Pydantic para el módulo de Ventas - FASE 1 POS Premium
Define validaciones y estructuras de datos para punto de venta
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum
from decimal import Decimal


class EstadoVenta(str, Enum):
    """Estados posibles de una venta"""
    ABIERTA = "abierta"
    CERRADA = "cerrada"
    SUSPENDIDA = "suspendida"
    CANCELADA = "cancelada"
    FACTURADA = "facturada"


class TipoPago(str, Enum):
    """Medios de pago soportados"""
    EFECTIVO = "efectivo"
    TARJETA_CREDITO = "tarjeta_credito"
    TARJETA_DEBITO = "tarjeta_debito"
    TRANSFERENCIA = "transferencia"
    BILLETERA_DIGITAL = "billetera_digital"
    CHEQUE = "cheque"


class TipoVenta(str, Enum):
    """Tipos de venta"""
    EN_MESA = "en_mesa"
    PARA_LLEVAR = "para_llevar"
    DOMICILIO = "domicilio"
    MOSTRADOR = "mostrador"


# ============================================================================
# SCHEMAS DE ENTRADA (Input)
# ============================================================================

class DetalleVentaCreate(BaseModel):
    """Crear detalle de venta (item individual)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "producto_id": 1,
            "cantidad": "2.00",
            "precio": "8500.00",
            "observaciones": "Sin azúcar"
        }
    })
    
    producto_id: int = Field(..., gt=0, description="ID del producto")
    cantidad: Decimal = Field(..., gt=0, description="Cantidad vendida")
    precio: Decimal = Field(..., gt=0, description="Precio unitario")
    observaciones: Optional[str] = Field(None, max_length=500, description="Notas especiales (sin gluten, etc)")
    
    @field_validator('cantidad', 'precio', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class VentaCreate(BaseModel):
    """Crear nueva venta - POS Premium"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tipo_venta": "en_mesa",
            "mesa_id": 1,
            "detalles": [
                {"producto_id": 5, "cantidad": "2", "precio": "8500"}
            ]
        }
    })
    
    mesa_id: Optional[int] = Field(None, description="ID de la mesa (si aplica)")
    cliente_id: Optional[int] = Field(None, description="ID del cliente frecuente")
    tipo_venta: TipoVenta = Field(default=TipoVenta.EN_MESA, description="Tipo de venta")
    zona_id: Optional[int] = Field(None, description="Zona del restaurante")
    detalles: List[DetalleVentaCreate] = Field(..., min_length=1, description="Items de la venta")
    descuento: Decimal = Field(default=Decimal("0"), ge=0, description="Descuento total")
    impuesto: Decimal = Field(default=Decimal("0"), ge=0, description="Impuesto")
    propina_porcentaje: Decimal = Field(default=Decimal("0"), ge=0, le=100, description="Propina en %")
    propina_fija: Decimal = Field(default=Decimal("0"), ge=0, description="Propina fija")
    cargo_envio: Decimal = Field(default=Decimal("0"), ge=0, description="Cargo envío (domicilio)")
    observaciones: Optional[str] = Field(None, max_length=1000, description="Notas de la venta")
    referencia_externa: Optional[str] = Field(None, max_length=100, description="Ref. externa (pedido app)")
    
    @model_validator(mode='after')
    def validar_venta(self):
        """Validaciones de negocio"""
        tipo = self.tipo_venta
        mesa_id = self.mesa_id
        
        # Validar mesa si es en_mesa
        if tipo == TipoVenta.EN_MESA and not mesa_id:
            raise ValueError("tipo_venta=en_mesa requiere mesa_id")
        
        if tipo != TipoVenta.EN_MESA and mesa_id:
            raise ValueError(f"tipo_venta={tipo} no puede tener mesa_id")
        
        # Validar propina
        propina_pct = self.propina_porcentaje or Decimal("0")
        if propina_pct < 0 or propina_pct > 100:
            raise ValueError("propina_porcentaje debe estar entre 0 y 100")
        
        return self


class PagoCreate(BaseModel):
    """Registrar pago en venta"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tipo_pago": "tarjeta_credito",
            "monto": "45000.00",
            "referencia": "AUTH123456"
        }
    })
    
    tipo_pago: TipoPago = Field(..., description="Medio de pago")
    monto: Decimal = Field(..., gt=0, description="Monto pagado")
    referencia: Optional[str] = Field(None, max_length=100, description="Ref. transacción")
    
    @field_validator('monto', mode='before')
    @classmethod
    def convert_monto(cls, v):
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


# ============================================================================
# SCHEMAS DE SALIDA (Response)
# ============================================================================

class DetalleVentaResponse(BaseModel):
    """Respuesta: Detalle de venta"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    venta_id: int
    producto_id: int
    cantidad: Decimal
    precio: Decimal
    subtotal: Decimal
    observaciones: Optional[str]


class VentaResponse(BaseModel):
    """Respuesta: Venta completa con detalles"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "estado": "cerrada",
                "tipo_venta": "en_mesa",
                "mesa_id": 1,
                "total": "45000.00",
                "detalles": []
            }
        }
    )
    
    id: int
    estado: EstadoVenta
    tipo_venta: TipoVenta
    mesa_id: Optional[int]
    zona_id: Optional[int]
    cliente_id: Optional[int]
    usuario_id: int
    empresa_id: int
    
    # Montos
    subtotal: Decimal
    descuento: Decimal
    impuesto: Decimal
    propina: Decimal
    cargo_envio: Decimal
    total: Decimal
    
    # Detalles
    detalles: List[DetalleVentaResponse]
    observaciones: Optional[str]
    referencia_externa: Optional[str]
    
    # Auditoría
    fecha_creacion: datetime
    fecha_cierre: Optional[datetime]


class VentaSuspendidaResponse(BaseModel):
    """Respuesta: Venta suspendida"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "venta_id": 5,
            "codigo_suspension": "SUS-2026-07-19-001",
            "mensaje": "Venta suspendida correctamente"
        }
    })
    
    venta_id: int
    codigo_suspension: str = Field(..., description="Código para recuperar después")
    mensaje: str


# ============================================================================
# SCHEMAS DE BÚSQUEDA Y LISTADO
# ============================================================================

class FiltroVentas(BaseModel):
    """Filtros para búsqueda de ventas"""
    estado: Optional[EstadoVenta] = None
    tipo_venta: Optional[TipoVenta] = None
    mesa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    monto_minimo: Optional[Decimal] = None
    monto_maximo: Optional[Decimal] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ReporteVentaResponse(BaseModel):
    """Reporte resumido de venta (para listados)"""
    id: int
    mesa_id: Optional[int]
    tipo_venta: TipoVenta
    total: Decimal
    items_count: int
    estado: EstadoVenta
    fecha: datetime
    usuario_nombre: str
    cliente_nombre: Optional[str]
