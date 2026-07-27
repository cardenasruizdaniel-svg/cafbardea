/*
 * Service Worker de la APP DE CLIENTE (autoservicio / pedido en mesa).
 *
 * A diferencia del SW general, esta app es PUBLICA y sin datos sensibles, asi
 * que si puede funcionar offline:
 *   - La pagina /cliente y la carta se cachean para verse sin conexion.
 *   - Los pedidos se pueden armar offline; el envio se encola en el cliente
 *     (IndexedDB en la pagina) y se reintenta al volver la red vía Background
 *     Sync o al recuperar conexion.
 *
 * Solo cachea rutas del cliente; jamas toca rutas autenticadas del sistema.
 */

const CACHE = "cafbardla-cliente-v1";
const RUTAS = [
  "/cliente",
  "/api/cliente/carta",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.allSettled(RUTAS.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((claves) =>
      Promise.all(claves.filter((c) => c !== CACHE).map((c) => caches.delete(c)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Solo mismo origen y solo rutas del cliente.
  if (url.origin !== self.location.origin) return;
  const esCliente = url.pathname === "/cliente" ||
                    url.pathname.startsWith("/api/cliente");
  if (!esCliente) return;

  // El envio de pedidos (POST) NUNCA se sirve de cache: se maneja en la pagina
  // con la cola offline. Aqui dejamos pasar a la red.
  if (req.method !== "GET") return;

  // La carta: network-first (datos frescos si hay red), cache si no hay.
  if (url.pathname.startsWith("/api/cliente/carta")) {
    event.respondWith(
      fetch(req).then((resp) => {
        if (resp.ok) {
          const copia = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, copia));
        }
        return resp;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // La pagina /cliente: network-first con fallback a la copia cacheada.
  if (req.mode === "navigate" || url.pathname === "/cliente") {
    event.respondWith(
      fetch(req).then((resp) => {
        if (resp.ok) {
          const copia = resp.clone();
          caches.open(CACHE).then((c) => c.put("/cliente", copia));
        }
        return resp;
      }).catch(() => caches.match("/cliente"))
    );
    return;
  }
});
