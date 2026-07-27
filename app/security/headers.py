"""Cabeceras de seguridad HTTP.

Middleware que agrega las cabeceras recomendadas por OWASP a cada respuesta:
proteccion contra clickjacking, sniffing de MIME, XSS, fuga de referrer y
downgrade a HTTP. La CSP se ajusta al hecho de que las plantillas usan estilos
en linea y algun script inline, por lo que se permite 'unsafe-inline' en style
y script (endurecer esto requeriria nonces en cada plantilla).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _construir_csp() -> str:
    """Content-Security-Policy. Se permite inline en estilos/scripts porque las
    plantillas actuales los usan; el resto queda restringido a mismo origen."""
    directivas = [
        "default-src 'self'",
        # Los templates traen <style> y algo de JS inline.
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        # El favicon es un data: URI SVG.
        "connect-src 'self'",
        "frame-ancestors 'none'",   # equivalente moderno a X-Frame-Options DENY
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ]
    return "; ".join(directivas)


CSP = _construir_csp()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Agrega cabeceras de seguridad a todas las respuestas."""

    def __init__(self, app, *, hsts: bool = False):
        super().__init__(app)
        # HSTS solo tiene sentido bajo HTTPS (produccion). En desarrollo (HTTP)
        # activarlo obligaria al navegador a intentar HTTPS y romperia el acceso.
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()")
        # Evita que respuestas con datos queden en caches compartidas.
        if request.url.path.startswith(("/api/", "/nomina/", "/caja")):
            response.headers.setdefault("Cache-Control", "no-store")

        if self.hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains")

        # No revelar el servidor.
        response.headers["X-Powered-By"] = "CafBarDLA"
        return response
