"""Reglas de negocio de Nomina (Colombia).

Los calculos se verifican con cifras conocidas. Parametros 2026:
SMMLV 1.623.500, auxilio 200.000.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.domains.nomina.services import NominaService, _peso
from app.models import (
    Empleado, LiquidacionNomina, NovedadNomina, ParametrosNomina, PeriodoNomina,
)

_cont = [0]


def _empleado(db_session, salario, *, tipo="ordinario", riesgo=1,
              auxilio=True, ingreso=date(2024, 1, 1)):
    _cont[0] += 1
    e = Empleado(
        nombre=f"Empleado {_cont[0]}", documento=f"DOC{_cont[0]:06d}",
        cargo="Operario", salario=Decimal(str(salario)), activo=True,
        empresa_id=1, tipo_salario=tipo, nivel_riesgo_arl=riesgo,
        auxilio_transporte=auxilio, fecha_ingreso=ingreso)
    db_session.add(e)
    db_session.commit()
    return e


@pytest.fixture
def parametros(db_session):
    p = db_session.scalar(
        __import__("sqlalchemy").select(ParametrosNomina)) if False else None
    from sqlalchemy import select
    p = db_session.scalar(select(ParametrosNomina))
    if not p:
        p = ParametrosNomina(vigencia_desde=date(2026, 1, 1),
                             salario_minimo=Decimal("1623500"),
                             auxilio_transporte=Decimal("200000"),
                             tope_auxilio_transporte=Decimal("3247000"))
        db_session.add(p)
        db_session.commit()
    else:
        p.salario_minimo = Decimal("1623500")
        p.auxilio_transporte = Decimal("200000")
        p.tope_auxilio_transporte = Decimal("3247000")
        db_session.commit()
    return p


@pytest.fixture
def svc(db_session):
    return NominaService(db_session)


@pytest.fixture
def periodo(db_session):
    p = PeriodoNomina(empresa_id=1, fecha_inicio=date(2026, 7, 1),
                      fecha_fin=date(2026, 7, 30), periodicidad="mensual",
                      estado="borrador")
    db_session.add(p)
    db_session.commit()
    return p


class TestDevengados:
    def test_salario_minimo_devenga_sueldo_mas_auxilio(self, svc, parametros,
                                                       periodo, db_session):
        emp = _empleado(db_session, 1623500)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        assert c["sueldo"] == Decimal("1623500")
        assert c["auxilio_transporte"] == Decimal("200000")
        assert c["devengados"] == Decimal("1823500")

    def test_salario_alto_no_recibe_auxilio(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 5000000)  # > 2 SMMLV
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        assert c["auxilio_transporte"] == Decimal("0")

    def test_hora_extra_diurna(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 1623500)
        # valor hora = 1623500/230 = 7058.70; HED = hora * 1.25
        nov = NovedadNomina(empresa_id=1, empleado_id=emp.id, periodo_id=periodo.id,
                            tipo="he_diurna", cantidad=Decimal("10"))
        db_session.add(nov); db_session.commit()
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[nov])
        esperado = _peso(Decimal("1623500") / Decimal("230") * Decimal("10")
                         * Decimal("1.25"))
        assert c["horas_extra"] == esperado

    def test_recargo_nocturno_solo_adicional(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 1623500)
        nov = NovedadNomina(empresa_id=1, empleado_id=emp.id, periodo_id=periodo.id,
                            tipo="recargo_nocturno", cantidad=Decimal("10"))
        db_session.add(nov); db_session.commit()
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[nov])
        # recargo solo paga el 35% adicional
        esperado = _peso(Decimal("1623500") / Decimal("230") * Decimal("10")
                         * Decimal("35") / Decimal("100"))
        assert c["recargos"] == esperado


class TestDeducciones:
    def test_salud_y_pension_4_por_ciento(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 2000000)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        # IBC = 2.000.000 (auxilio no cotiza). 4% cada uno.
        assert c["salud_empleado"] == Decimal("80000")
        assert c["pension_empleado"] == Decimal("80000")

    def test_auxilio_no_entra_al_ibc(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 1623500)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        # IBC = salario, sin auxilio
        assert c["ibc"] == Decimal("1623500")

    def test_fondo_solidaridad_desde_4_smmlv(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 7000000)  # > 4 SMMLV
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        assert c["fondo_solidaridad"] > 0

    def test_sin_fsp_bajo_4_smmlv(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 2000000)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        assert c["fondo_solidaridad"] == Decimal("0")

    def test_salario_bajo_sin_retencion(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 2000000)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        assert c["retencion_fuente"] == Decimal("0")


class TestAportesEmpleador:
    def test_exoneracion_ley_1607(self, svc, parametros, periodo, db_session):
        """Persona juridica, salario < 10 SMMLV: sin salud-empleador, ICBF, SENA."""
        emp = _empleado(db_session, 2000000)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        assert c["salud_empleador"] == Decimal("0")
        assert c["icbf_empleador"] == Decimal("0")
        assert c["sena_empleador"] == Decimal("0")
        # Pension y ARL siempre se pagan
        assert c["pension_empleador"] == Decimal("240000")  # 12%
        assert c["caja_empleador"] == Decimal("80000")      # 4%

    def test_arl_por_nivel_riesgo(self, svc, parametros, periodo, db_session):
        emp5 = _empleado(db_session, 2000000, riesgo=5)
        c = svc.calcular_empleado(emp5, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        # riesgo V = 6.960%
        assert c["arl_empleador"] == _peso(Decimal("2000000") * Decimal("6.960") / Decimal("100"))


class TestProvisiones:
    def test_provisiones_ordinario(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 1623500)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        # base prestacional = sueldo + auxilio = 1.823.500
        base = Decimal("1823500")
        assert c["prov_prima"] == _peso(base * Decimal("8.33") / Decimal("100"))
        assert c["prov_cesantias"] == _peso(base * Decimal("8.33") / Decimal("100"))
        # vacaciones sin auxilio
        assert c["prov_vacaciones"] == _peso(Decimal("1623500") * Decimal("4.17") / Decimal("100"))


class TestSalarioIntegral:
    def test_integral_ibc_es_70_por_ciento(self, svc, parametros, periodo, db_session):
        emp = _empleado(db_session, 15000000, tipo="integral", auxilio=False)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        assert c["ibc"] == Decimal("10500000")  # 70%
        assert c["auxilio_transporte"] == Decimal("0")

    def test_integral_sin_provisiones_prestacionales(self, svc, parametros,
                                                     periodo, db_session):
        emp = _empleado(db_session, 15000000, tipo="integral", auxilio=False)
        c = svc.calcular_empleado(emp, periodo, parametros,
                                  dias=Decimal("30"), novedades=[])
        # el integral ya incluye prestaciones en el factor
        assert c["prov_prima"] == Decimal("0")
        assert c["prov_cesantias"] == Decimal("0")


class TestLiquidacionPeriodo:
    def test_liquidar_crea_desprendibles(self, svc, parametros, periodo, db_session):
        _empleado(db_session, 1623500)
        _empleado(db_session, 2500000)
        svc.liquidar_periodo(periodo.id)
        db_session.commit()
        liqs = db_session.query(LiquidacionNomina).filter_by(periodo_id=periodo.id).all()
        assert len(liqs) >= 2
        assert periodo.estado == "liquidado"
        assert periodo.total_neto > 0

    def test_no_liquidar_dos_veces(self, svc, parametros, periodo, db_session):
        _empleado(db_session, 1623500)
        svc.liquidar_periodo(periodo.id)
        db_session.commit()
        with pytest.raises(ValueError, match="estado"):
            svc.liquidar_periodo(periodo.id)

    def test_anular_reabre_periodo(self, svc, parametros, periodo, db_session):
        _empleado(db_session, 1623500)
        svc.liquidar_periodo(periodo.id)
        db_session.commit()
        svc.anular_liquidacion(periodo.id)
        db_session.commit()
        assert periodo.estado == "borrador"
        assert db_session.query(LiquidacionNomina).filter_by(
            periodo_id=periodo.id).count() == 0

    def test_costo_total_incluye_aportes_y_provisiones(self, svc, parametros,
                                                       periodo, db_session):
        _empleado(db_session, 2000000)
        svc.liquidar_periodo(periodo.id)
        db_session.commit()
        r = svc.resumen_periodo(periodo.id)
        assert r["costo_total_empresa"] > r["total_devengado"]


class TestNovedades:
    def test_registrar_novedad(self, svc, parametros, db_session):
        emp = _empleado(db_session, 1623500)
        nov = svc.registrar_novedad(emp.id, "he_diurna", cantidad=Decimal("5"))
        db_session.commit()
        assert nov.id is not None
        assert nov.aplicada is False

    def test_novedad_valor_negativo_se_rechaza(self, svc, parametros, db_session):
        emp = _empleado(db_session, 1623500)
        with pytest.raises(ValueError, match="negativ"):
            svc.registrar_novedad(emp.id, "bonificacion", valor=Decimal("-100"))


class TestLiquidacionDefinitiva:
    def test_liquidacion_definitiva(self, svc, parametros, db_session):
        emp = _empleado(db_session, 1623500, ingreso=date(2025, 1, 1))
        r = svc.liquidacion_definitiva(emp.id, date(2026, 1, 1))
        assert r["cesantias"] > 0
        assert r["prima"] > 0
        assert r["vacaciones"] > 0
        assert r["total"] > 0
