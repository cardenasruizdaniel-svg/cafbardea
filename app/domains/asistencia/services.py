"""Servicio de Asistencia (control de marcaciones).

Registra las marcaciones de los empleados (entrada, receso, salida), calcula
las horas efectivamente trabajadas descontando los recesos, determina las horas
extra diarias (lo que exceda la jornada) y, al cerrar el turno, genera
automaticamente la novedad de nomina correspondiente.

La jornada extra se cuenta por dia: lo que exceda las horas ordinarias diarias
configuradas. El tipo de hora extra (diurna/nocturna) se determina por la hora
de salida.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Empleado, Marcacion, NovedadNomina, Turno, TurnoProgramado, hora_colombia,
)

logger = logging.getLogger(__name__)

CERO = Decimal("0")

# Jornada ordinaria diaria por defecto (horas). Lo que exceda es extra.
JORNADA_DIARIA_DEFAULT = Decimal("8")
# Franja nocturna en Colombia: 9:00 p.m. a 6:00 a.m.
INICIO_NOCTURNO = time(21, 0)
FIN_NOCTURNO = time(6, 0)


def _horas(td_segundos: float) -> Decimal:
    """Convierte segundos a horas decimales con 2 decimales."""
    return (Decimal(str(td_segundos)) / Decimal("3600")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


class AsistenciaService:
    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    # ------------------------------------------------------------------
    # Marcaciones
    # ------------------------------------------------------------------
    def turno_abierto(self, empleado_id: int) -> Optional[Turno]:
        return self.db.scalar(
            select(Turno).where(Turno.empleado_id == empleado_id,
                                Turno.estado.in_(("abierto", "en_receso"))))

    def marcar_entrada(self, empleado_id: int, *, empresa_id: int = 1,
                       momento: Optional[datetime] = None,
                       origen: str = "manual") -> Turno:
        empleado = self.db.get(Empleado, empleado_id)
        if not empleado:
            raise ValueError(f"Empleado {empleado_id} no existe")
        if self.turno_abierto(empleado_id):
            raise ValueError("El empleado ya tiene un turno abierto")

        momento = momento or hora_colombia()
        # Buscar turno programado del dia para medir tardanza
        programado = self.db.scalar(
            select(TurnoProgramado).where(
                TurnoProgramado.empleado_id == empleado_id,
                TurnoProgramado.fecha == momento.date()))

        tardanza = 0
        if programado:
            esperado = datetime.combine(momento.date(), programado.hora_entrada)
            atraso_min = (momento - esperado).total_seconds() / 60
            if atraso_min > programado.tolerancia_min:
                tardanza = int(atraso_min)

        turno = Turno(
            empresa_id=empresa_id, empleado_id=empleado_id, entrada=momento,
            estado="abierto", minutos_tardanza=tardanza,
            programado_id=programado.id if programado else None)
        self.db.add(turno)
        self.db.flush()
        self.db.add(Marcacion(turno_id=turno.id, tipo="entrada",
                              momento=momento, origen=origen))
        self.db.flush()
        return turno

    def marcar_salida_receso(self, empleado_id: int,
                             momento: Optional[datetime] = None) -> Turno:
        turno = self.turno_abierto(empleado_id)
        if not turno:
            raise ValueError("El empleado no tiene un turno abierto")
        if turno.estado == "en_receso":
            raise ValueError("El empleado ya esta en receso")
        momento = momento or hora_colombia()
        turno.estado = "en_receso"
        self.db.add(Marcacion(turno_id=turno.id, tipo="salida_receso",
                              momento=momento))
        self.db.flush()
        return turno

    def marcar_regreso_receso(self, empleado_id: int,
                              momento: Optional[datetime] = None) -> Turno:
        turno = self.turno_abierto(empleado_id)
        if not turno:
            raise ValueError("El empleado no tiene un turno abierto")
        if turno.estado != "en_receso":
            raise ValueError("El empleado no esta en receso")
        momento = momento or hora_colombia()
        turno.estado = "abierto"
        self.db.add(Marcacion(turno_id=turno.id, tipo="regreso_receso",
                              momento=momento))
        self.db.flush()
        return turno

    def marcar_salida(self, empleado_id: int, *,
                      momento: Optional[datetime] = None,
                      jornada_diaria: Decimal = JORNADA_DIARIA_DEFAULT,
                      generar_novedad: bool = True) -> Turno:
        turno = self.turno_abierto(empleado_id)
        if not turno:
            raise ValueError("El empleado no tiene un turno abierto")
        momento = momento or hora_colombia()
        if momento < turno.entrada:
            raise ValueError("La salida no puede ser anterior a la entrada")

        # Si estaba en receso, cerrar el receso primero
        if turno.estado == "en_receso":
            self.db.add(Marcacion(turno_id=turno.id, tipo="regreso_receso",
                                  momento=momento))
        turno.salida = momento
        self.db.add(Marcacion(turno_id=turno.id, tipo="salida", momento=momento))
        turno.estado = "cerrado"
        self.db.flush()

        self._calcular_horas(turno, jornada_diaria)
        if generar_novedad:
            self._generar_novedad(turno)
        self.db.flush()
        return turno

    # ------------------------------------------------------------------
    # Calculo de horas
    # ------------------------------------------------------------------
    def _calcular_horas(self, turno: Turno, jornada_diaria: Decimal) -> None:
        """Calcula horas trabajadas descontando recesos y separa extra."""
        marcaciones = sorted(turno.marcaciones, key=lambda m: m.momento)

        # Sumar el tiempo de receso (entre salida_receso y regreso_receso)
        receso_seg = 0.0
        inicio_receso = None
        for m in marcaciones:
            if m.tipo == "salida_receso":
                inicio_receso = m.momento
            elif m.tipo == "regreso_receso" and inicio_receso:
                receso_seg += (m.momento - inicio_receso).total_seconds()
                inicio_receso = None

        bruto_seg = (turno.salida - turno.entrada).total_seconds()
        trabajado_seg = max(0.0, bruto_seg - receso_seg)

        horas_trabajadas = _horas(trabajado_seg)
        horas_receso = _horas(receso_seg)

        # Ordinarias vs extra (por exceso sobre la jornada diaria)
        if horas_trabajadas > jornada_diaria:
            ordinarias = jornada_diaria
            extra = horas_trabajadas - jornada_diaria
        else:
            ordinarias = horas_trabajadas
            extra = CERO

        # Tipo de jornada por la hora de salida (simplificado):
        # si sale dentro de la franja nocturna, la extra es nocturna.
        hora_salida = turno.salida.time()
        es_nocturna = hora_salida >= INICIO_NOCTURNO or hora_salida < FIN_NOCTURNO
        es_domingo = turno.entrada.weekday() == 6  # 6 = domingo

        turno.horas_trabajadas = horas_trabajadas
        turno.horas_receso = horas_receso
        turno.horas_ordinarias = ordinarias
        turno.horas_nocturnas = extra if (es_nocturna and not es_domingo) else CERO
        turno.horas_dominicales = horas_trabajadas if es_domingo else CERO
        if es_nocturna:
            turno.horas_extra_nocturna = extra
            turno.horas_extra_diurna = CERO
        else:
            turno.horas_extra_diurna = extra
            turno.horas_extra_nocturna = CERO

    def _generar_novedad(self, turno: Turno) -> None:
        """Crea la novedad de nomina por las horas extra del turno."""
        extra_diurna = turno.horas_extra_diurna or CERO
        extra_nocturna = turno.horas_extra_nocturna or CERO
        if extra_diurna <= 0 and extra_nocturna <= 0:
            return

        es_domingo = turno.entrada.weekday() == 6
        if extra_nocturna > 0:
            tipo = "he_dominical_nocturna" if es_domingo else "he_nocturna"
            cantidad = extra_nocturna
        else:
            tipo = "he_dominical_diurna" if es_domingo else "he_diurna"
            cantidad = extra_diurna

        nov = NovedadNomina(
            empresa_id=turno.empresa_id, empleado_id=turno.empleado_id,
            tipo=tipo, cantidad=cantidad, fecha=turno.entrada.date(),
            descripcion=f"Horas extra del turno #{turno.id} "
                        f"({turno.entrada:%Y-%m-%d})",
            constitutivo_salario=True)
        self.db.add(nov)
        self.db.flush()
        turno.novedad_generada_id = nov.id

    def anular_turno(self, turno_id: int) -> Turno:
        """Anula un turno y, si genero novedad no aplicada, la elimina."""
        turno = self.db.get(Turno, turno_id)
        if not turno:
            raise ValueError(f"Turno {turno_id} no existe")
        if turno.novedad_generada_id:
            nov = self.db.get(NovedadNomina, turno.novedad_generada_id)
            if nov and not nov.aplicada:
                self.db.delete(nov)
                turno.novedad_generada_id = None
            elif nov and nov.aplicada:
                raise ValueError(
                    "No se puede anular: la novedad ya fue liquidada en nomina")
        turno.estado = "anulado"
        self.db.flush()
        return turno

    # ------------------------------------------------------------------
    # Turnos programados
    # ------------------------------------------------------------------
    def programar_turno(self, empleado_id: int, fecha: date,
                        hora_entrada: time, hora_salida: time, *,
                        empresa_id: int = 1, tolerancia_min: int = 5
                        ) -> TurnoProgramado:
        empleado = self.db.get(Empleado, empleado_id)
        if not empleado:
            raise ValueError(f"Empleado {empleado_id} no existe")
        prog = TurnoProgramado(
            empresa_id=empresa_id, empleado_id=empleado_id, fecha=fecha,
            hora_entrada=hora_entrada, hora_salida=hora_salida,
            tolerancia_min=tolerancia_min)
        self.db.add(prog)
        self.db.flush()
        return prog

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def resumen_empleado(self, empleado_id: int, desde: date, hasta: date
                         ) -> dict:
        turnos = self.db.scalars(
            select(Turno).where(
                Turno.empleado_id == empleado_id,
                Turno.estado == "cerrado",
                Turno.entrada >= datetime.combine(desde, time.min),
                Turno.entrada <= datetime.combine(hasta, time.max))).all()
        total_trab = sum((t.horas_trabajadas or CERO for t in turnos), CERO)
        total_extra = sum(((t.horas_extra_diurna or CERO)
                           + (t.horas_extra_nocturna or CERO) for t in turnos), CERO)
        total_tardanza = sum((t.minutos_tardanza or 0 for t in turnos), 0)
        return {
            "empleado_id": empleado_id,
            "turnos": len(turnos),
            "horas_trabajadas": total_trab,
            "horas_extra": total_extra,
            "minutos_tardanza": total_tardanza,
        }
