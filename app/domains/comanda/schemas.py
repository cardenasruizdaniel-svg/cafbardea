"""
Schemas de validación para Comanda (Kitchen Management) - FASE 3
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class EstadoComanda(str, Enum):
    """Estados posibles de una comanda"""
    PENDIENTE = "pendiente"
    PREPARANDO = "preparando"
    LISTA = "lista"
    ENTREGADA = "entregada"
    CANCELADA = "cancelada"


class PrioridadComanda(str, Enum):
    """Prioridades de comanda"""
    NORMAL = "normal"
    ALTA = "alta"
    URGENTE = "urgente"


class ComandaCreate(BaseModel):
    """Crear nueva comanda"""
    venta_id: int = Field(..., gt=0, description="ID de la venta asociada")
    mesa_id: Optional[int] = Field(None, gt=0, description="ID de la mesa (opcional)")
    prioridad: PrioridadComanda = Field(
        default=PrioridadComanda.NORMAL,
        description="Prioridad de la comanda"
    )
    notas: Optional[str] = Field(
        None,
        max_length=500,
        description="Notas especiales para cocina"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "venta_id": 1,
                "mesa_id": 5,
                "prioridad": "alta",
                "notas": "Sin picante, al diente"
            }
        }
    }


class ComandaUpdate(BaseModel):
    """Actualizar comanda"""
    prioridad: Optional[PrioridadComanda] = Field(None, description="Cambiar prioridad")
    notas: Optional[str] = Field(None, max_length=500, description="Actualizar notas")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prioridad": "urgente",
                "notas": "Cliente muy apurado"
            }
        }
    }


class CambiarEstadoComanda(BaseModel):
    """Cambiar estado de una comanda"""
    estado: EstadoComanda = Field(..., description="Nuevo estado")
    notas: Optional[str] = Field(
        None,
        max_length=250,
        description="Notas del cambio de estado"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "estado": "lista",
                "notas": "Comanda completada"
            }
        }
    }


class ComandaResponse(BaseModel):
    """Respuesta de comanda"""
    id: int
    venta_id: int
    mesa_id: Optional[int]
    estado: str
    prioridad: str
    fecha_creacion: datetime
    fecha_entrega: Optional[datetime]
    notas: Optional[str]
    tiempo_preparacion_minutos: Optional[int] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "venta_id": 1,
                "mesa_id": 5,
                "estado": "preparando",
                "prioridad": "alta",
                "fecha_creacion": "2026-07-19T10:30:00",
                "fecha_entrega": None,
                "notas": "Sin picante",
                "tiempo_preparacion_minutos": 15
            }
        }
    }


class ComandaDetalleResponse(BaseModel):
    """Comanda con detalles de items"""
    id: int
    venta_id: int
    mesa_id: Optional[int]
    estado: str
    prioridad: str
    fecha_creacion: datetime
    fecha_entrega: Optional[datetime]
    notas: Optional[str]
    items: List[dict] = Field(default_factory=list, description="Items en la comanda")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "venta_id": 1,
                "mesa_id": 5,
                "estado": "preparando",
                "prioridad": "alta",
                "fecha_creacion": "2026-07-19T10:30:00",
                "fecha_entrega": None,
                "notas": "Sin picante",
                "items": [
                    {
                        "producto": "Capuchino",
                        "cantidad": 2,
                        "estado_cocina": "en_preparacion",
                        "notas": "Sin espuma"
                    }
                ]
            }
        }
    }


class EstadisticasComanda(BaseModel):
    """Estadísticas de comandas"""
    total_comandas: int
    por_estado: dict = Field(
        default_factory=dict,
        description="Conteo por estado (pendiente, preparando, lista, entregada)"
    )
    por_prioridad: dict = Field(
        default_factory=dict,
        description="Conteo por prioridad (normal, alta, urgente)"
    )
    tiempo_promedio_minutos: Optional[Decimal] = Field(
        None,
        description="Tiempo promedio de preparación en minutos"
    )
    comandas_pendientes: int = 0
    comandas_en_cocina: int = 0

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_comandas": 45,
                "por_estado": {
                    "pendiente": 5,
                    "preparando": 12,
                    "lista": 15,
                    "entregada": 13
                },
                "por_prioridad": {
                    "normal": 30,
                    "alta": 12,
                    "urgente": 3
                },
                "tiempo_promedio_minutos": 18.5,
                "comandas_pendientes": 5,
                "comandas_en_cocina": 12
            }
        }
    }


class ListaEsperaComanda(BaseModel):
    """Comanda en lista de espera"""
    id: int
    venta_id: int
    mesa_id: Optional[int]
    estado: str
    prioridad: str
    tiempo_espera_minutos: int
    notas: Optional[str]

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "venta_id": 1,
                "mesa_id": 5,
                "estado": "pendiente",
                "prioridad": "normal",
                "tiempo_espera_minutos": 8,
                "notas": "Sin picante"
            }
        }
    }
