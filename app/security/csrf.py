"""Proteccion CSRF para formularios que usan sesion por cookie.

El token se genera por sesion (ya existia) y ahora SE VALIDA en cada peticion
que modifica estado (POST, PUT, PATCH, DELETE) proveniente de un formulario.

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

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Rutas exentas (no usan cookie de sesion o no cambian estado de negocio).
EXENTAS = {"/login", "/logout"}
EXENTAS_PREFIJO = ("/api/v1/mobile/", "/api/v1/kds/", "/api/cliente", "/api/mesero")


class CSRFMiddleware(BaseHTTPMiddleware):
    """Valida el token CSRF en peticiones que modifican estado."""

    def __init__(self, app, *, activo: bool = True):
        super().__init__(app)
        self.activo = activo

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.activo or request.method in METODOS_SEGUROS:
            return await call_next(request)

        ruta = request.url.path
        if ruta in EXENTAS or ruta.startswith(EXENTAS_PREFIJO):
            return await call_next(request)

        # Las peticiones con cuerpo JSON no son explotables por el CSRF clasico
        # de formularios: un formulario HTML cross-site no puede fijar el
        # Content-Type a application/json. Las APIs REST bajo /api/ que reciben
        # JSON se eximen; su autenticacion real es por token Bearer.
        ctype = request.headers.get("content-type", "")
        if ruta.startswith("/api/") and "application/json" in ctype:
            return await call_next(request)

        # Solo aplica si hay sesion (formularios autenticados por cookie).
        sesion = request.scope.get("session") or {}
        token_sesion = sesion.get("csrf_token")
        autenticado = bool(sesion.get("usuario_id"))

        if not token_sesion:
            # Si el usuario esta autenticado pero aun no hay token en la sesion,
            # una peticion que modifica estado debe rechazarse: sin token no se
            # puede verificar el origen. (En el flujo normal el token se siembra
            # al renderizar cualquier pagina, antes de cualquier POST.)
            if autenticado:
                logger.warning("POST autenticado sin token CSRF en sesion: %s",
                               ruta)
                return JSONResponse(
                    {"detail": "Token de seguridad ausente. "
                               "Recargue la pagina e intente de nuevo."},
                    status_code=403)
            # Sin sesion no hay nada que proteger por CSRF (el guard de
            # autenticacion rechazara si la ruta es privada).
            return await call_next(request)

        token_recibido = await self._extraer_token(request)
        if not token_recibido or not hmac.compare_digest(
                str(token_recibido), str(token_sesion)):
            logger.warning("CSRF invalido en %s desde %s", ruta,
                           request.client.host if request.client else "?")
            return JSONResponse(
                {"detail": "Token de seguridad invalido o ausente. "
                           "Recargue la pagina e intente de nuevo."},
                status_code=403)

        return await call_next(request)

    async def _extraer_token(self, request: Request):
        # Cabecera primero (peticiones AJAX). No consume el body.
        header = request.headers.get("x-csrf-token")
        if header:
            return header
        # Campo de formulario. IMPORTANTE: leer el body aqui lo consume, y luego
        # la ruta recibiria un form vacio ("nombre: null"). Para evitarlo,
        # cacheamos el body crudo y lo reponemos en el canal de recepcion para
        # que FastAPI pueda volver a leerlo en la ruta.
        ctype = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
            try:
                body = await request.body()
                sent = False
                async def _receive():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {"type": "http.request", "body": body, "more_body": False}
                    return {"type": "http.disconnect"}
                request._receive = _receive

                # Parsear el token del body ya cacheado.
                from urllib.parse import parse_qs
                if "application/x-www-form-urlencoded" in ctype:
                    datos = parse_qs(body.decode("utf-8", "ignore"))
                    valores = datos.get("csrf_token")
                    return valores[0] if valores else None
                # multipart: usar el parser de Starlette (ya con el body repuesto)
                form = await request.form()
                return form.get("csrf_token")
            except Exception:
                return None
        return None
