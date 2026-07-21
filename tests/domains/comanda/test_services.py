"""
Tests para Service layer de Comanda - FASE 3
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models import Comanda, Venta
from app.domains.comanda.schemas import (
    ComandaCreate, ComandaUpdate, CambiarEstadoComanda
)
from app.domains.comanda.services import ComandaService


class TestComandaServiceCrear:
    """Tests para crear comandas"""
    
    def test_crear_comanda_exitosa(self, db_session):
        """Crear comanda exitosamente"""
        # Obtener primera venta del seed
        venta = db_session.query(Venta).first()
        if venta:
            service = ComandaService(db_session)
            comanda_data = ComandaCreate(
                venta_id=venta.id,
                mesa_id=1,
                prioridad="normal",
                notas="Test comanda"
            )
            comanda = service.crear_comanda(comanda_data)
            
            assert comanda.id is not None
            assert comanda.venta_id == venta.id
            assert comanda.estado == "pendiente"
    
    def test_crear_comanda_venta_inexistente(self, db_session):
        """Error creando comanda con venta inexistente"""
        service = ComandaService(db_session)
        comanda_data = ComandaCreate(venta_id=99999)
        
        with pytest.raises(ValueError):
            service.crear_comanda(comanda_data)


class TestComandaServiceObtener:
    """Tests para obtener comandas"""
    
    def test_obtener_comanda_por_id(self, db_session):
        """Obtener comanda existente"""
        comanda = db_session.query(Comanda).first()
        if comanda:
            service = ComandaService(db_session)
            resultado = service.obtener_comanda(comanda.id)
            
            assert resultado is not None
            assert resultado.id == comanda.id
    
    def test_obtener_comanda_inexistente(self, db_session):
        """Obtener comanda que no existe"""
        service = ComandaService(db_session)
        resultado = service.obtener_comanda(99999)
        
        assert resultado is None
    
    def test_listar_comandas_por_estado(self, db_session):
        """Listar comandas por estado"""
        service = ComandaService(db_session)
        pendientes = service.listar_comandas_por_estado("pendiente")
        
        assert isinstance(pendientes, list)


class TestComandaServiceCambiarEstado:
    """Tests para cambiar estado de comanda"""
    
    def test_cambiar_estado_pendiente_a_preparando(self, db_session):
        """Cambiar estado pendiente → preparando"""
        comanda = db_session.query(Comanda).filter(
            Comanda.estado == "pendiente"
        ).first()
        
        if comanda:
            service = ComandaService(db_session)
            cambio = CambiarEstadoComanda(
                estado="preparando",
                notas="Iniciando preparación"
            )
            resultado = service.cambiar_estado(comanda.id, cambio)
            
            assert resultado.estado == "preparando"
    
    def test_cambiar_a_lista_registra_fecha_entrega(self, db_session):
        """Cambiar a lista registra fecha de entrega"""
        comanda = db_session.query(Comanda).filter(
            Comanda.estado == "preparando"
        ).first()
        
        if comanda:
            service = ComandaService(db_session)
            cambio = CambiarEstadoComanda(
                estado="lista",
                notas="Lista para entregar"
            )
            resultado = service.cambiar_estado(comanda.id, cambio)
            
            assert resultado.estado == "lista"
            assert resultado.fecha_entrega is not None
    
    def test_cambiar_estado_inexistente(self, db_session):
        """Error cambiar estado de comanda inexistente"""
        service = ComandaService(db_session)
        cambio = CambiarEstadoComanda(estado="preparando")
        
        with pytest.raises(ValueError):
            service.cambiar_estado(99999, cambio)


class TestComandaServicePrioridad:
    """Tests para aumentar prioridad"""
    
    def test_aumentar_prioridad_normal_a_alta(self, db_session):
        """Aumentar prioridad: normal → alta"""
        # Crear comanda normal
        venta = db_session.query(Venta).first()
        if venta:
            comanda = Comanda(
                venta_id=venta.id,
                estado="pendiente",
                prioridad="normal"
            )
            db_session.add(comanda)
            db_session.commit()
            
            service = ComandaService(db_session)
            resultado = service.aumentar_prioridad(comanda.id)
            
            assert resultado.prioridad == "alta"
    
    def test_aumentar_prioridad_alta_a_urgente(self, db_session):
        """Aumentar prioridad: alta → urgente"""
        # Crear comanda con prioridad alta
        venta = db_session.query(Venta).first()
        if venta:
            comanda = Comanda(
                venta_id=venta.id,
                estado="pendiente",
                prioridad="alta"
            )
            db_session.add(comanda)
            db_session.commit()
            
            service = ComandaService(db_session)
            resultado = service.aumentar_prioridad(comanda.id)
            
            assert resultado.prioridad == "urgente"


class TestComandaServiceLista:
    """Tests para lista de espera"""
    
    def test_obtener_lista_espera(self, db_session):
        """Obtener lista de espera"""
        service = ComandaService(db_session)
        lista = service.obtener_lista_espera()
        
        assert isinstance(lista, list)
        for item in lista:
            assert "id" in item
            assert "tiempo_espera_minutos" in item


class TestComandaServiceEstadisticas:
    """Tests para estadísticas"""
    
    def test_obtener_estadisticas(self, db_session):
        """Obtener estadísticas de comandas"""
        service = ComandaService(db_session)
        stats = service.obtener_estadisticas()
        
        assert "total_comandas" in stats
        assert "por_estado" in stats
        assert "por_prioridad" in stats
        assert stats["total_comandas"] >= 0
    
    def test_tiempo_promedio_preparacion(self, db_session):
        """Obtener tiempo promedio de preparación"""
        service = ComandaService(db_session)
        tiempo = service.obtener_tiempo_promedio_preparacion()
        
        # Puede ser None si no hay comandas entregadas
        assert tiempo is None or tiempo > 0
