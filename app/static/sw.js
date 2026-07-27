/*
 * Service Worker de CafBarDLA (PWA).
 *
 * Estrategia deliberada y conservadora, pensada para un sistema con datos
 * sensibles y sesion por cookie:
 *
 *  - Estaticos (/static/...): cache-first. Son versionados por CACHE_NAME;
 *    al cambiar la version se limpian los viejos.
 *  - Navegaciones (documentos HTML): network-first. NUNCA se cachea el HTML
 *    de paginas autenticadas: podria mostrar datos de otro usuario o cifras
 *    viejas. Si la red falla, se muestra la pagina offline.
 *  - Todo lo demas (APIs, POST, login, logout): pasa directo a la red, sin
 *    tocar la cache. Jamas se interceptan peticiones que no sean GET.
 */

const CACHE_NAME = "cafbardla-v1";
const OFFLINE_URL = "/offline";

// Shell minima: solo estaticos y la pagina offline. NADA autenticado.
const PRECACHE = [
  "/offline",
  "/static/app.css",
  "/static/css/design-system.css",
  "/static/css/layout.css",
  "/static/css/dashboard.css",
  "/static/css/app-additional.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // addAll falla si un recurso da 404; usamos add individual tolerante.
      Promise.allSettled(PRECACHE.map((url) => cache.add(url)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((claves) =>
      Promise.all(
        claves.filter((c) => c !== CACHE_NAME).map((c) => caches.delete(c))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Solo GET. Los POST (login, ventas, etc.) nunca se tocan.
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Solo mismo origen. Peticiones externas pasan directo.
  if (url.origin !== self.location.origin) return;

  // Estaticos: cache-first.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((cached) =>
        cached ||
        fetch(req).then((resp) => {
          if (resp.ok) {
            const copia = resp.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copia));
          }
          return resp;
        })
      )
    );
    return;
  }

  // Navegaciones (paginas): network-first, fallback a offline.
  // No se cachea el HTML autenticado.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Resto (incl. /api/...): red directa, sin cache.
});
