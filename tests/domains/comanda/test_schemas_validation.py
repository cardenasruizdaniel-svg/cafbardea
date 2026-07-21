"""
Tests para validación de Schemas de Comanda - FASE 3
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.domains.comanda.schemas import (
    EstadoComanda,
    PrioridadComanda,
    ComandaCreate,
    ComandaUpdate,
    CambiarEstadoComanda,
    ComandaResponse,
    EstadisticasComanda,
    ListaEsperaComanda
)


class TestEstadoComandaEnum:
    """Tests para enum EstadoComanda"""
    
    def test_estados_validos(self):
        """Verificar que todos los estados son válidos"""
        estados = ["pendiente", "preparando", "lista", "entregada", "cancelada"]
        for estado in estados:
            assert estado in [e.value for e in EstadoComanda]
    
    def test_estado_creacion_desde_string(self):
        """Crear EstadoComanda desde string"""
        estado = EstadoComanda("pendiente")
        assert estado == EstadoComanda.PENDIENTE


class TestPrioridadComandaEnum:
    """Tests para enum PrioridadComanda"""
    
    def test_prioridades_validas(self):
        """Verificar que todas las prioridades son válidas"""
        prioridades = ["normal", "alta", "urgente"]
        for prioridad in prioridades:
            assert prioridad in [p.value for p in PrioridadComanda]


class TestComandaCreate:
    """Tests para schema ComandaCreate"""
    
    def test_crear_comanda_minima(self):
        """Crear comanda con datos mínimos"""
        data = {
            "venta_id": 1
        }
        comanda = ComandaCreate(**data)
        assert comanda.venta_id == 1
        assert comanda.prioridad == "normal"
    
    def test_crear_comanda_completa(self):
        """Crear comanda con todos los datos"""
        data = {
            "venta_id": 1,
            "mesa_id": 5,
            "prioridad": "alta",
            "notas": "Sin picante"
        }
        comanda = ComandaCreate(**data)
        assert comanda.venta_id == 1
        assert comanda.mesa_id == 5
        assert comanda.prioridad == "alta"
        assert comanda.notas == "Sin picante"
    
    def test_venta_id_requerido(self):
        """venta_id es obligatorio"""
        with pytest.raises(ValidationError):
            ComandaCreate()
    
    def test_venta_id_mayor_que_cero(self):
        """venta_id debe ser > 0"""
        with pytest.raises(ValidationError):
            ComandaCreate(venta_id=0)
    
    def test_mesa_id_mayor_que_cero(self):
        """mesa_id debe ser > 0 si se proporciona"""
        with pytest.raises(ValidationError):
            ComandaCreate(venta_id=1, mesa_id=0)
    
    def test_notas_max_length(self):
        """Notas no puede exceder 500 caracteres"""
        notas_largo = "a" * 501
        with pytest.raises(ValidationError):
            ComandaCreate(venta_id=1, notas=notas_largo)


class TestComandaUpdate:
    """Tests para schema ComandaUpdate"""
    
    def test_actualizar_vacio(self):
        """ComandaUpdate puede estar vacío"""
        comanda = ComandaUpdate()
        assert comanda.prioridad is None
        assert comanda.notas is None
    
    def test_actualizar_prioridad(self):
        """Actualizar solo prioridad"""
        data = {"prioridad": "urgente"}
        comanda = ComandaUpdate(**data)
        assert comanda.prioridad == "urgente"
    
    def test_actualizar_notas(self):
        """Actualizar solo notas"""
        data = {"notas": "Nueva nota"}
        comanda = ComandaUpdate(**data)
        assert comanda.notas == "Nueva nota"
    
    def test_todos_campos_opcionales(self):
        """Todos los campos son opcionales"""
        comanda = ComandaUpdate()
        assert comanda.prioridad is None
        assert comanda.notas is None


class TestCambiarEstadoComanda:
    """Tests para schema CambiarEstadoComanda"""
    
    def test_cambiar_estado_requerido(self):
        """estado es obligatorio"""
        with pytest.raises(ValidationError):
            CambiarEstadoComanda()
    
    def test_cambiar_estado_valido(self):
        """Cambiar a estado válido"""
        data = {"estado": "preparando"}
        cambio = CambiarEstadoComanda(**data)
        assert cambio.estado == "preparando"
    
    def test_cambiar_con_notas(self):
        """Cambiar estado con notas"""
        data = {
            "estado": "lista",
            "notas": "Completada"
        }
        cambio = CambiarEstadoComanda(**data)
        assert cambio.estado == "lista"
        assert cambio.notas == "Completada"


class TestComandaResponse:
    """Tests para schema ComandaResponse"""
    
    def test_comanda_response_estructura(self):
        """Verificar estructura de ComandaResponse"""
        data = {
            "id": 1,
            "venta_id": 1,
            "mesa_id": 5,
            "estado": "preparando",
            "prioridad": "alta",
            "fecha_creacion": datetime.now(),
            "fecha_entrega": None,
            "notas": "Sin picante"
        }
        comanda = ComandaResponse(**data)
        assert comanda.id == 1
        assert comanda.venta_id == 1
        assert comanda.estado == "preparando"
    
    def test_comanda_response_con_entrega(self):
        """ComandaResponse con fecha de entrega"""
        data = {
            "id": 1,
            "venta_id": 1,
            "mesa_id": 5,
            "estado": "entregada",
            "prioridad": "normal",
            "fecha_creacion": datetime.now(),
            "fecha_entrega": datetime.now(),
            "notas": None
        }
        comanda = ComandaResponse(**data)
        assert comanda.estado == "entregada"
        assert comanda.fecha_entrega is not None


class TestEstadisticasComanda:
    """Tests para schema EstadisticasComanda"""
    
    def test_estadisticas_estructura(self):
        """Verificar estructura de EstadisticasComanda"""
        data = {
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
            "comandas_pendientes": 5,
            "comandas_en_cocina": 12
        }
        stats = EstadisticasComanda(**data)
        assert stats.total_comandas == 45
        assert stats.comandas_pendientes == 5
    
    def test_estadisticas_vacías(self):
        """EstadisticasComanda con valores por defecto"""
        data = {"total_comandas": 0}
        stats = EstadisticasComanda(**data)
        assert stats.total_comandas == 0
        assert stats.comandas_pendientes == 0


class TestListaEsperaComanda:
    """Tests para schema ListaEsperaComanda"""
    
    def test_lista_espera_estructura(self):
        """Verificar estructura de ListaEsperaComanda"""
        data = {
            "id": 1,
            "venta_id": 1,
            "mesa_id": 5,
            "estado": "pendiente",
            "prioridad": "normal",
            "tiempo_espera_minutos": 8,
            "notas": "Sin picante"
        }
        item = ListaEsperaComanda(**data)
        assert item.id == 1
        assert item.tiempo_espera_minutos == 8
