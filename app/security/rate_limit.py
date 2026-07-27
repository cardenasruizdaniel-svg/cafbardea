"""Rate limiting en memoria (sin dependencias externas).

Limita peticiones por IP con una ventana deslizante simple. Pensado para frenar
fuerza bruta y abuso; para un despliegue con varios procesos conviene un backend
compartido (Redis), pero para un negocio de un solo servidor esto es suficiente.

Se aplican dos limites:
  - uno estricto al login (contra fuerza bruta de credenciales);
  - uno general al resto (contra abuso/DoS ligero).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class _Ventana:
    """Cuenta marcas de tiempo dentro de una ventana deslizante por clave."""

    def __init__(self):
        self._eventos: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def permitido(self, clave: str, limite: int, periodo: float) -> bool:
        ahora = time.monotonic()
        with self._lock:
            cola = self._eventos[clave]
            # descartar lo que salio de la ventana
            while cola and cola[0] <= ahora - periodo:
                cola.popleft()
            if len(cola) >= limite:
                return False
            cola.append(ahora)
            return True

    def limpiar(self, antiguedad: float = 3600) -> None:
        ahora = time.monotonic()
        with self._lock:
            for clave in list(self._eventos):
                cola = self._eventos[clave]
                while cola and cola[0] <= ahora - antiguedad:
                    cola.popleft()
                if not cola:
                    del self._eventos[clave]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Aplica limites por IP. El login tiene un limite mas estricto."""

    def __init__(self, app, *, activo: bool = True,
                 limite_general: int = 100, periodo_general: int = 3600,
                 limite_login: int = 10, periodo_login: int = 300):
        super().__init__(app)
        self.activo = activo
        self.limite_general = limite_general
        self.periodo_general = periodo_general
        self.limite_login = limite_login
        self.periodo_login = periodo_login
        self._ventana = _Ventana()
        self._ultimo_barrido = time.monotonic()

    def _ip(self, request: Request) -> str:
        # Respeta X-Forwarded-For si hay proxy reverso, cae al cliente directo.
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "desconocido"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.activo:
            return await call_next(request)

        # No limitar recursos estaticos ni health (ruido).
        ruta = request.url.path
        if ruta.startswith(("/static", "/favicon")) or ruta == "/health":
            return await call_next(request)

        ip = self._ip(request)

        # Limite estricto al login por POST (fuerza bruta de credenciales).
        if ruta == "/login" and request.method == "POST":
            if not self._ventana.permitido(
                    f"login:{ip}", self.limite_login, self.periodo_login):
                return self._bloqueo("Demasiados intentos de acceso. "
                                     "Espere unos minutos e intente de nuevo.")

        # Limite general por IP.
        if not self._ventana.permitido(
                f"gen:{ip}", self.limite_general, self.periodo_general):
            return self._bloqueo("Demasiadas peticiones. Intente mas tarde.")

        # Barrido periodico de claves viejas.
        ahora = time.monotonic()
        if ahora - self._ultimo_barrido > 600:
            self._ventana.limpiar()
            self._ultimo_barrido = ahora

        return await call_next(request)

    def _bloqueo(self, mensaje: str) -> Response:
        return JSONResponse({"detail": mensaje}, status_code=429)
