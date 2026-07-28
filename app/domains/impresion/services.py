"""Servicio de impresion: resuelve a que impresora va cada producto.

La regla es una cascada de tres niveles, en este orden:
  1. La impresora especifica del producto (Producto.impresora_id).
  2. Si el producto no tiene, la impresora de su grupo de impresion.
  3. Si tampoco, la impresora marcada por defecto del negocio.

El sistema no envia bytes al hardware desde el servidor (eso depende del SO y
los drivers del equipo cliente); su trabajo es DECIDIR el destino de cada linea
de una comanda y agrupar las lineas por impresora, para que el cliente de
impresion las mande al lugar correcto (cocina, barra, caja...).
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import GrupoImpresion, Impresora, Producto

logger = logging.getLogger("impresion")


class ImpresionService:
    def __init__(self, db: Session):
        self.db = db

    def impresora_por_defecto(self) -> Optional[Impresora]:
        return self.db.scalar(
            select(Impresora).where(Impresora.es_por_defecto.is_(True),
                                    Impresora.activa.is_(True)))

    def resolver_impresora(self, producto: Producto) -> Optional[Impresora]:
        """Devuelve la impresora destino de un producto segun la cascada."""
        # 1. Impresora especifica del producto.
        if producto.impresora_id:
            imp = self.db.get(Impresora, producto.impresora_id)
            if imp and imp.activa:
                return imp
        # 2. Impresora del grupo de impresion.
        if producto.grupo_impresion_id:
            grupo = self.db.get(GrupoImpresion, producto.grupo_impresion_id)
            if grupo and grupo.impresora_id:
                imp = self.db.get(Impresora, grupo.impresora_id)
                if imp and imp.activa:
                    return imp
        # 3. Impresora por defecto.
        return self.impresora_por_defecto()

    def agrupar_comanda(self, items: list[tuple[Producto, int]]) -> dict:
        """Agrupa las lineas de una comanda por impresora destino.

        items: lista de (producto, cantidad).
        Devuelve un dict {nombre_impresora: {"destino":..., "lineas":[...]}}.
        Las lineas sin impresora resoluble van a un grupo 'SIN_DESTINO' para que
        el cliente las muestre y el negocio configure lo que falte.
        """
        grupos: dict = {}
        for producto, cantidad in items:
            imp = self.resolver_impresora(producto)
            if imp:
                clave = imp.nombre
                destino = imp.destino
            else:
                clave = "SIN_DESTINO"
                destino = None
            grupos.setdefault(clave, {"destino": destino, "lineas": []})
            grupos[clave]["lineas"].append(
                {"producto": producto.nombre, "cantidad": cantidad})
        return grupos

    def comandar_venta(self, venta_id: int) -> dict:
        """Comanda una venta imprimiendo SOLO las lineas nuevas (incremental).

        Regla de negocio: al comandar una mesa, se imprimen unicamente los
        productos agregados desde la ultima vez (comandado=False). Si es la
        primera comanda, se imprime todo; si ya se habia comandado antes, solo lo
        nuevo. Las lineas impresas se marcan como comandadas.

        Devuelve {"grupos": {impresora: {...}}, "nuevas": n, "primera": bool}.
        """
        from app.models import Venta, DetalleVenta, hora_colombia

        venta = self.db.get(Venta, venta_id)
        if not venta:
            raise ValueError("Venta no encontrada")

        # ¿Habia lineas ya comandadas? -> define si es la primera comanda.
        ya_comandadas = self.db.scalar(
            select(func.count(DetalleVenta.id)).where(
                DetalleVenta.venta_id == venta_id,
                DetalleVenta.comandado.is_(True))) or 0
        primera = ya_comandadas == 0

        # Lineas nuevas (no comandadas aun).
        nuevas = self.db.scalars(
            select(DetalleVenta).where(
                DetalleVenta.venta_id == venta_id,
                DetalleVenta.comandado.is_(False))).all()

        if not nuevas:
            return {"grupos": {}, "nuevas": 0, "primera": primera,
                    "mensaje": "No hay productos nuevos por comandar"}

        # Agrupar por impresora destino.
        items = []
        for d in nuevas:
            prod = self.db.get(Producto, d.producto_id)
            if prod:
                items.append((prod, float(d.cantidad)))
        grupos = self.agrupar_comanda(items)

        # Marcar como comandadas.
        ahora = hora_colombia()
        for d in nuevas:
            d.comandado = True
            d.comandado_en = ahora
        self.db.flush()

        return {"grupos": grupos, "nuevas": len(nuevas), "primera": primera,
                "mensaje": ("Comanda completa enviada" if primera
                            else f"{len(nuevas)} producto(s) nuevo(s) enviado(s)")}

    # ------------------------------------------------------------------
    # Gestion
    # ------------------------------------------------------------------
    def crear_impresora(self, nombre: str, destino: str = "local",
                        tipo_conexion: str = "local",
                        es_por_defecto: bool = False) -> Impresora:
        if not nombre.strip():
            raise ValueError("El nombre de la impresora es obligatorio")
        # Solo una impresora por defecto: si esta se marca, desmarca las demas.
        if es_por_defecto:
            for otra in self.db.scalars(
                    select(Impresora).where(Impresora.es_por_defecto.is_(True))):
                otra.es_por_defecto = False
        imp = Impresora(nombre=nombre.strip(), destino=destino.strip() or "local",
                        tipo_conexion=tipo_conexion, es_por_defecto=es_por_defecto,
                        activa=True)
        self.db.add(imp)
        self.db.flush()
        return imp

    def listar_impresoras(self) -> list[Impresora]:
        return self.db.scalars(
            select(Impresora).order_by(Impresora.nombre)).all()

    def crear_grupo(self, nombre: str,
                    impresora_id: Optional[int] = None) -> GrupoImpresion:
        if not nombre.strip():
            raise ValueError("El nombre del grupo es obligatorio")
        g = GrupoImpresion(nombre=nombre.strip(), impresora_id=impresora_id,
                           activo=True)
        self.db.add(g)
        self.db.flush()
        return g

    def listar_grupos(self) -> list[GrupoImpresion]:
        return self.db.scalars(
            select(GrupoImpresion).order_by(GrupoImpresion.nombre)).all()
