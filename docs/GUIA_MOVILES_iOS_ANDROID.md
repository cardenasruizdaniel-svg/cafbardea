# 📱 CafBarDLA en iOS y Android

## 🎯 Resumen

CafBarDLA es una **aplicación web**, por lo que **no necesitas instalar nada especial** en iOS/Android. Simplemente abre el navegador y accede a la URL del servidor.

---

## 🖥️ Paso 1: Instalar y Ejecutar en Windows

### Instalación:
1. **Ejecuta el instalador:** `CafBarDLA-Installer.bat`
2. **Sigue las instrucciones** (selecciona carpeta, espera dependencias)
3. **Se creará acceso directo** en tu escritorio

### Ejecutar:
```bash
# Opción A: Haz doble clic en CafBarDLA.lnk (escritorio)

# Opción B: Abre PowerShell en carpeta de instalación:
cd "C:\Program Files\CafBarDLA"
.buildenv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Verás:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started 4 worker processes
```

---

## 📡 Paso 2: Obtener IP del PC

Necesitas la dirección IP local de tu computadora para acceder desde el móvil.

### En Windows:

**Opción A: CMD (Rápido)**
```cmd
ipconfig
```
Busca la línea: `IPv4 Address: 192.168.1.XXX`

**Opción B: PowerShell**
```powershell
$env:COMPUTERNAME
(Get-NetIPAddress | Where-Object {$_.AddressFamily -eq "IPv4" -and $_.PrefixOrigin -eq "Dhcp"}).IPAddress
```

### Ejemplo:
```
Si tu IP es: 192.168.1.100
Entonces accederás desde móvil: http://192.168.1.100:8000
```

---

## 📱 Paso 3: Acceder desde iPhone/iPad (iOS)

### Requisitos:
- ✅ Estar en la **misma red WiFi** que el PC
- ✅ Tener Safari, Chrome, Firefox, Edge instalado

### Instrucciones:

1. **Abre el navegador** (Safari, Chrome, etc.)

2. **En la barra de dirección**, ingresa:
   ```
   http://192.168.1.100:8000
   ```
   (Reemplaza 192.168.1.100 con tu IP real)

3. **Presiona Enter**

4. **¡Listo!** La aplicación se carga en el navegador

5. **Login:**
   - Usuario: `admin`
   - Contraseña: `admin`

### Para ahorrar pasos:

**Guardar como favorito:**
- Presiona el ícono de compartir (↗️)
- Selecciona "Añadir a pantalla de inicio"
- Dale un nombre: "CafBarDLA"
- Presiona "Añadir"
- ¡Ahora tienes un ícono en la pantalla de inicio!

### Acceso sin escribir URL:

**En Safari:**
1. Ve a la dirección: http://192.168.1.100:8000
2. Presiona el ícono de compartir (↗️) 
3. Selecciona "Añadir marcador" o "Añadir a pantalla de inicio"

**En Chrome:**
1. Ve a la dirección: http://192.168.1.100:8000
2. Presiona los tres puntos (⋮)
3. Selecciona "Añadir a pantalla de inicio"

---

## 🤖 Acceder desde Android

### Requisitos:
- ✅ Estar en la **misma red WiFi** que el PC
- ✅ Tener navegador instalado (Chrome, Firefox, Edge, etc.)

### Instrucciones:

1. **Abre el navegador** (Chrome, Firefox, etc.)

2. **En la barra de dirección**, ingresa:
   ```
   http://192.168.1.100:8000
   ```
   (Reemplaza con tu IP real)

3. **Presiona Enter / Ir**

4. **¡Listo!** La aplicación se abre

5. **Login:**
   - Usuario: `admin`
   - Contraseña: `admin`

### Para ahorrar pasos:

**Crear acceso rápido (Chrome):**
1. Ve a: http://192.168.1.100:8000
2. Presiona los tres puntos (⋮)
3. Selecciona "Instalar aplicación" o "Añadir a pantalla de inicio"
4. Dale un nombre: "CafBarDLA"
5. Presiona "Instalar"
6. ¡Ahora tienes un ícono en la pantalla de inicio!

