"""Inicializa la base de datos con datos de demostracion coherentes.

Crea un cafe-bar completo y operable: empresa, zonas, mesas, categorias,
productos con existencias, bodegas, empleados, usuarios por rol, clientes,
proveedores y un historial breve de operaciones reales generado a traves de
los servicios del sistema (no con INSERT directos), de modo que el kardex,
los costos promedio y los estados de mesa queden coherentes desde el primer
arranque.

Uso:
    python scripts/inicializar_datos.py            # crea si esta vacia
    python scripts/inicializar_datos.py --reiniciar  # BORRA TODO y recrea

El modo --reiniciar elimina la base existente. Pide confirmacion salvo que
se pase --si.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.context import CryptContext  # noqa: E402
from sqlalchemy import func, select, text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app import models_enterprise  # noqa: E402,F401  (registra tablas RBAC, etc.)
from app.models import (  # noqa: E402
    Categoria, Cliente, Comanda, Empleado, Empresa, Mesa, ParametrosNomina,
    PeriodoNomina, Producto, Proveedor, Turno, Usuario, Zona,
)

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")

CLAVE_DEMO = "Demo123*"
CLAVE_ADMIN = "Admin123*"


# ---------------------------------------------------------------------------
def _log(mensaje: str) -> None:
    print(f"  {mensaje}")


def borrar_base() -> None:
    """Elimina todas las tablas."""
    print("\nBorrando esquema existente...")
    Base.metadata.drop_all(engine)
    with engine.begin() as cn:
        try:
            cn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        except Exception:
            pass
    _log("esquema eliminado")


def crear_esquema() -> None:
    print("\nCreando esquema...")
    Base.metadata.create_all(engine)
    _log(f"{len(Base.metadata.tables)} tablas creadas")


# ---------------------------------------------------------------------------
def sembrar(db) -> None:
    print("\nSembrando datos...")

    # --- Empresa -----------------------------------------------------------
    empresa = Empresa(
        nombre="Café Bar DLA",
        nit="900.123.456-7",
        direccion="Cra 14 # 12-45, Armenia, Quindío",
        telefono="606 7412580",
        moneda="COP",
        prefijo_factura="FE",
        consecutivo_factura=1,
        impuesto_porcentaje=Decimal("19"),
        tipo_persona="juridica",
        regimen_tributario="responsable_iva",
        permitir_stock_negativo=True,
    )
    db.add(empresa)
    db.flush()
    _log(f"empresa: {empresa.nombre}")

    # --- Zonas y mesas -----------------------------------------------------
    zonas_def = [
        ("Salón principal", 1, [
            ("M1", 4, 10, 15, "redonda"), ("M2", 2, 30, 15, "cuadrada"),
            ("M3", 6, 50, 15, "rectangular"), ("M4", 4, 70, 15, "redonda"),
            ("M5", 4, 10, 45, "redonda"), ("M6", 2, 30, 45, "cuadrada"),
            ("M7", 8, 55, 45, "rectangular"),
        ]),
        ("Terraza", 2, [
            ("T1", 4, 15, 20, "redonda"), ("T2", 4, 45, 20, "redonda"),
            ("T3", 6, 75, 20, "rectangular"), ("T4", 2, 15, 55, "cuadrada"),
            ("T5", 2, 45, 55, "cuadrada"),
        ]),
        ("Barra", 3, [
            ("B1", 2, 20, 30, "cuadrada"), ("B2", 2, 40, 30, "cuadrada"),
            ("B3", 2, 60, 30, "cuadrada"),
        ]),
    ]
    total_mesas = 0
    for nombre, orden, mesas in zonas_def:
        zona = Zona(empresa_id=empresa.id, nombre=nombre, orden=orden, activa=True)
        db.add(zona)
        db.flush()
        for mn, cap, px, py, forma in mesas:
            db.add(Mesa(empresa_id=empresa.id, zona_id=zona.id, nombre=mn,
                        capacidad=cap, posicion_x=px, posicion_y=py,
                        forma=forma, estado="libre"))
            total_mesas += 1
    db.flush()
    _log(f"{len(zonas_def)} zonas, {total_mesas} mesas")

    # --- Categorias --------------------------------------------------------
    cats = {}
    for nombre in ["Café", "Bebidas frías", "Cervezas y licores",
                   "Comidas", "Postres", "Insumos"]:
        c = Categoria(nombre=nombre)
        db.add(c)
        db.flush()
        cats[nombre] = c.id
    _log(f"{len(cats)} categorías")

    # --- Productos ---------------------------------------------------------
    # (codigo, nombre, categoria, tipo, precio, costo, existencias, minimo)
    productos_def = [
        # Café
        ("CAF-001", "Café americano", "Café", "venta", 4500, 1200, 0, 0),
        ("CAF-002", "Capuchino", "Café", "venta", 8500, 2400, 0, 0),
        ("CAF-003", "Latte", "Café", "venta", 9000, 2700, 0, 0),
        ("CAF-004", "Espresso doble", "Café", "venta", 6000, 1600, 0, 0),
        ("CAF-005", "Mocaccino", "Café", "venta", 10500, 3200, 0, 0),
        # Bebidas frias
        ("BEB-001", "Limonada natural", "Bebidas frías", "venta", 7000, 1800, 0, 0),
        ("BEB-002", "Jugo de naranja", "Bebidas frías", "venta", 8000, 2200, 0, 0),
        ("BEB-003", "Gaseosa 400ml", "Bebidas frías", "venta", 4000, 1900, 0, 0),
        ("BEB-004", "Agua mineral", "Bebidas frías", "venta", 3500, 1400, 0, 0),
        # Cervezas y licores
        ("LIC-001", "Cerveza nacional", "Cervezas y licores", "venta", 7000, 3200, 0, 0),
        ("LIC-002", "Cerveza importada", "Cervezas y licores", "venta", 12000, 6500, 0, 0),
        ("LIC-003", "Copa de vino tinto", "Cervezas y licores", "venta", 15000, 6000, 0, 0),
        ("LIC-004", "Mojito", "Cervezas y licores", "venta", 18000, 5500, 0, 0),
        # Comidas
        ("COM-001", "Croissant de jamón y queso", "Comidas", "venta", 9500, 3500, 0, 0),
        ("COM-002", "Sándwich de pollo", "Comidas", "venta", 16000, 6200, 0, 0),
        ("COM-003", "Hamburguesa artesanal", "Comidas", "venta", 24000, 9500, 0, 0),
        ("COM-004", "Ensalada césar", "Comidas", "venta", 18000, 6800, 0, 0),
        ("COM-005", "Papas a la francesa", "Comidas", "venta", 9000, 3000, 0, 0),
        # Postres
        ("POS-001", "Torta de chocolate", "Postres", "venta", 9000, 3200, 0, 0),
        ("POS-002", "Cheesecake", "Postres", "venta", 11000, 4100, 0, 0),
        ("POS-003", "Brownie con helado", "Postres", "venta", 12000, 4500, 0, 0),
        # Insumos (materia prima)
        ("INS-001", "Café en grano (kg)", "Insumos", "insumo", 0, 38000, 0, 5),
        ("INS-002", "Leche entera (lt)", "Insumos", "insumo", 0, 3800, 0, 20),
        ("INS-003", "Azúcar (kg)", "Insumos", "insumo", 0, 4200, 0, 10),
        ("INS-004", "Pan de hamburguesa (und)", "Insumos", "insumo", 0, 1200, 0, 30),
        ("INS-005", "Carne de res (kg)", "Insumos", "insumo", 0, 28000, 0, 5),
        ("INS-006", "Queso mozzarella (kg)", "Insumos", "insumo", 0, 22000, 0, 3),
    ]
    productos = {}
    for cod, nom, cat, tipo, precio, costo, exi, minimo in productos_def:
        p = Producto(
            empresa_id=empresa.id, categoria_id=cats[cat], codigo=cod, nombre=nom,
            tipo=tipo, precio_venta=Decimal(str(precio)), costo=Decimal("0"),
            existencias=Decimal("0"), stock_minimo=Decimal(str(minimo)), activo=True,
            iva_porcentaje=Decimal("19") if tipo == "venta" else Decimal("0"),
        )
        db.add(p)
        db.flush()
        productos[cod] = p
    _log(f"{len(productos)} productos (sin existencias: entran por compra)")

    # --- Empleados y usuarios ---------------------------------------------
    empleados_def = [
        ("Carlos Ramírez", "1094123456", "Administrador", 3500000, "admin", "administrador", CLAVE_ADMIN),
        ("Laura Céspedes", "1094223344", "Gerente", 2800000, "gerente", "gerente", CLAVE_DEMO),
        ("Andrés Motta", "1094334455", "Cajero", 1600000, "cajero", "cajero", CLAVE_DEMO),
        ("Diana Ospina", "1094445566", "Mesera", 1450000, "mesero1", "mesero", CLAVE_DEMO),
        ("Julián Torres", "1094556677", "Mesero", 1450000, "mesero2", "mesero", CLAVE_DEMO),
        ("Sofía Grisales", "1094667788", "Cocinera", 1700000, "cocina", "cocinero", CLAVE_DEMO),
        ("Mateo Arias", "1094778899", "Bartender", 1600000, "barra", "bartender", CLAVE_DEMO),
    ]
    usuarios = {}
    for nombre, doc, cargo, salario, login, rol, clave in empleados_def:
        emp = Empleado(
            nombre=nombre, documento=doc, cargo=cargo, empresa_id=empresa.id,
            salario=Decimal(str(salario)), activo=True, tipo_documento="CC",
            fecha_ingreso=date.today() - timedelta(days=365),
            tipo_contrato="indefinido", eps="Sura", pension="Porvenir", arl="Sura",
            tipo_salario="ordinario", nivel_riesgo_arl=1, auxilio_transporte=True,
            caja_compensacion="Comfenalco",
        )
        db.add(emp)
        db.flush()
        u = Usuario(empleado_id=emp.id, empresa_id=empresa.id, usuario=login,
                    password_hash=passwords.hash(clave), rol=rol, activo=True)
        db.add(u)
        db.flush()
        usuarios[login] = u
    _log(f"{len(usuarios)} empleados con usuario")

    # --- Clientes ----------------------------------------------------------
    clientes_def = [
        ("Consumidor final", "222222222222", None, 0),
        ("Inversiones El Roble SAS", "901234567", "606 7451200", 2000000),
        ("María Fernanda Loaiza", "41987654", "310 4567890", 500000),
        ("Grupo Empresarial Andino", "900876543", "606 7339900", 3000000),
    ]
    for nombre, doc, tel, cupo in clientes_def:
        db.add(Cliente(nombre=nombre, documento=doc, telefono=tel,
                       cupo_credito=Decimal(str(cupo)), saldo_cartera=Decimal("0")))
    _log(f"{len(clientes_def)} clientes")

    # --- Proveedores -------------------------------------------------------
    proveedores_def = [
        ("Distribuidora de Café del Quindío SAS", "NIT", "900111222", "606 7412000", "ventas@cafequindio.co"),
        ("Lácteos La Pradera", "NIT", "900333444", "606 7415500", "pedidos@lapradera.co"),
        ("Cervecería Nacional", "NIT", "890900608", "601 3078000", "distribucion@cerveceria.co"),
        ("Panificadora El Trigal", "NIT", "900555666", "606 7448899", "contacto@eltrigal.co"),
    ]
    for nombre, td, doc, tel, email in proveedores_def:
        db.add(Proveedor(nombre=nombre, tipo_documento=td, documento=doc,
                         telefono=tel, email=email, obligado_facturar=True))
    _log(f"{len(proveedores_def)} proveedores")

    # --- Parametros de nomina (Colombia 2026) -----------------------------
    # Los porcentajes van como enteros (4 = 4%), no como fraccion: el servicio
    # divide entre 100. Antes estaban como 0.04, lo que daba deducciones 100
    # veces menores.
    db.add(ParametrosNomina(
        vigencia_desde=date(2026, 1, 1),
        salario_minimo=Decimal("1623500"),
        auxilio_transporte=Decimal("200000"),
        tope_auxilio_transporte=Decimal("3247000"),
        salud_empleado_pct=Decimal("4"),
        pension_empleado_pct=Decimal("4"),
    ))
    _log("parámetros de nómina 2026 cargados")

    # --- RBAC: roles y permisos parametrizables (Paso 17) -----------------
    from app.services.rbac_service import inicializar_rbac
    inicializar_rbac(db)
    _log("RBAC: roles y permisos por módulo inicializados")

    db.commit()


# ---------------------------------------------------------------------------
def sembrar_operaciones(db) -> None:
    """Genera movimientos reales a traves de los servicios del sistema.

    Se usan los servicios y no INSERT directos para que el kardex, los costos
    promedio y los estados queden coherentes: es la misma ruta que seguira la
    operacion diaria.
    """
    from app.domains.inventario.services import InventarioService
    from app.domains.ventas.schemas import DetalleVentaCreate, PagoCreate, TipoPago, VentaCreate
    from app.domains.ventas.services import VentaService

    print("\nGenerando operación inicial...")
    inv = InventarioService(db)
    ventas = VentaService(db)

    empresa = db.scalar(select(Empresa))
    admin = db.scalar(select(Usuario).where(Usuario.usuario == "admin"))
    mesero = db.scalar(select(Usuario).where(Usuario.usuario == "mesero1"))

    # Bodegas
    principal = inv.bodega_principal(empresa.id)
    barra = inv.crear_bodega("BARRA", "Bodega de barra", empresa.id, "Junto a la caja")
    cocina = inv.crear_bodega("COCINA", "Bodega de cocina", empresa.id, "Área de preparación")
    db.commit()
    _log(f"3 bodegas: {principal.codigo}, {barra.codigo}, {cocina.codigo}")

    def prod(codigo):
        return db.scalar(select(Producto).where(Producto.codigo == codigo))

    # --- Compras iniciales: entran las existencias con su costo -----------
    compras = [
        ("CAF-001", 200, 1200), ("CAF-002", 180, 2400), ("CAF-003", 150, 2700),
        ("CAF-004", 120, 1600), ("CAF-005", 90, 3200),
        ("BEB-001", 100, 1800), ("BEB-002", 80, 2200),
        ("BEB-003", 240, 1900), ("BEB-004", 200, 1400),
        ("LIC-001", 300, 3200), ("LIC-002", 120, 6500),
        ("LIC-003", 60, 6000), ("LIC-004", 80, 5500),
        ("COM-001", 60, 3500), ("COM-002", 50, 6200), ("COM-003", 45, 9500),
        ("COM-004", 40, 6800), ("COM-005", 70, 3000),
        ("POS-001", 30, 3200), ("POS-002", 25, 4100), ("POS-003", 28, 4500),
        ("INS-001", 25, 38000), ("INS-002", 60, 3800), ("INS-003", 40, 4200),
        ("INS-004", 120, 1200), ("INS-005", 18, 28000), ("INS-006", 12, 22000),
    ]
    for codigo, cantidad, costo in compras:
        inv.registrar_movimiento(
            producto_id=prod(codigo).id, tipo="compra", cantidad=Decimal(str(cantidad)),
            costo_unitario=Decimal(str(costo)), bodega_id=principal.id,
            referencia="COMPRA-INICIAL", usuario_id=admin.id, empresa_id=empresa.id,
        )
    db.commit()
    _log(f"{len(compras)} entradas de inventario con costo")

    # --- Traslados a barra y cocina ---------------------------------------
    for codigo, cantidad, destino in [
        ("LIC-001", 80, barra.id), ("LIC-002", 30, barra.id),
        ("BEB-003", 60, barra.id), ("BEB-004", 50, barra.id),
        ("INS-004", 40, cocina.id), ("INS-005", 6, cocina.id),
        ("INS-006", 4, cocina.id),
    ]:
        inv.trasladar(prod(codigo).id, principal.id, destino,
                      Decimal(str(cantidad)), usuario_id=admin.id,
                      referencia="SURTIDO-INICIAL", empresa_id=empresa.id)
    db.commit()
    _log("7 traslados entre bodegas")

    # --- Lote con vencimiento proximo (para ver la alerta funcionando) ----
    inv.crear_lote(prod("INS-002").id, "LECHE-2026-07", Decimal("24"),
                   costo_unitario=Decimal("3800"),
                   fecha_vencimiento=date.today() + timedelta(days=6),
                   bodega_id=cocina.id, usuario_id=admin.id, empresa_id=empresa.id)
    inv.crear_lote(prod("INS-005").id, "CARNE-2026-08", Decimal("8"),
                   costo_unitario=Decimal("28000"),
                   fecha_vencimiento=date.today() + timedelta(days=20),
                   bodega_id=cocina.id, usuario_id=admin.id, empresa_id=empresa.id)
    db.commit()
    _log("2 lotes con fecha de vencimiento")

    # --- Ventas cerradas de hoy (para que el dashboard muestre cifras) ----
    def _venta(items, mesa_id=None, tipo="mostrador"):
        detalles = []
        for cod, cant in items:
            p = prod(cod)
            detalles.append(DetalleVentaCreate(
                producto_id=p.id, cantidad=Decimal(str(cant)), precio=p.precio_venta))
        return VentaCreate(mesa_id=mesa_id, tipo_venta=tipo, detalles=detalles)

    cerradas = [
        [("CAF-002", 2), ("POS-001", 1)],
        [("COM-003", 2), ("BEB-003", 2)],
        [("CAF-001", 3), ("COM-001", 2)],
        [("LIC-001", 4), ("COM-005", 1)],
        [("CAF-005", 1), ("POS-002", 1)],
        [("COM-002", 2), ("BEB-001", 2)],
    ]
    for items in cerradas:
        v = ventas.crear_venta(_venta(items), usuario_id=mesero.id, empresa_id=empresa.id)
        ventas.procesar_pago(
            v.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO, monto=v.total),
            empresa_id=empresa.id, usuario_id=mesero.id)
    _log(f"{len(cerradas)} ventas cerradas")

    # --- Mesas ocupadas ahora mismo ---------------------------------------
    mesas = db.scalars(select(Mesa).order_by(Mesa.id)).all()
    abiertas = [
        (mesas[0], [("CAF-002", 2), ("COM-001", 1)], 3),
        (mesas[2], [("LIC-001", 3), ("COM-005", 2)], 5),
        (mesas[7], [("CAF-003", 2), ("POS-003", 2)], 2),
    ]
    for mesa, items, comensales in abiertas:
        v = ventas.crear_venta(_venta(items, mesa_id=mesa.id, tipo="en_mesa"),
                               usuario_id=mesero.id, empresa_id=empresa.id)
        mesa.comensales = comensales
        db.add(Comanda(venta_id=v.id, mesa_id=mesa.id, estado="pendiente",
                       prioridad="normal", notas=f"Comanda mesa {mesa.nombre}"))
    db.commit()
    _log(f"{len(abiertas)} mesas ocupadas con cuenta abierta")

    # --- Asistencia: turnos de ejemplo con marcaciones --------------------
    from app.domains.asistencia.services import AsistenciaService
    from datetime import datetime as _dt
    asistencia = AsistenciaService(db)
    hoy = date.today()
    # Barra: turno de 8h exactas (sin extra)
    barra_emp = db.scalar(select(Empleado).where(Empleado.documento == "1094556677"))
    if barra_emp:
        asistencia.marcar_entrada(barra_emp.id, empresa_id=empresa.id,
                                  momento=_dt.combine(hoy, _dt.min.time()).replace(hour=8))
        asistencia.marcar_salida(
            barra_emp.id,
            momento=_dt.combine(hoy, _dt.min.time()).replace(hour=16))
    # Mesero: turno de 10h con receso de 1h => 9h, 1h extra (genera novedad)
    mesero_ast = db.scalar(select(Empleado).where(Empleado.documento == "1094445566"))
    if mesero_ast:
        asistencia.marcar_entrada(mesero_ast.id, empresa_id=empresa.id,
                                  momento=_dt.combine(hoy, _dt.min.time()).replace(hour=8))
        asistencia.marcar_salida_receso(
            mesero_ast.id, momento=_dt.combine(hoy, _dt.min.time()).replace(hour=13))
        asistencia.marcar_regreso_receso(
            mesero_ast.id, momento=_dt.combine(hoy, _dt.min.time()).replace(hour=14))
        asistencia.marcar_salida(
            mesero_ast.id, momento=_dt.combine(hoy, _dt.min.time()).replace(hour=19))
    db.commit()
    turnos_cerrados = db.scalars(
        select(Turno).where(Turno.estado == "cerrado")).all()
    con_extra = [t for t in turnos_cerrados if t.novedad_generada_id]
    _log(f"asistencia: {len(turnos_cerrados)} turnos cerrados, "
         f"{len(con_extra)} con horas extra (novedad automática)")

    # --- Nomina: un periodo liquidado con novedades ------------------------
    from app.domains.nomina.services import NominaService
    nomina = NominaService(db)
    periodo = PeriodoNomina(
        empresa_id=empresa.id,
        fecha_inicio=date.today().replace(day=1),
        fecha_fin=date.today().replace(day=1) + timedelta(days=29),
        periodicidad="mensual", estado="borrador")
    db.add(periodo)
    db.flush()

    # Un par de novedades sobre empleados del periodo
    mesero = db.scalar(select(Empleado).where(Empleado.documento == "1094445566"))
    if mesero:
        n1 = nomina.registrar_novedad(mesero.id, "he_diurna", cantidad=Decimal("12"),
                                      empresa_id=empresa.id,
                                      descripcion="Horas extra fin de semana")
        n1.periodo_id = periodo.id
    cocina_emp = db.scalar(select(Empleado).where(Empleado.documento == "1094667788"))
    if cocina_emp:
        n2 = nomina.registrar_novedad(cocina_emp.id, "recargo_nocturno",
                                      cantidad=Decimal("20"), empresa_id=empresa.id,
                                      descripcion="Recargo nocturno")
        n2.periodo_id = periodo.id
    db.commit()

    nomina.liquidar_periodo(periodo.id)
    db.commit()
    resumen_nom = nomina.resumen_periodo(periodo.id)
    _log(f"nómina liquidada: {resumen_nom['empleados']} empleados, "
         f"neto ${resumen_nom['total_neto']:,.0f}")

    # --- Produccion: un elaborado con receta ------------------------------
    from app.domains.produccion.services import ProduccionService
    produccion = ProduccionService(db)

    # Producto elaborado: masa para pizza (se produce, no se compra)
    from app.models import Categoria
    cat_insumos = db.scalar(select(Categoria).where(Categoria.nombre == "Insumos"))
    masa = Producto(
        empresa_id=empresa.id, categoria_id=cat_insumos.id if cat_insumos else None,
        codigo="ELA-001", nombre="Masa para pizza (und)", tipo="elaborado",
        precio_venta=Decimal("0"), costo=Decimal("0"),
        existencias=Decimal("0"), stock_minimo=Decimal("10"),
        iva_porcentaje=Decimal("0"), activo=True)
    db.add(masa)
    db.flush()

    receta = produccion.crear_receta(masa.id, rendimiento=Decimal("20"),
                                     instrucciones="Amasar, reposar 2h, porcionar")
    produccion.agregar_insumo(receta.id, prod("INS-003").id, Decimal("2"))       # azucar
    produccion.agregar_insumo(receta.id, prod("INS-002").id, Decimal("1"),
                              merma_porcentaje=Decimal("5"))                       # leche con merma
    db.commit()
    _log(f"receta de '{masa.nombre}' (rinde 20 und)")

    # Ejecutar una produccion real
    orden_prod = produccion.ejecutar(receta.id, Decimal("3"), empresa_id=empresa.id,
                                     usuario_id=admin.id, bodega_id=cocina.id)
    db.commit()
    _log(f"produccion {orden_prod.numero}: {orden_prod.unidades_producidas} und "
         f"a ${orden_prod.costo_unitario} c/u")

    # --- Ciclo de compras: solicitud, orden y recepcion parcial -----------
    from app.domains.compras.services import ComprasService
    compras = ComprasService(db)
    prov = db.scalar(select(Proveedor).where(Proveedor.nombre.like("Distribuidora%")))
    if prov:
        prov.dias_credito = 30
        prov.activo = True
        orden = compras.crear_orden(prov.id, [
            {"producto_id": prod("INS-001").id, "cantidad": 30, "costo_unitario": 38000},
            {"producto_id": prod("INS-002").id, "cantidad": 100, "costo_unitario": 3800},
        ], empresa_id=empresa.id, usuario_id=admin.id,
           fecha_entrega_esperada=date.today() + timedelta(days=3),
           observaciones="Reposición semanal de insumos")
        compras.emitir_orden(orden.id)
        # Recepcion parcial: llega parte del pedido
        compras.recibir(orden.id, [
            {"producto_id": prod("INS-001").id, "cantidad": 30},
            {"producto_id": prod("INS-002").id, "cantidad": 60},
        ], bodega_id=principal.id, usuario_id=admin.id, remision="REM-8891")
        db.commit()
        _log(f"orden {orden.numero} con recepción parcial")

        # Una factura de compra a credito
        compras.crear_compra(prov.id, [
            {"producto_id": prod("INS-005").id, "cantidad": 10, "costo_unitario": 28000},
            {"producto_id": prod("INS-006").id, "cantidad": 6, "costo_unitario": 22000},
        ], empresa_id=empresa.id, usuario_id=admin.id,
           numero_documento="FV-2026-4471", concepto="Carne y queso",
           forma_pago="credito")
        db.commit()
        _log("1 factura de compra a crédito")

        # Una solicitud pendiente de aprobar
        compras.crear_solicitud([
            {"producto_id": prod("LIC-002").id, "cantidad": 48},
        ], empresa_id=empresa.id, solicitante_id=admin.id,
           justificacion="Reposición de cerveza importada para el fin de semana")
        db.commit()
        _log("1 solicitud de compra pendiente")

    # --- Una reserva -------------------------------------------------------
    from app.domains.mesas.schemas import ReservarMesa
    from app.domains.mesas.services import MesaService
    MesaService(db).reservar(mesas[3].id, ReservarMesa(
        cliente_nombre="Familia Restrepo", telefono="310 7778899",
        personas=4, fecha_hora=datetime.now() + timedelta(hours=3),
        notas="Cumpleaños, mesa junto a la ventana"))
    db.commit()
    _log("1 reserva registrada")


# ---------------------------------------------------------------------------
def resumen(db) -> None:
    from app.models import AlertaStock, Bodega, Lote, MovimientoInventario, Venta

    print("\n" + "=" * 58)
    print("RESUMEN")
    print("=" * 58)
    filas = [
        ("Zonas", Zona), ("Mesas", Mesa), ("Categorías", Categoria),
        ("Productos", Producto), ("Empleados", Empleado), ("Usuarios", Usuario),
        ("Clientes", Cliente), ("Proveedores", Proveedor), ("Bodegas", Bodega),
        ("Lotes", Lote), ("Movimientos", MovimientoInventario),
        ("Ventas", Venta), ("Alertas", AlertaStock),
    ]
    for etiqueta, modelo in filas:
        print(f"  {etiqueta:.<22} {db.scalar(select(func.count(modelo.id))) or 0}")

    valor = db.scalar(select(func.sum(Producto.existencias * Producto.costo))) or 0
    cerradas = db.scalar(select(func.sum(Venta.total)).where(Venta.estado == "pagada")) or 0
    abiertas = db.scalar(select(func.count(Venta.id)).where(Venta.estado == "abierta")) or 0
    print(f"\n  Valor del inventario ... ${valor:,.0f}")
    print(f"  Ventas pagadas ......... ${cerradas:,.0f}")
    print(f"  Cuentas abiertas ....... {abiertas}")

    print("\n" + "=" * 58)
    print("ACCESO")
    print("=" * 58)
    print(f"  admin    / {CLAVE_ADMIN}   (administrador)")
    for login in ["gerente", "cajero", "mesero1", "mesero2", "cocina", "barra"]:
        u = db.scalar(select(Usuario).where(Usuario.usuario == login))
        if u:
            print(f"  {login:<8} / {CLAVE_DEMO}    ({u.rol})")
    print("\n  Cambie estas contraseñas antes de operar en producción.")
    print("=" * 58)


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Inicializa datos de demostración")
    ap.add_argument("--reiniciar", action="store_true",
                    help="BORRA la base existente y la recrea desde cero")
    ap.add_argument("--si", action="store_true", help="No pedir confirmación")
    args = ap.parse_args()

    motor = settings.database_url.split(":")[0]
    print("=" * 58)
    print("INICIALIZACIÓN DE DATOS — Café Bar DLA")
    print("=" * 58)
    print(f"  Motor: {motor}")

    if args.reiniciar:
        if settings.is_production:
            print("\nABORTADO: no se permite --reiniciar en producción.")
            return 1
        if not args.si:
            print("\n  Se BORRARÁN todos los datos existentes.")
            if input("  Escriba 'BORRAR' para continuar: ").strip() != "BORRAR":
                print("  Cancelado.")
                return 1
        borrar_base()
        crear_esquema()
    else:
        crear_esquema()

    with SessionLocal() as db:
        if db.scalar(select(func.count(Empresa.id))):
            print("\nLa base ya tiene datos. Use --reiniciar para recrearla.")
            resumen(db)
            return 0
        sembrar(db)
        sembrar_operaciones(db)
        resumen(db)

    print("\nListo. Arranque con:  python -m uvicorn app.main:app\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
