/*
 * Registro del service worker + experiencia de instalacion y estado offline.
 * Se carga en todas las paginas desde base.html.
 */
(function () {
  "use strict";

  // 1. Registrar el service worker.
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function (e) {
        console.warn("SW no registrado:", e);
      });
    });
  }

  // 2. Boton de instalacion (aparece cuando el navegador lo permite).
  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    mostrarBotonInstalar();
  });

  function mostrarBotonInstalar() {
    if (document.getElementById("pwa-instalar")) return;
    var btn = document.createElement("button");
    btn.id = "pwa-instalar";
    btn.type = "button";
    btn.textContent = "Instalar app";
    btn.className = "pwa-install-btn";
    btn.addEventListener("click", function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        btn.remove();
      });
    });
    document.body.appendChild(btn);
  }

  window.addEventListener("appinstalled", function () {
    var btn = document.getElementById("pwa-instalar");
    if (btn) btn.remove();
  });

  // 3. Indicador de conexion perdida.
  var banner = null;
  function mostrarOffline() {
    if (banner) return;
    banner = document.createElement("div");
    banner.className = "pwa-offline-banner";
    banner.textContent = "Sin conexión — trabajando en modo offline";
    document.body.appendChild(banner);
  }
  function ocultarOffline() {
    if (banner) { banner.remove(); banner = null; }
  }
  window.addEventListener("offline", mostrarOffline);
  window.addEventListener("online", ocultarOffline);
  if (!navigator.onLine) mostrarOffline();
})();
