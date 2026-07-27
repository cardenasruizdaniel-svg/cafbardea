"""Reglas de negocio de Asistencia (marcaciones y horas)."""
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.domains.asistencia.services import AsistenciaService
from app.models import Empleado, NovedadNomina, Turno

_cont = [0]


def _empleado(db_session, salario=1623500):
    _cont[0] += 1
    e = Empleado(nombre=f"Emp {_cont[0]}", documento=f"AST{_cont[0]:06d}",
                 cargo="Mesero", salario=Decimal(str(salario)), activo=True,
                 empresa_id=1)
    db_session.add(e)
    db_session.commit()
    return e


@pytest.fixture
def svc(db_session):
    return AsistenciaService(db_session)


class TestMarcacionBasica:
    def test_entrada_abre_turno(self, svc, db_session):
        emp = _empleado(db_session)
        t = svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        assert t.estado == "abierto"
        assert len(t.marcaciones) == 1

    def test_no_dos_turnos_abiertos(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        with pytest.raises(ValueError, match="ya tiene un turno"):
            svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 9, 0))

    def test_turno_8h_sin_extra(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 16, 0))
        db_session.commit()
        assert t.horas_trabajadas == Decimal("8.00")
        assert t.horas_extra_diurna == Decimal("0")


class TestReceso:
    def test_receso_se_descuenta(self, svc, db_session):
        emp = _empleado(db_session)
        # 8:00 entrada, receso 12:00-13:00, salida 17:00 => 8h trabajadas
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        svc.marcar_salida_receso(emp.id, momento=datetime(2026, 7, 20, 12, 0))
        db_session.commit()
        svc.marcar_regreso_receso(emp.id, momento=datetime(2026, 7, 20, 13, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 17, 0))
        db_session.commit()
        # 9h brutas - 1h receso = 8h trabajadas
        assert t.horas_receso == Decimal("1.00")
        assert t.horas_trabajadas == Decimal("8.00")
        assert t.horas_extra_diurna == Decimal("0")

    def test_no_regreso_sin_receso(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        with pytest.raises(ValueError, match="no esta en receso"):
            svc.marcar_regreso_receso(emp.id, momento=datetime(2026, 7, 20, 9, 0))


class TestHorasExtra:
    def test_dos_horas_extra_diurnas(self, svc, db_session):
        emp = _empleado(db_session)
        # 8:00 a 18:00 = 10h => 2h extra
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 18, 0))
        db_session.commit()
        assert t.horas_trabajadas == Decimal("10.00")
        assert t.horas_ordinarias == Decimal("8.00")
        assert t.horas_extra_diurna == Decimal("2.00")

    def test_extra_genera_novedad_automatica(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 18, 0))
        db_session.commit()
        assert t.novedad_generada_id is not None
        nov = db_session.get(NovedadNomina, t.novedad_generada_id)
        assert nov.tipo == "he_diurna"
        assert nov.cantidad == Decimal("2.00")

    def test_sin_extra_no_genera_novedad(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 16, 0))
        db_session.commit()
        assert t.novedad_generada_id is None

    def test_extra_nocturna(self, svc, db_session):
        emp = _empleado(db_session)
        # sale despues de las 9pm => extra nocturna
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 14, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 23, 0))
        db_session.commit()
        # 9h => 1h extra, nocturna
        assert t.horas_extra_nocturna == Decimal("1.00")
        nov = db_session.get(NovedadNomina, t.novedad_generada_id)
        assert nov.tipo == "he_nocturna"


class TestAnulacion:
    def test_anular_elimina_novedad_no_aplicada(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 18, 0))
        db_session.commit()
        nov_id = t.novedad_generada_id
        svc.anular_turno(t.id)
        db_session.commit()
        assert t.estado == "anulado"
        assert db_session.get(NovedadNomina, nov_id) is None

    def test_no_anular_si_novedad_liquidada(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        t = svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 18, 0))
        db_session.commit()
        nov = db_session.get(NovedadNomina, t.novedad_generada_id)
        nov.aplicada = True
        db_session.commit()
        with pytest.raises(ValueError, match="ya fue liquidada"):
            svc.anular_turno(t.id)


class TestTardanza:
    def test_tardanza_con_turno_programado(self, svc, db_session):
        emp = _empleado(db_session)
        svc.programar_turno(emp.id, date(2026, 7, 20), time(8, 0), time(16, 0),
                            tolerancia_min=5)
        db_session.commit()
        # llega 8:20, 20 min tarde
        t = svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 20))
        db_session.commit()
        assert t.minutos_tardanza == 20

    def test_sin_tardanza_dentro_de_tolerancia(self, svc, db_session):
        emp = _empleado(db_session)
        svc.programar_turno(emp.id, date(2026, 7, 20), time(8, 0), time(16, 0),
                            tolerancia_min=5)
        db_session.commit()
        t = svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 3))
        db_session.commit()
        assert t.minutos_tardanza == 0


class TestResumen:
    def test_resumen_suma_horas(self, svc, db_session):
        emp = _empleado(db_session)
        svc.marcar_entrada(emp.id, momento=datetime(2026, 7, 20, 8, 0))
        db_session.commit()
        svc.marcar_salida(emp.id, momento=datetime(2026, 7, 20, 18, 0))
        db_session.commit()
        r = svc.resumen_empleado(emp.id, date(2026, 7, 1), date(2026, 7, 31))
        assert r["turnos"] == 1
        assert r["horas_trabajadas"] == Decimal("10.00")
        assert r["horas_extra"] == Decimal("2.00")
