"""
Service layer para Nómina (Payroll Management) - FASE 4
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import (
    LiquidacionNomina, PeriodoNomina, Empleado, ParametrosNomina
)
from .schemas import (
    LiquidacionNominaCreate, LiquidacionNominaUpdate, 
    PeriodoNominaCreate, DetalleDevengadoCreate, DetalleDeduccionCreate
)

logger = logging.getLogger(__name__)


class NominaService:
    """Servicio de gestión de nómina (payroll)"""

    def __init__(self, db: Session):
        self.db = db
        logger.debug("NominaService inicializado")

    # ========================================================================
    # PERÍODOS DE NÓMINA
    # ========================================================================

    def crear_periodo(self, periodo_data: PeriodoNominaCreate) -> PeriodoNomina:
        """Crear nuevo período de nómina"""
        # Validar que las fechas sean válidas
        if periodo_data.fecha_inicio >= periodo_data.fecha_fin:
            raise ValueError("fecha_inicio debe ser menor a fecha_fin")

        periodo = PeriodoNomina(
            fecha_inicio=periodo_data.fecha_inicio,
            fecha_fin=periodo_data.fecha_fin,
            periodicidad=periodo_data.periodicidad,
            estado="borrador"
        )

        self.db.add(periodo)
        self.db.commit()
        self.db.refresh(periodo)

        logger.info(
            f"Período de nómina {periodo.id} creado: "
            f"{periodo.fecha_inicio} a {periodo.fecha_fin}"
        )
        return periodo

    def obtener_periodo(self, periodo_id: int) -> Optional[PeriodoNomina]:
        """Obtener período por ID"""
        periodo = self.db.query(PeriodoNomina).filter(
            PeriodoNomina.id == periodo_id
        ).first()
        if not periodo:
            logger.warning(f"Período {periodo_id} no encontrado")
        return periodo

    def listar_periodos(self) -> List[PeriodoNomina]:
        """Listar todos los períodos de nómina"""
        periodos = self.db.query(PeriodoNomina).order_by(
            PeriodoNomina.fecha_inicio.desc()
        ).all()
        return periodos

    def obtener_periodo_actual(self) -> Optional[PeriodoNomina]:
        """Obtener período que contiene la fecha actual"""
        hoy = date.today()
        periodo = self.db.query(PeriodoNomina).filter(
            PeriodoNomina.fecha_inicio <= hoy,
            PeriodoNomina.fecha_fin >= hoy
        ).first()
        return periodo

    # ========================================================================
    # LIQUIDACIONES DE NÓMINA
    # ========================================================================

    def crear_liquidacion(self, liquidacion_data: LiquidacionNominaCreate) -> LiquidacionNomina:
        """Crear liquidación de nómina para un empleado"""
        # Validar periodo
        periodo = self.obtener_periodo(liquidacion_data.periodo_id)
        if not periodo:
            raise ValueError(f"Período {liquidacion_data.periodo_id} no existe")

        # Validar empleado
        empleado = self.db.query(Empleado).filter(
            Empleado.id == liquidacion_data.empleado_id
        ).first()
        if not empleado:
            raise ValueError(f"Empleado {liquidacion_data.empleado_id} no existe")

        # Calcular aportes automáticos
        salario_diario = liquidacion_data.salario_base / Decimal("30")
        salario_liquidado = salario_diario * liquidacion_data.dias_liquidados

        # Devengados (salario base)
        devengados = salario_liquidado

        # Deducciones (salud 4% + pensión 4%)
        deduccion_salud = salario_liquidado * Decimal("0.04")
        deduccion_pension = salario_liquidado * Decimal("0.04")
        deducciones = deduccion_salud + deduccion_pension

        # Neto = Devengados - Deducciones
        neto = devengados - deducciones

        liquidacion = LiquidacionNomina(
            periodo_id=liquidacion_data.periodo_id,
            empleado_id=liquidacion_data.empleado_id,
            dias_liquidados=liquidacion_data.dias_liquidados,
            salario_base=liquidacion_data.salario_base,
            devengados=devengados,
            deducciones=deducciones,
            neto=neto,
            estado_electronico="pendiente_configuracion"
        )

        self.db.add(liquidacion)
        self.db.commit()
        self.db.refresh(liquidacion)

        logger.info(
            f"Liquidación {liquidacion.id} creada para empleado {empleado.nombre}: "
            f"Neto ${neto}"
        )
        return liquidacion

    def obtener_liquidacion(self, liquidacion_id: int) -> Optional[LiquidacionNomina]:
        """Obtener liquidación por ID"""
        liquidacion = self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.id == liquidacion_id
        ).first()
        return liquidacion

    def listar_liquidaciones_periodo(
        self, periodo_id: int
    ) -> List[LiquidacionNomina]:
        """Listar liquidaciones de un período"""
        liquidaciones = self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.periodo_id == periodo_id
        ).all()
        return liquidaciones

    def listar_liquidaciones_empleado(
        self, empleado_id: int
    ) -> List[LiquidacionNomina]:
        """Listar liquidaciones de un empleado"""
        liquidaciones = self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.empleado_id == empleado_id
        ).order_by(LiquidacionNomina.id.desc()).all()
        return liquidaciones

    def actualizar_liquidacion(
        self, liquidacion_id: int, data: LiquidacionNominaUpdate
    ) -> LiquidacionNomina:
        """Actualizar datos de liquidación"""
        liquidacion = self.obtener_liquidacion(liquidacion_id)
        if not liquidacion:
            raise ValueError(f"Liquidación {liquidacion_id} no existe")

        if liquidacion.estado_electronico != "pendiente_configuracion":
            raise ValueError(
                f"No se puede modificar liquidación en estado {liquidacion.estado_electronico}"
            )

        if data.dias_liquidados is not None:
            liquidacion.dias_liquidados = data.dias_liquidados

        if data.salario_base is not None:
            liquidacion.salario_base = data.salario_base

        # Recalcular montos
        salario_diario = liquidacion.salario_base / Decimal("30")
        salario_liquidado = salario_diario * liquidacion.dias_liquidados
        liquidacion.devengados = salario_liquidado
        liquidacion.deducciones = salario_liquidado * Decimal("0.08")  # 4% + 4%
        liquidacion.neto = liquidacion.devengados - liquidacion.deducciones

        self.db.commit()
        self.db.refresh(liquidacion)

        logger.info(f"Liquidación {liquidacion_id} actualizada")
        return liquidacion

    def procesar_periodo(self, periodo_id: int) -> Dict:
        """Procesar todas las liquidaciones de un período"""
        periodo = self.obtener_periodo(periodo_id)
        if not periodo:
            raise ValueError(f"Período {periodo_id} no existe")

        if periodo.estado != "borrador":
            raise ValueError(f"Período ya ha sido procesado: {periodo.estado}")

        # Obtener todas las liquidaciones
        liquidaciones = self.listar_liquidaciones_periodo(periodo_id)

        if not liquidaciones:
            raise ValueError(f"No hay liquidaciones para procesar en período {periodo_id}")

        # Cambiar estado
        periodo.estado = "procesada"

        total_neto = Decimal("0")
        for liq in liquidaciones:
            total_neto += liq.neto

        self.db.commit()

        logger.info(
            f"Período {periodo_id} procesado: "
            f"{len(liquidaciones)} liquidaciones, Total neto: ${total_neto}"
        )

        return {
            "periodo_id": periodo_id,
            "liquidaciones_procesadas": len(liquidaciones),
            "total_neto": total_neto,
            "estado": periodo.estado
        }

    def pagar_periodo(self, periodo_id: int) -> Dict:
        """Marcar período como pagado"""
        periodo = self.obtener_periodo(periodo_id)
        if not periodo:
            raise ValueError(f"Período {periodo_id} no existe")

        if periodo.estado != "procesada":
            raise ValueError(
                f"Período debe estar procesado para pagar. Estado actual: {periodo.estado}"
            )

        periodo.estado = "pagada"
        self.db.commit()

        liquidaciones = self.listar_liquidaciones_periodo(periodo_id)
        total_pagado = sum((l.neto for l in liquidaciones), Decimal("0"))

        logger.info(f"Período {periodo_id} marcado como pagado - Total: ${total_pagado}")

        return {
            "periodo_id": periodo_id,
            "estado": periodo.estado,
            "total_pagado": total_pagado
        }

    # ========================================================================
    # ESTADÍSTICAS Y REPORTES
    # ========================================================================

    def obtener_estadisticas(self, periodo_id: Optional[int] = None) -> Dict:
        """Obtener estadísticas de nómina"""
        query_liq = self.db.query(LiquidacionNomina)

        if periodo_id:
            query_liq = query_liq.filter(LiquidacionNomina.periodo_id == periodo_id)

        liquidaciones = query_liq.all()

        total_empleados = len(set(l.empleado_id for l in liquidaciones))
        total_neto = sum((l.neto for l in liquidaciones), Decimal("0"))
        total_devengados = sum((l.devengados for l in liquidaciones), Decimal("0"))
        total_deducciones = sum((l.deducciones for l in liquidaciones), Decimal("0"))

        promedio_salario = (
            total_neto / total_empleados if total_empleados > 0 else None
        )

        return {
            "total_empleados": total_empleados,
            "total_liquidaciones": len(liquidaciones),
            "nominas_procesadas": len([l for l in liquidaciones]),
            "nominas_pagadas": 0,
            "monto_total_devengados": total_devengados,
            "monto_total_deducciones": total_deducciones,
            "monto_total_neto": total_neto,
            "promedio_salario": promedio_salario
        }

    def obtener_recibo_nomina(self, liquidacion_id: int) -> Dict:
        """Generar recibo de nómina"""
        liquidacion = self.obtener_liquidacion(liquidacion_id)
        if not liquidacion:
            return None

        empleado = self.db.query(Empleado).filter(
            Empleado.id == liquidacion.empleado_id
        ).first()

        periodo = self.obtener_periodo(liquidacion.periodo_id)

        return {
            "id": liquidacion_id,
            "empleado_nombre": empleado.nombre if empleado else "N/A",
            "documento": empleado.documento if empleado else "N/A",
            "periodo": f"{periodo.fecha_inicio} a {periodo.fecha_fin}" if periodo else "N/A",
            "dias_liquidados": liquidacion.dias_liquidados,
            "salario_base": liquidacion.salario_base,
            "devengados": liquidacion.devengados,
            "deducciones": liquidacion.deducciones,
            "neto": liquidacion.neto,
            "fecha_generacion": datetime.utcnow()
        }

    def obtener_deuda_empleado(self, empleado_id: int) -> Decimal:
        """Calcular deuda acumulada de un empleado (nóminas pendientes de pago)"""
        # En este caso simplificado, retornamos el total de nóminas no pagadas
        liquidaciones = self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.empleado_id == empleado_id
        ).all()

        return sum((l.neto for l in liquidaciones), Decimal("0"))
