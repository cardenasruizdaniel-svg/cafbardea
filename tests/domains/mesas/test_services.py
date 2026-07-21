"""
Tests para Service layer de Mesas
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Mesa, Zona, Venta
from app.domains.mesas.schemas import MesaCreate, MesaUpdate, CambiarEstadoMesa, EstadoMesa
from app.domains.mesas.services import MesaService


class TestMesaServiceCrear:
    """Tests para crear mesas"""
    
    def test_crear_mesa_exitosa(self, db_session):
        """Crear mesa exitosamente"""
        # Crear zona
        zona = Zona(nombre="Salón", orden=1)
        db_session.add(zona)
        db_session.flush()
        
        # Crear mesa
        service = MesaService(db_session)
        mesa_data = MesaCreate(
            zona_id=zona.id,
            nombre="M1",
            capacidad=4,
            posicion_x=10,
            posicion_y=15
        )
        mesa = service.crear_mesa(mesa_data, empresa_id=1)
        
        assert mesa.id is not None
        assert mesa.nombre == "M1"
        assert mesa.capacidad == 4
        assert mesa.estado == "disponible"
    
    def test_crear_mesa_zona_no_existe(self, db_session):
        """Error si zona no existe"""
        service = MesaService(db_session)
        mesa_data = MesaCreate(
            zona_id=9999,
            nombre="M1"
        )
        
        with pytest.raises(ValueError, match="Zona"):
            service.crear_mesa(mesa_data, empresa_id=1)


class TestMesaServiceObtener:
    """Tests para obtener mesas"""
    
    def test_obtener_mesa_existente(self, db_session):
        """Obtener mesa que existe"""
        zona = Zona(nombre="Salón", orden=1)
        mesa = Mesa(zona_id=0, nombre="M1", capacidad=4, estado="disponible")
        db_session.add_all([zona, mesa])
        db_session.flush()
        
        service = MesaService(db_session)
        resultado = service.obtener_mesa(mesa.id)
        
        assert resultado is not None
        assert resultado.nombre == "M1"
    
    def test_obtener_mesa_no_existe(self, db_session):
        """Obtener mesa inexistente"""
        service = MesaService(db_session)
        resultado = service.obtener_mesa(9999)
        
        assert resultado is None
    
    def test_listar_mesas_por_zona(self, db_session):
        """Listar mesas de una zona"""
        zona = Zona(nombre="Salón", orden=1)
        db_session.add(zona)
        db_session.flush()
        
        mesas = [
            Mesa(zona_id=zona.id, nombre="M1", capacidad=4, estado="disponible"),
            Mesa(zona_id=zona.id, nombre="M2", capacidad=2, estado="disponible"),
        ]
        db_session.add_all(mesas)
        db_session.flush()
        
        service = MesaService(db_session)
        resultado = service.listar_mesas_por_zona(zona.id)
        
        assert len(resultado) == 2


class TestMesaServiceCambiarEstado:
    """Tests para cambiar estado de mesas"""
    
    def test_cambiar_a_limpieza(self, db_session):
        """Cambiar mesa a limpieza"""
        zona = Zona(nombre="Salón", orden=1)
        mesa = Mesa(zona_id=0, nombre="M1", capacidad=4, estado="disponible")
        db_session.add_all([zona, mesa])
        db_session.flush()
        
        service = MesaService(db_session)
        cambio = CambiarEstadoMesa(estado=EstadoMesa.LIMPIEZA)
        resultado = service.cambiar_estado(mesa.id, cambio)
        
        assert resultado.estado == "limpieza"
    
    def test_cambiar_estado_mesa_no_existe(self, db_session):
        """Error si mesa no existe"""
        service = MesaService(db_session)
        cambio = CambiarEstadoMesa(estado=EstadoMesa.LIMPIEZA)
        
        with pytest.raises(ValueError, match="Mesa"):
            service.cambiar_estado(9999, cambio)
    
    def test_ocupar_mesa(self, db_session):
        """Ocupar mesa disponible"""
        zona = Zona(nombre="Salón", orden=1)
        mesa = Mesa(zona_id=0, nombre="M1", capacidad=4, estado="disponible")
        db_session.add_all([zona, mesa])
        db_session.flush()
        
        service = MesaService(db_session)
        resultado = service.ocupar_mesa(mesa.id, venta_id=1)
        
        assert resultado.estado == "ocupada"
    
    def test_liberar_mesa(self, db_session):
        """Liberar mesa ocupada"""
        zona = Zona(nombre="Salón", orden=1)
        mesa = Mesa(zona_id=0, nombre="M1", capacidad=4, estado="ocupada")
        db_session.add_all([zona, mesa])
        db_session.flush()
        
        service = MesaService(db_session)
        resultado = service.liberar_mesa(mesa.id)
        
        assert resultado.estado == "disponible"


class TestMesaServiceEstadisticas:
    """Tests para estadísticas de mesas"""
    
    def test_obtener_estadisticas(self, db_session):
        """Obtener estadísticas de ocupación"""
        service = MesaService(db_session)
        stats = service.obtener_estadisticas()
        
        # Solo verificar que devuelve la estructura correcta
        # (hay datos de seed previos)
        assert "total_mesas" in stats
        assert "disponibles" in stats
        assert "ocupadas" in stats
        assert "en_limpieza" in stats
        assert stats["total_mesas"] >= 0
    
    def test_obtener_mesas_disponibles(self, db_session):
        """Obtener mesas disponibles con capacidad mínima"""
        service = MesaService(db_session)
        
        # Obtener mesas disponibles con capacidad mínima
        resultado = service.obtener_mesas_disponibles(capacidad_minima=1)
        
        # Solo verificar que devuelve lista
        assert isinstance(resultado, list)
