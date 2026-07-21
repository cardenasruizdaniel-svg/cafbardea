"""
Tests para validación de Schemas de Nómina - FASE 4
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pydantic import ValidationError

from app.domains.nomina.schemas import (
    EstadoNomina,
    TipoNomina,
    TipoDeduccion,
    TipoDevengado,
    PeriodoNominaCreate,
    PeriodoNominaResponse,
    LiquidacionNominaCreate,
    LiquidacionNominaUpdate,
    LiquidacionNominaResponse,
    DetalleDevengadoCreate,
    DetalleDeduccionCreate,
    ReciboNominaResponse,
    EstadisticasNomina,
    ProcesarNominaCreate
)


class TestEstadoNominaEnum:
    """Tests para enum EstadoNomina"""
    
    def test_estados_validos(self):
        """Verificar estados válidos"""
        estados = ["borrador", "procesada", "pagada", "revertida"]
        for estado in estados:
            assert estado in [e.value for e in EstadoNomina]


class TestTipoNominaEnum:
    """Tests para enum TipoNomina"""
    
    def test_tipos_validos(self):
        """Verificar tipos válidos"""
        tipos = ["ordinaria", "extraordinaria", "cesantia", "vacaciones"]
        for tipo in tipos:
            assert tipo in [t.value for t in TipoNomina]


class TestPeriodoNominaCreate:
    """Tests para schema PeriodoNominaCreate"""
    
    def test_crear_periodo_valido(self):
        """Crear período válido"""
        data = {
            "fecha_inicio": date(2026, 7, 1),
            "fecha_fin": date(2026, 7, 31),
            "periodicidad": "mensual"
        }
        periodo = PeriodoNominaCreate(**data)
        assert periodo.fecha_inicio == date(2026, 7, 1)
        assert periodo.fecha_fin == date(2026, 7, 31)
    
    def test_fechas_requeridas(self):
        """Fechas son obligatorias"""
        with pytest.raises(ValidationError):
            PeriodoNominaCreate()


class TestLiquidacionNominaCreate:
    """Tests para schema LiquidacionNominaCreate"""
    
    def test_crear_liquidacion_minima(self):
        """Crear liquidación con datos mínimos"""
        data = {
            "periodo_id": 1,
            "empleado_id": 5,
            "salario_base": Decimal("2500000")
        }
        liq = LiquidacionNominaCreate(**data)
        assert liq.periodo_id == 1
        assert liq.empleado_id == 5
        assert liq.dias_liquidados == Decimal("30")
    
    def test_conversión_string_a_decimal(self):
        """Convertir strings a Decimal"""
        data = {
            "periodo_id": 1,
            "empleado_id": 5,
            "dias_liquidados": "28",
            "salario_base": "2500000"
        }
        liq = LiquidacionNominaCreate(**data)
        assert liq.dias_liquidados == Decimal("28")
        assert liq.salario_base == Decimal("2500000")
    
    def test_campos_obligatorios(self):
        """Verificar campos obligatorios"""
        with pytest.raises(ValidationError):
            LiquidacionNominaCreate()
    
    def test_empleado_id_mayor_cero(self):
        """empleado_id debe ser > 0"""
        with pytest.raises(ValidationError):
            LiquidacionNominaCreate(
                periodo_id=1,
                empleado_id=0,
                salario_base=Decimal("2500000")
            )


class TestLiquidacionNominaUpdate:
    """Tests para schema LiquidacionNominaUpdate"""
    
    def test_actualizar_vacio(self):
        """Puede estar vacío"""
        liq = LiquidacionNominaUpdate()
        assert liq.dias_liquidados is None
        assert liq.salario_base is None
    
    def test_actualizar_parcial(self):
        """Actualizar solo algunos campos"""
        data = {"dias_liquidados": "28"}
        liq = LiquidacionNominaUpdate(**data)
        assert liq.dias_liquidados == Decimal("28")
        assert liq.salario_base is None


class TestDetalleDevengadoCreate:
    """Tests para agregar devengados"""
    
    def test_crear_devengado(self):
        """Crear devengado válido"""
        data = {
            "tipo": "horas_extra",
            "monto": Decimal("150000"),
            "descripcion": "8 horas extra"
        }
        dev = DetalleDevengadoCreate(**data)
        assert dev.tipo == "horas_extra"
        assert dev.monto == Decimal("150000")


class TestDetalleDeduccionCreate:
    """Tests para agregar deducciones"""
    
    def test_crear_deduccion(self):
        """Crear deducción válida"""
        data = {
            "tipo": "salud",
            "monto": Decimal("312500"),
            "descripcion": "Aporte EPS"
        }
        ded = DetalleDeduccionCreate(**data)
        assert ded.tipo == "salud"
        assert ded.monto == Decimal("312500")


class TestReciboNominaResponse:
    """Tests para recibo de nómina"""
    
    def test_recibo_estructura(self):
        """Verificar estructura de recibo"""
        data = {
            "id": 1,
            "empleado_nombre": "Juan García",
            "documento": "12345678",
            "periodo": "2026-07-01 a 2026-07-31",
            "dias_liquidados": Decimal("30"),
            "salario_base": Decimal("2500000"),
            "devengados": Decimal("2500000"),
            "deducciones": Decimal("625000"),
            "neto": Decimal("1875000"),
            "fecha_generacion": datetime.now()
        }
        recibo = ReciboNominaResponse(**data)
        assert recibo.empleado_nombre == "Juan García"
        assert recibo.neto == Decimal("1875000")


class TestEstadisticasNomina:
    """Tests para estadísticas"""
    
    def test_estadisticas_estructura(self):
        """Verificar estructura de estadísticas"""
        data = {
            "total_empleados": 25,
            "total_liquidaciones": 50,
            "nominas_procesadas": 45,
            "nominas_pagadas": 40,
            "monto_total_devengados": Decimal("62500000"),
            "monto_total_deducciones": Decimal("15625000"),
            "monto_total_neto": Decimal("46875000")
        }
        stats = EstadisticasNomina(**data)
        assert stats.total_empleados == 25
        assert stats.monto_total_neto == Decimal("46875000")


class TestProcesarNominaCreate:
    """Tests para procesar nómina"""
    
    def test_procesar_valido(self):
        """Crear procesamiento válido"""
        data = {
            "periodo_id": 1,
            "descripcion": "Nómina del mes de julio"
        }
        proc = ProcesarNominaCreate(**data)
        assert proc.periodo_id == 1