**Crear acceso rápido (Firefox):**
1. Ve a: http://192.168.1.100:8000
2. Presiona los tres puntos (⋮)
3. Selecciona "Instalar"
4. Presiona "Instalar" nuevamente

---

## 🌐 Características de la Aplicación Web

Una vez dentro de la aplicación, puedes:

### 📋 Para Meseros/Vendedores:
- Crear comandas
- Seleccionar mesa/cliente
- Agregar productos
- Enviar a cocina
- Ver estado de preparación

### 👨‍🍳 Para Cocineros (KDS):
- Ver órdenes en tiempo real
- Marcar items listos
- Recibir notificaciones

### 💼 Para Gerentes:
- Reportes de ventas
- Control de inventario
- Gestión de usuarios
- Cierre de caja

### 📊 Para Análisis:
- Gráficos de ventas
- Productos más vendidos
- Tendencias

---

## 🔧 Solución de Problemas

### "No puedo acceder desde el móvil"

**Causa 1: No están en la misma red**
- ✅ Verifica que PC y móvil están conectados al **mismo WiFi**
- ✅ No uses WiFi de invitados (generalmente está aislado)

**Causa 2: Firewall bloqueando**
- Abre Windows Defender Firewall
- Permite CafBarDLA en redes privadas
- O desactiva firewall temporalmente para pruebas

**Causa 3: Servidor no está ejecutándose**
- Verifica que ves "Uvicorn running on http://0.0.0.0:8000"
- Si no, ejecuta nuevamente: `RunServer.bat`

**Causa 4: IP incorrecta**
- Ejecuta `ipconfig` en CMD
- Copia la IP exacta (ej: 192.168.1.100)
- Prueba desde el navegador del PC primero: http://localhost:8000

### "Aparece pantalla en blanco"

- Espera unos segundos a que cargue
- Presiona F5 para recargar
- Verifica la consola (F12) para mensajes de error

### "Dice 'Conexión rechazada'"

- El servidor no está ejecutándose
- Ejecuta: `RunServer.bat`
- Espera a ver "Uvicorn running on..."

### "El login no funciona"

- Usuario: `admin` (exactamente)
- Contraseña: `admin` (exactamente)
- Las credenciales son sensibles a mayúsculas

### "Error de seguridad / No confiable"

- Es normal porque usamos HTTP (no HTTPS)
- Para uso local es seguro
- Presiona "Continuar" o "Proceder de todas formas"

---

## 🚀 Para Producción

Si quieres acceso desde internet (no solo red local):

**Opción 1: DigitalOcean (Recomendado - $5/mes)**
- Ver: `docs/CLOUD_DEPLOYMENT_GUIDE.md`
- Se accede desde cualquier lugar: `https://tu-dominio.com`

**Opción 2: Acceso remoto con VPN**
- Usa VPN (NordVPN, ExpressVPN, etc.)
- Conecta desde móvil a la misma VPN
- Accede por IP local

**Opción 3: Port Forwarding**
- Configura router para exponer puerto 8000
- ⚠️ Menos seguro, no recomendado

---

## 📋 Checklist

- [ ] CafBarDLA instalado en PC
- [ ] Servidor ejecutándose (RunServer.bat)
- [ ] Obtuve la IP del PC (ipconfig)
- [ ] Móvil conectado a la misma WiFi
- [ ] Accedí desde móvil: http://IP:8000
- [ ] Hice login: admin / admin
- [ ] Creé acceso rápido en pantalla de inicio

---

## 💡 Tips

1. **Mantén el PC encendido** mientras uses la app desde móvil
2. **La red debe ser estable** (WiFi de buena señal)
3. **Cambia la contraseña** del admin en primera sesión
4. **Prueba en PC primero** (http://localhost:8000) si falla en móvil
5. **Para producción real** usa DigitalOcean o similar

---

## 📞 Soporte

- Email: support@dlatecnologia.com
- Teléfono: +57 1 2345678
- WhatsApp: +57 310 5678901

---

**¡Disfruta usando CafBarDLA desde tu dispositivo móvil! ☕📱**
