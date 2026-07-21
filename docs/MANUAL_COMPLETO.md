# 📘 CafBarDLA POS - MANUAL COMPLETO DE INSTALACIÓN, CONFIGURACIÓN Y FUNCIONAMIENTO

**Versión:** 0.1.0  
**Fecha:** 2026-07-20  
**Empresa:** DLA Tecnología  
**Soporte:** support@dlatecnologia.com  

---

## 📚 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Requisitos del Sistema](#requisitos)
3. [Instalación Windows (Método Manual)](#instalación-windows)
4. [Instalación Windows (Ejecutable)](#instalación-ejecutable)
5. [Configuración de la Aplicación](#configuración)
6. [Parametrización del Sistema](#parametrización)
7. [Manual de Funcionamiento](#funcionamiento)
8. [Deployment en la Nube](#nube)
9. [Mantenimiento y Soporte](#mantenimiento)

---

## 🎯 Descripción General {#descripción-general}

**CafBarDLA** es un sistema de Punto de Venta (POS) profesional diseñado específicamente para cafeterías, bares y restaurantes. 

### Características Principales

✅ **FASE 1-4: Sistema POS Completo**
- Gestión de comandas y mesas
- Control de inventario
- Gestión de clientes y proveedores
- Reportes y análisis de ventas
- Facturación electrónica
- Nomina de empleados

✅ **FASE 5: Sistema Enterprise**
- Control de acceso y permisos
- Auditoría de operaciones
- Backups automáticos
- Sincronización multi-sucursal

✅ **FASE 6: Sistema de WebSocket**
- Notificaciones en tiempo real
- Actualizaciones de stock en vivo
- Pedidos sincronizados entre dispositivos

✅ **FASE 7: Mobile API**
- Aplicación móvil iOS/Android
- Toma de pedidos desde mesa
- Cierre de caja móvil

✅ **FASE 8: Kitchen Display System (KDS)**
- Pantalla de cocina en tiempo real
- Control de órdenes
- Priorización de pedidos

### Arquitectura Técnica

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENTE (Frontend)                    │
│              HTML5 + JavaScript + WebSocket            │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/HTTPS
┌────────────────────▼────────────────────────────────────┐
│                 FastAPI (Backend)                       │
│         Python 3.14 + SQLAlchemy + Uvicorn             │
│                 4 Worker Processes                      │
└────────────────────┬────────────────────────────────────┘
                     │ SQL
┌────────────────────▼────────────────────────────────────┐
│            Base de Datos (PostgreSQL/SQLite)           │
│         Alembic Migrations + SQLAlchemy ORM           │
└─────────────────────────────────────────────────────────┘
```

---

## 🖥️ Requisitos del Sistema {#requisitos}

### Para Windows (Servidor)

| Componente | Requisito |
|-----------|-----------|
| **SO** | Windows 10 / Windows 11 / Windows Server 2019+ |
| **Procesador** | Intel Core i5 o equivalente (2+ núcleos) |
| **RAM** | 4 GB mínimo, 8 GB recomendado |
| **Disco** | 2 GB libres (más para backups) |
| **Red** | Conexión Ethernet confiable |
| **Python** | Python 3.10+ (incluido en instalador) |
| **PostgreSQL** | 13+ (opcional, SQLite incluido) |

### Para Clientes (Terminales POS)

| Dispositivo | Requisito |
|-----------|-----------|
| **Windows** | Windows 10+ / Chrome / Firefox / Edge |
| **Tablet** | iPad / Android 10+ |
| **Smartphone** | iOS 13+ / Android 10+ |
| **Conexión** | Red WiFi o LAN (mín. 5 Mbps) |

### Requisitos de Red

```
┌──────────────────────────────────────┐
│     Servidor CafBarDLA               │
│     IP: 192.168.1.100:8000           │
└─────────────┬───────────────┬────────┘
              │               │
     ┌────────▼──────┐  ┌─────▼──────┐
     │  Terminal 1   │  │  Tablet 1  │
     │ 192.168.1.101 │  │192.168.1.50│
     └───────────────┘  └────────────┘
     ┌────────────────┐  ┌────────────┐
     │  Terminal 2    │  │ Smartphone │
     │ 192.168.1.102  │  │192.168.1.51│
     └────────────────┘  └────────────┘
```

**Requerimientos de Red:**
- Router con DHCP habilitado
- Ancho de banda: ≥ 50 Mbps entre terminales
- Latencia: ≤ 100 ms
- Pérdida de paquetes: ≤ 1%

---

## 📦 Instalación Windows (Método Manual) {#instalación-windows}

### Paso 1: Preparar el Servidor

```powershell
# Abrir PowerShell como Administrador
# (Click derecho → Ejecutar como administrador)

# 1. Crear carpeta de instalación
New-Item -ItemType Directory -Path "D:\CafBarDLA" -Force

# 2. Cambiar a esa carpeta
cd D:\CafBarDLA

# 3. Descargar proyecto (o copiar)
# Opción A: Desde Git
git clone https://github.com/tuusuario/CafBarDLA.git .

# Opción B: Descargar ZIP y extraer en D:\CafBarDLA
```

### Paso 2: Instalar Python y Dependencias

```powershell
# Verificar si Python está instalado
python --version

# Si no está instalado:
# Descargar de https://www.python.org/downloads/
# Instalar versión 3.11 o superior
# ✅ Marcar: "Add Python to PATH" durante instalación

# Verificar pip
pip --version

# Actualizar pip
python -m pip install --upgrade pip
```

### Paso 3: Crear Entorno Virtual

```powershell
# En D:\CafBarDLA

# Crear entorno virtual
python -m venv .buildenv

# Activar entorno virtual
.buildenv\Scripts\Activate.ps1

# Si falla con error de permisos:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.buildenv\Scripts\Activate.ps1

# Verificar (verás (.buildenv) al inicio de la línea de comandos)
```

### Paso 4: Instalar Dependencias Python

```powershell
# Asegúrate que el entorno virtual esté activado (.buildenv debe verse)

# Instalar dependencias
pip install -r requirements.txt

# Instalar herramientas adicionales
pip install alembic sqlalchemy-utils python-multipart

# Verificar instalación
pip list
```

### Paso 5: Configurar la Base de Datos

```powershell
# Opción A: SQLite (Recomendado para inicio)
# No requiere configuración, se crea automáticamente

# Opción B: PostgreSQL (Para producción real)
# Descargar e instalar desde https://www.postgresql.org/download/windows/
# Durante instalación:
#   - Username: postgres
#   - Password: (guardar de forma segura)
#   - Puerto: 5432
```

### Paso 6: Configurar Variables de Entorno

```powershell
# Copiar archivo de ejemplo
Copy-Item .env.production.example -Destination .env.production

# Editar el archivo .env.production
notepad .env.production

# Cambiar estas líneas (IMPORTANTE):

# Para SQLite:
DATABASE_URL=sqlite:///./cafbardla_prod.db

# Para PostgreSQL (cambiar PASSWORD y HOST):
DATABASE_URL=postgresql://user:PASSWORD@localhost:5432/cafbardla

# Generar claves JWT (necesitas tener el entorno activado)
# En PowerShell:
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('SESSION_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Copiar los valores generados al .env.production
```

### Paso 7: Inicializar la Base de Datos

```powershell
# Ejecutar migraciones Alembic
alembic upgrade head

# Verificar que se creó la BD (si es SQLite)
# Debe aparecer: cafbardla_prod.db en D:\CafBarDLA

# Verificar BD
ls *.db
```

### Paso 8: Ejecutar la Aplicación

```powershell
# Iniciar servidor FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Verás mensajes como:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Started 4 worker processes

# Presiona CTRL+C para detener
```

### ✅ ¡Instalación Completada!

Accede a la aplicación:
- **Interfaz Web:** http://localhost:8000
- **Documentación API:** http://localhost:8000/docs
- **Usuario por defecto:** admin / admin

---

## 🚀 Instalación Windows (Ejecutable) {#instalación-ejecutable}

### Opción A: Descargar Instalador (Más Fácil)

```powershell
# 1. Descargar CafBarDLA-Setup.exe
# Desde: https://releases.cafbardla.com/CafBarDLA-Setup.exe

# 2. Ejecutar instalador
.\CafBarDLA-Setup.exe

# 3. Seguir asistente:
#    - Aceptar términos
#    - Seleccionar carpeta de instalación (ej: C:\Program Files\CafBarDLA)
#    - Crear atajo de escritorio (opcional)
#    - Finalizar

# 4. La aplicación se ejecutará automáticamente
# Acceder a: http://localhost:8000
```

### Opción B: Compilar Instalador Localmente

```powershell
# Requisitos previos:
# - Inno Setup instalado (https://jrsoftware.org/isdl.php)
# - Completar pasos 1-7 de "Instalación Manual"

cd D:\CafBarDLA

# Compilar ejecutable con PyInstaller
python -m PyInstaller launcher.py `
    --onefile `
    --windowed `
    --name CafBarDLA `
    --icon app/static/favicon.ico `
    --distpath dist_production `
    --add-data "app/templates;app/templates" `
    --add-data "app/static;app/static" `
    --add-data ".env.production;."

# Esperar a que se compile...
# Resultado: dist_production\CafBarDLA.exe

# Compilar instalador
.\scripts\build_installer.ps1

# Resultado: installer\Output\CafBarDLA-Setup.exe
```

---

## ⚙️ Configuración de la Aplicación {#configuración}

### Archivo .env.production

Ubicación: `D:\CafBarDLA\.env.production`

```ini
# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================

# SQLite (Desarrollo/Pruebas)
DATABASE_URL=sqlite:///./cafbardla_prod.db

# PostgreSQL (Producción)
# DATABASE_URL=postgresql://user:password@localhost:5432/cafbardla

# ============================================
# SEGURIDAD (IMPORTANTE - CAMBIAR EN PRODUCCIÓN)
# ============================================

JWT_SECRET_KEY=ZWhwTz3FusQdrtU1SUnG6_tREmcJM6HBHBGyyfGgAO0
SESSION_SECRET_KEY=deJ_iBzbxVs_mo3KkkAhU_BABnsjTg5aXlpH-tylDoM

# ============================================
# ENTORNO DE EJECUCIÓN
# ============================================

ENVIRONMENT=production      # development | production
DEBUG=false                 # true | false
LOG_LEVEL=INFO             # DEBUG | INFO | WARNING | ERROR

# ============================================
# SERVIDOR
# ============================================

HOST=0.0.0.0               # 0.0.0.0 = accesible desde cualquier IP
PORT=8000                  # Puerto del servidor
WORKERS=4                  # Número de procesos workers
RELOAD=false               # Auto-reload en cambios (solo desarrollo)

# ============================================
# CORS Y ACCESO
# ============================================

ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,http://192.168.1.100,https://tu-dominio.com

# Para desarrollo: http://localhost,http://127.0.0.1
# Para producción: https://tu-dominio.com

# ============================================
# BACKUPS
# ============================================

BACKUP_PATH=D:\Backups\CafBarDLA
BACKUP_RETENTION_DAYS=30   # Mantener backups por 30 días
BACKUP_SCHEDULE=0 2 * * *  # Ejecutar a las 2:00 AM todos los días

# Para S3 (DigitalOcean Spaces):
# BACKUP_S3_KEY=xxxxx
# BACKUP_S3_SECRET=xxxxx
# BACKUP_S3_ENDPOINT=nyc3.digitaloceanspaces.com
# BACKUP_S3_BUCKET=cafbardla-backups

# ============================================
# INTEGRACIONES (Opcional)
# ============================================

# Facturación electrónica (Colombia)
FACTURA_ELECTRONICA_ENABLED=false
# FACTURA_API_KEY=xxxxx
# FACTURA_API_SECRET=xxxxx

# Pagos (Stripe, PayPal, etc)
PAYMENT_GATEWAY=stripe
# STRIPE_API_KEY=xxxxx
# PAYPAL_CLIENT_ID=xxxxx

# Email (Para recibos, reportes)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password
MAIL_FROM=noreply@cafbardla.com

# ============================================
# REPORTES
# ============================================

REPORTES_ENABLED=true
REPORTES_FORMAT=PDF        # PDF | Excel | CSV
REPORTES_PATH=D:\Reportes\CafBarDLA
```

### Crear Carpetas Necesarias

```powershell
# En PowerShell como Administrador

# Carpeta de backups
New-Item -ItemType Directory -Path "D:\Backups\CafBarDLA" -Force

# Carpeta de reportes
New-Item -ItemType Directory -Path "D:\Reportes\CafBarDLA" -Force

# Carpeta de logs
New-Item -ItemType Directory -Path "D:\Logs\CafBarDLA" -Force

# Dar permisos
$ACL = Get-Acl "D:\Backups\CafBarDLA"
$AccessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
$ACL.SetAccessRule($AccessRule)
Set-Acl "D:\Backups\CafBarDLA" $ACL
```

---

## 🎛️ Parametrización del Sistema {#parametrización}

### Acceder a Configuración

```
1. Abrir navegador: http://localhost:8000
2. Login con admin/admin
3. Menú → Configuración → Parametrización
```

### Parámetros Principales

#### 1. Información de la Empresa

```
Nombre: [Tu Café/Bar/Restaurante]
NIT/CÉDULA: [123456789]
Dirección: [Calle 123 #45-67]
Teléfono: [+57 1 2345678]
Email: [contacto@tunegocion.com]
Logo: [Subir imagen 300x300px]
Eslogan: [Tu eslogan aquí]
```

#### 2. Configuración de Facturación

```
Tipo de Factura: Electrónica / Manual
Numeración: 1 (comenzará desde número 1)
Resolución: [Número de resolución DIAN]
Prefix: FAC- (ej: FAC-000001)
Base Gravable: 19% (IVA por defecto)
```

#### 3. Mesas y Secciones

Crear estructura física del negocio:

```
Sección: Salón Principal
├─ Mesa 1 (Capacidad: 4)
├─ Mesa 2 (Capacidad: 4)
├─ Mesa 3 (Capacidad: 6)
└─ Mesa 4 (Capacidad: 2)

Sección: Barra
├─ Barra 1 (Capacidad: 5)
└─ Barra 2 (Capacidad: 5)

Sección: Terraza
├─ Mesa 5 (Capacidad: 8)
└─ Mesa 6 (Capacidad: 8)
```

#### 4. Categorías de Productos

```
☕ Bebidas Calientes
  ├─ Café
  ├─ Té
  └─ Chocolate

🥤 Bebidas Frías
  ├─ Jugos
  ├─ Refrescos
  └─ Cerveza

🍰 Repostería
  ├─ Pasteles
  ├─ Galletas
  └─ Postres

🍕 Comida Rápida
  ├─ Sándwiches
  ├─ Hamburguesas
  └─ Pizzas
```

#### 5. Productos y Precios

Para cada producto configurar:

```
Nombre: Café Americano
Categoría: Bebidas Calientes
Descripción: Café especial con agua caliente
Código: CAFE-001
Precio Base: $5.000
Impuesto: 19%
Costo: $1.500
Margen: 70%
Stock Mínimo: 100
Stock Máximo: 500
Activo: ✓ Sí
```

#### 6. Empleados y Usuarios

```
Usuario: juan.perez
Nombre: Juan Pérez García
Email: juan@cafbardla.com
Teléfono: 3001234567
Rol: Vendedor
Contraseña: [Autogenerada y enviada por email]
Estado: Activo
```

Roles disponibles:
- **Admin**: Acceso total al sistema
- **Gerente**: Acceso a reportes y configuración
- **Vendedor**: Toma de comandas
- **Mesero**: Toma de pedidos (KDS)
- **Cocinero**: Visualización de órdenes (KDS)
- **Caja**: Cierre de caja y pagos

#### 7. Métodos de Pago

```
Efectivo
├─ Código: CASH
├─ Comisión: 0%
└─ Activo: ✓

Tarjeta Débito
├─ Código: DEBIT
├─ Comisión: 1.5%
└─ Activo: ✓

Tarjeta Crédito
├─ Código: CREDIT
├─ Comisión: 2.5%
├─ Banco: [Seleccionar]
└─ Activo: ✓

Transferencia
├─ Código: TRANSFER
├─ Comisión: 0%
└─ Activo: ✓

Billetera Digital
├─ Código: WALLET
├─ Comisión: 1%
└─ Activo: ✓
```

#### 8. Impuestos

```
IVA General: 19%
├─ Categorías aplicables: Todas excepto Bebidas Calientes

IVA Bebidas Calientes: 8%
├─ Categorías: Bebidas Calientes

Propina Sugerida: 10%
├─ Automática: No
└─ Editable: ✓
```

#### 9. Horarios y Turnos

```
Turno Mañana
├─ Entrada: 06:00
├─ Salida: 14:00
└─ Empleados: 2

Turno Tarde
├─ Entrada: 14:00
├─ Salida: 22:00
└─ Empleados: 3

Turno Noche
├─ Entrada: 22:00
├─ Salida: 06:00
└─ Empleados: 1
```

#### 10. Alertas y Notificaciones

```
Alerta de Stock Bajo: ✓ Habilitada
├─ Umbral: 20% del stock mínimo
└─ Email: gerente@cafbardla.com

Alerta de Vencimiento: ✓ Habilitada
├─ Días previos: 7
└─ Email: admin@cafbardla.com

Alerta de Cierre de Caja: ✓ Habilitada
├─ Notificación: 30 minutos antes del cierre
└─ Sonido: ✓

Alerta de Pedidos: ✓ Habilitada
├─ WebSocket: En tiempo real
└─ Email: cocinero@cafbardla.com
```

---

## 🎮 Manual de Funcionamiento {#funcionamiento}

### A. Toma de Comanda (Vendedor/Mesero)

#### Paso 1: Seleccionar Mesa

```
[Pantalla Principal]
    ↓
Clic: Mesas
    ↓
Seleccionar Mesa 1 (Estado: Disponible)
```

#### Paso 2: Crear Nueva Comanda

```
[Mesa 1 - Nueva Comanda]

Hora: 14:35
Mesero: Juan Pérez
Número de clientes: 4
```

#### Paso 3: Agregar Productos

```
1. Búsqueda: "Café"
   ↓
   ✓ Café Americano
   ✓ Café con Leche
   ✓ Café Capuchino

2. Seleccionar: Café Americano (x2)
   ↓
   Cantidad: 2
   Observaciones: Sin azúcar
   
3. Agregar a Comanda
   ↓
   Total Comanda: $10.000

4. Continuar agregando productos...
   - Jugo Natural: 1
   - Sándwich: 2
   - Postre: 1
   
5. Total Final: $45.000
```

#### Paso 4: Enviar a Cocina

```
[Botón ENVIAR A COCINA]
    ↓
✓ Comanda #2345 enviada a KDS
    ↓
[Estado: EN PREPARACIÓN]
```

#### Paso 5: Seguimiento

```
Estado en tiempo real:

⏳ Café: 3 min
✓ Jugo: Listo
⏳ Sándwich: 8 min
⏳ Postre: 5 min

[Botón COMANDA LISTA - cuando todo esté listo]
```

---

### B. Sistema de Cocina (Kitchen Display System - KDS)

#### Pantalla Principal

```
┌─────────────────────────────────────────────────┐
│        KITCHEN DISPLAY SYSTEM - 14:35            │
├─────────────────────────────────────────────────┤
│                                                 │
│  Órdenes Pendientes: 5                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                 │
│  ORDEN #2345 (Mesa 1) [3 min en cocina]        │
│  ├─ 2x Café Americano (Sin azúcar)            │
│  ├─ 1x Jugo Natural ✓                          │
│  └─ 1x Sándwich (En parrilla)                  │
│     [Marcar como Listo]                        │
│                                                 │
│  ORDEN #2346 (Barra) [8 min en cocina]        │
│  ├─ 3x Cerveza ✓                               │
│  └─ 2x Botanas                                 │
│     [Marcar como Listo]                        │
│                                                 │
│  ORDEN #2347 (Mesa 3) [1 min]                 │
│  └─ 1x Hamburguesa (En parrilla)              │
│     [Marcar como Listo]                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

#### Flujo de Operación

```
1. Recibir orden en pantalla (notificación sonora)
2. Verificar ingredientes disponibles
3. Preparar productos
4. Marcar items como completados
5. Cuando toda la orden esté lista: [Marcar Orden Completa]
6. El mesero la recibe en la pantalla
```

---

### C. Cierre de Caja

#### Paso 1: Acceso a Cierre

```
Menú → Caja → Cierre de Caja
```

#### Paso 2: Revisar Movimientos

```
CIERRE DE CAJA - Turno Tarde (14:00 - 22:00)
Fecha: 20/07/2026
Vendedor: Juan Pérez

Total Ventas: $450.000
├─ Efectivo: $300.000
├─ Tarjeta Débito: $100.000
├─ Tarjeta Crédito: $50.000
└─ Transferencia: $0

Total Egresos: $50.000
├─ Aperitivos: $30.000
├─ Útiles: $15.000
└─ Otro: $5.000

Total Neto: $400.000
```

#### Paso 3: Contar Efectivo

```
Ingresar cantidad física de dinero:

Billetes:
├─ $100.000 x 2 = $200.000
├─ $50.000 x 2 = $100.000
└─ $20.000 x 0 = $0

Monedas:
├─ $5.000 x 0 = $0
└─ $1.000 x 0 = $0

Total Contado: $300.000
Sistema: $300.000
✓ Diferencia: $0 (Correcto!)
```

#### Paso 4: Generar Reporte

```
[Botón GENERAR REPORTE]
    ↓
✓ Reporte de Cierre generado
    ↓
Opciones:
- [PDF] Descargar en PDF
- [Email] Enviar por correo
- [Imprimir] Imprimir recibo
```

---

### D. Gestión de Inventario

#### Verificar Stock

```
Menú → Inventario → Productos

Buscar: "Café"
    ↓
┌─────────────────────────────┐
│ Café Americano              │
├─────────────────────────────┤
│ Stock Actual: 245 unidades  │
│ Stock Mínimo: 100 unidades  │
│ Stock Máximo: 500 unidades  │
│ Estado: ✓ OK                │
│ Última compra: 15/07/2026   │
│ Costo Unitario: $1.500      │
│ Valor Total: $367.500       │
└─────────────────────────────┘
```

#### Entrada de Mercancía

```
Menú → Inventario → Entrada de Mercancía

1. Seleccionar Proveedor: Café Importado S.A.
2. Agregar Producto:
   ├─ Café Americano: 100 unidades @ $1.500
   ├─ Café Capuchino: 50 unidades @ $1.600
   └─ Café con Leche: 75 unidades @ $1.400

3. Total Compra: $292.500
4. Guardar entrada
```

#### Ajuste de Inventario

```
Menú → Inventario → Ajustes

Motivo: Merma/Vencimiento/Rotura

Producto: Jugo de Naranja
Cantidad: -5
Motivo: Botellas rotas durante transporte
Costo: $25.000
```

---

### E. Reportes y Análisis

#### Reporte de Ventas Diarias

```
Menú → Reportes → Ventas Diarias

Fecha: 20/07/2026

Total Ventas: $2.850.000
Total Descuentos: $85.500
Total Impuestos: $513.600
TOTAL NETO: $3.278.100

Productos Más Vendidos:
1. Café Americano: 145 unidades ($725.000)
2. Sándwich: 87 unidades ($1.044.000)
3. Jugo Natural: 92 unidades ($644.000)

Métodos de Pago:
├─ Efectivo: 65% ($1.853.250)
├─ Tarjeta Débito: 25% ($819.525)
└─ Tarjeta Crédito: 10% ($327.810)

Hora Pico: 12:00 - 14:00 (35% de ventas)
```

#### Reporte de Inventario

```
Menú → Reportes → Inventario

Valor Total en Stock: $12.500.000

Productos por Vencer (7 días):
├─ Leche descremada: 3 botellas (20/07/2026)
├─ Jamón de Pavo: 2 paquetes (22/07/2026)
└─ Queso Fresco: 1 kg (25/07/2026)

Productos con Stock Bajo:
├─ Café Artesanal: 5 unidades (Mín: 50)
├─ Chocolate: 8 unidades (Mín: 20)
└─ Panela: 12 kilos (Mín: 50)

Recomendación: Realizar compra urgente
```

---

### F. Facturación

#### Generar Factura

```
Menú → Facturación → Crear Factura

Cliente: Jorge López García
Documento: 1024567890
Email: jorge@correo.com

Items:
├─ Café Americano x2: $10.000
├─ Sándwich x1: $12.000
└─ Jugo x1: $7.000

Subtotal: $29.000
IVA (19%): $5.510
TOTAL: $34.510

Método de Pago: Tarjeta Crédito
[GENERAR FACTURA ELECTRÓNICA]
```

#### Radicación en DIAN

```
✓ Factura #FAC-000001 radicada exitosamente en DIAN
Número Radicado: 21073100012200026
Hora: 14:35:42

Confirmación enviada a: jorge@correo.com
```

---

### G. Gestión de Clientes

#### Registrar Cliente

```
Menú → Clientes → Nuevo Cliente

Nombre: María García López
Documento: 45876923
Teléfono: 3105678901
Email: maria.garcia@gmail.com
Dirección: Calle 50 #10-20, Apto 502

Preferences:
☑ Recibir promociones por email
☑ Aviso de nuevos productos
☐ Envío a domicilio

Clientes VIP:
☑ Es cliente VIP (Descuento 5%)
```

#### Historial de Compras

```
Cliente: María García López

Total gastado: $850.000
Compras totales: 24
Promedio por compra: $35.417

Últimas compras:
- 20/07/2026: $45.000 (Café + Sándwich)
- 19/07/2026: $32.000 (Bebidas)
- 18/07/2026: $38.000 (Comida rápida)
```

---

### H. Aplicación Móvil (iOS/Android)

#### Login Móvil

```
┌─────────────────────┐
│   CAFBARDLA POS     │
│                     │
│ [Logo]              │
│                     │
│ Usuario: [________] │
│ Contraseña: [______]│
│                     │
│  [INICIAR SESIÓN]   │
│                     │
│ ¿Olvidó contraseña? │
└─────────────────────┘
```

#### Toma de Pedidos Móvil

```
┌─────────────────────────────────┐
│ MESA 3 - Comanda #2350         │
├─────────────────────────────────┤
│                                 │
│ 🔍 Buscar producto...          │
│                                 │
│ ☕ Bebidas Calientes (5)        │
│    • Café Americano      $5.000│
│    • Café con Leche      $5.500│
│    • Capuchino           $6.000│
│                                 │
│ 🍰 Repostería (3)              │
│    • Croissant           $3.000│
│    • Pastel de chocolate $4.000│
│                                 │
│ 📱 [Mi Comanda] [ENVIAR]        │
└─────────────────────────────────┘
```

---

## ☁️ Deployment en la Nube {#nube}

Para instrucciones completas de deployment en:
- **Docker:** Ver `scripts/docker-compose.yml`
- **Heroku:** Ver `docs/CLOUD_DEPLOYMENT_GUIDE.md`
- **AWS:** Ver `docs/CLOUD_DEPLOYMENT_GUIDE.md`
- **DigitalOcean:** Ver `docs/CLOUD_DEPLOYMENT_GUIDE.md`

Resumen rápido con **DigitalOcean** (Recomendado):

```bash
# 1. Crear droplet (Ubuntu 22.04, $5/mes)
# 2. SSH a servidor
ssh root@<IP>

# 3. Instalar Docker
curl -fsSL https://get.docker.com | sh

# 4. Clonar proyecto
git clone https://github.com/tuusuario/CafBarDLA.git
cd CafBarDLA

# 5. Ejecutar con Docker Compose
docker-compose up -d

# 6. Configurar SSL con Let's Encrypt
sudo certbot certonly --standalone -d cafbardla.tudominio.com

# 7. Acceder
# https://cafbardla.tudominio.com
```

---

## 🔧 Mantenimiento y Soporte {#mantenimiento}

### Tareas Diarias

- [ ] Verificar que la aplicación está corriendo
- [ ] Revisar alertas del sistema
- [ ] Validar integridad de datos

### Tareas Semanales

- [ ] Revisar reportes de ventas
- [ ] Verificar stock de productos críticos
- [ ] Ejecutar limpieza de logs

### Tareas Mensuales

- [ ] Hacer backup completo fuera del sitio
- [ ] Revisar acceso de usuarios
- [ ] Actualizar datos de configuración (precios, impuestos)

### Respaldo (Backup)

```powershell
# Backup manual
cd D:\CafBarDLA
.\scripts\backup_sqlite_production.ps1

# Backup automático (configurado en .env.production)
# Se ejecuta cada 2:00 AM

# Ubicación: D:\Backups\CafBarDLA\
# Retención: 30 días
```

### Troubleshooting

#### Problema: "Puerto 8000 ya está en uso"

```powershell
# Encontrar proceso usando puerto 8000
netstat -ano | findstr :8000

# Matar proceso (reemplazar PID)
taskkill /PID 12345 /F

# Usar puerto diferente
uvicorn app.main:app --port 8001
```

#### Problema: "No se puede conectar a la base de datos"

```powershell
# Verificar si SQLite existe
ls *.db

# Recrear base de datos
del cafbardla_prod.db
alembic upgrade head

# Si es PostgreSQL, verificar servicio
psql -U postgres -c "\l"
```

#### Problema: "Error de memoria en PyInstaller"

```powershell
# No es necesario usar PyInstaller
# El servidor FastAPI funciona sin instalador

# Usar en lugar de ejecutable:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Contacto de Soporte

- **Email:** support@dlatecnologia.com
- **Teléfono:** +57 1 2345678
- **WhatsApp:** +57 310 5678901
- **Portal Web:** https://support.dlatecnologia.com

---

## 📞 FAQ - Preguntas Frecuentes

**P: ¿Puedo usar CafBarDLA sin conexión a Internet?**
R: Sí, funciona completamente offline. Sin embargo, perderás acceso a:
- Facturación electrónica DIAN
- Actualizaciones automáticas
- Sincronización en la nube

**P: ¿Cuántos usuarios simultáneos puede soportar?**
R: Con la configuración estándar (4 workers), hasta 100 usuarios concurrentes sin problemas. Para mayor capacidad, escalar a más workers o usar balanceador de carga.

**P: ¿Dónde se guardan los datos?**
R: En la base de datos (SQLite o PostgreSQL). Para máxima seguridad, hacer backups regulares.

**P: ¿Puedo cambiar de SQLite a PostgreSQL después?**
R: Sí, con script de migración. Contactar a soporte técnico.

**P: ¿Cómo recupero un backup?**
R: Reemplazar archivo `cafbardla_prod.db` con el archivo de backup de la fecha deseada.

---

## 📋 Checklist de Implementación

- [ ] Servidor preparado y conectado a la red
- [ ] Python 3.11+ instalado
- [ ] Aplicación CafBarDLA ejecutándose
- [ ] Base de datos inicializada
- [ ] Backups configurados
- [ ] Usuarios creados y asignados
- [ ] Mesas y categorías configuradas
- [ ] Productos ingresados
- [ ] Métodos de pago configurados
- [ ] Terminales POS conectadas
- [ ] Pruebas de funcionamiento completadas
- [ ] Capacitación de usuarios realizada
- [ ] Documentación entregada

---

**Documento Generado:** 2026-07-20  
**Versión:** 1.0  
**Empresa:** DLA Tecnología  
**Soporte:** support@dlatecnologia.com

---

**GRACIAS POR ELEGIR CAFBARDLA** ☕
