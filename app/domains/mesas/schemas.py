"""
Schemas Pydantic para el módulo de Mesas - FASE 2 Floor Plan
Define validaciones y estructuras para gestión de mesas del restaurante
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum


class EstadoMesa(str, Enum):
    """Estados posibles de una mesa"""
    DISPONIBLE = "disponible"
    OCUPADA = "ocupada"
    RESERVADA = "reservada"
    LIMPIEZA = "limpieza"
    MANTENIMIENTO = "mantenimiento"


class FormaMesa(str, Enum):
    """Formas de mesa soportadas"""
    REDONDA = "redonda"
    CUADRADA = "cuadrada"
    RECTANGULAR = "rectangular"
    OVALADA = "ovalada"


# ============================================================================
# SCHEMAS DE ENTRADA (Input)
# ============================================================================

class MesaCreate(BaseModel):
    """Crear nueva mesa"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "zona_id": 1,
            "nombre": "M1",
            "capacidad": 4,
            "posicion_x": 10,
            "posicion_y": 15,
            "forma": "redonda"
        }
    })
    
    zona_id: int = Field(..., gt=0, description="ID de la zona")
    nombre: str = Field(..., min_length=1, max_length=40, description="Nombre/Número de mesa")
    capacidad: int = Field(default=4, ge=1, le=20, description="Número de puestos")
    posicion_x: int = Field(default=0, ge=0, le=1000, description="Posición X en plano")
    posicion_y: int = Field(default=0, ge=0, le=1000, description="Posición Y en plano")
    forma: FormaMesa = Field(default=FormaMesa.REDONDA, description="Forma de la mesa")


class MesaUpdate(BaseModel):
    """Actualizar mesa existente"""
    nombre: Optional[str] = Field(None, min_length=1, max_length=40)
    capacidad: Optional[int] = Field(None, ge=1, le=20)
    posicion_x: Optional[int] = Field(None, ge=0, le=1000)
    posicion_y: Optional[int] = Field(None, ge=0, le=1000)
    forma: Optional[FormaMesa] = None
    estado: Optional[EstadoMesa] = None


class CambiarEstadoMesa(BaseModel):
    """Cambiar estado de mesa"""
    estado: EstadoMesa = Field(..., description="Nuevo estado")
    motivo: Optional[str] = Field(None, max_length=200, description="Razón del cambio")


class ReservarMesa(BaseModel):
    """Reservar mesa"""
    cliente_nombre: str = Field(..., min_length=1, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    personas: int = Field(..., ge=1, le=20)
    fecha_hora: Optional[datetime] = None
    notas: Optional[str] = Field(None, max_length=500)


# ============================================================================
# SCHEMAS DE SALIDA (Response)
# ============================================================================

class MesaResponse(BaseModel):
    """Respuesta: Información completa de mesa"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "zona_id": 1,
                "nombre": "M1",
                "capacidad": 4,
                "posicion_x": 10,
                "posicion_y": 15,
                "forma": "redonda",
                "estado": "disponible",
                "venta_activa": None,
                "numero_personas": None
            }
        }
    )
    
    id: int
    zona_id: int
    nombre: str
    capacidad: int
    posicion_x: int
    posicion_y: int
    forma: FormaMesa
    estado: EstadoMesa
    venta_activa: Optional[int] = None  # ID de venta si está ocupada
    numero_personas: Optional[int] = None
    observaciones: Optional[str] = None


class ZonaResponse(BaseModel):
    """Respuesta: Zona con mesas"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    nombre: str
    orden: int
    mesas_count: int
    mesas_disponibles: int
    mesas: List[MesaResponse] = []


class FloorPlanResponse(BaseModel):
    """Respuesta: Plano completo del restaurante"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "restaurante": "Mi Café",
            "zonas": [],
            "estadisticas": {
                "total_mesas": 10,
                "mesas_disponibles": 7,
                "mesas_ocupadas": 3,
                "ocupacion_porcentaje": 30
            }
        }
    })
    
    restaurante: str
    zonas: List[ZonaResponse]
    estadisticas: dict = {}


class EstadisticasMesa(BaseModel):
    """Estadísticas de uso de mesas"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "fecha": "2026-07-19",
            "total_mesas": 10,
            "ocupadas": 3,
            "disponibles": 7,
            "en_limpieza": 0,
            "reservadas": 0,
            "ocupacion_promedio": 30,
            "mesas_por_estado": {
                "disponible": 7,
                "ocupada": 3,
                "reservada": 0,
                "limpieza": 0,
                "mantenimiento": 0
            }
        }
    })
    
    fecha: str
    total_mesas: int
    ocupadas: int
    disponibles: int
    en_limpieza: int
    reservadas: int
    ocupacion_promedio: int
    mesas_por_estado: dict


# ============================================================================
# SCHEMAS DE BÚSQUEDA
# ============================================================================

class FiltroMesas(BaseModel):
    """Filtros para búsqueda de mesas"""
    zona_id: Optional[int] = None
    estado: Optional[EstadoMesa] = None
    capacidad_minima: Optional[int] = None
    forma: Optional[FormaMesa] = None


class ReporteMesaResponse(BaseModel):
    """Reporte resumido de mesa para listados"""
    id: int
    nombre: str
    zona: str
    capacidad: int
    estado: EstadoMesa
    ocupacion: str  # "Disponible" o "Ocupada por Juan"
