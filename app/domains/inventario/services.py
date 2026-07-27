"""Servicio de Inventario.

Punto unico de entrada para TODO movimiento de existencias. Antes la logica
estaba repartida y era incoherente:

- `/inventario/movimiento` sumaba o restaba sin validar nada y sin tocar el
  costo, de modo que un producto con 2 unidades admitia una salida de 100 y
  quedaba en -98 sin dejar alerta.
- La ruta de compras si calculaba el promedio ponderado, pero por su cuenta.
- Ventas descargaba stock con sus propias reglas.

Tres implementaciones distintas del mismo concepto. Este servicio las unifica.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AlertaStock, Bodega, Empresa, ExistenciaBodega, Lote,
    MovimientoInventario, Producto,
)

logger = logging.getLogger(__name__)

CERO = Decimal("0")

# Tipos que incrementan existencias
TIPOS_ENTRADA = {"entrada", "compra", "ajuste_positivo", "devolucion_venta",
                 "traslado_entrada", "produccion_entrada", "conteo_sobrante"}
# Tipos que las disminuyen
TIPOS_SALIDA = {"salida", "venta", "merma", "ajuste_negativo", "consumo_receta",
                "traslado_salida", "produccion_consumo", "conteo_faltante"}


class InventarioService:
    """Logica de negocio de existencias, costeo y kardex."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    # ------------------------------------------------------------------
    # Bodegas
    # ------------------------------------------------------------------
    def bodega_principal(self, empresa_id: int = 1) -> Bodega:
        """Devuelve la bodega principal, creandola si aun no existe."""
        bodega = self.db.scalar(
            select(Bodega).where(Bodega.empresa_id == empresa_id,
                                 Bodega.es_principal == True)  # noqa: E712
        )
        if bodega:
            return bodega
        bodega = Bodega(empresa_id=empresa_id, codigo="PRINCIPAL",
                        nombre="Bodega principal", es_principal=True)
        self.db.add(bodega)
        self.db.flush()
        return bodega

    def crear_bodega(self, codigo: str, nombre: str, empresa_id: int = 1,
                     ubicacion: Optional[str] = None) -> Bodega:
        codigo = (codigo or "").strip().upper()
        if not codigo:
            raise ValueError("El codigo de la bodega es obligatorio")
        if self.db.scalar(select(Bodega).where(Bodega.codigo == codigo)):
            raise ValueError(f"Ya existe una bodega con codigo {codigo}")
        bodega = Bodega(empresa_id=empresa_id, codigo=codigo,
                        nombre=nombre.strip(), ubicacion=ubicacion)
        self.db.add(bodega)
        self.db.flush()
        return bodega

    # ------------------------------------------------------------------
    # Existencias por bodega
    # ------------------------------------------------------------------
    def _existencia(self, producto_id: int, bodega_id: int) -> ExistenciaBodega:
        ex = self.db.scalar(
            select(ExistenciaBodega).where(
                ExistenciaBodega.producto_id == producto_id,
                ExistenciaBodega.bodega_id == bodega_id,
            )
        )
        if ex is None:
            ex = ExistenciaBodega(producto_id=producto_id, bodega_id=bodega_id,
                                  cantidad=CERO)
            self.db.add(ex)
            self.db.flush()
        return ex

    def existencia_en(self, producto_id: int, bodega_id: int) -> Decimal:
        ex = self.db.scalar(
            select(ExistenciaBodega).where(
                ExistenciaBodega.producto_id == producto_id,
                ExistenciaBodega.bodega_id == bodega_id,
            )
        )
        return ex.cantidad if ex else CERO

    # ------------------------------------------------------------------
    # Costeo: promedio ponderado
    # ------------------------------------------------------------------
    @staticmethod
    def _promedio_ponderado(saldo: Decimal, costo_actual: Decimal,
                            cantidad: Decimal, costo_entrada: Decimal) -> Decimal:
        """Costo promedio tras una entrada.

        (saldo * costo_actual + cantidad * costo_entrada) / (saldo + cantidad)

        Si el saldo previo es negativo se toma el costo de la entrada, porque
        un valor negativo distorsionaria el promedio.
        """
        nuevo_saldo = saldo + cantidad
        if nuevo_saldo <= 0 or saldo < 0:
            return costo_entrada if costo_entrada > 0 else costo_actual
        if costo_entrada <= 0:
            return costo_actual
        valor = (saldo * costo_actual) + (cantidad * costo_entrada)
        return (valor / nuevo_saldo).quantize(Decimal("0.01"))

    # ------------------------------------------------------------------
    # Movimiento: unico punto de entrada
    # ------------------------------------------------------------------
    def registrar_movimiento(
        self,
        producto_id: int,
        tipo: str,
        cantidad: Decimal,
        *,
        costo_unitario: Optional[Decimal] = None,
        bodega_id: Optional[int] = None,
        lote_id: Optional[int] = None,
        referencia: Optional[str] = None,
        observacion: Optional[str] = None,
        usuario_id: Optional[int] = None,
        empresa_id: int = 1,
        permitir_negativo: Optional[bool] = None,
    ) -> MovimientoInventario:
        """Registra un movimiento y actualiza saldo, costo y alertas.

        `cantidad` siempre se recibe en positivo; el signo lo determina `tipo`.
        """
        if cantidad is None or cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")

        tipo = (tipo or "").strip().lower()
        if tipo not in TIPOS_ENTRADA and tipo not in TIPOS_SALIDA:
            raise ValueError(f"Tipo de movimiento no valido: {tipo}")

        producto = self.db.get(Producto, producto_id)
        if not producto:
            raise ValueError(f"Producto {producto_id} no existe")

        if bodega_id is None:
            bodega_id = self.bodega_principal(empresa_id).id
        elif not self.db.get(Bodega, bodega_id):
            raise ValueError(f"Bodega {bodega_id} no existe")

        if permitir_negativo is None:
            empresa = self.db.get(Empresa, empresa_id)
            permitir_negativo = bool(getattr(empresa, "permitir_stock_negativo", True))

        es_entrada = tipo in TIPOS_ENTRADA
        delta = cantidad if es_entrada else -cantidad

        saldo_anterior = producto.existencias or CERO
        costo_anterior = producto.costo or CERO
        saldo_posterior = saldo_anterior + delta

        if not es_entrada and saldo_posterior < 0 and not permitir_negativo:
            raise ValueError(
                f"Stock insuficiente de '{producto.nombre}': "
                f"disponible {saldo_anterior}, solicitado {cantidad}"
            )

        # Costo: solo las entradas con costo lo modifican
        if es_entrada and costo_unitario and costo_unitario > 0:
            costo_posterior = self._promedio_ponderado(
                saldo_anterior, costo_anterior, cantidad, costo_unitario)
        else:
            costo_posterior = costo_anterior

        producto.existencias = saldo_posterior
        producto.costo = costo_posterior

        ex = self._existencia(producto.id, bodega_id)
        ex.cantidad = (ex.cantidad or CERO) + delta

        if lote_id:
            lote = self.db.get(Lote, lote_id)
            if not lote:
                raise ValueError(f"Lote {lote_id} no existe")
            lote.cantidad_disponible = (lote.cantidad_disponible or CERO) + delta

        movimiento = MovimientoInventario(
            producto_id=producto.id,
            tipo=tipo,
            cantidad=delta,
            costo_unitario=costo_unitario if costo_unitario is not None else costo_posterior,
            referencia=referencia,
            bodega_id=bodega_id,
            lote_id=lote_id,
            saldo_anterior=saldo_anterior,
            saldo_posterior=saldo_posterior,
            costo_promedio_anterior=costo_anterior,
            costo_promedio_posterior=costo_posterior,
            usuario_id=usuario_id,
            observacion=observacion,
        )
        self.db.add(movimiento)

        self._evaluar_alertas(producto, saldo_posterior, cantidad, referencia)
        self.db.flush()
        return movimiento

    def _evaluar_alertas(self, producto: Producto, saldo: Decimal,
                         cantidad: Decimal, referencia: Optional[str]) -> None:
        if saldo < 0:
            self.db.add(AlertaStock(
                producto_id=producto.id, tipo="negativo",
                existencia_resultante=saldo, cantidad_solicitada=cantidad,
                referencia=referencia,
            ))
            self.logger.warning("Existencia negativa en '%s': %s", producto.nombre, saldo)
        elif producto.stock_minimo and saldo <= producto.stock_minimo:
            self.db.add(AlertaStock(
                producto_id=producto.id, tipo="bajo_minimo",
                existencia_resultante=saldo, cantidad_solicitada=cantidad,
                referencia=referencia,
            ))

    # ------------------------------------------------------------------
    # Traslados entre bodegas
    # ------------------------------------------------------------------
    def trasladar(self, producto_id: int, origen_id: int, destino_id: int,
                  cantidad: Decimal, *, usuario_id: Optional[int] = None,
                  referencia: Optional[str] = None,
                  empresa_id: int = 1) -> tuple[MovimientoInventario, MovimientoInventario]:
        """Mueve existencias entre bodegas sin alterar el total consolidado."""
        if origen_id == destino_id:
            raise ValueError("La bodega de origen y destino no pueden ser la misma")
        if cantidad is None or cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")

        disponible = self.existencia_en(producto_id, origen_id)
        if disponible < cantidad:
            raise ValueError(
                f"La bodega de origen solo tiene {disponible} unidades disponibles"
            )

        ref = referencia or f"TRASLADO-{origen_id}-{destino_id}"
        salida = self.registrar_movimiento(
            producto_id, "traslado_salida", cantidad, bodega_id=origen_id,
            referencia=ref, usuario_id=usuario_id, empresa_id=empresa_id,
            permitir_negativo=False,
        )
        entrada = self.registrar_movimiento(
            producto_id, "traslado_entrada", cantidad, bodega_id=destino_id,
            referencia=ref, usuario_id=usuario_id, empresa_id=empresa_id,
        )
        return salida, entrada

    # ------------------------------------------------------------------
    # Lotes y vencimientos
    # ------------------------------------------------------------------
    def crear_lote(self, producto_id: int, codigo: str, cantidad: Decimal,
                   *, costo_unitario: Decimal = CERO,
                   fecha_vencimiento: Optional[date] = None,
                   bodega_id: Optional[int] = None,
                   usuario_id: Optional[int] = None,
                   empresa_id: int = 1) -> Lote:
        """Ingresa un lote y su entrada de inventario correspondiente."""
        if cantidad is None or cantidad <= 0:
            raise ValueError("La cantidad del lote debe ser mayor que cero")
        if bodega_id is None:
            bodega_id = self.bodega_principal(empresa_id).id

        lote = Lote(
            producto_id=producto_id, bodega_id=bodega_id,
            codigo=(codigo or "").strip(),
            fecha_vencimiento=fecha_vencimiento,
            cantidad_inicial=cantidad, cantidad_disponible=CERO,
            costo_unitario=costo_unitario,
        )
        self.db.add(lote)
        self.db.flush()

        self.registrar_movimiento(
            producto_id, "entrada", cantidad, costo_unitario=costo_unitario,
            bodega_id=bodega_id, lote_id=lote.id,
            referencia=f"LOTE-{lote.codigo}", usuario_id=usuario_id,
            empresa_id=empresa_id,
        )
        return lote

    def lotes_por_vencer(self, dias: int = 30,
                         empresa_id: int = 1) -> list[Lote]:
        """Lotes con existencia que vencen dentro del plazo indicado."""
        lotes = self.db.scalars(
            select(Lote).where(Lote.activo == True,  # noqa: E712
                               Lote.cantidad_disponible > 0,
                               Lote.fecha_vencimiento.isnot(None))
        ).all()
        return sorted(
            [l for l in lotes if (l.dias_para_vencer() or 9999) <= dias],
            key=lambda l: l.fecha_vencimiento,
        )

    def lotes_vencidos(self) -> list[Lote]:
        lotes = self.db.scalars(
            select(Lote).where(Lote.activo == True,  # noqa: E712
                               Lote.cantidad_disponible > 0)
        ).all()
        return [l for l in lotes if l.vencido]

    # ------------------------------------------------------------------
    # Kardex
    # ------------------------------------------------------------------
    def kardex(self, producto_id: int, *, desde: Optional[date] = None,
               hasta: Optional[date] = None,
               bodega_id: Optional[int] = None) -> list[dict]:
        """Kardex del producto: cada movimiento con saldo y valor resultante.

        Antes no existia: los movimientos se guardaban pero nadie los leia.
        """
        q = select(MovimientoInventario).where(
            MovimientoInventario.producto_id == producto_id)
        if bodega_id:
            q = q.where(MovimientoInventario.bodega_id == bodega_id)
        if desde:
            q = q.where(MovimientoInventario.fecha >= desde)
        if hasta:
            q = q.where(MovimientoInventario.fecha <= hasta)

        movimientos = self.db.scalars(
            q.order_by(MovimientoInventario.fecha, MovimientoInventario.id)).all()

        filas = []
        for m in movimientos:
            cantidad = m.cantidad or CERO
            filas.append({
                "fecha": m.fecha,
                "tipo": m.tipo,
                "referencia": m.referencia,
                "entrada": cantidad if cantidad > 0 else CERO,
                "salida": -cantidad if cantidad < 0 else CERO,
                "saldo": m.saldo_posterior,
                "costo_unitario": m.costo_unitario,
                "costo_promedio": m.costo_promedio_posterior,
                "valor_saldo": (m.saldo_posterior or CERO) * (m.costo_promedio_posterior or CERO),
                "bodega_id": m.bodega_id,
                "lote_id": m.lote_id,
            })
        return filas

    def valor_inventario(self, empresa_id: int = 1) -> Decimal:
        """Valor total del inventario a costo promedio vigente."""
        productos = self.db.scalars(
            select(Producto).where(Producto.activo == True)  # noqa: E712
        ).all()
        return sum(((p.existencias or CERO) * (p.costo or CERO) for p in productos), CERO)

    def alertas_pendientes(self, limite: int = 100) -> list[AlertaStock]:
        """Alertas sin atender. Ventas ya las generaba, pero nadie las leia."""
        return self.db.scalars(
            select(AlertaStock).where(AlertaStock.atendida == False)  # noqa: E712
            .order_by(AlertaStock.fecha.desc()).limit(limite)
        ).all()
