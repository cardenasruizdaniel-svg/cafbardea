"""Generacion de desprendibles de pago (PDF) y archivo de nomina electronica.

El desprendible es el comprobante legal que se entrega al empleado. El archivo
electronico es un JSON con la estructura de la nomina electronica DIAN, listo
para que el proveedor tecnologico lo transforme y firme.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Empleado, Empresa, LiquidacionNomina, PeriodoNomina,
)


def _money(v) -> str:
    return f"${Decimal(str(v or 0)):,.0f}"


# ======================================================================
# DESPRENDIBLE PDF
# ======================================================================
def desprendible_pdf(db: Session, liquidacion_id: int) -> bytes:
    """Genera el desprendible de pago de una liquidacion en PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)

    liq = db.get(LiquidacionNomina, liquidacion_id)
    if not liq:
        raise ValueError(f"Liquidacion {liquidacion_id} no existe")
    empleado = db.get(Empleado, liq.empleado_id)
    periodo = db.get(PeriodoNomina, liq.periodo_id)
    empresa = db.get(Empresa, empleado.empresa_id or 1)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Title"], fontSize=15)
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8,
                           textColor=colors.grey)

    story = []
    story.append(Paragraph(empresa.nombre if empresa else "Empresa", titulo))
    story.append(Paragraph(f"NIT {empresa.nit if empresa else ''}", small))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Comprobante de pago de nomina", styles["Heading2"]))
    story.append(Spacer(1, 8))

    # Datos del empleado
    info = [
        ["Empleado:", empleado.nombre, "Documento:", empleado.documento],
        ["Cargo:", empleado.cargo, "Periodo:",
         f"{periodo.fecha_inicio} a {periodo.fecha_fin}"],
        ["Días:", str(liq.dias_liquidados), "Salario:", _money(liq.salario_base)],
    ]
    t = Table(info, colWidths=[2.2*cm, 6*cm, 2.5*cm, 4.5*cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Devengados y deducciones lado a lado
    devengados = [["DEVENGADOS", ""]]
    for etiqueta, valor in [
        ("Sueldo", liq.sueldo), ("Auxilio de transporte", liq.auxilio_transporte),
        ("Horas extra", liq.horas_extra), ("Recargos", liq.recargos),
        ("Comisiones", liq.comisiones), ("Bonificaciones", liq.bonificaciones),
        ("Otros", liq.otros_devengados),
    ]:
        if valor and valor > 0:
            devengados.append([etiqueta, _money(valor)])
    devengados.append(["Total devengado", _money(liq.devengados)])

    deducciones = [["DEDUCCIONES", ""]]
    for etiqueta, valor in [
        ("Salud (4%)", liq.salud_empleado), ("Pensión (4%)", liq.pension_empleado),
        ("Fondo solidaridad", liq.fondo_solidaridad),
        ("Retención en la fuente", liq.retencion_fuente),
        ("Otras deducciones", liq.otras_deducciones),
    ]:
        if valor and valor > 0:
            deducciones.append([etiqueta, _money(valor)])
    deducciones.append(["Total deducido", _money(liq.deducciones)])

    filas = max(len(devengados), len(deducciones))
    while len(devengados) < filas:
        devengados.append(["", ""])
    while len(deducciones) < filas:
        deducciones.append(["", ""])

    combinada = [[d[0], d[1], dd[0], dd[1]]
                 for d, dd in zip(devengados, deducciones)]
    tc = Table(combinada, colWidths=[4.5*cm, 3.2*cm, 4.5*cm, 3.2*cm])
    tc.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#e8f5e9")),
        ("BACKGROUND", (2, 0), (3, 0), colors.HexColor("#ffebee")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tc)
    story.append(Spacer(1, 12))

    # Neto a pagar
    neto = Table([["NETO A PAGAR", _money(liq.neto)]],
                 colWidths=[11.4*cm, 4*cm])
    neto.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1565c0")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (1, 0), (1, 0), 10),
    ]))
    story.append(neto)
    story.append(Spacer(1, 16))

    # Aportes del empleador (informativo)
    story.append(Paragraph("Aportes del empleador (no se descuentan al empleado)",
                           small))
    aportes = [
        ["Salud", _money(liq.salud_empleador), "Pensión", _money(liq.pension_empleador)],
        ["ARL", _money(liq.arl_empleador), "Caja", _money(liq.caja_empleador)],
        ["ICBF", _money(liq.icbf_empleador), "SENA", _money(liq.sena_empleador)],
    ]
    ta = Table(aportes, colWidths=[2.5*cm, 3.2*cm, 2.5*cm, 3.2*cm])
    ta.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
    ]))
    story.append(ta)
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f"Documento generado el {datetime.now():%Y-%m-%d %H:%M}. "
        "Este comprobante no requiere firma.", small))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ======================================================================
