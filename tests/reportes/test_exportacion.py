"""Reportes gerenciales: exportación a Excel y estado de ventas unificado."""
import io

import pytest
import openpyxl


class TestEstadoVentaUnificado:
    def test_pago_deja_venta_pagada(self, db_session):
        """Al procesar el pago, la venta queda 'pagada' (no 'cerrada')."""
        from app.domains.ventas.services import VentaService
        from app.domains.ventas.schemas import VentaCreate, DetalleVentaCreate, PagoCreate, TipoPago, TipoVenta
        from app.models import Producto
        p = db_session.query(Producto).first()
        svc = VentaService(db_session)
        venta = svc.crear_venta(
            VentaCreate(tipo_venta=TipoVenta.MOSTRADOR,
                        detalles=[DetalleVentaCreate(producto_id=p.id, cantidad=1, precio=p.precio_venta)]),
            usuario_id=1, empresa_id=1)
        svc.procesar_pago(
            venta.id, PagoCreate(tipo_pago=TipoPago.EFECTIVO, monto=venta.total),
            empresa_id=1, usuario_id=1)
        db_session.refresh(venta)
        assert venta.estado == "pagada"


class TestExportacionExcel:
    @pytest.mark.parametrize("tipo", ["ventas", "productos", "inventario",
                                      "meseros", "rentabilidad"])
    def test_exporta_xlsx_valido(self, client_autenticado, tipo):
        r = client_autenticado.get(f"/api/v1/reportes/exportar?tipo={tipo}")
        assert r.status_code == 200
        assert "spreadsheet" in r.headers.get("content-type", "")
        # el archivo abre como xlsx valido
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        assert wb.active.max_row >= 1  # al menos la cabecera

    def test_tipo_invalido_rechazado(self, client_autenticado):
        r = client_autenticado.get("/api/v1/reportes/exportar?tipo=inexistente")
        assert r.status_code == 400


class TestInformesGerenciales:
    def test_vista_informes_carga(self, client_autenticado):
        r = client_autenticado.get("/informes")
        assert r.status_code == 200

    def test_informes_tiene_export_e_imprimir(self, client_autenticado):
        r = client_autenticado.get("/informes")
        assert "a Excel" in r.text
        assert "Imprimir" in r.text
        assert "@media print" in r.text
