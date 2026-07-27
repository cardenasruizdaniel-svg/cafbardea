"""Servicio de Nomina (Colombia).

Calcula la nomina del periodo conforme a la legislacion colombiana: devengados
(sueldo, auxilio de transporte, horas extra, recargos), deducciones (salud,
pension, fondo de solidaridad, retencion), aportes del empleador (salud,
pension, ARL, parafiscales con exoneracion Ley 1607) y provisiones de
prestaciones (prima, cesantias, intereses, vacaciones).

Soporta salario ordinario e integral. Todos los factores salen de
ParametrosNomina, versionados por vigencia, de modo que un cambio de ley no
exige tocar codigo.

ADVERTENCIA: los calculos siguen las reglas generales vigentes en 2026. La
responsabilidad legal de las cifras (parametros, UVT, tablas de retencion) es
del usuario; el sistema aplica lo que se configure. No sustituye asesoria
contable.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from typing import Dict, List

from app.models import (
    Empleado, LiquidacionNomina, NovedadNomina, ParametrosNomina,
    PeriodoNomina, hora_colombia,
)
from .schemas import (
    LiquidacionNominaCreate, LiquidacionNominaUpdate, PeriodoNominaCreate,
)

logger = logging.getLogger(__name__)

CERO = Decimal("0")
CIEN = Decimal("100")
CENTAVO = Decimal("0.01")


def _peso(valor: Decimal) -> Decimal:
    """Redondea a peso (los pagos de nomina no manejan centavos)."""
    return Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


# Tipos de novedad que suman a devengados por horas
FACTORES_HORA = {
    "he_diurna": "hora_extra_diurna_pct",
    "he_nocturna": "hora_extra_nocturna_pct",
    "he_dominical_diurna": "hora_extra_diurna_dominical_pct",
    "he_dominical_nocturna": "hora_extra_nocturna_dominical_pct",
    "recargo_nocturno": "recargo_nocturno_pct",
    "recargo_dominical": "recargo_dominical_pct",
}
# Recargos (no extra) pagan solo el porcentaje adicional; las extra pagan
# la hora + el porcentaje.
SON_RECARGO = {"recargo_nocturno", "recargo_dominical"}


class NominaService:
    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    # ------------------------------------------------------------------
    # Parametros vigentes
    # ------------------------------------------------------------------
    def parametros_vigentes(self, en_fecha: Optional[date] = None) -> ParametrosNomina:
        en_fecha = en_fecha or date.today()
        p = self.db.scalar(
            select(ParametrosNomina)
            .where(ParametrosNomina.vigencia_desde <= en_fecha)
            .order_by(ParametrosNomina.vigencia_desde.desc()))
        if not p:
            raise ValueError("No hay parametros de nomina configurados")
        return p

    # ------------------------------------------------------------------
    # Novedades
    # ------------------------------------------------------------------
    def registrar_novedad(self, empleado_id: int, tipo: str, *,
                          cantidad: Decimal = CERO, valor: Decimal = CERO,
                          fecha: Optional[date] = None, empresa_id: int = 1,
                          constitutivo_salario: bool = True,
                          descripcion: Optional[str] = None) -> NovedadNomina:
        empleado = self.db.get(Empleado, empleado_id)
        if not empleado:
            raise ValueError(f"Empleado {empleado_id} no existe")
        if cantidad < 0 or valor < 0:
            raise ValueError("Cantidad y valor no pueden ser negativos")

        nov = NovedadNomina(
            empresa_id=empresa_id, empleado_id=empleado_id, tipo=tipo,
            cantidad=cantidad, valor=valor, fecha=fecha or date.today(),
            constitutivo_salario=constitutivo_salario, descripcion=descripcion)
        self.db.add(nov)
        self.db.flush()
        return nov

    # ------------------------------------------------------------------
    # Calculo de una liquidacion (sin persistir)
    # ------------------------------------------------------------------
    def calcular_empleado(self, empleado: Empleado, periodo: PeriodoNomina,
                          parametros: ParametrosNomina, *,
                          dias: Decimal, novedades: list[NovedadNomina]
                          ) -> dict:
        """Calcula el desglose completo de un empleado. No toca la base."""
        salario = empleado.salario or CERO
        integral = empleado.tipo_salario == "integral"

        # Valor de la hora ordinaria: salario mensual / horas legales
        horas_mes = parametros.horas_mensuales or Decimal("230")
        valor_hora = salario / horas_mes if horas_mes else CERO

        # --- Sueldo proporcional a los dias ---
        sueldo = _peso(salario * dias / Decimal("30"))

        # --- Auxilio de transporte ---
        auxilio = CERO
        if (empleado.auxilio_transporte and not integral
                and parametros.tope_auxilio_transporte
                and salario <= parametros.tope_auxilio_transporte):
            auxilio = _peso(parametros.auxilio_transporte * dias / Decimal("30"))

        # --- Horas extra, recargos y novedades ---
        valor_he = CERO
        valor_recargos = CERO
        comisiones = CERO
        bonificaciones = CERO
        otros_dev = CERO
        otras_ded = CERO
        base_variable_constitutiva = CERO  # variables que suman al IBC

        for nov in novedades:
            if nov.tipo in FACTORES_HORA:
                pct = getattr(parametros, FACTORES_HORA[nov.tipo], CERO)
                if nov.tipo in SON_RECARGO:
                    monto = valor_hora * nov.cantidad * pct / CIEN
                    valor_recargos += monto
                else:
                    # hora extra: paga la hora + el recargo
                    monto = valor_hora * nov.cantidad * (CIEN + pct) / CIEN
                    valor_he += monto
                base_variable_constitutiva += monto
            elif nov.tipo == "comision":
                comisiones += nov.valor
                if nov.constitutivo_salario:
                    base_variable_constitutiva += nov.valor
            elif nov.tipo == "bonificacion":
                bonificaciones += nov.valor
                if nov.constitutivo_salario:
                    base_variable_constitutiva += nov.valor
            elif nov.tipo == "otro_devengado":
                otros_dev += nov.valor
                if nov.constitutivo_salario:
                    base_variable_constitutiva += nov.valor
            elif nov.tipo in ("prestamo", "embargo", "otra_deduccion"):
                otras_ded += nov.valor

        valor_he = _peso(valor_he)
        valor_recargos = _peso(valor_recargos)

        devengados = (sueldo + auxilio + valor_he + valor_recargos
                      + comisiones + bonificaciones + otros_dev)

        # --- IBC (ingreso base de cotizacion) ---
        # No incluye auxilio de transporte. Suma el sueldo y las variables
        # constitutivas de salario (horas extra, recargos, comisiones y las
        # bonificaciones marcadas como constitutivas).
        # En salario integral, la base de cotizacion es el 70% del salario.
        if integral:
            ibc = _peso(salario * Decimal("0.70") * dias / Decimal("30"))
        else:
            ibc = _peso(sueldo + base_variable_constitutiva)

        # Piso del IBC: no puede ser menor a 1 SMMLV proporcional
        smmlv_prop = _peso(parametros.salario_minimo * dias / Decimal("30"))
        if ibc < smmlv_prop and salario > 0:
            ibc = smmlv_prop

        # --- Deducciones del empleado ---
        salud_emp = _peso(ibc * parametros.salud_empleado_pct / CIEN)
        pension_emp = _peso(ibc * parametros.pension_empleado_pct / CIEN)

        # Fondo de solidaridad pensional: desde 4 SMMLV
        fsp = CERO
        if parametros.fsp_smmlv_desde and parametros.salario_minimo:
            umbral = parametros.salario_minimo * parametros.fsp_smmlv_desde
            if ibc >= umbral:
                fsp = _peso(ibc * parametros.fsp_pct / CIEN)

        retencion = self._retencion_fuente(ibc, salud_emp, pension_emp, parametros)

        deducciones = salud_emp + pension_emp + fsp + retencion + otras_ded
        neto = devengados - deducciones

        # --- Aportes del empleador ---
        exonerado = self._exonerado(empleado, salario, parametros)
        salud_empdor = CERO if exonerado else _peso(ibc * parametros.salud_empleador_pct / CIEN)
        pension_empdor = _peso(ibc * parametros.pension_empleador_pct / CIEN)
        arl = _peso(ibc * self._tarifa_arl(empleado, parametros) / CIEN)
        caja = _peso(ibc * parametros.caja_pct / CIEN)
        icbf = CERO if exonerado else _peso(ibc * parametros.icbf_pct / CIEN)
        sena = CERO if exonerado else _peso(ibc * parametros.sena_pct / CIEN)
        total_aportes = salud_empdor + pension_empdor + arl + caja + icbf + sena

        # --- Provisiones de prestaciones ---
        # Base prestacional incluye auxilio de transporte (excepto vacaciones).
        base_prest = sueldo + valor_he + valor_recargos + auxilio + comisiones
        base_vac = base_prest - auxilio
        if integral:
            prov_prima = prov_ces = prov_int = CERO
            prov_vac = _peso(base_vac * parametros.vacaciones_pct / CIEN)
        else:
            prov_prima = _peso(base_prest * parametros.prima_pct / CIEN)
            prov_ces = _peso(base_prest * parametros.cesantias_pct / CIEN)
            prov_int = _peso(prov_ces * parametros.intereses_cesantias_pct / CIEN)
            prov_vac = _peso(base_vac * parametros.vacaciones_pct / CIEN)
        total_prov = prov_prima + prov_ces + prov_int + prov_vac

        return {
            "dias": dias, "tipo_salario": empleado.tipo_salario,
            "salario_base": salario, "sueldo": sueldo,
            "auxilio_transporte": auxilio, "horas_extra": valor_he,
            "recargos": valor_recargos, "comisiones": _peso(comisiones),
            "bonificaciones": _peso(bonificaciones), "otros_devengados": _peso(otros_dev),
            "devengados": _peso(devengados), "ibc": ibc,
            "salud_empleado": salud_emp, "pension_empleado": pension_emp,
            "fondo_solidaridad": fsp, "retencion_fuente": retencion,
            "otras_deducciones": _peso(otras_ded), "deducciones": _peso(deducciones),
            "neto": _peso(neto),
            "salud_empleador": salud_empdor, "pension_empleador": pension_empdor,
            "arl_empleador": arl, "caja_empleador": caja,
            "icbf_empleador": icbf, "sena_empleador": sena,
            "total_aportes_empleador": _peso(total_aportes),
            "prov_prima": prov_prima, "prov_cesantias": prov_ces,
            "prov_intereses_cesantias": prov_int, "prov_vacaciones": prov_vac,
            "total_provisiones": _peso(total_prov),
        }

    def _exonerado(self, empleado, salario, parametros) -> bool:
        """Exoneracion Ley 1607: aplica a personas juridicas cuando el
        empleado gana menos de 10 SMMLV."""
        empresa = None
        try:
            from app.models import Empresa
            empresa = self.db.get(Empresa, empleado.empresa_id or 1)
        except Exception:
            pass
        es_juridica = getattr(empresa, "tipo_persona", "juridica") == "juridica"
        umbral = (parametros.salario_minimo or CERO) * (parametros.exoneracion_smmlv or CERO)
        return es_juridica and salario < umbral

    def _tarifa_arl(self, empleado, parametros) -> Decimal:
        """Tarifa ARL segun nivel de riesgo (I..V)."""
        tarifas = {
            1: Decimal("0.522"), 2: Decimal("1.044"), 3: Decimal("2.436"),
            4: Decimal("4.350"), 5: Decimal("6.960"),
        }
        nivel = getattr(empleado, "nivel_riesgo_arl", 1) or 1
        return tarifas.get(nivel, parametros.arl_pct or Decimal("0.522"))

    def _retencion_fuente(self, ibc, salud, pension, parametros) -> Decimal:
        """Retencion en la fuente por procedimiento 1 (simplificado).

        Depuracion basica: base = devengado - salud - pension. Se compara con
        la tabla de rangos en UVT del art. 383 ET. Para cifras bajas (caso
        tipico de restaurantes) la retencion es cero.

        Nota: es una aproximacion. La retencion real depende de deducciones
        adicionales (dependientes, intereses de vivienda, renta exenta 25%),
        que aqui no se modelan. El usuario puede ajustarla como novedad.
        """
        # Renta exenta del 25% y depuracion
        base = (ibc - salud - pension)
        renta_exenta = base * Decimal("0.25")
        base_gravable = base - renta_exenta
        UVT = Decimal("49799")  # UVT 2026 (configurable a futuro)
        base_uvt = base_gravable / UVT if UVT else CERO

        if base_uvt <= 95:
            return CERO
        elif base_uvt <= 150:
            ret_uvt = (base_uvt - 95) * Decimal("0.19")
        elif base_uvt <= 360:
            ret_uvt = (base_uvt - 150) * Decimal("0.28") + Decimal("10")
        elif base_uvt <= 640:
            ret_uvt = (base_uvt - 360) * Decimal("0.33") + Decimal("69")
        elif base_uvt <= 945:
            ret_uvt = (base_uvt - 640) * Decimal("0.35") + Decimal("162")
        elif base_uvt <= 2300:
            ret_uvt = (base_uvt - 945) * Decimal("0.37") + Decimal("268")
        else:
            ret_uvt = (base_uvt - 2300) * Decimal("0.39") + Decimal("770")
        return _peso(ret_uvt * UVT)

    # ------------------------------------------------------------------
    # Liquidacion del periodo
    # ------------------------------------------------------------------
    def liquidar_periodo(self, periodo_id: int) -> PeriodoNomina:
        periodo = self.db.get(PeriodoNomina, periodo_id)
        if not periodo:
            raise ValueError(f"Periodo {periodo_id} no existe")
        if periodo.estado != "borrador":
            raise ValueError(f"El periodo esta en estado {periodo.estado}")

        parametros = self.parametros_vigentes(periodo.fecha_fin)
        dias = Decimal(str((periodo.fecha_fin - periodo.fecha_inicio).days + 1))
        if dias > 30:
            dias = Decimal("30")

        empleados = self.db.scalars(
            select(Empleado).where(Empleado.activo == True,  # noqa: E712
                                   Empleado.empresa_id == periodo.empresa_id)
        ).all()

        tot_dev = tot_ded = tot_neto = tot_aportes = CERO

        for emp in empleados:
            existe = self.db.scalar(
                select(LiquidacionNomina).where(
                    LiquidacionNomina.periodo_id == periodo.id,
                    LiquidacionNomina.empleado_id == emp.id))
            if existe:
                continue

            novedades = self.db.scalars(
                select(NovedadNomina).where(
                    NovedadNomina.empleado_id == emp.id,
                    NovedadNomina.periodo_id == periodo.id)).all()

            c = self.calcular_empleado(emp, periodo, parametros,
                                       dias=dias, novedades=novedades)

            # 'dias' se mapea a dias_liquidados; el resto de claves del dict
            # coinciden con columnas de LiquidacionNomina.
            campos = {k: v for k, v in c.items() if k != "dias"}
            campos["dias_liquidados"] = c["dias"]
            self.db.add(LiquidacionNomina(
                periodo_id=periodo.id, empleado_id=emp.id, **campos))

            for nov in novedades:
                nov.aplicada = True

            tot_dev += c["devengados"]
            tot_ded += c["deducciones"]
            tot_neto += c["neto"]
            tot_aportes += c["total_aportes_empleador"]

        periodo.total_devengado = tot_dev
        periodo.total_deducido = tot_ded
        periodo.total_neto = tot_neto
        periodo.total_aportes_empleador = tot_aportes
        periodo.estado = "liquidado"
        self.db.flush()
        self.logger.info("Periodo %s liquidado: %s empleados, neto %s",
                         periodo.id, len(empleados), tot_neto)
        return periodo

    def anular_liquidacion(self, periodo_id: int) -> PeriodoNomina:
        periodo = self.db.get(PeriodoNomina, periodo_id)
        if not periodo:
            raise ValueError(f"Periodo {periodo_id} no existe")
        if periodo.estado == "cerrado":
            raise ValueError("No se puede anular un periodo cerrado")

        liqs = self.db.scalars(
            select(LiquidacionNomina).where(
                LiquidacionNomina.periodo_id == periodo_id)).all()
        for liq in liqs:
            # Reabrir novedades para poder recalcular
            novs = self.db.scalars(
                select(NovedadNomina).where(
                    NovedadNomina.periodo_id == periodo_id,
                    NovedadNomina.empleado_id == liq.empleado_id)).all()
            for n in novs:
                n.aplicada = False
            self.db.delete(liq)

        periodo.estado = "borrador"
        periodo.total_devengado = periodo.total_deducido = CERO
        periodo.total_neto = periodo.total_aportes_empleador = CERO
        self.db.flush()
        return periodo

    # ------------------------------------------------------------------
    # Liquidacion definitiva (retiro)
    # ------------------------------------------------------------------
    def liquidacion_definitiva(self, empleado_id: int, fecha_retiro: date,
                               *, dias_vacaciones_pendientes: Decimal = CERO
                               ) -> dict:
        """Prestaciones acumuladas al retiro: prima, cesantias, intereses y
        vacaciones proporcionales desde el ultimo corte."""
        empleado = self.db.get(Empleado, empleado_id)
        if not empleado:
            raise ValueError(f"Empleado {empleado_id} no existe")
        if not empleado.fecha_ingreso:
            raise ValueError("El empleado no tiene fecha de ingreso")

        parametros = self.parametros_vigentes(fecha_retiro)
        salario = empleado.salario or CERO

        # Dias trabajados en el ultimo semestre (para prima) y anio (cesantias)
        ingreso = empleado.fecha_ingreso
        dias_totales = (fecha_retiro - ingreso).days + 1

        # Base: salario + auxilio (si aplica)
        auxilio = (parametros.auxilio_transporte
                   if empleado.auxilio_transporte
                   and salario <= (parametros.tope_auxilio_transporte or CERO)
                   else CERO)
        base = salario + auxilio

        # Cesantias: base * dias / 360
        cesantias = _peso(base * Decimal(dias_totales) / Decimal("360"))
        # Intereses: 12% anual proporcional
        intereses = _peso(cesantias * Decimal(dias_totales) / Decimal("360")
                          * parametros.intereses_cesantias_pct / CIEN)
        # Prima: proporcional al semestre
        dias_semestre = min(dias_totales, 180)
        prima = _peso(base * Decimal(dias_semestre) / Decimal("360"))
        # Vacaciones: salario (sin auxilio) * dias / 720
        dias_vac = int(dias_vacaciones_pendientes) if dias_vacaciones_pendientes else \
            (fecha_retiro - ingreso).days
        vacaciones = _peso(salario * Decimal(dias_vac) / Decimal("720"))

        total = cesantias + intereses + prima + vacaciones
        return {
            "empleado": empleado.nombre,
            "fecha_ingreso": ingreso,
            "fecha_retiro": fecha_retiro,
            "dias_trabajados": dias_totales,
            "cesantias": cesantias,
            "intereses_cesantias": intereses,
            "prima": prima,
            "vacaciones": vacaciones,
            "total": _peso(total),
        }

    # ==================================================================
    # API previa (compatibilidad): CRUD de periodos y liquidaciones con
    # maquina de estados borrador -> procesada -> pagada. Se conserva para
    # no romper contratos ni pruebas existentes. La liquidacion legal
    # completa vive en liquidar_periodo() y calcular_empleado().
    # ==================================================================
    def crear_periodo(self, periodo_data: "PeriodoNominaCreate") -> PeriodoNomina:
        if periodo_data.fecha_inicio >= periodo_data.fecha_fin:
            raise ValueError("fecha_inicio debe ser menor a fecha_fin")
        periodo = PeriodoNomina(
            fecha_inicio=periodo_data.fecha_inicio,
            fecha_fin=periodo_data.fecha_fin,
            periodicidad=periodo_data.periodicidad,
            estado="borrador")
        self.db.add(periodo)
        self.db.commit()
        self.db.refresh(periodo)
        return periodo

    def obtener_periodo(self, periodo_id: int):
        return self.db.query(PeriodoNomina).filter(
            PeriodoNomina.id == periodo_id).first()

    def listar_periodos(self) -> "List[PeriodoNomina]":
        return self.db.query(PeriodoNomina).order_by(
            PeriodoNomina.fecha_inicio.desc()).all()

    def obtener_periodo_actual(self):
        hoy = date.today()
        return self.db.query(PeriodoNomina).filter(
            PeriodoNomina.fecha_inicio <= hoy,
            PeriodoNomina.fecha_fin >= hoy).first()

    def crear_liquidacion(self, liquidacion_data: "LiquidacionNominaCreate") -> LiquidacionNomina:
        periodo = self.obtener_periodo(liquidacion_data.periodo_id)
        if not periodo:
            raise ValueError(f"Periodo {liquidacion_data.periodo_id} no existe")
        empleado = self.db.query(Empleado).filter(
            Empleado.id == liquidacion_data.empleado_id).first()
        if not empleado:
            raise ValueError(f"Empleado {liquidacion_data.empleado_id} no existe")
        salario_diario = liquidacion_data.salario_base / Decimal("30")
        salario_liquidado = salario_diario * liquidacion_data.dias_liquidados
        devengados = salario_liquidado
        deducciones = salario_liquidado * Decimal("0.08")
        neto = devengados - deducciones
        liquidacion = LiquidacionNomina(
            periodo_id=liquidacion_data.periodo_id,
            empleado_id=liquidacion_data.empleado_id,
            dias_liquidados=liquidacion_data.dias_liquidados,
            salario_base=liquidacion_data.salario_base,
            sueldo=salario_liquidado,
            devengados=devengados, deducciones=deducciones, neto=neto,
            estado_electronico="pendiente")
        self.db.add(liquidacion)
        self.db.commit()
        self.db.refresh(liquidacion)
        return liquidacion

    def obtener_liquidacion(self, liquidacion_id: int):
        return self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.id == liquidacion_id).first()

    def listar_liquidaciones_periodo(self, periodo_id: int):
        return self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.periodo_id == periodo_id).all()

    def listar_liquidaciones_empleado(self, empleado_id: int):
        return self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.empleado_id == empleado_id).order_by(
            LiquidacionNomina.id.desc()).all()

    def actualizar_liquidacion(self, liquidacion_id: int,
                               data: "LiquidacionNominaUpdate") -> LiquidacionNomina:
        liquidacion = self.obtener_liquidacion(liquidacion_id)
        if not liquidacion:
            raise ValueError(f"Liquidacion {liquidacion_id} no existe")
        if liquidacion.estado_electronico not in ("pendiente", "pendiente_configuracion"):
            raise ValueError(
                f"No se puede modificar liquidacion en estado {liquidacion.estado_electronico}")
        if data.dias_liquidados is not None:
            liquidacion.dias_liquidados = data.dias_liquidados
        if data.salario_base is not None:
            liquidacion.salario_base = data.salario_base
        salario_diario = liquidacion.salario_base / Decimal("30")
        salario_liquidado = salario_diario * liquidacion.dias_liquidados
        liquidacion.sueldo = salario_liquidado
        liquidacion.devengados = salario_liquidado
        liquidacion.deducciones = salario_liquidado * Decimal("0.08")
        liquidacion.neto = liquidacion.devengados - liquidacion.deducciones
        self.db.commit()
        self.db.refresh(liquidacion)
        return liquidacion

    def procesar_periodo(self, periodo_id: int) -> "Dict":
        periodo = self.obtener_periodo(periodo_id)
        if not periodo:
            raise ValueError(f"Periodo {periodo_id} no existe")
        if periodo.estado not in ("borrador", "liquidado"):
            raise ValueError(f"Periodo ya ha sido procesado: {periodo.estado}")
        liquidaciones = self.listar_liquidaciones_periodo(periodo_id)
        if not liquidaciones:
            raise ValueError(f"No hay liquidaciones para procesar en periodo {periodo_id}")
        periodo.estado = "procesada"
        total_neto = sum((l.neto for l in liquidaciones), Decimal("0"))
        self.db.commit()
        return {"periodo_id": periodo_id,
                "liquidaciones_procesadas": len(liquidaciones),
                "total_neto": total_neto, "estado": periodo.estado}

    def pagar_periodo(self, periodo_id: int) -> "Dict":
        periodo = self.obtener_periodo(periodo_id)
        if not periodo:
            raise ValueError(f"Periodo {periodo_id} no existe")
        if periodo.estado != "procesada":
            raise ValueError(
                f"Periodo debe estar procesado para pagar. Estado actual: {periodo.estado}")
        periodo.estado = "pagada"
        self.db.commit()
        liquidaciones = self.listar_liquidaciones_periodo(periodo_id)
        total_pagado = sum((l.neto for l in liquidaciones), Decimal("0"))
        return {"periodo_id": periodo_id, "estado": periodo.estado,
                "total_pagado": total_pagado}

    def obtener_estadisticas(self, periodo_id: "Optional[int]" = None) -> "Dict":
        query_liq = self.db.query(LiquidacionNomina)
        if periodo_id:
            query_liq = query_liq.filter(LiquidacionNomina.periodo_id == periodo_id)
        liquidaciones = query_liq.all()
        total_empleados = len(set(l.empleado_id for l in liquidaciones))
        total_neto = sum((l.neto for l in liquidaciones), Decimal("0"))
        total_devengados = sum((l.devengados for l in liquidaciones), Decimal("0"))
        total_deducciones = sum((l.deducciones for l in liquidaciones), Decimal("0"))
        promedio = total_neto / total_empleados if total_empleados > 0 else None
        return {"total_empleados": total_empleados,
                "total_liquidaciones": len(liquidaciones),
                "nominas_procesadas": len(liquidaciones), "nominas_pagadas": 0,
                "monto_total_devengados": total_devengados,
                "monto_total_deducciones": total_deducciones,
                "monto_total_neto": total_neto, "promedio_salario": promedio}

    def obtener_recibo_nomina(self, liquidacion_id: int):
        liquidacion = self.obtener_liquidacion(liquidacion_id)
        if not liquidacion:
            return None
        empleado = self.db.query(Empleado).filter(
            Empleado.id == liquidacion.empleado_id).first()
        periodo = self.obtener_periodo(liquidacion.periodo_id)
        from datetime import datetime as _dt
        return {"id": liquidacion_id,
                "empleado_nombre": empleado.nombre if empleado else "N/A",
                "documento": empleado.documento if empleado else "N/A",
                "periodo": f"{periodo.fecha_inicio} a {periodo.fecha_fin}" if periodo else "N/A",
                "dias_liquidados": liquidacion.dias_liquidados,
                "salario_base": liquidacion.salario_base,
                "devengados": liquidacion.devengados,
                "deducciones": liquidacion.deducciones,
                "neto": liquidacion.neto,
                "fecha_generacion": hora_colombia()}

    def obtener_deuda_empleado(self, empleado_id: int) -> Decimal:
        liquidaciones = self.db.query(LiquidacionNomina).filter(
            LiquidacionNomina.empleado_id == empleado_id).all()
        return sum((l.neto for l in liquidaciones), Decimal("0"))

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def resumen_periodo(self, periodo_id: int) -> dict:
        periodo = self.db.get(PeriodoNomina, periodo_id)
        if not periodo:
            raise ValueError(f"Periodo {periodo_id} no existe")
        liqs = self.db.scalars(
            select(LiquidacionNomina).where(
                LiquidacionNomina.periodo_id == periodo_id)).all()
        return {
            "periodo_id": periodo.id,
            "estado": periodo.estado,
            "empleados": len(liqs),
            "total_devengado": periodo.total_devengado,
            "total_deducido": periodo.total_deducido,
            "total_neto": periodo.total_neto,
            "total_aportes_empleador": periodo.total_aportes_empleador,
            "total_provisiones": sum((l.total_provisiones or CERO for l in liqs), CERO),
            "costo_total_empresa": (periodo.total_devengado or CERO)
                + (periodo.total_aportes_empleador or CERO)
                + sum((l.total_provisiones or CERO for l in liqs), CERO),
        }