# ARCHIVO DE NOMINA ELECTRONICA (DIAN)
# ======================================================================
def nomina_electronica_json(db: Session, periodo_id: int) -> dict:
    """Estructura de nomina electronica para el periodo.

    Genera el JSON con la informacion que exige la nomina electronica DIAN.
    No firma ni transmite: eso lo hace el proveedor tecnologico. El objetivo
    es entregar los datos completos y cuadrados.
    """
    periodo = db.get(PeriodoNomina, periodo_id)
    if not periodo:
        raise ValueError(f"Periodo {periodo_id} no existe")
    empresa = db.get(Empresa, periodo.empresa_id or 1)

    liquidaciones = db.scalars(
        select(LiquidacionNomina).where(
            LiquidacionNomina.periodo_id == periodo_id)).all()

    def num(v):
        return float(Decimal(str(v or 0)))

    empleados_json = []
    for liq in liquidaciones:
        emp = db.get(Empleado, liq.empleado_id)
        empleados_json.append({
            "empleado": {
                "tipo_documento": emp.tipo_documento,
                "numero_documento": emp.documento,
                "primer_apellido": emp.nombre.split()[-1] if emp.nombre else "",
                "nombres": emp.nombre,
                "tipo_contrato": emp.tipo_contrato,
                "salario_integral": emp.tipo_salario == "integral",
                "sueldo": num(emp.salario),
                "cuenta_bancaria": emp.cuenta_bancaria,
                "banco": emp.banco,
            },
            "periodo": {
                "fecha_ingreso": emp.fecha_ingreso.isoformat() if emp.fecha_ingreso else None,
                "fecha_liquidacion_inicio": periodo.fecha_inicio.isoformat(),
                "fecha_liquidacion_fin": periodo.fecha_fin.isoformat(),
                "dias_trabajados": num(liq.dias_liquidados),
            },
            "devengados": {
                "sueldo": num(liq.sueldo),
                "auxilio_transporte": num(liq.auxilio_transporte),
                "horas_extra": num(liq.horas_extra),
                "recargos": num(liq.recargos),
                "comisiones": num(liq.comisiones),
                "bonificaciones": num(liq.bonificaciones),
                "otros": num(liq.otros_devengados),
                "total": num(liq.devengados),
            },
            "deducciones": {
                "salud": num(liq.salud_empleado),
                "pension": num(liq.pension_empleado),
                "fondo_solidaridad": num(liq.fondo_solidaridad),
                "retencion_fuente": num(liq.retencion_fuente),
                "otras": num(liq.otras_deducciones),
                "total": num(liq.deducciones),
            },
            "neto_pagado": num(liq.neto),
            "cune": liq.cune,
        })

    return {
        "version": "DIAN 1.0 (estructura de datos)",
        "generado": datetime.now().isoformat(),
        "empleador": {
            "nit": empresa.nit if empresa else None,
            "razon_social": empresa.nombre if empresa else None,
        },
        "periodo": {
            "id": periodo.id,
            "inicio": periodo.fecha_inicio.isoformat(),
            "fin": periodo.fecha_fin.isoformat(),
            "periodicidad": periodo.periodicidad,
        },
        "totales": {
            "devengado": num(periodo.total_devengado),
            "deducido": num(periodo.total_deducido),
            "neto": num(periodo.total_neto),
            "aportes_empleador": num(periodo.total_aportes_empleador),
        },
        "empleados": empleados_json,
        "_nota": ("Estructura de datos para nomina electronica. La firma y "
                  "transmision a la DIAN las realiza el proveedor tecnologico "
                  "autorizado."),
    }
