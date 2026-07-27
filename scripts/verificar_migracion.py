"""Verifica el estado de la base antes y despues de migrar.

Uso:
    python scripts/verificar_migracion.py

Lee DATABASE_URL del .env. No modifica nada: solo informa.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect, text  # noqa: E402

from app.config import settings  # noqa: E402

TABLAS_NUEVAS = [
    "pagos_venta", "alertas_stock", "bodegas",
    "lotes", "existencias_bodega", "reservas_mesa",
    # Paso 9: compras
    "detalle_compras", "solicitudes_compra", "detalle_solicitudes",
    "cotizaciones", "detalle_cotizaciones", "ordenes_compra",
    "detalle_ordenes", "recepciones", "detalle_recepciones",
    # Paso 10: produccion
    "consumos_produccion",
    # Paso 12: nomina
    "novedades_nomina",
    # Paso 14: asistencia
    "marcaciones", "turnos_programados",
    "registros_auditoria",
    "impresoras", "grupos_impresion",
]
COLUMNAS_NUEVAS = {
    "empresas": ["permitir_stock_negativo"],
    "mesas": ["fecha_apertura", "mesero_id", "comensales", "mesa_padre_id"],
    "movimientos_inventario": [
        "bodega_id", "lote_id", "saldo_anterior", "saldo_posterior",
        "costo_promedio_anterior", "costo_promedio_posterior",
        "usuario_id", "observacion",
    ],
    "productos": ["iva_porcentaje"],
    "proveedores": ["direccion", "dias_credito", "activo"],
    "compras": ["estado", "subtotal", "iva", "total", "empresa_id"],
    "ordenes_produccion": ["estado", "costo_insumos", "merma_valor", "usuario_id"],
    "receta_detalles": ["rol", "valor_aprovechable"],
    "parametros_nomina": [
        "salud_empleador_pct", "pension_empleador_pct", "arl_pct",
        "hora_extra_diurna_pct", "prima_pct", "cesantias_pct",
        "factor_integral_prestacional",
    ],
    "empleados": [
        "empresa_id", "tipo_salario", "nivel_riesgo_arl", "auxilio_transporte",
        "fecha_retiro",
    ],
    "periodos_nomina": ["empresa_id", "total_devengado", "total_neto"],
    "liquidaciones_nomina": [
        "sueldo", "ibc", "salud_empleado", "pension_empleado",
        "retencion_fuente", "salud_empleador", "total_aportes_empleador",
        "total_provisiones",
    ],
    "turnos": [
        "empresa_id", "horas_trabajadas", "horas_extra_diurna",
        "horas_extra_nocturna", "horas_receso", "estado", "novedad_generada_id",
    ],
}


def main() -> int:
    print(f"Base de datos: {settings.database_url.split('://')[0]}://...")
    engine = create_engine(settings.database_url)
    insp = inspect(engine)
    existentes = set(insp.get_table_names())

    pendientes = 0

    print("\n--- Version de Alembic ---")
    if "alembic_version" in existentes:
        with engine.connect() as cn:
            v = cn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"  {v}")
    else:
        print("  SIN control de versiones. Ejecute: alembic stamp 0001_initial_schema")
        pendientes += 1

    print("\n--- Tablas nuevas ---")
    for t in TABLAS_NUEVAS:
        ok = t in existentes
        print(f"  [{'x' if ok else ' '}] {t}")
        pendientes += 0 if ok else 1

    print("\n--- Columnas nuevas ---")
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        if tabla not in existentes:
            print(f"  {tabla}: NO EXISTE")
            pendientes += len(columnas)
            continue
        actuales = {c["name"] for c in insp.get_columns(tabla)}
        for col in columnas:
            ok = col in actuales
            print(f"  [{'x' if ok else ' '}] {tabla}.{col}")
            pendientes += 0 if ok else 1

    print("\n--- Coherencia de datos ---")
    with engine.connect() as cn:
        if "mesas" in existentes:
            n = cn.execute(text(
                "SELECT COUNT(*) FROM mesas WHERE estado = 'disponible'")).scalar()
            if n:
                print(f"  {n} mesa(s) con estado obsoleto 'disponible'")
                print("     La migracion 0002 las normaliza a 'libre'.")
                pendientes += 1
            else:
                print("  [x] estados de mesa coherentes")

        if "existencias_bodega" in existentes and "productos" in existentes:
            total_prod = cn.execute(text(
                "SELECT COALESCE(SUM(existencias), 0) FROM productos")).scalar() or 0
            total_bod = cn.execute(text(
                "SELECT COALESCE(SUM(cantidad), 0) FROM existencias_bodega")).scalar() or 0
            if abs(float(total_prod) - float(total_bod)) < 0.001:
                print("  [x] existencias por bodega cuadran con el total")
            else:
                print(f"  Descuadre: productos={total_prod} vs bodegas={total_bod}")
                pendientes += 1

        if "parametros_nomina" in existentes:
            cols = {c["name"] for c in insp.get_columns("parametros_nomina")}
            if "salud_empleado_pct" in cols:
                n = cn.execute(text(
                    "SELECT COUNT(*) FROM parametros_nomina "
                    "WHERE salud_empleado_pct < 1 AND salud_empleado_pct > 0")).scalar()
                if n:
                    print(f"  {n} parametro(s) con porcentaje en fraccion (0.04)")
                    print("     La migracion 0005 los normaliza a entero (4).")
                    pendientes += 1
                else:
                    print("  [x] porcentajes de nomina en formato correcto")

    print()
    if pendientes:
        print(f"PENDIENTE: {pendientes} elemento(s). Ejecute: alembic upgrade head")
        return 1
    print("Todo al dia. La base tiene el esquema de los pasos 4-21.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
