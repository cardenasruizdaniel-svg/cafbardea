"""
Schemas de validación para Nómina (Payroll Management) - FASE 4
"""

from enum import Enum
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class EstadoNomina(str, Enum):
    """Estados posibles de una liquidación de nómina"""
    BORRADOR = "borrador"
    PROCESADA = "procesada"
    PAGADA = "pagada"
    REVERTIDA = "revertida"


class TipoNomina(str, Enum):
    """Tipos de nómina"""
    ORDINARIA = "ordinaria"
    EXTRAORDINARIA = "extraordinaria"
    CESANTIA = "cesantia"
    VACACIONES = "vacaciones"


class TipoDeduccion(str, Enum):
    """Tipos de deducciones"""
    SALUD = "salud"
    PENSION = "pension"
    FONDO_SOLIDARIO = "fondo_solidario"
    LIBRANZA = "libranza"
    EMBARGO = "embargo"


class TipoDevengado(str, Enum):
    """Tipos de devengados/bonificaciones"""
    BASICO = "basico"
    AUXILIO_TRANSPORTE = "auxilio_transporte"
    HORAS_EXTRA = "horas_extra"
    DOMINICAL = "dominical"
    FESTIVO = "festivo"
    COMISION = "comision"
    BONO = "bono"


class PeriodoNominaCreate(BaseModel):
    """Crear periodo de nómina"""
    fecha_inicio: date = Field(..., description="Fecha inicio del periodo")
    fecha_fin: date = Field(..., description="Fecha fin del periodo")
    periodicidad: str = Field(
        default="mensual",
        description="Periodicidad: mensual, quincenal, semanal"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "fecha_inicio": "2026-07-01",
                "fecha_fin": "2026-07-31",
                "periodicidad": "mensual"
            }
        }
    }


class PeriodoNominaResponse(BaseModel):
    """Respuesta de periodo de nómina"""
    id: int
    fecha_inicio: date
    fecha_fin: date
    periodicidad: str
    estado: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "fecha_inicio": "2026-07-01",
                "fecha_fin": "2026-07-31",
                "periodicidad": "mensual",
                "estado": "borrador"
            }
        }
    }


class LiquidacionNominaCreate(BaseModel):
    """Crear liquidación de nómina"""
    periodo_id: int = Field(..., gt=0, description="ID del periodo")
    empleado_id: int = Field(..., gt=0, description="ID del empleado")
    dias_liquidados: Decimal = Field(
        default=Decimal("30"),
        ge=0,
        le=31,
        description="Días trabajados"
    )
    salario_base: Decimal = Field(..., gt=0, description="Salario base del empleado")

    @field_validator("dias_liquidados", mode="before")
    @classmethod
    def convertir_dias(cls, v):
        if isinstance(v, str):
            return Decimal(v)
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "periodo_id": 1,
                "empleado_id": 5,
                "dias_liquidados": 30,
                "salario_base": 2500000
            }
        }
    }


class LiquidacionNominaUpdate(BaseModel):
    """Actualizar liquidación de nómina"""
    dias_liquidados: Optional[Decimal] = Field(None, ge=0, le=31)
    salario_base: Optional[Decimal] = Field(None, gt=0)

    @field_validator("dias_liquidados", "salario_base", mode="before")
    @classmethod
    def convertir_decimales(cls, v):
        if isinstance(v, str):
            return Decimal(v)
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "dias_liquidados": 28,
                "salario_base": 2500000
            }
        }
    }


class LiquidacionNominaResponse(BaseModel):
    """Respuesta de liquidación de nómina"""
    id: int
    periodo_id: int
    empleado_id: int
    dias_liquidados: Decimal
    salario_base: Decimal
    devengados: Decimal
    deducciones: Decimal
    neto: Decimal
    estado_electronico: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "periodo_id": 1,
                "empleado_id": 5,
                "dias_liquidados": 30,
                "salario_base": 2500000,
                "devengados": 2500000,
                "deducciones": 625000,
                "neto": 1875000,
                "estado_electronico": "pendiente_configuracion"
            }
        }
    }


class DetalleDevengadoCreate(BaseModel):
    """Agregar devengado a nómina"""
    tipo: TipoDevengado = Field(..., description="Tipo de devengado")
    monto: Decimal = Field(..., gt=0, description="Monto")
    descripcion: Optional[str] = Field(None, max_length=200)

    @field_validator("monto", mode="before")
    @classmethod
    def convertir_monto(cls, v):
        if isinstance(v, str):
            return Decimal(v)
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "tipo": "horas_extra",
                "monto": 150000,
                "descripcion": "8 horas extra ordinarias"
            }
        }
    }


class DetalleDeduccionCreate(BaseModel):
    """Agregar deducción a nómina"""
    tipo: TipoDeduccion = Field(..., description="Tipo de deducción")
    monto: Decimal = Field(..., gt=0, description="Monto")
    descripcion: Optional[str] = Field(None, max_length=200)

    @field_validator("monto", mode="before")
    @classmethod
    def convertir_monto(cls, v):
        if isinstance(v, str):
            return Decimal(v)
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "tipo": "salud",
                "monto": 312500,
                "descripcion": "Aporte a EPS"
            }
        }
    }


class ReciboNominaResponse(BaseModel):
    """Recibo de pago de nómina"""
    id: int
    empleado_nombre: str
    documento: str
    periodo: str
    dias_liquidados: Decimal
    salario_base: Decimal
    devengados: Decimal
    deducciones: Decimal
    neto: Decimal
    fecha_generacion: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "empleado_nombre": "Juan García",
                "documento": "12345678",
                "periodo": "2026-07-01 a 2026-07-31",
                "dias_liquidados": 30,
                "salario_base": 2500000,
                "devengados": 2500000,
                "deducciones": 625000,
                "neto": 1875000,
                "fecha_generacion": "2026-07-31T18:00:00"
            }
        }
    }


class EstadisticasNomina(BaseModel):
    """Estadísticas de nómina"""
    total_empleados: int = 0
    total_liquidaciones: int = 0
    nominas_procesadas: int = 0
    nominas_pagadas: int = 0
    monto_total_devengados: Decimal = Decimal("0")
    monto_total_deducciones: Decimal = Decimal("0")
    monto_total_neto: Decimal = Decimal("0")
    promedio_salario: Optional[Decimal] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_empleados": 25,
                "total_liquidaciones": 50,
                "nominas_procesadas": 45,
                "nominas_pagadas": 40,
                "monto_total_devengados": 62500000,
                "monto_total_deducciones": 15625000,
                "monto_total_neto": 46875000,
                "promedio_salario": 2500000
            }
        }
    }


class ProcesarNominaCreate(BaseModel):
    """Procesar período de nómina"""
    periodo_id: int = Field(..., gt=0, description="ID del período a procesar")
    descripcion: Optional[str] = Field(None, max_length=500, description="Observaciones")

    model_config = {
        "json_schema_extra": {
            "example": {
                "periodo_id": 1,
                "descripcion": "Nómina del mes de julio"
            }
        }
    }
