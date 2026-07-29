"""Proteccion CSRF para formularios que usan sesion por cookie.

Implementado como middleware ASGI puro (sin BaseHTTPMiddleware) para evitar
los bugs conocidos de Starlette con el consumo del body:
  - "RuntimeError: No response returned."
  - "RuntimeError: Unexpected message received: http.request"

El token se genera por sesion y SE VALIDA en cada peticion que modifica estado
(POST, PUT, PATCH, DELETE) proveniente de un formulario.

Se excluyen:
  - metodos seguros (GET, HEAD, OPTIONS);
  - el login y logout (aun no hay sesion / no cambia datos de negocio);
  - las APIs que se autentican por token Bearer (no por cookie), inmunes a CSRF.

El token se acepta desde el campo de formulario 'csrf_token' o la cabecera
'X-CSRF-Token'. La comparacion es de tiempo constante.
"""

from __future__ import annotations

import hmac
import logging
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Rutas exentas (no usan cookie de sesion o no cambian estado de negocio).
EXENTAS = {"/login", "/logout"}
EXENTAS_PREFIJO = ("/api/v1/mobile/", "/api/v1/kds/", "/api/cliente", "/api/mesero")


class CSRFMiddleware:
    """Valida el token CSRF en peticiones que modifican estado.

    Middleware ASGI puro — no hereda de BaseHTTPMiddleware para evitar
    la corrupcion del stream de body que causa RuntimeError.
    """

    def __init__(self, app: ASGIApp, *, activo: bool = True):
        self.app = app
        self.activo = activo

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        metodo = scope.get("method", "GET")

        # Metodos seguros: dejar pasar sin validar.
        if not self.activo or metodo in METODOS_SEGUROS:
            await self.app(scope, receive, send)
            return

        ruta = scope["path"]
        if ruta in EXENTAS or ruta.startswith(EXENTAS_PREFIJO):
            await self.app(scope, receive, send)
            return

        # APIs JSON: inmunes al CSRF clasico de formularios.
        raw_headers = dict(scope.get("headers", []))
        ctype = raw_headers.get(b"content-type", b"").decode("latin-1")
        if ruta.startswith("/api/") and "application/json" in ctype:
            await self.app(scope, receive, send)
            return

        # Solo aplica si hay sesion (formularios autenticados por cookie).
        sesion = scope.get("session") or {}
        token_sesion = sesion.get("csrf_token")
        autenticado = bool(sesion.get("usuario_id"))

        if not token_sesion:
            if autenticado:
                logger.warning("POST autenticado sin token CSRF en sesion: %s", ruta)
                resp = JSONResponse(
                    {"detail": "Token de seguridad ausente. "
                               "Recargue la pagina e intente de nuevo."},
                    status_code=403)
                await resp(scope, receive, send)
                return
            # Sin sesion no hay nada que proteger.
            await self.app(scope, receive, send)
            return

        # Extraer token. Si se consume el body, _extraer_token almacena
        # un receive sustituto en scope["_csrf_cached_receive"].
        token_recibido = await self._extraer_token(scope, receive, ctype)

        if not token_recibido or not hmac.compare_digest(
                str(token_recibido), str(token_sesion)):
            logger.warning("CSRF invalido en %s", ruta)
            resp = JSONResponse(
                {"detail": "Token de seguridad invalido o ausente. "
                           "Recargue la pagina e intente de nuevo."},
                status_code=403)
            await resp(scope, receive, send)
            return

        # Usar el receive cacheado si el body fue consumido para extraer el token.
        downstream_receive = scope.pop("_csrf_cached_receive", None) or receive
        await self.app(scope, downstream_receive, send)

    async def _extraer_token(self, scope: Scope, receive: Receive, ctype: str):
        """Extrae el token CSRF del header o del body del formulario.

        Para formularios: lee todo el body, parsea el token, y reemplaza
        `receive` con una version que re-entrega el body ya leido al downstream.
        """
        # Header primero (peticiones AJAX). No consume body.
        raw_headers = dict(scope.get("headers", []))
        header_token = raw_headers.get(b"x-csrf-token", b"").decode("latin-1")
        if header_token:
            return header_token

        # Solo parsear body para formularios.
        if "application/x-www-form-urlencoded" not in ctype and "multipart/form-data" not in ctype:
            return None

        try:
            # Leer todo el body.
            body = b""
            while True:
                msg = await receive()
                body += msg.get("body", b"")
                if not msg.get("more_body", False):
                    break

            # Crear un receive sustituto que re-entrega el body ya leido.
            body_sent = False
            original_receive = receive

            async def cached_receive():
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": body, "more_body": False}
                # Despues del body, esperar el disconnect real del cliente.
                return await original_receive()

            # Almacenar en scope para que __call__ lo pase al downstream.
            scope["_csrf_cached_receive"] = cached_receive

            # Parsear el token del body.
            if "application/x-www-form-urlencoded" in ctype:
                datos = parse_qs(body.decode("utf-8", "ignore"))
                valores = datos.get("csrf_token")
                return valores[0] if valores else None

            # Para multipart, buscar el campo csrf_token manualmente
            # en el body crudo (evita usar request.form() que corrompe el stream).
            csrf_marker = b'name="csrf_token"'
            if csrf_marker in body:
                idx = body.index(csrf_marker) + len(csrf_marker)
                rest = body[idx:]
                sep = rest.find(b"\r\n\r\n")
                if sep != -1:
                    valor_start = sep + 4
                    end = rest.find(b"\r\n--", valor_start)
                    if end == -1:
                        end = rest.find(b"\r\n", valor_start)
                    if end != -1:
                        return rest[valor_start:end].decode("utf-8", "ignore").strip()
            return None
        except Exception:
            return None

