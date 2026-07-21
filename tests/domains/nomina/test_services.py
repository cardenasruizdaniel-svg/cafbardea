"""
Tests para Service layer de Nómina - FASE 4
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select

from app.models import PeriodoNomina, LiquidacionNomina, Empleado
from app.domains.nomina.schemas import (
    PeriodoNominaCreate, LiquidacionNominaCreate, LiquidacionNominaUpdate
)
from app.domains.nomina.services import NominaService


class TestNominaServicePeriodo:
    """Tests para períodos de nómina"""
    
    def test_crear_periodo_exitoso(self, db_session):
        """Crear período exitosamente"""
        service = NominaService(db_session)
        periodo_data = PeriodoNominaCreate(
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
            periodicidad="mensual"
        )
        
        periodo = service.crear_periodo(periodo_data)
        
        assert periodo.id is not None
        assert periodo.fecha_inicio == date(2026, 7, 1)
        assert periodo.estado == "borrador"
    
    def test_crear_periodo_fechas_invalidas(self, db_session):
        """Error si fecha_inicio >= fecha_fin"""
        service = NominaService(db_session)
        periodo_data = PeriodoNominaCreate(
            fecha_inicio=date(2026, 7, 31),
            fecha_fin=date(2026, 7, 1),
            periodicidad="mensual"
        )
        
        with pytest.raises(ValueError):
            service.crear_periodo(periodo_data)
    
    def test_obtener_periodo(self, db_session):
        """Obtener período por ID"""
        service = NominaService(db_session)
        
        # Crear período primero
        periodo_data = PeriodoNominaCreate(
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31)
        )
        periodo = service.crear_periodo(periodo_data)
        
        # Obtenerlo
        obtenido = service.obtener_periodo(periodo.id)
        assert obtenido.id == periodo.id
    
    def test_obtener_periodo_inexistente(self, db_session):
        """Obtener período que no existe"""
        service = NominaService(db_session)
        resultado = service.obtener_periodo(99999)
        assert resultado is None


class TestNominaServiceLiquidacion:
    """Tests para liquidaciones de nómina"""
    
    def test_crear_liquidacion_exitosa(self, db_session):
        """Crear liquidación exitosamente"""
        service = NominaService(db_session)
        
        # Crear período
        periodo_data = PeriodoNominaCreate(
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31)
        )
        periodo = service.crear_periodo(periodo_data)
        
        # Obtener empleado del seed
        empleado = db_session.query(Empleado).first()
        
        if empleado:
            liq_data = LiquidacionNominaCreate(
                periodo_id=periodo.id,
                empleado_id=empleado.id,
                dias_liquidados=Decimal("30"),
                salario_base=Decimal("2500000")
            )
            
            liq = service.crear_liquidacion(liq_data)
            
            assert liq.id is not None
            assert liq.periodo_id == periodo.id
            assert liq.empleado_id == empleado.id
            assert liq.neto > Decimal("0")
    
    def test_crear_liquidacion_periodo_inexistente(self, db_session):
        """Error si período no existe"""
        service = NominaService(db_session)
        
        liq_data = LiquidacionNominaCreate(
            periodo_id=99999,
            empleado_id=1,
            salario_base=Decimal("2500000")
        )
        
        with pytest.raises(ValueError):
            service.crear_liquidacion(liq_data)
    
    def test_obtener_liquidacion(self, db_session):
        """Obtener liquidación por ID"""
        service = NominaService(db_session)
        
        # Crear período y liquidación
        periodo_data = PeriodoNominaCreate(
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31)
        )
        periodo = service.crear_periodo(periodo_data)
        
        empleado = db_session.query(Empleado).first()
        if empleado:
            liq_data = LiquidacionNominaCreate(
                periodo_id=periodo.id,
                empleado_id=empleado.id,
                salario_base=Decimal("2500000")
            )
            liq = service.crear_liquidacion(liq_data)
            
            # Obtenerla
            obtenida = service.obtener_liquidacion(liq.id)
            assert obtenida.id == liq.id


class TestNominaServiceProcesamiento:
    """Tests para procesamiento de nómina"""
    
    def test_procesar_periodo_exitoso(self, db_session):
        """Procesar período exitosamente"""
        service = NominaService(db_session)
        
        # Crear período y liquidación
        periodo_data = PeriodoNominaCreate(
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31)
        )
        periodo = service.crear_periodo(periodo_data)
        
        empleado = db_session.query(Empleado).first()
        if empleado:
            liq_data = LiquidacionNominaCreate(
                periodo_id=periodo.id,
                empleado_id=empleado.id,
                salario_base=Decimal("2500000")
            )
            service.crear_liquidacion(liq_data)
            
            # Procesar
            resultado = service.procesar_periodo(periodo.id)
            
            assert resultado["periodo_id"] == periodo.id
            assert resultado["liquidaciones_procesadas"] == 1
            assert resultado["estado"] == "procesada"
    
    def test_pagar_periodo(self, db_session):
        """Pagar período de nómina"""
        service = NominaService(db_session)
        
        # Crear y procesar período
        periodo_data = PeriodoNominaCreate(
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31)
        )
        periodo = service.crear_periodo(periodo_data)
        
        empleado = db_session.query(Empleado).first()
        if empleado:
            liq_data = LiquidacionNominaCreate(
                periodo_id=periodo.id,
                empleado_id=empleado.id,
                salario_base=Decimal("2500000")
            )
            service.crear_liquidacion(liq_data)
            service.procesar_periodo(periodo.id)
            
            # Pagar
            resultado = service.pagar_periodo(periodo.id)
            
            assert resultado["estado"] == "pagada"


class TestNominaServiceEstadisticas:
    """Tests para estadísticas"""
    
    def test_obtener_estadisticas(self, db_session):
        """Obtener estadísticas de nómina"""
        service = NominaService(db_session)
        stats = service.obtener_estadisticas()
        
        assert "total_empleados" in stats
        assert "total_liquidaciones" in stats
        assert "monto_total_neto" in stats
        assert stats["total_empleados"] >= 0
    
    def test_obtener_deuda_empleado(self, db_session):
        """Obtener deuda de empleado"""
        service = NominaService(db_session)
        empleado = db_session.query(Empleado).first()
        
        if empleado:
            deuda = service.obtener_deuda_empleado(empleado.id)
            assert isinstance(deuda, Decimal)
            assert deuda >= Decimal("0")
