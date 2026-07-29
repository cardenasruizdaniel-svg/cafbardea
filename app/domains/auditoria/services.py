"""Servicio de auditoria: registro de acciones del sistema.

Punto unico para registrar quien hizo que, cuando y desde donde. Se usa de forma
manual en los puntos importantes (ventas, nomina, anulaciones, accesos), tal
como se decidio, porque el registro explicito es mas preciso que interceptar
todas las tablas.

Principios:
  - Nunca tumba una operacion de negocio: si el registro falla, se traga el
    error (con log) en vez de propagarlo.
  - Nunca guarda datos sensibles (contrasenas, hashes, tokens): hay una lista
    de campos que se ocultan al serializar antes/despues.
  - Es append-only: el servicio solo crea; no edita ni borra.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RegistroAuditoria, hora_colombia

logger = logging.getLogger("auditoria")

# Campos que NUNCA se registran (aunque vengan en un dict de antes/despues).
CAMPOS_SENSIBLES = {
    "password", "password_hash", "clave", "contrasena", "contrasena_hash",
    "token", "jwt", "secret", "secret_key", "csrf_token", "hash",
}

ACCIONES = {"acceso", "acceso_denegado", "crear", "editar", "anular",
            "eliminar", "otro"}


def _serializar(valor: Any) -> Optional[str]:
    """Convierte un dict/valor a JSON, ocultando campos sensibles."""
    if valor is None:
        return None
    if isinstance(valor, dict):
        limpio = {}
        for k, v in valor.items():
            if k.lower() in CAMPOS_SENSIBLES:
                limpio[k] = "***"
            else:
                limpio[k] = _valor_simple(v)
        try:
            return json.dumps(limpio, ensure_ascii=False, default=str)
        except Exception:
            return str(limpio)
    return str(valor)


def _valor_simple(v: Any) -> Any:
    if isinstance(v, (Decimal, )):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


class AuditoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.logger = logger

    def registrar(self, *, accion: str,
                  usuario_id: Optional[int] = None,
                  usuario_nombre: Optional[str] = None,
                  rol: Optional[str] = None, ip: Optional[str] = None,
                  modulo: Optional[str] = None, entidad: Optional[str] = None,
                  entidad_id: Optional[Any] = None,
                  descripcion: Optional[str] = None,
                  antes: Any = None, despues: Any = None,
                  resultado: str = "exito", empresa_id: Optional[int] = None
                  ) -> Optional[RegistroAuditoria]:
        try:
            if accion not in ACCIONES:
                accion = "otro"
            if not empresa_id:
                from app.models import Empresa
                from sqlalchemy import select
                emp = self.db.scalar(select(Empresa).limit(1))
                empresa_id = emp.id if emp else 1

            reg = RegistroAuditoria(
                empresa_id=empresa_id,
                fecha_hora=hora_colombia(),
                usuario_id=usuario_id,
                usuario_nombre=usuario_nombre or "sistema",
                rol=rol, ip=ip, accion=accion,
                modulo=modulo, entidad=entidad,
                entidad_id=str(entidad_id) if entidad_id is not None else None,
                descripcion=descripcion,
                valor_anterior=_serializar(antes),
                valor_nuevo=_serializar(despues),
                resultado=resultado
            )
            self.db.add(reg)
            return reg
        except Exception as e:
            self.logger.warning("No se pudo registrar log de auditoría: %s", e)
            return None

    def registrar_desde_request(self, request, *, accion: str, **kwargs
                                ) -> Optional[RegistroAuditoria]:
        """Atajo que toma usuario/rol/IP de la sesion y la peticion."""
        sesion = {}
        try:
            sesion = request.scope.get("session") or {}
        except Exception:
            pass
        ip = self._ip(request)
        emp_id = sesion.get("empresa_id")
        return self.registrar(
            accion=accion,
            usuario_id=sesion.get("usuario_id"),
            usuario_nombre=sesion.get("usuario_nombre"),
            rol=sesion.get("rol"), ip=ip,
            empresa_id=emp_id,
            **kwargs)

    @staticmethod
    def _ip(request) -> Optional[str]:
        try:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                return xff.split(",")[0].strip()
            return request.client.host if request.client else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Consulta (para la pantalla de auditoria)
    # ------------------------------------------------------------------
    def listar(self, *, limite: int = 100,
               accion: Optional[str] = None,
               modulo: Optional[str] = None,
               usuario_id: Optional[int] = None) -> list[RegistroAuditoria]:
        q = select(RegistroAuditoria).order_by(RegistroAuditoria.id.desc())
        if accion:
            q = q.where(RegistroAuditoria.accion == accion)
        if modulo:
            q = q.where(RegistroAuditoria.modulo == modulo)
        if usuario_id:
            q = q.where(RegistroAuditoria.usuario_id == usuario_id)
        return self.db.scalars(q.limit(limite)).all()
