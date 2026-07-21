"""
Tests para validación de schemas de Mesas
"""

import pytest
from pydantic import ValidationError
from app.domains.mesas.schemas import (
    MesaCreate, MesaUpdate, CambiarEstadoMesa, ReservarMesa,
    EstadoMesa, FormaMesa, MesaResponse
)


class TestEstadoMesaEnum:
    """Tests para enum EstadoMesa"""
    
    def test_estados_validos(self):
        """Verificar todos los estados válidos"""
        assert EstadoMesa.DISPONIBLE.value == "disponible"
        assert EstadoMesa.OCUPADA.value == "ocupada"
        assert EstadoMesa.RESERVADA.value == "reservada"
        assert EstadoMesa.LIMPIEZA.value == "limpieza"
        assert EstadoMesa.MANTENIMIENTO.value == "mantenimiento"
    
    def test_crear_desde_string(self):
        """Poder crear enum desde string"""
        estado = EstadoMesa("disponible")
        assert estado == EstadoMesa.DISPONIBLE


class TestFormaMesaEnum:
    """Tests para enum FormaMesa"""
    
    def test_formas_validas(self):
        """Verificar todas las formas válidas"""
        assert FormaMesa.REDONDA.value == "redonda"
        assert FormaMesa.CUADRADA.value == "cuadrada"
        assert FormaMesa.RECTANGULAR.value == "rectangular"
        assert FormaMesa.OVALADA.value == "ovalada"


class TestMesaCreate:
    """Tests para schema MesaCreate"""
    
    def test_crear_mesa_valida(self):
        """Crear mesa con datos válidos"""
        mesa_data = MesaCreate(
            zona_id=1,
            nombre="M1",
            capacidad=4,
            posicion_x=10,
            posicion_y=15,
            forma=FormaMesa.REDONDA
        )
        assert mesa_data.zona_id == 1
        assert mesa_data.nombre == "M1"
        assert mesa_data.capacidad == 4
        assert mesa_data.posicion_x == 10
        assert mesa_data.posicion_y == 15
    
    def test_zona_id_requerido(self):
        """zona_id es requerido"""
        with pytest.raises(ValidationError) as exc_info:
            MesaCreate(nombre="M1")
        assert "zona_id" in str(exc_info.value)
    
    def test_nombre_requerido(self):
        """nombre es requerido"""
        with pytest.raises(ValidationError) as exc_info:
            MesaCreate(zona_id=1)
        assert "nombre" in str(exc_info.value)
    
    def test_nombre_vacio_invalido(self):
        """nombre vacío es inválido"""
        with pytest.raises(ValidationError):
            MesaCreate(zona_id=1, nombre="")
    
    def test_capacidad_minima(self):
        """capacidad mínima es 1"""
        with pytest.raises(ValidationError):
            MesaCreate(zona_id=1, nombre="M1", capacidad=0)
    
    def test_capacidad_maxima(self):
        """capacidad máxima es 20"""
        with pytest.raises(ValidationError):
            MesaCreate(zona_id=1, nombre="M1", capacidad=21)
    
    def test_posicion_negativa_invalida(self):
        """posiciones negativas son inválidas"""
        with pytest.raises(ValidationError):
            MesaCreate(zona_id=1, nombre="M1", posicion_x=-5)
    
    def test_defaults(self):
        """Verificar valores por defecto"""
        mesa_data = MesaCreate(zona_id=1, nombre="M1")
        assert mesa_data.capacidad == 4
        assert mesa_data.posicion_x == 0
        assert mesa_data.posicion_y == 0
        assert mesa_data.forma == FormaMesa.REDONDA
    
    def test_forma_string(self):
        """Aceptar forma como string"""
        mesa_data = MesaCreate(
            zona_id=1, nombre="M1", forma="cuadrada"
        )
        assert mesa_data.forma == "cuadrada"


class TestMesaUpdate:
    """Tests para schema MesaUpdate"""
    
    def test_todos_campos_opcionales(self):
        """Todos los campos son opcionales"""
        update = MesaUpdate()
        assert update.nombre is None
        assert update.capacidad is None
        assert update.estado is None
    
    def test_actualizar_nombre(self):
        """Actualizar solo nombre"""
        update = MesaUpdate(nombre="M1-Premium")
        assert update.nombre == "M1-Premium"
        assert update.capacidad is None
    
    def test_actualizar_multiples_campos(self):
        """Actualizar múltiples campos"""
        update = MesaUpdate(
            nombre="M1",
            capacidad=6,
            estado=EstadoMesa.LIMPIEZA
        )
        assert update.nombre == "M1"
        assert update.capacidad == 6
        assert update.estado == EstadoMesa.LIMPIEZA


class TestCambiarEstadoMesa:
    """Tests para schema CambiarEstadoMesa"""
    
    def test_cambiar_estado_valido(self):
        """Cambiar a estado válido"""
        cambio = CambiarEstadoMesa(estado=EstadoMesa.LIMPIEZA)
        assert cambio.estado == EstadoMesa.LIMPIEZA
    
    def test_motivo_opcional(self):
        """Motivo es opcional"""
        cambio = CambiarEstadoMesa(estado=EstadoMesa.LIMPIEZA)
        assert cambio.motivo is None
    
    def test_cambio_con_motivo(self):
        """Cambio con motivo"""
        cambio = CambiarEstadoMesa(
            estado=EstadoMesa.MANTENIMIENTO,
            motivo="Silla rota"
        )
        assert cambio.motivo == "Silla rota"


class TestReservarMesa:
    """Tests para schema ReservarMesa"""
    
    def test_reservar_mesa_valida(self):
        """Reservar mesa con datos válidos"""
        from datetime import datetime
        reserva = ReservarMesa(
            cliente_nombre="Juan Pérez",
            telefono="3001234567",
            personas=4,
            fecha_hora=datetime(2026, 7, 20, 19, 30)
        )
        assert reserva.cliente_nombre == "Juan Pérez"
        assert reserva.personas == 4
    
    def test_cliente_nombre_requerido(self):
        """cliente_nombre es requerido"""
        with pytest.raises(ValidationError):
            ReservarMesa(personas=4)
    
    def test_personas_minimo(self):
        """Mínimo 1 persona"""
        with pytest.raises(ValidationError):
            ReservarMesa(cliente_nombre="Juan", personas=0)


class TestMesaResponse:
    """Tests para schema MesaResponse"""
    
    def test_crear_respuesta(self):
        """Crear respuesta de mesa"""
        response = MesaResponse(
            id=1,
            zona_id=1,
            nombre="M1",
            capacidad=4,
            posicion_x=10,
            posicion_y=15,
            forma="redonda",
            estado="disponible"
        )
        assert response.id == 1
        assert response.nombre == "M1"
        assert response.estado == "disponible"
    
    def test_from_attributes_config(self):
        """Verificar que puede crearse desde atributos de modelo"""
        # Este test valida que ConfigDict está bien configurado
        assert MesaResponse.model_config["from_attributes"] is True
