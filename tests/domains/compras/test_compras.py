"""Reglas de negocio del dominio Compras.

Cada prueba corresponde a un defecto observado ejecutando el codigo real
antes de corregirlo.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domains.compras.services import ComprasService
from app.models import (
    Compra, Cotizacion, DetalleCompra, OrdenCompra, Producto, Proveedor,
    SolicitudCompra,
)


@pytest.fixture
def svc(db_session):
    return ComprasService(db_session)


@pytest.fixture
def proveedor(db_session):
    p = Proveedor(nombre="Distribuidora Prueba", tipo_documento="NIT",
                  documento="900999888", telefono="606 000000",
                  obligado_facturar=True, activo=True, dias_credito=30)
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture
def producto(db_session):
    p = db_session.query(Producto).filter(Producto.activo == True).first()
    p.existencias = Decimal("100")
    p.costo = Decimal("1000")
    p.iva_porcentaje = Decimal("19")
    db_session.commit()
    return p


@pytest.fixture
def producto2(db_session):
    p = db_session.query(Producto).filter(Producto.activo == True).offset(1).first()
    p.existencias = Decimal("50")
    p.costo = Decimal("2000")
    p.iva_porcentaje = Decimal("5")
    db_session.commit()
    return p


class TestFacturaConVariosItems:
    def test_una_compra_admite_varios_productos(self, svc, proveedor, producto,
                                                producto2, db_session):
        """Antes: la compra tenia UN producto_id. Diez items = diez filas."""
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000},
            {"producto_id": producto2.id, "cantidad": 5, "costo_unitario": 2000},
        ], numero_documento="FV-001")
        db_session.commit()
        assert len(compra.detalles) == 2

    def test_desglose_fiscal(self, svc, proveedor, producto, db_session):
        """Antes solo existia `valor` plano, sin subtotal, IVA ni total."""
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10,
             "costo_unitario": 1000, "iva_porcentaje": 19},
        ], numero_documento="FV-002")
        db_session.commit()
        assert compra.subtotal == Decimal("10000.00")
        assert compra.iva == Decimal("1900.00")
        assert compra.total == Decimal("11900.00")

    def test_iva_por_producto_ajustable(self, svc, proveedor, producto,
                                        producto2, db_session):
        """Cada linea toma el IVA de su producto; puede sobrescribirse."""
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000},
            {"producto_id": producto2.id, "cantidad": 10, "costo_unitario": 1000},
            {"producto_id": producto.id, "cantidad": 10,
             "costo_unitario": 1000, "iva_porcentaje": 0},
        ], numero_documento="FV-003")
        db_session.commit()
        ivas = sorted(d.iva_porcentaje for d in compra.detalles)
        assert ivas == [Decimal("0"), Decimal("5"), Decimal("19")]
        assert compra.iva == Decimal("2400.00")  # 1900 + 500 + 0

    def test_descuento_por_linea(self, svc, proveedor, producto, db_session):
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000,
             "descuento_porcentaje": 10, "iva_porcentaje": 0},
        ], numero_documento="FV-004")
        db_session.commit()
        assert compra.subtotal == Decimal("9000.00")
        assert compra.descuento == Decimal("1000.00")

    def test_retenciones_restan_del_total(self, svc, proveedor, producto, db_session):
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10,
             "costo_unitario": 1000, "iva_porcentaje": 19},
        ], numero_documento="FV-005", retencion_fuente=Decimal("250"))
        db_session.commit()
        assert compra.total == Decimal("11650.00")  # 10000 + 1900 - 250


class TestInventario:
    def test_confirmar_ingresa_stock_y_recalcula_costo(self, svc, proveedor,
                                                       producto, db_session):
        """100 @ $1.000 + 100 @ $2.000 = promedio $1.500."""
        svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 100, "costo_unitario": 2000},
        ], numero_documento="FV-010")
        db_session.commit()
        db_session.refresh(producto)
        assert producto.existencias == Decimal("200")
        assert producto.costo == Decimal("1500")

    def test_borrador_no_mueve_inventario(self, svc, proveedor, producto, db_session):
        antes = producto.existencias
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 50, "costo_unitario": 1000},
        ], numero_documento="FV-011", confirmar=False)
        db_session.commit()
        db_session.refresh(producto)
        assert compra.estado == "borrador"
        assert producto.existencias == antes

    def test_compra_genera_kardex(self, svc, proveedor, producto, db_session):
        from app.domains.inventario.services import InventarioService
        svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 20, "costo_unitario": 1500},
        ], numero_documento="FV-012")
        db_session.commit()
        filas = InventarioService(db_session).kardex(producto.id)
        assert any(f["referencia"] == "FV-012" for f in filas)


class TestAnulacion:
    def test_anular_revierte_stock_y_costo(self, svc, proveedor, producto, db_session):
        """Antes no existia: un error contaminaba el costo para siempre."""
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 100, "costo_unitario": 2000},
        ], numero_documento="FV-020")
        db_session.commit()
        db_session.refresh(producto)
        assert producto.existencias == Decimal("200")

        svc.anular_compra(compra.id, "Error de digitacion")
        db_session.commit()
        db_session.refresh(producto)
        assert compra.estado == "anulada"
        assert producto.existencias == Decimal("100")

    def test_anular_exige_motivo(self, svc, proveedor, producto, db_session):
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 5, "costo_unitario": 1000},
        ], numero_documento="FV-021")
        db_session.commit()
        with pytest.raises(ValueError, match="motivo"):
            svc.anular_compra(compra.id, "")

    def test_no_anular_dos_veces(self, svc, proveedor, producto, db_session):
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 5, "costo_unitario": 1000},
        ], numero_documento="FV-022")
        db_session.commit()
        svc.anular_compra(compra.id, "Primera")
        db_session.commit()
        with pytest.raises(ValueError, match="ya esta anulada"):
            svc.anular_compra(compra.id, "Segunda")

    def test_no_anular_si_la_mercancia_ya_se_consumio(self, svc, proveedor,
                                                      producto, db_session):
        """Protege el inventario: no deja el stock en negativo."""
        compra = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 50, "costo_unitario": 1000},
        ], numero_documento="FV-023")
        db_session.commit()

        producto.existencias = Decimal("10")  # se vendio casi todo
        db_session.commit()

        with pytest.raises(ValueError, match="ya se consumio"):
            svc.anular_compra(compra.id, "Intento tardio")


class TestValidaciones:
    def test_factura_duplicada_se_rechaza(self, svc, proveedor, producto, db_session):
        svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 5, "costo_unitario": 1000},
        ], numero_documento="FV-DUP")
        db_session.commit()
        with pytest.raises(ValueError, match="Ya existe la factura"):
            svc.crear_compra(proveedor.id, [
                {"producto_id": producto.id, "cantidad": 5, "costo_unitario": 1000},
            ], numero_documento="FV-DUP")

    def test_proveedor_inactivo_se_rechaza(self, svc, proveedor, producto, db_session):
        proveedor.activo = False
        db_session.commit()
        try:
            with pytest.raises(ValueError, match="inactivo"):
                svc.crear_compra(proveedor.id, [
                    {"producto_id": producto.id, "cantidad": 5, "costo_unitario": 1000},
                ])
        finally:
            proveedor.activo = True
            db_session.commit()

    def test_cantidad_cero_se_rechaza(self, svc, proveedor, producto):
        with pytest.raises(ValueError, match="mayor que cero"):
            svc.crear_compra(proveedor.id, [
                {"producto_id": producto.id, "cantidad": 0, "costo_unitario": 1000},
            ])

    def test_compra_sin_lineas_se_rechaza(self, svc, proveedor):
        with pytest.raises(ValueError, match="al menos una linea"):
            svc.crear_compra(proveedor.id, [])


class TestSolicitudes:
    def test_crear_y_aprobar(self, svc, producto, db_session):
        s = svc.crear_solicitud([{"producto_id": producto.id, "cantidad": 20}])
        db_session.commit()
        assert s.estado == "pendiente"
        svc.aprobar_solicitud(s.id, usuario_id=1)
        db_session.commit()
        assert s.estado == "aprobada"

    def test_rechazar_exige_motivo(self, svc, producto, db_session):
        s = svc.crear_solicitud([{"producto_id": producto.id, "cantidad": 5}])
        db_session.commit()
        with pytest.raises(ValueError, match="motivo"):
            svc.rechazar_solicitud(s.id, "")

    def test_sugerencia_por_stock_bajo_minimo(self, svc, producto, db_session):
        producto.existencias = Decimal("2")
        producto.stock_minimo = Decimal("10")
        db_session.commit()
        s = svc.sugerir_solicitud()
        db_session.commit()
        assert s is not None
        assert producto.id in [d.producto_id for d in s.detalles]


class TestCotizaciones:
    def test_comparar_ordena_por_total(self, svc, producto, db_session):
        s = svc.crear_solicitud([{"producto_id": producto.id, "cantidad": 10}])
        svc.aprobar_solicitud(s.id)
        db_session.commit()

        caro = Proveedor(nombre="Caro SAS", documento="111", activo=True)
        barato = Proveedor(nombre="Barato SAS", documento="222", activo=True)
        db_session.add_all([caro, barato])
        db_session.commit()

        svc.registrar_cotizacion(caro.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1500}],
            solicitud_id=s.id, dias_entrega=2)
        svc.registrar_cotizacion(barato.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000}],
            solicitud_id=s.id, dias_entrega=10)
        db_session.commit()

        comp = svc.comparar_cotizaciones(s.id)
        assert len(comp) == 2
        assert comp[0]["proveedor"] == "Barato SAS"
        assert comp[0]["es_mas_economica"] is True
        assert comp[1]["sobrecosto_porcentaje"] > 0
        assert comp[1]["es_mas_rapida"] is True

    def test_seleccionar_descarta_las_demas(self, svc, producto, db_session):
        s = svc.crear_solicitud([{"producto_id": producto.id, "cantidad": 10}])
        svc.aprobar_solicitud(s.id)
        db_session.commit()
        p1 = Proveedor(nombre="P1", documento="333", activo=True)
        p2 = Proveedor(nombre="P2", documento="444", activo=True)
        db_session.add_all([p1, p2])
        db_session.commit()

        c1 = svc.registrar_cotizacion(p1.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000}],
            solicitud_id=s.id)
        c2 = svc.registrar_cotizacion(p2.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1200}],
            solicitud_id=s.id)
        db_session.commit()

        svc.seleccionar_cotizacion(c1.id)
        db_session.commit()
        assert c1.estado == "seleccionada"
        assert c2.estado == "descartada"


class TestOrdenesYRecepciones:
    def test_recepcion_parcial(self, svc, proveedor, producto, db_session):
        """Antes no existia el concepto de recepcion parcial."""
        orden = svc.crear_orden(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 100, "costo_unitario": 1000}])
        svc.emitir_orden(orden.id)
        db_session.commit()

        svc.recibir(orden.id, [{"producto_id": producto.id, "cantidad": 40}])
        db_session.commit()
        assert orden.estado == "parcial"
        assert orden.detalles[0].cantidad_recibida == Decimal("40")
        assert orden.detalles[0].pendiente == Decimal("60")
        assert orden.porcentaje_recibido == Decimal("40.00")

        svc.recibir(orden.id, [{"producto_id": producto.id, "cantidad": 60}])
        db_session.commit()
        assert orden.estado == "recibida"

    def test_no_recibir_mas_de_lo_pedido(self, svc, proveedor, producto, db_session):
        orden = svc.crear_orden(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000}])
        svc.emitir_orden(orden.id)
        db_session.commit()
        with pytest.raises(ValueError, match="quedan"):
            svc.recibir(orden.id, [{"producto_id": producto.id, "cantidad": 50}])

    def test_recepcion_ingresa_al_inventario(self, svc, proveedor, producto, db_session):
        antes = producto.existencias
        orden = svc.crear_orden(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 30, "costo_unitario": 1000}])
        svc.emitir_orden(orden.id)
        db_session.commit()
        svc.recibir(orden.id, [{"producto_id": producto.id, "cantidad": 30}])
        db_session.commit()
        db_session.refresh(producto)
        assert producto.existencias == antes + Decimal("30")

    def test_no_recibir_sobre_orden_en_borrador(self, svc, proveedor, producto, db_session):
        orden = svc.crear_orden(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000}])
        db_session.commit()
        with pytest.raises(ValueError, match="emitidas"):
            svc.recibir(orden.id, [{"producto_id": producto.id, "cantidad": 5}])

    def test_orden_desde_cotizacion(self, svc, producto, db_session):
        s = svc.crear_solicitud([{"producto_id": producto.id, "cantidad": 10}])
        svc.aprobar_solicitud(s.id)
        db_session.commit()
        prov = Proveedor(nombre="Elegido SAS", documento="555", activo=True)
        db_session.add(prov)
        db_session.commit()

        cot = svc.registrar_cotizacion(prov.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 900}],
            solicitud_id=s.id)
        db_session.commit()

        orden = svc.crear_orden_desde_cotizacion(cot.id)
        db_session.commit()
        assert orden.proveedor_id == prov.id
        assert orden.detalles[0].costo_unitario == Decimal("900")
        assert cot.estado == "seleccionada"

    def test_no_anular_orden_con_recepciones(self, svc, proveedor, producto, db_session):
        orden = svc.crear_orden(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 20, "costo_unitario": 1000}])
        svc.emitir_orden(orden.id)
        db_session.commit()
        svc.recibir(orden.id, [{"producto_id": producto.id, "cantidad": 5}])
        db_session.commit()
        with pytest.raises(ValueError, match="recepciones parciales"):
            svc.anular_orden(orden.id, "Ya no se necesita")


class TestConsultas:
    def test_cuentas_por_pagar_detecta_vencidas(self, svc, proveedor,
                                                producto, db_session):
        c = svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000}],
            numero_documento="FV-CXP", forma_pago="credito")
        db_session.commit()
        c.fecha_vencimiento = date.today() - timedelta(days=5)
        db_session.commit()

        cxp = svc.cuentas_por_pagar()
        fila = [f for f in cxp if f["compra_id"] == c.id][0]
        assert fila["vencida"] is True
        assert fila["dias_para_vencer"] == -5

    def test_historial_de_producto(self, svc, proveedor, producto, db_session):
        svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1000}],
            numero_documento="FV-H1")
        svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10, "costo_unitario": 1200}],
            numero_documento="FV-H2")
        db_session.commit()
        hist = svc.historial_producto(producto.id)
        assert len(hist) >= 2
        assert {Decimal("1000"), Decimal("1200")} <= {h["costo_unitario"] for h in hist}

    def test_indicadores(self, svc, proveedor, producto, db_session):
        svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 10,
             "costo_unitario": 1000, "iva_porcentaje": 19}],
            numero_documento="FV-IND")
        db_session.commit()
        ind = svc.indicadores()
        assert ind["compras"] >= 1
        assert ind["total"] > 0
        assert any(p["proveedor"] == proveedor.nombre for p in ind["por_proveedor"])

    def test_listar_filtra_por_estado(self, svc, proveedor, producto, db_session):
        svc.crear_compra(proveedor.id, [
            {"producto_id": producto.id, "cantidad": 5, "costo_unitario": 1000}],
            numero_documento="FV-L1", confirmar=False)
        db_session.commit()
        borradores = svc.listar_compras(estado="borrador")
        assert all(c.estado == "borrador" for c in borradores)
