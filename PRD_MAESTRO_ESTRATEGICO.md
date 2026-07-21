# 📋 PRD - PLAN MAESTRO ESTRATÉGICO CAFBARDLA PREMIUM

**Versión**: 1.0  
**Fecha**: Julio 2026  
**Estado**: Plan de Implementación 400 Horas  
**Objetivo**: Transformar CafBarDLA en ERP Premium Enterprise para Restaurantes, Cafeterías y Bares

---

## 🎯 VISIÓN GLOBAL

### Objetivo Comercial
Crear un **ERP de clase mundial** (comparable con Square, Toast, Toast, MarginEdge) que sea:
- ✅ **Enterprise-Ready**: Múltiples sucursales, empresas, configuración granular
- ✅ **Modular**: Cada restaurante compra solo lo que necesita
- ✅ **Escalable**: De 1 mesa a 100+ puntos de venta
- ✅ **Premium**: Interfaz lujo (Marriott + Starbucks Reserve)
- ✅ **Integrable**: APIs abiertas para ecosistema de partners
- ✅ **Rentable**: SaaS multi-tenant con analytics avanzados

### Posicionamiento
```
ANTES: CafBarDLA v1
├─ POS básico para un café
├─ Gestión sencilla de mesas
└─ Reportes limitados

DESPUÉS: CafBarDLA Premium
├─ ERP completo para restauración
├─ Multi-sucursal, multi-empresa
├─ Inteligencia de datos
├─ Mobile + Desktop + Tablets
├─ Notificaciones Real-time
└─ Integración con terceros (Rappi, Uber Eats, etc.)
```

---

## 📊 ANÁLISIS DEL ESTADO ACTUAL

### ✅ Fortalezas Actuales

**Stack Técnico Sólido**
```
Backend:   FastAPI 0.115 (async-ready, production-grade)
ORM:       SQLAlchemy 2.0 (moderno, type-safe)
BD:        PostgreSQL (enterprise, escalable)
Frontend:  Jinja2 templates + CSS3 + Vanilla JS
Auth:      Bcrypt + Session-based
Security:  Logging, CSRF, Rate limiting
```

**22 Modelos ORM Bien Diseñados**
- Empresa, Zona, Mesa, Producto, Categoría
- Venta, DetalleVenta, Cliente, AbonoCartera
- Empleado, Usuario, Nómina
- Receta, RecetaDetalle, OrdenProduccion
- MovimientoInventario, Gasto
- Y más...

**Sistema de Diseño Premium Implementado**
- Paleta: Negro #0a0e27, Dorado #d4af37, Cobre #b87333
- Tipografía: Inter + Poppins
- Componentes: Cards, Botones, Tablas, Modales
- Animaciones: 150-350ms transiciones fluidas

**Base de Seguridad**
- ✅ Bcrypt para contraseñas
- ✅ Logging centralizado
- ✅ Rate limiting (slowapi)
- ✅ CSRF tokens
- ✅ Session middleware HTTPS-ready

### ⚠️ Debilidades a Solucionar

**Validación Inconsistente**
- Problema: Formularios validados solo en frontend
- Impacto: Vulnerabilidad a API abuse
- Solución: Pydantic schemas en todos los endpoints

**Performance**
- Problema: Queries N+1 en reportes
- Impacto: Timeouts con >1000 transacciones
- Solución: Eager loading, caching, índices BD

**Testing**
- Problema: Cero tests automatizados
- Impacto: Riesgos de regresiones
- Solución: pytest + fixtures + CI/CD

**Documentación API**
- Problema: Swagger incomplete
- Impacto: Difícil para partners integrar
- Solución: OpenAPI completo con ejemplos

**Scalabilidad**
- Problema: Sin paginación, sin caché
- Impacto: Listas grandes = bloqueo
- Solución: Redis, pagination, materialized views

### 📈 Métricas de Estado Actual
```
Cobertura de funcionalidad:   35%
Seguridad:                    72/100
Performance:                  40/100
Documentación:                25/100
Tests:                        0/100
Enterprise-readiness:         30/100

TOTAL MADUREZ:               33.7/100 (PRE-PRODUCCIÓN)
```

---

## 🗓️ ROADMAP DE 10 SEMANAS (400 HORAS)

### Distribución de Horas

```
FASE 1: CORE (Semana 1-2)         = 80 horas
├─ POS Premium
├─ Mesas & Layout
└─ Productos

FASE 2: OPERACIONES (Semana 3-4)  = 80 horas
├─ Inventarios Profesional
├─ Producción con Recetas
└─ Gastos

FASE 3: TALENTO (Semana 5-6)      = 80 horas
├─ Nómina Avanzada
├─ Personal & Asistencia
└─ Comisiones

FASE 4: INTELIGENCIA (Semana 7-8) = 100 horas
├─ Reportes Ejecutivos
├─ Dashboard KPI
└─ Analítica

FASE 5: MOVILIDAD (Semana 9-10)   = 60 horas
├─ App Móvil Meseros
├─ Kitchen Display
└─ Notificaciones Real-time
```

---

## 📦 MODELOS Y MÓDULOS POR FASE

### FASE 1: CORE (Semana 1-2) ⭐ PRIORIDAD MÁX

**1.1 POS PREMIUM - FACTURACIÓN**

**Estado Actual**: 70% completo
- ✅ Modelo Venta creado
- ✅ DetalleVenta funcional
- ✅ Cálculo básico de impuestos
- ❌ Facturación electrónica (DIAN)
- ❌ Anulaciones con auditoría
- ❌ Reimpresión de facturas

**Descripción Funcional**
Es el corazón del sistema. Captura cada venta con máxima precisión, aplica impuestos, genera facturas y rastrea todo para auditoría.

**Casos de Uso Principales**
```
CU-1.1.1: Crear venta por mesa
├─ Mesero abre mesa y comienza a agregar productos
├─ Sistema calcula subtotal en real-time
├─ Permite notas especiales por producto
└─ Guarda estado "abierta"

CU-1.1.2: Cerrar venta (cobro)
├─ Mesero solicita cierre
├─ Sistema aplica impuesto (IVA)
├─ Permite seleccionar medio de pago
├─ Genera número de factura único
├─ Imprime/Email comprobante
└─ Registra en BD con timestamp

CU-1.1.3: Anular factura
├─ Admin autoriza anulación
├─ Sistema revierte inventario
├─ Guarda motivo de anulación
├─ Log de auditoría completo
└─ Genera nota de crédito

CU-1.1.4: Descuentos y promociones
├─ Descuento por ítem individual
├─ Descuento global por mesa
├─ Código de cupón aplicable
└─ Historial de descuentos para análisis
```

**Datos a Capturar**
```
Venta (Mejorada)
├─ venta_id (PK)
├─ empresa_id (FK) → multi-empresa
├─ mesa_id (FK) → NULL si domicilio
├─ cliente_id (FK) → NULL si consumidor
├─ empleado_id (FK) → mesero que atiende
├─ fecha_apertura (TS)
├─ fecha_cierre (TS, nullable)
├─ estado: "abierta|cerrada|anulada|en_espera"
├─ subtotal (Decimal)
├─ descuento_pesos (Decimal)
├─ descuento_porcentaje (Decimal)
├─ subtotal_neto (Computed)
├─ impuesto_value (Decimal)
├─ propina_pesos (Decimal)
├─ total_pago (Decimal)
├─ medio_pago: "efectivo|tarjeta|transferencia|mixto"
├─ numero_factura (String, unique)
├─ referencia_factura_electronica (String, nullable)
├─ estado_electronica: "pendiente|enviada|rechazada|aceptada"
├─ motivo_anulacion (Text, nullable)
├─ anulada_por_id (FK → Usuario, nullable)
├─ fecha_anulacion (TS, nullable)
├─ observaciones (Text)
├─ canal: "mesa|delivery|domicilio|mostrador"
└─ tags (JSON) → para búsqueda, ej: ["rappi", "tarde"]

DetalleVenta (Mejorada)
├─ detalle_id (PK)
├─ venta_id (FK)
├─ producto_id (FK)
├─ cantidad (Decimal 12,3)
├─ precio_unitario (Decimal)
├─ descuento_unitario (Decimal)
├─ subtotal_linea (Computed)
├─ impuesto_linea (Computed)
├─ total_linea (Computed)
├─ notas_especiales (Text) → "Sin sal", "Bien cocido", etc.
├─ estado_cocina: "pendiente|preparando|listo|entregado"
├─ fecha_estado_cocina (TS)
├─ costo_unitario (Decimal)
├─ margen_linea (Computed)
├─ modificaciones (JSON) → cambios de precio, extras
└─ anulada_por_linea (Boolean) → permite devolver solo items

FacturaPDF
├─ factura_id (PK)
├─ venta_id (FK)
├─ contenido_pdf (Bytea)
├─ fecha_generacion (TS)
├─ digital: Boolean
├─ url_descarga (String, nullable)
└─ viazos_impresion (Integer)
```

**Validaciones Necesarias**

```python
# Pydantic Schema
class VentaCreate(BaseModel):
    mesa_id: Optional[int]
    cliente_id: Optional[int]
    # Validaciones
    @field_validator('mesa_id')
    def mesa_debe_existir(cls, v):
        if v and not db.get(Mesa, v): raise ValueError("Mesa no existe")
        return v
    
    @field_validator('cliente_id')
    def cliente_debe_existir_o_null(cls, v):
        if v and not db.get(Cliente, v): raise ValueError("Cliente no existe")
        return v

class DetalleVentaCreate(BaseModel):
    producto_id: int
    cantidad: Decimal = Field(gt=0, decimal_places=3)
    precio_unitario: Decimal = Field(gt=0, decimal_places=2)
    
    @field_validator('producto_id')
    def producto_debe_existir(cls, v):
        if not db.get(Producto, v): raise ValueError("Producto no existe")
        return v
    
    @field_validator('cantidad')
    def cantidad_disponible(cls, v, values):
        prod = db.get(Producto, values['producto_id'])
        if v > prod.existencias: 
            raise ValueError(f"Stock insuficiente. Disponible: {prod.existencias}")
        return v
```

**Integraciones con Otros Módulos**
```
POS ←→ Inventario
├─ Cierre de venta decrementa stock
└─ Notificación si stock < mínimo

POS ←→ Cocina (Kitchen Display)
├─ DetalleVenta → estado_cocina
└─ Cocinero marca como "listo"

POS ←→ Nómina
├─ Comisión del mesero por venta
└─ Propina registrada → distribución

POS ←→ Reportes
├─ Venta cerrada → cálculo de KPIs
└─ Auditoría completa de transacción

POS ←→ Clientes
├─ Venta registra cliente
└─ Saldo cartera actualizado (si crédito)
```

**UI/UX Recomendada**

```
INTERFAZ POS - Diseño Responsive
┌─────────────────────────────────────────────────────┐
│ HEADER                                              │
│ [Logo] MESA 5 │ 14:32 │ Mesero: Juan │ [👤 Menú]   │
├─────────────────────────────────────────────────────┤
│ CARRITO (60% ancho)      │ PRODUCTOS (40% ancho)   │
│                          │                          │
│ [🔍 Buscar productos]    │ [BEBIDAS]                │
│                          │ ├─ Capuchino    $8,500   │
│ Capuchino      ×2  $17k  │ ├─ Latte        $9,000  │
│ Croissant      ×1  $7k   │ ├─ Americano    $7,500  │
│                          │                          │
│ ─────────────────────────┼──────────────────────────│
│ Subtotal:     $24,000    │ [COMIDAS]                │
│ Descuento:    -$0        │ ├─ Croissant     $7,000 │
│ Impuesto:     +$2,400    │ └─ Sándwich     $12,000 │
│ ═════════════════════    │                          │
│ TOTAL:        $26,400    │ [POSTRES]                │
│                          │ └─ Brownie       $6,000 │
│ [💳 Cobrar] [🔄 Mantener]│                          │
│ [❌ Cancelar]            │ [Notas especiales ✎]     │
└─────────────────────────────────────────────────────┘

INTERFAZ COBRO
┌──────────────────────────┐
│ CIERRE DE VENTA          │
├──────────────────────────┤
│ Subtotal:     $24,000    │
│ Descuento:       -$0     │
│ Impuesto (8%): +$1,920   │
│ ─────────────────────────│
│ TOTAL:        $25,920    │
│                          │
│ [Medio de Pago]          │
│ ◉ Efectivo               │
│ ○ Tarjeta (débito/crédito)
│ ○ Transferencia          │
│ ○ Mixto                  │
│                          │
│ [💰 Dinero Recibido]     │
│ [_________] $30,000      │
│ Cambio: $4,080           │
│                          │
│ [Agregar Propina]        │
│ $_______ o ____%         │
│                          │
│ [✅ Confirmar] [↶ Volver]│
└──────────────────────────┘
```

**Estimación de Desarrollo**
- Backend API (CRUD + validaciones): 16 horas
- Formularios + Carrito: 12 horas
- Cálculos (impuesto, descuentos): 8 horas
- Facturación PDF/impresión: 10 horas
- Manejo de anulaciones: 8 horas
- Testing: 10 horas
- **Subtotal Módulo POS: 64 horas**

---

**1.2 MESAS Y LAYOUT**

**Estado Actual**: 90% completo
- ✅ Modelo Mesa
- ✅ Modelo Zona
- ✅ Posicionamiento x,y
- ❌ Grid visual drag-and-drop
- ❌ Estados de mesa en tiempo real
- ❌ Fusión/división de mesas

**Descripción Funcional**
Gestión visual del espacio físico del restaurante. Meseros ven en tiempo real qué mesas están libres, ocupadas, en espera o requieren atención.

**Casos de Uso Principales**
```
CU-1.2.1: Crear layout de mesas
├─ Admin define zonas (Salón, Terraza, VIP)
├─ Por zona crea mesas con coordenadas
├─ Asigna capacidad y forma (redonda, cuadrada)
└─ Guarda layout como "plantilla del día"

CU-1.2.2: Ver estado mesas en tiempo real
├─ Dashboard principal muestra grid visual
├─ Mesas libres en verde
├─ Mesas ocupadas en dorado con mesa_id
├─ Mesas en espera parpadeando
└─ Click en mesa abre carrito

CU-1.2.3: Fusionar/dividir mesas
├─ Mesero selecciona mesa A y B
├─ Sistema crea venta combinada
├─ Después permite dividir por cliente
└─ Auditoría completa de cambios

CU-1.2.4: Transferir mesa entre meseros
├─ Mesero 1 inicia transferencia
├─ Mesero 2 acepta/rechaza
├─ Sistema migra cliente + historial
└─ Ambos en log de auditoría
```

**Datos a Capturar**
```
Mesa (Mejorada)
├─ mesa_id (PK)
├─ empresa_id (FK)
├─ zona_id (FK)
├─ numero: "1", "M5", "VIP-1"
├─ capacidad: 2-12
├─ posicion_x, posicion_y (Grid)
├─ forma: "redonda|cuadrada|rectangular|barra"
├─ estado: "libre|ocupada|en_espera|bloqueada"
├─ estado_cambio_ts (TS) → para timing
├─ venta_actual_id (FK, nullable)
├─ mesero_id (FK, nullable)
├─ cliente_cantidad (Integer)
├─ notas_operacionales (Text)
├─ es_vip (Boolean)
├─ es_barra (Boolean)
├─ imagen_qr (Bytea) → QR code mesa
└─ datos_config (JSON) → custom config

EstadoMesaHistorico
├─ id (PK)
├─ mesa_id (FK)
├─ estado_anterior
├─ estado_nuevo
├─ cambio_ts
├─ usuario_id (FK)
└─ razon (String)

Zona (Mejorada)
├─ zona_id (PK)
├─ empresa_id (FK)
├─ nombre: "Salón", "Terraza", "VIP"
├─ capacidad_total (Integer)
├─ orden_display (Integer)
├─ color_tema (String hex)
├─ activa (Boolean)
├─ imagen_fondo (Bytea, nullable)
└─ configuracion (JSON)
```

**UI/UX Recomendada**

```
DASHBOARD MESAS - Vista Principal
┌────────────────────────────────────────────────────┐
│ CAFBARDLA         14:32    [👤 Juan]  [⚙️ Menú]     │
├────────────────────────────────────────────────────┤
│ [SALÓN] [TERRAZA] [VIP]  │ Filtro: [Todas ▼]      │
├────────────────────────────────────────────────────┤
│                                                    │
│    🟢         🟢         🟡         🟡             │
│    M1         M2         M3         M4             │
│   4 pax      2 pax      6 pax      4 pax           │
│   13:45      14:10      12:30      ---             │
│                                                    │
│    🟠         🔴         🟢         🟢             │
│    M5         M6         M7         M8             │
│   8 pax      3 pax      2 pax      4 pax           │
│   12:00      14:22      ---        ---             │
│                                                    │
│  Leyenda:                                          │
│  🟢 Libre  🟡 En espera  🟠 Ocupada  🔴 Bloqueada  │
│                                                    │
│ [➕ Nueva Mesa] [✏️ Editar Layout] [🔄 Refresh]   │
└────────────────────────────────────────────────────┘

Click en Mesa M3
┌──────────────────────────┐
│ MESA 3 (6 pax)           │
├──────────────────────────┤
│ Estado: OCUPADA (20min)  │
│ Mesero: Carlos           │
│ Cliente: Anónimo         │
│ Items: 4                 │
│ Total: $45,600           │
│                          │
│ [🛒 Ver Carrito]        │
│ [➕ Agregar Items]      │
│ [💳 Cobrar]             │
│ [🔄 Transferir Mesero]  │
│ [⏸️ Poner en Espera]    │
│ [🚫 Bloquear Mesa]      │
└──────────────────────────┘
```

**Estimación de Desarrollo**
- Modelo Mesa mejorado: 4 horas
- API endpoints (CRUD + estados): 8 horas
- Dashboard visual (grid + drag): 16 horas
- WebSocket real-time: 12 horas
- Testing: 6 horas
- **Subtotal Módulo Mesas: 46 horas**

---

**1.3 PRODUCTOS Y CATEGORÍAS**

**Estado Actual**: 60% completo
- ✅ Modelo Producto
- ✅ Modelo Categoría
- ❌ Imágenes de productos
- ❌ Variantes (tamaños: S/M/L)
- ❌ Add-ons (extras: Bacon +$2,000)
- ❌ Descripción markdown

**Descripción Funcional**
Catálogo completo de items que se venden. Cada producto tiene múltiples variantes y extras para customización.

**Casos de Uso Principales**
```
CU-1.3.1: Crear producto con variantes
├─ Admin ingresa nombre, descripción
├─ Sube imagen (jpg/png, redimensiona automático)
├─ Define variantes: Small $8k, Medium $9.5k, Large $11k
├─ Asigna add-ons disponibles: +Bacon, +Cheese, +etc
├─ Sistema genera SKU único
└─ Guarda en catálogo

CU-1.3.2: Buscar producto en POS
├─ Mesero empieza a escribir "cap"
├─ Autocomplete: "Capuchino", "Capuchino Frío"
├─ Selecciona → abre selector de variantes
├─ Elige tamaño → muestra add-ons
├─ Agrega a carrito con precio correcto
└─ Sistema valida stock

CU-1.3.3: Gestionar categorías
├─ Admin crea/edita categorías
├─ Define orden de display
├─ Puede asignar colores temáticos
├─ Activa/desactiva categorías
└─ Reporte de items por categoría
```

**Datos a Capturar**
```
Producto (Mejorada)
├─ producto_id (PK)
├─ empresa_id (FK)
├─ categoria_id (FK)
├─ sku: código único
├─ nombre: "Capuchino"
├─ descripcion_markdown: "Espresso con..."
├─ imagen_url (String)
├─ precio_base (Decimal)
├─ costo_base (Decimal)
├─ existencias (Decimal)
├─ stock_minimo (Decimal)
├─ stock_maximo (Decimal)
├─ unidad_medida: "taza|porción|gramo"
├─ tipo: "venta|insumo|elaborado"
├─ activo (Boolean)
├─ disponible_delivery (Boolean)
├─ tiempo_preparacion (Integer minutes)
├─ es_bebida (Boolean)
├─ es_alcholico (Boolean)
├─ campos_config (JSON) → custom
└─ fecha_creacion (TS)

ProductoVariante
├─ variante_id (PK)
├─ producto_id (FK)
├─ nombre: "Pequeño", "Mediano", "Grande"
├─ sku_variante
├─ precio_ajuste (Decimal, puede ser -ve)
├─ costo_ajuste (Decimal)
├─ activa (Boolean)
└─ orden_display (Integer)

ProductoAddon
├─ addon_id (PK)
├─ producto_id (FK) → NULL si addon global
├─ nombre: "Bacon Extra", "Queso"
├─ precio_addon (Decimal)
├─ activo (Boolean)
├─ orden (Integer)
└─ tipo: "individual|grupo"

Categoria (Mejorada)
├─ categoria_id (PK)
├─ empresa_id (FK)
├─ nombre: "Bebidas", "Comidas"
├─ descripcion (Text)
├─ icono (String emoji o URL)
├─ color_hex (String)
├─ orden_display (Integer)
├─ activa (Boolean)
├─ imagen_fondo (URL)
└─ campos_metadata (JSON)
```

**Validaciones Necesarias**
```python
class ProductoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    categoria_id: int
    precio_base: Decimal = Field(gt=0)
    costo_base: Decimal = Field(ge=0, le_precio=precio_base)
    sku: str = Field(regex=r"^[A-Z0-9\-]{3,30}$")
    
    @field_validator('sku')
    def sku_unico(cls, v, values):
        if Producto.get_by_sku(v):
            raise ValueError("SKU ya existe")
        return v
    
    @field_validator('costo_base')
    def costo_menor_precio(cls, v, values):
        if v >= values['precio_base']:
            raise ValueError("Costo no puede ser ≥ precio")
        return v
```

**Estimación de Desarrollo**
- Modelo Producto + Variantes: 6 horas
- API endpoints: 10 horas
- UI admin productos: 14 horas
- Upload y procesamiento imágenes: 8 horas
- Búsqueda + autocomplete: 6 horas
- Testing: 6 horas
- **Subtotal Módulo Productos: 50 horas**

**TOTAL FASE 1: 64 + 46 + 50 = 160 horas**
*Nota: Reducir a 80 horas optimizando, reusando componentes*

---

### FASE 2: OPERACIONES (Semana 3-4) ⚙️

**2.1 INVENTARIOS PROFESIONAL**

**Estado Actual**: 40% completo
- ✅ Modelo MovimientoInventario
- ✅ Rastreo básico
- ❌ Recuentos físicos (auditorías)
- ❌ Trasferencias entre ubicaciones
- ❌ Código de barras

**Descripción Funcional**
Control total del inventario en tiempo real. Cada movimiento registrado (venta, entrada, ajuste, transferencia) y auditado.

**Casos de Uso Principales**
```
CU-2.1.1: Entrada de mercancía
├─ Compras → Recibe orden de compra
├─ Escanea código de barras (o ingresa manual)
├─ Registra cantidad y fecha vencimiento
├─ Sistema actualiza stock
└─ Movimiento en auditoría

CU-2.1.2: Recuento físico (auditoría)
├─ Admin inicia recuento
├─ Equipo físico cuenta mesas
├─ Ingresa cantidades vs sistema
├─ Sistema calcula variancia
├─ Registra "Ajuste por auditoría"
└─ Reporte de diferencias

CU-2.1.3: Alertas de stock
├─ Sistema monitorea stock_minimo
├─ Si existencias < mínimo → alerta
├─ Dashboard admin ve items críticos
├─ Notificación Whatsapp/Email
└─ Link para generar orden compra

CU-2.1.4: Análisis de rotación
├─ Reporte FIFO: qué se vende primero
├─ Velocidad de rotación por producto
├─ ABC: 20% productos = 80% ventas
└─ Recomendación: qué reponer
```

**Datos a Capturar**
```
MovimientoInventario (Mejorada)
├─ movimiento_id (PK)
├─ empresa_id (FK)
├─ producto_id (FK)
├─ fecha_movimiento (TS)
├─ tipo: "venta|entrada|ajuste|transferencia|devolucion|merma"
├─ cantidad (Decimal signed)
├─ ubicacion_origen (String) → "Almacén", "Barra", etc
├─ ubicacion_destino (String)
├─ costo_unitario (Decimal)
├─ motivo (Text)
├─ usuario_id (FK)
├─ referencia_id (String) → venta_123, compra_456
├─ fecha_vencimiento (Date, nullable)
├─ lote (String, nullable)
└─ campos_metadata (JSON)

InventarioSaldo
├─ saldo_id (PK)
├─ empresa_id (FK)
├─ producto_id (FK)
├─ ubicacion (String)
├─ cantidad_actual (Decimal)
├─ cantidad_reservada (Decimal)
├─ cantidad_disponible (Computed)
├─ ultima_actualizacion (TS)
├─ costo_promedio (Decimal)
└─ valor_total (Computed)

AuditoriaInventario
├─ auditoria_id (PK)
├─ empresa_id (FK)
├─ fecha_auditoria (TS)
├─ inicio_ts, fin_ts
├─ usuario_id (FK)
├─ diferencias (JSON) → [{sku, sistema, fisico, variancia}]
├─ total_diferencia (Decimal)
├─ estado: "borrador|finalizada|aprobada"
└─ observaciones (Text)

AlertaInventario
├─ alerta_id (PK)
├─ empresa_id (FK)
├─ producto_id (FK)
├─ tipo: "bajo_stock|vencimiento|exceso|desviacion"
├─ fecha_alerta (TS)
├─ valor_alerta (Decimal)
├─ leida (Boolean)
└─ accion_tomada (Text, nullable)
```

**Estimación de Desarrollo**
- Modelos mejorados: 6 horas
- API movimientos: 12 horas
- Recuentos físicos: 10 horas
- Alertas automáticas: 8 horas
- Reportes de rotación: 10 horas
- Testing: 8 horas
- **Subtotal: 54 horas**

---

**2.2 PRODUCCIÓN CON RECETAS**

**Estado Actual**: 50% completo
- ✅ Modelo Receta
- ✅ RecetaDetalle con insumos
- ❌ Kitchen Display System (KDS)
- ❌ Control de merma
- ❌ Integración con comanda

**Descripción Funcional**
Gestión de producciones (preparación de bebidas, platos, etc). Desde la orden de producción hasta el plato listo.

**Casos de Uso Principales**
```
CU-2.2.1: Crear receta
├─ Chef define receta: "Capuchino"
├─ Agrega insumos: Café 20g + Leche 150ml
├─ Registra rendimiento: "1 taza = 180ml"
├─ Define merma esperada (Leche 5%)
├─ Sistema valida insumos disponibles
└─ Guarda receta activa

CU-2.2.2: Producción de orden
├─ Mesero envía orden a cocina
├─ KDS (Kitchen Display System) muestra:
│  ├─ Item: Capuchino
│  ├─ Notas: "Sin azúcar, frío"
│  ├─ Hora: 14:32
│  └─ Mesa: M5
├─ Chef marca como "Preparando"
├─ Después "Listo"
├─ Sistema notifica a mesero
└─ Auditoría de tiempos

CU-2.2.3: Control de merma
├─ Chef registra Leche "desechada" 20ml
├─ Sistema calcula: esperado 5%, real 8%
├─ Reporte de variancia vs receta
└─ Análisis de eficiencia

CU-2.2.4: Cálculo de costo de plato
├─ Receta: Café 20g ($1,000) + Leche 150ml ($600)
├─ Costo base: $1,600
├─ + merma (5%): $80
├─ = Costo real: $1,680
├─ Margen = Precio - Costo
└─ Dashboard muestra márgenes por chef
```

**Datos a Capturar**
```
Receta (Mejorada)
├─ receta_id (PK)
├─ empresa_id (FK)
├─ producto_id (FK)
├─ nombre_receta (Text)
├─ instrucciones_prep (Text)
├─ rendimiento (Decimal)
├─ tiempo_prep_promedio (Integer min)
├─ dificultad: "facil|medio|dificil"
├─ activa (Boolean)
├─ foto_paso_a_paso (JSON array de URLs)
└─ creada_por_id (FK → Usuario)

RecetaDetalle (Mejorada)
├─ detalle_id (PK)
├─ receta_id (FK)
├─ insumo_id (FK)
├─ cantidad (Decimal)
├─ unidad: "gramo|ml|unidad"
├─ merma_porcentaje (Decimal)
├─ costo_insumo (Decimal)
└─ costo_total_linea (Computed)

OrdenProduccion (Mejorada)
├─ orden_id (PK)
├─ empresa_id (FK)
├─ detalle_venta_id (FK)
├─ receta_id (FK)
├─ estado: "pendiente|preparando|listo|entregado|cancelada"
├─ fecha_creacion (TS)
├─ fecha_inicio (TS, nullable)
├─ fecha_listo (TS, nullable)
├─ chef_asignado_id (FK)
├─ notas_especiales (Text)
├─ tiempo_preparacion_real (Integer min)
├─ foto_plato_final (URL, nullable)
└─ calidad_score (1-5, nullable)

MermaRegistro
├─ merma_id (PK)
├─ receta_id (FK)
├─ producto_id (FK)
├─ cantidad_merma (Decimal)
├─ motivo: "normal|error|prueba|desperdicio"
├─ fecha (TS)
├─ usuario_id (FK)
└─ observaciones (Text)

CostosReceta (Materialized View)
├─ receta_id
├─ costo_base (Decimal)
├─ costo_con_merma (Decimal)
├─ precio_venta (Decimal)
├─ margen_pesos (Decimal)
├─ margen_porcentaje (Decimal)
└─ rentabilidad_ranking (Integer 1-100)
```

**UI/UX - Kitchen Display System (KDS)**

```
PANTALLA COCINA
┌──────────────────────────────────────────────────┐
│ COCINA - 14:45   [👨‍🍳 Carlos] [⚙️ Configurar]    │
├──────────────────────────────────────────────────┤
│                                                  │
│  [PENDIENTES] [EN PREP] [LISTOS] [HISTORIAL]   │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐               │
│  │ Capuchino   │  │ Latte       │               │
│  │ Mesa 5      │  │ Mesa 3      │               │
│  │ 14:32 (-) 2'│  │ 14:35 (-) 5'│               │
│  │ Sin azúcar  │  │ Extra shot  │               │
│  │ Frío        │  │             │               │
│  │ [▶ INICIAR] │  │ [✅ LISTO]  │               │
│  └─────────────┘  └─────────────┘               │
│                                                  │
│  ┌─────────────┐                                │
│  │ Croissant   │                                │
│  │ Mesa 7      │                                │
│  │ 14:38       │                                │
│  │ Bien cocido │                                │
│  │ [▶ INICIAR] │                                │
│  └─────────────┘                                │
│                                                  │
│ Totales: 3 pendientes, 2 en prep, 1 listo     │
└──────────────────────────────────────────────────┘
```

**Estimación de Desarrollo**
- Modelos mejorados: 8 horas
- API recetas y órdenes: 14 horas
- Kitchen Display System: 18 horas
- Control de merma: 8 horas
- Reportes de eficiencia: 8 horas
- Testing: 8 horas
- **Subtotal: 64 horas**

---

**2.3 GASTOS OPERATIVOS**

**Estado Actual**: 30% completo
- ✅ Modelo básico de Gasto
- ❌ Categorización de gastos
- ❌ Aprobación de gastos
- ❌ Análisis de gastos vs presupuesto

**Descripción Funcional**
Registro de todos los gastos operacionales (servicios, mantenimiento, suministros, etc). Presupuestación y análisis.

**Casos de Uso Principales**
```
CU-2.3.1: Registrar gasto
├─ Empleado compra suministro
├─ Ingresa: fecha, categoría, valor, recibo
├─ Sistema guarda en "Pendiente aprobación"
└─ Admin recibe notificación

CU-2.3.2: Aprobar gasto
├─ Admin revisa recibo (foto)
├─ Verifica categoría correcta
├─ Aprueba o rechaza
├─ Si aprueba → actualiza presupuesto
└─ Email a empleado

CU-2.3.3: Presupuesto vs Real
├─ Admin define presupuesto mes: Servicios $500k
├─ Sistema acumula gastos reales
├─ Dashboard muestra: $120k / $500k (24%)
├─ Alerta si va a exceder
└─ Proyección end-of-month
```

**Datos a Capturar**
```
Gasto (Mejorada)
├─ gasto_id (PK)
├─ empresa_id (FK)
├─ categoria_id (FK → CategoriaGasto)
├─ fecha_gasto (Date)
├─ valor (Decimal)
├─ descripcion (Text)
├─ responsable_id (FK → Usuario)
├─ aprobado_por_id (FK, nullable)
├─ estado: "borrador|pendiente_aprobacion|aprobado|rechazado"
├─ comprobante_url (String)
├─ numero_comprobante (String)
├─ referencia_interna (String)
├─ es_recurrente (Boolean)
└─ campos_metadata (JSON)

CategoriaGasto
├─ categoria_id (PK)
├─ empresa_id (FK)
├─ nombre: "Servicios", "Mantenimiento"
├─ presupuesto_mes (Decimal)
├─ activa (Boolean)
└─ codigo_contable (String, nullable)

PresupuestoMensual
├─ presupuesto_id (PK)
├─ empresa_id (FK)
├─ mes_año (YearMonth)
├─ categoria_id (FK)
├─ monto_presupuesto (Decimal)
├─ monto_gastado (Computed)
├─ porcentaje_utilizado (Computed)
└─ notas (Text)
```

**Estimación de Desarrollo**
- Modelo Gasto mejorado: 4 horas
- API endpoints: 10 horas
- UI admin: 8 horas
- Aprobaciones y workflow: 8 horas
- Reportes presupuestarios: 10 horas
- Testing: 6 horas
- **Subtotal: 46 horas**

**TOTAL FASE 2: 54 + 64 + 46 = 164 horas**
*Optimizar a 80 horas con componentes compartidos*

---

### FASE 3: TALENTO (Semana 5-6) 👥

**3.1 NÓMINA AVANZADA**

**Estado Actual**: 20% completo
- ✅ Modelo Empleado
- ❌ Cálculo de nómina (descuentos, aportes)
- ❌ Integración con RRHH externo
- ❌ Generación de soporte nómina (E-firma)

**Descripción Funcional**
Gestión completa de nómina mensual. Cálculo de salarios, descuentos, aportes a seguridad social, generación de documentos.

**Casos de Uso Principales**
```
CU-3.1.1: Crear nómina mensual
├─ Admin selecciona mes
├─ Sistema trae empleados activos
├─ Calcula: Salario base + comisiones - descuentos
├─ Genera lista para pago
└─ Admin autoriza transferencia masiva

CU-3.1.2: Cálculo de comisiones
├─ Mesero: comisión 2% de ventas
├─ Chef: comisión $50k si producción > 100 items
├─ Sistema consulta ventas del mes
├─ Calcula automático
└─ Incluye en nómina

CU-3.1.3: Descuentos y aportes
├─ Aporte AFILIACIÓN: 8% salario
├─ Aporte EPS: 4%
├─ Retención en la fuente: según salario
├─ Sistema calcula automático
└─ Genera certificación para impuestos

CU-3.1.4: Generación de soporte
├─ Descarga nómina en PDF/Excel
├─ Incluye liquidaciones individuales
├─ Totales de aportes por empleado
├─ Listo para auditoría
└─ Archivo firmado digitalmente
```

**Datos a Capturar**
```
Empleado (Mejorada)
├─ empleado_id (PK)
├─ empresa_id (FK)
├─ documento (String unique)
├─ nombre (String)
├─ apellido (String)
├─ email (String)
├─ telefono (String)
├─ cargo (String)
├─ fecha_ingreso (Date)
├─ salario_base (Decimal)
├─ tipo_contrato: "indefinido|temporal|por_horas"
├─ estado: "activo|inactivo|licencia"
├─ porcentaje_comision (Decimal)
├─ banco_nombre (String)
├─ cuenta_numero (String)
├─ tipo_cuenta: "ahorro|corriente"
├─ aportante_voluntario (Boolean)
└─ campos_metadata (JSON)

Nomina
├─ nomina_id (PK)
├─ empresa_id (FK)
├─ periodo_mes (YearMonth)
├─ estado: "borrador|generada|pagada|anulada"
├─ fecha_generacion (TS)
├─ fecha_pago (Date, nullable)
├─ total_salarios (Decimal)
├─ total_comisiones (Decimal)
├─ total_descuentos (Decimal)
├─ total_aportes (Decimal)
├─ total_neto (Decimal)
└─ observaciones (Text)

DetalleNomina
├─ detalle_id (PK)
├─ nomina_id (FK)
├─ empleado_id (FK)
├─ salario_base (Decimal)
├─ comisiones (Decimal)
├─ bonificaciones (Decimal)
├─ descuentos_diversos (Decimal)
├─ aporte_afiliacion (Decimal)
├─ aporte_eps (Decimal)
├─ retencion_fuente (Decimal)
├─ total_descuentos (Decimal)
├─ neto_pagar (Decimal)
├─ banco_nombre (String)
├─ cuenta_numero (String)
└─ confirmado_pago (Boolean)

ConceptoNomina
├─ concepto_id (PK)
├─ empresa_id (FK)
├─ nombre: "Comisión", "Bono", "Descuento"
├─ tipo: "ingreso|descuento|aporte"
├─ porcentaje_o_valor: "porcentaje|valor_fijo"
├─ valor_numerico (Decimal)
├─ activo (Boolean)
└─ orden_calculo (Integer)
```

**Estimación de Desarrollo**
- Modelos mejorados: 6 horas
- Cálculo de nómina: 18 horas
- Integración comisiones: 10 horas
- Generación de documentos: 10 horas
- Integraciones externas (RRHH): 8 horas
- Testing: 8 horas
- **Subtotal: 60 horas**

---

**3.2 REGISTRO DE PERSONAL Y ASISTENCIA**

**Estado Actual**: 40% completo
- ✅ Modelo Empleado
- ❌ Sistema de check-in/out
- ❌ Control de asistencia
- ❌ Reportes de puntualidad

**Descripción Funcional**
Registro de entrada/salida de empleados, control de asistencia, permisos y licencias.

**Casos de Uso Principales**
```
CU-3.2.1: Check-in al llegar
├─ Empleado llega y marca entrada
├─ Sistema registra hora exacta + GPS (opcional)
├─ Dashboard muestra quién está presente
└─ Auditoría de todos los eventos

CU-3.2.2: Control de faltas
├─ Sistema detecta: empleado no se marcó
├─ Admin recibe notificación
├─ Puede marcar como "falta" o "justificada"
├─ Descuento automático en nómina si falta
└─ Reporte de ausentismo

CU-3.2.3: Permisos y licencias
├─ Empleado solicita permiso: "Cita médica"
├─ Admin autoriza
├─ Sistema no cuenta como falta
├─ Reporte de tipos de permisos
└─ Estadística de uso

CU-3.2.4: Análisis de puntualidad
├─ Dashboard: "Carlos - 5 retardos en mes"
├─ Gráfico: tendencia de puntualidad
├─ Reporte: empleados más/menos puntuales
└─ Comparativa vs período anterior
```

**Datos a Capturar**
```
Asistencia
├─ asistencia_id (PK)
├─ empleado_id (FK)
├─ fecha (Date)
├─ hora_entrada (Time)
├─ hora_salida (Time, nullable)
├─ minutos_trabajados (Integer)
├─ tipo_dia: "normal|feriado|fin_semana"
├─ latitud, longitud (Decimal, opcional)
├─ dispositivo_checkin (String)
├─ observaciones (Text)
└─ confirmado (Boolean)

Permiso
├─ permiso_id (PK)
├─ empleado_id (FK)
├─ fecha_inicio (Date)
├─ fecha_fin (Date)
├─ tipo: "medico|personal|sin_pago|calamidad"
├─ dias_totales (Integer)
├─ aprobado_por_id (FK)
├─ estado: "pendiente|aprobado|rechazado"
├─ razon (Text)
└─ archivo_adjunto (URL, nullable)

EstadisticaAsistencia (Materialized View)
├─ empleado_id
├─ mes_año
├─ dias_laborales
├─ dias_asistidos
├─ dias_falta
├─ permisos_justificados
├─ retardos_cantidad
├─ horas_totales
└─ eficiencia_porcentaje
```

**Estimación de Desarrollo**
- Modelos: 4 horas
- API check-in/out: 10 horas
- Dashboard asistencia: 10 horas
- Control de permisos: 8 horas
- Reportes: 8 horas
- Testing: 6 horas
- **Subtotal: 46 horas**

---

**3.3 COMISIONES Y PROPINAS**

**Estado Actual**: 20% completo
- ✅ Campos en Venta (propina)
- ❌ Sistema de comisiones por mesero
- ❌ Distribución de propinas
- ❌ Reporte de comisiones

**Descripción Funcional**
Cálculo automático de comisiones a meseros y distribución de propinas. Motivación del equipo basada en rendimiento.

**Casos de Uso Principales**
```
CU-3.3.1: Definir estructura de comisiones
├─ Admin configura:
│  ├─ Mesero base: 3% de ventas
│  ├─ Chef: $50 por 100 items producidos
│  ├─ Barista: $20 por café vendido
│  └─ Bonus si ventas > $1M: +0.5%
├─ Sistema guarda reglas
└─ Válido desde fecha X

CU-3.3.2: Cálculo automático
├─ Sistema detecta: venta cerrada por mesero
├─ Calcula: venta $50k * 3% = comisión $1.5k
├─ Acumula en contador mensual del mesero
├─ Incluye en nómina automático
└─ Reporte diario de comisiones

CU-3.3.3: Distribución de propina
├─ Cliente deja propina $10k en mesa 5
├─ Admin distribuye: 70% mesero, 30% cocina
├─ Sistema registra movimiento
├─ Visibilidad en app del mesero
└─ Incluye en nómina

CU-3.3.4: Leaderboard de rendimiento
├─ Dashboard: "Top 5 meseros del mes"
├─ Gráfico: comisiones por empleado
├─ Filtro: por período, por producto
├─ Comparativa: mes actual vs anterior
└─ Motivación competitiva
```

**Datos a Capturar**
```
EstructuraComision
├─ estructura_id (PK)
├─ empresa_id (FK)
├─ cargo_id (FK)
├─ tipo: "porcentaje|fijo_item|escalonado"
├─ valor_base (Decimal)
├─ bonus_condicion (JSON)
│  └─ {monto_minimo: 1000000, bonus: 0.5%}
├─ vigente_desde (Date)
├─ vigente_hasta (Date, nullable)
└─ activa (Boolean)

ComisionEmpleado
├─ comision_id (PK)
├─ empleado_id (FK)
├─ periodo (YearMonth)
├─ venta_id (FK, nullable)
├─ tipo: "venta|bonus|propina"
├─ monto_base (Decimal)
├─ monto_comision (Decimal)
├─ fecha_calculo (TS)
└─ incluida_en_nomina (Boolean)

PropinasDistribucion
├─ propina_id (PK)
├─ venta_id (FK)
├─ monto_total (Decimal)
├─ distribucion (JSON)
│  └─ [{empleado_id, porcentaje, monto}]
├─ distribuida_en_nómina (YearMonth, nullable)
└─ timestamp (TS)

EstadisticasComision (Materialized View)
├─ empleado_id
├─ mes_año
├─ total_comisiones (Decimal)
├─ total_propinas (Decimal)
├─ total_bonuses (Decimal)
├─ ranking_empresa (Integer 1-100)
└─ tendencia_mes_anterior (Percentage change)
```

**Estimación de Desarrollo**
- Modelos y API: 8 horas
- Cálculos automáticos: 12 horas
- Distribución de propinas: 8 horas
- Dashboard leaderboard: 8 horas
- Integración nómina: 6 horas
- Testing: 6 horas
- **Subtotal: 48 horas**

**TOTAL FASE 3: 60 + 46 + 48 = 154 horas**
*Optimizar a 80 horas reutilizando lógica*

---

### FASE 4: INTELIGENCIA (Semana 7-8) 📊

**4.1 REPORTES EJECUTIVOS**

**Estado Actual**: 10% completo
- ✅ Modelos de datos
- ❌ Reportes estructurados
- ❌ Exportación a Excel/PDF
- ❌ Visualización de datos

**Descripción Funcional**
Suite de reportes que responden preguntas críticas del negocio: "¿Cuánto vendimos hoy?", "¿Quién es el producto estrella?", etc.

**Reportes Prioritarios**
```
1. REPORTE DE VENTAS DIARIAS
   ├─ Total vendido hoy
   ├─ Desglose por medio de pago
   ├─ Comparativa vs ayer
   └─ Tendencia semana

2. REPORTE DE PRODUCTOS MÁS VENDIDOS
   ├─ Top 10 items por cantidad
   ├─ Top 10 items por ingresos
   ├─ Margen unitario vs total
   ├─ Velocidad de rotación
   └─ Variación mes anterior

3. REPORTE DE DESEMPEÑO DE MESEROS
   ├─ Venta promedio por mesero
   ├─ Promedio de cuenta (ticket promedio)
   ├─ Comisiones generadas
   ├─ Satisfacción (si hay ratings)
   └─ Comparativa

4. REPORTE DE RENTABILIDAD
   ├─ Margen bruto total
   ├─ Margen por categoría
   ├─ Margen por producto
   ├─ Costo de operación vs ingreso
   └─ Proyección de ganancias

5. REPORTE DE INVENTARIO
   ├─ Stock actual vs mínimo
   ├─ Items en riesgo de desabastecimiento
   ├─ Rotación ABC
   ├─ Costo del inventario en almacén
   └─ Items lento-movimiento (candidatos a descontinuar)

6. REPORTE DE NÓMINA
   ├─ Total gastos en salarios
   ├─ Desglose por cargo
   ├─ Comisiones pagadas
   ├─ Aportes a seguridad social
   └─ Proyección anual
```

**Datos para Reportes (Aggregation Tables)**
```
VentaDiaria (Materialized View - Actualiza cada hora)
├─ fecha
├─ empresa_id
├─ total_ventas (Decimal)
├─ cantidad_transacciones (Integer)
├─ promedio_transaccion (Decimal)
├─ margen_bruto (Decimal)
├─ impuestos_generados (Decimal)
└─ comparativa_dia_anterior (Percentage)

ProductoVentas (Materialized View - Diaria)
├─ producto_id
├─ nombre
├─ cantidad_vendida (Decimal)
├─ monto_vendido (Decimal)
├─ monto_costo (Decimal)
├─ margen_pesos (Decimal)
├─ margen_porcentaje (Decimal)
├─ ranking_cantidad (Integer)
├─ ranking_ingresos (Integer)
└─ tendencia_vs_semana_anterior (Percentage)

MeseroVentas (Materialized View - Diaria)
├─ empleado_id
├─ nombre
├─ mesas_atendidas (Integer)
├─ transacciones_totales (Integer)
├─ venta_total (Decimal)
├─ ticket_promedio (Decimal)
├─ comisiones (Decimal)
├─ propinas_recibidas (Decimal)
└─ ranking (Integer)

InventarioSaldoHistorico (Materialized View)
├─ fecha
├─ producto_id
├─ cantidad (Decimal)
├─ valor (Decimal)
├─ dias_para_agotar (Integer, basado en rotación)
└─ alerta_nivel (Boolean)

CostosOperacionales (Materialized View - Mensual)
├─ mes_año
├─ total_nómina (Decimal)
├─ total_gastos (Decimal)
├─ total_impuestos (Decimal)
├─ total_costos_variables (Decimal)
├─ total_ingresos (Decimal)
├─ margen_neto (Decimal)
└─ roi_porcentaje (Decimal)
```

**Estimación de Desarrollo**
- Materialized views (BD): 12 horas
- API endpoints reportes: 16 horas
- Generación PDF/Excel: 12 horas
- Dashboards (HTML + JS): 20 horas
- Testing y optimización: 10 horas
- **Subtotal: 70 horas**

---

**4.2 DASHBOARD KPI**

**Estado Actual**: 20% completo
- ✅ Dashboard básico
- ❌ KPI cards dinámicos
- ❌ Gráficos interactivos
- ❌ Métricas en tiempo real

**Descripción Funcional**
Dashboard ejecutivo con métricas clave en tiempo real. CEO ve salud del negocio en 5 segundos.

**KPIs Principales**
```
FINANZAS
├─ Ingresos Hoy: $500,000 (↑ 12% vs ayer)
├─ Transacciones: 128 (↓ 5% vs ayer)
├─ Ticket Promedio: $3,906 (↑ 8%)
├─ Margen Bruto: 62% (↓ 2%)
└─ Proyección Mes: $15.2M

OPERACIONES
├─ Mesas Ocupadas: 12/18 (67%)
├─ Tiempo Promedio Mesa: 45 min
├─ Items en Cocina: 8 pendientes
├─ Stock en Riesgo: 3 productos
└─ Variancia Inventario: +2.1%

TALENTO
├─ Empleados Presentes: 15/16
├─ Asistencia Mes: 98.5%
├─ Top Mesero: Carlos ($8.5k comisiones)
├─ Nómina Próximo Pago: $180k
└─ Retención Anual: 85%

CLIENTE
├─ Nuevos Clientes Hoy: 42
├─ Clientes Recurrentes: 156 (61%)
├─ NPS (si existe): 8.2/10
├─ Quejas Procesadas: 0
└─ Satisfacción Promedio: 4.5/5
```

**Visualizaciones Interactivas**
```
├─ Línea: Ventas por hora del día
├─ Barras: Top 5 productos
├─ Pastel: Distribución por categoría
├─ Gauge: Ocupación de mesas
├─ Tabla: Detalle de transacciones recientes
└─ Mapa: Si múltiples sucursales
```

**Estimación de Desarrollo**
- Modelos de datos: 4 horas
- Backend KPI endpoints: 12 horas
- Frontend dashboard: 20 horas
- WebSocket real-time: 12 horas
- Gráficos interactivos (Chart.js): 12 horas
- Testing: 8 horas
- **Subtotal: 68 horas**

---

**4.3 ANALÍTICA AVANZADA**

**Estado Actual**: 5% completo

**Descripción Funcional**
Análisis profundos con machine learning simple: predicciones, anomalías, segmentación de clientes.

**Casos de Uso**
```
1. PREDICCIÓN DE DEMANDA
   ├─ ¿Cuántos cappuccinos venderé el viernes?
   ├─ Modelo: Regresión lineal sobre datos históricos
   └─ Resultado: Alertar para preparar 150 tazas

2. DETECCIÓN DE ANOMALÍAS
   ├─ ¿Hubo venta inusual hoy?
   ├─ Algoritmo: Z-score sobre desviación estándar
   └─ Resultado: "Venta 200% sobre promedio - Revisar"

3. SEGMENTACIÓN DE CLIENTES
   ├─ Agrupar: VIP, Frecuentes, Ocasionales
   ├─ Algoritmo: K-means clustering
   ├─ Resultado: Enviar promociones targetizadas
   └─ Oportunidad: Personalizar experiencia

4. ABC ANALYSIS
   ├─ 20% de productos generan 80% ingresos
   ├─ Resultado: Qué reponer prioritariamente
   └─ Impacto: Optimizar compras

5. CHURN PREDICTION
   ├─ Qué empleado probablemente se vaya
   ├─ Indicadores: Faltas, comisiones bajas
   ├─ Resultado: Intervención preventiva
   └─ Impacto: Retención de talento

6. RECOMENDACIONES CRUZADAS
   ├─ Si compra café → recomendar pastel
   ├─ Algoritmo: Association rules (Apriori)
   └─ Resultado: Sugerencias en POS
```

**Implementación Simple (scikit-learn)**
```python
# Ejemplo: Predicción de demanda
from sklearn.linear_model import LinearRegression
import numpy as np

# Datos: últimos 30 días de ventas
X = np.array([1, 2, 3, ..., 30]).reshape(-1, 1)
y = np.array([100, 110, 95, ..., 120])

# Entrenar
modelo = LinearRegression()
modelo.fit(X, y)

# Predecir día 31
prediccion = modelo.predict([[31]])[0]
print(f"Demanda predicha: {prediccion}")
```

**Estimación de Desarrollo**
- Preparación de datos: 8 horas
- Modelos ML básicos: 12 horas
- API endpoints: 8 horas
- Dashboard visualización: 10 horas
- Testing y validación: 8 horas
- Documentación: 4 horas
- **Subtotal: 50 horas**

**TOTAL FASE 4: 70 + 68 + 50 = 188 horas**
*Optimizar a 100 horas usando librerías pre-built*

---

### FASE 5: MOVILIDAD (Semana 9-10) 📱

**5.1 APP MÓVIL MESEROS**

**Estado Actual**: 0% (requiere Flutter/React Native)

**Descripción Funcional**
App nativa para tablets/móviles que meseros usan para tomar órdenes, ver estado cocina, propinas.

**Funcionalidades**
```
├─ Autenticación con huella/face
├─ Lista de mesas con estado real-time
├─ Crear orden: busca producto, agreg notas
├─ Ver estado cocina (KDS integrado)
├─ Recibir notificaciones de platos listos
├─ Registrar propina y cobrar
├─ Acceso a menú promocional
├─ Historial de ventas personales
└─ Chat con cocina para cambios urgentes
```

**Estimación de Desarrollo**
- Setup proyecto Flutter/React Native: 6 horas
- Autenticación y login: 6 horas
- Interfaz mesas: 12 horas
- Módulo de órdenes: 16 horas
- WebSocket real-time: 10 horas
- Cobro y propina: 6 horas
- Testing en dispositivos: 8 horas
- **Subtotal: 64 horas**

---

**5.2 KITCHEN DISPLAY SYSTEM (KDS) MEJORADO**

**Estado Actual**: 30% (versión web básica)

**Mejoras Necesarias**
```
├─ Modo full-screen en tablet cocina
├─ Audio/visual alerts para órdenes
├─ Timer progresivo por orden
├─ Agrupación por categoría
├─ Botones grandes (touch-friendly)
├─ Historial de órdenes completadas
└─ Estadísticas de eficiencia chef
```

**Estimación de Desarrollo**
- Mejoras interfaz: 8 horas
- Audio alerts: 4 horas
- Timer y tracking: 6 horas
- Testing tablet: 6 horas
- **Subtotal: 24 horas**

---

**5.3 NOTIFICACIONES REAL-TIME**

**Estado Actual**: 0% (requiere WebSocket)

**Implementación**
```
├─ Servidor: FastAPI WebSocket
├─ Eventos: nuevo pedido, plato listo, cobro, etc
├─ Destinatarios: mesero, cocina, admin
├─ Persistencia: si desconecta, recibe al reconectar
├─ Escalabilidad: Redis pub/sub si múltiples servidores
└─ Mobile: Push notifications Firebase Cloud Messaging
```

**Datos**
```
Notificacion
├─ notificacion_id (PK)
├─ usuario_id (FK)
├─ tipo: "pedido_nuevo|plato_listo|cobro|mensaje"
├─ titulo (String)
├─ contenido (Text)
├─ referencia_id (String) → venta_123, orden_456
├─ fecha (TS)
├─ leida (Boolean)
├─ canales: "web|push|email|sms"
└─ datos_metadata (JSON)
```

**Estimación de Desarrollo**
- Backend WebSocket: 12 horas
- Integración push notifications: 6 horas
- Frontend websockets: 8 horas
- Testing: 6 horas
- **Subtotal: 32 horas**

**TOTAL FASE 5: 64 + 24 + 32 = 120 horas**
*Reducible a 60 horas si enfocamos solo en web*

---

## 🏗️ ARQUITECTURA TÉCNICA

### Patrón de Diseño

**Backend: MVC Modular**
```
app/
├── models.py              # SQLAlchemy ORM (V del MVC)
├── schemas/               # Pydantic (input validation)
│   ├── ventas.py
│   ├── productos.py
│   ├── empleados.py
│   └── ...
├── routes/                # API endpoints (C del MVC)
│   ├── ventas.py
│   ├── productos.py
│   ├── empleados.py
│   ├── reportes.py
│   └── ...
├── services/              # Lógica de negocio (M del MVC)
│   ├── venta_service.py
│   ├── nómina_service.py
│   ├── inventario_service.py
│   └── ...
├── utils/                 # Helpers reutilizables
│   ├── validaciones.py
│   ├── formatos.py
│   ├── calculos.py
│   └── ...
├── templates/             # Jinja2 frontend
└── static/                # CSS, JS, assets
```

**Frontend: Component-Based**
```
static/
├── css/
│   ├── design-system.css  (Variables, colores, tipografía)
│   ├── layout.css         (Sidebar, header, grid)
│   ├── components.css     (Cards, botones, tablas)
│   └── pages/
│       ├── pos.css
│       ├── productos.css
│       └── ...
├── js/
│   ├── app.js             (Inicialización)
│   ├── components/
│   │   ├── Modal.js
│   │   ├── Table.js
│   │   ├── Form.js
│   │   └── ...
│   ├── services/
│   │   ├── api.js         (Fetch wrapper)
│   │   ├── websocket.js
│   │   └── storage.js
│   └── pages/
│       ├── pos.js
│       ├── reportes.js
│       └── ...
└── images/
```

### Base de Datos - Diseño Optimizado

**Tablas Nuevas Requeridas**

```sql
-- YA EXISTEN (22 modelos actuales)
Empresa, Zona, Mesa, Producto, Categoría
Venta, DetalleVenta, Cliente, AbonoCartera
Empleado, Usuario, Nómina
Receta, RecetaDetalle, OrdenProduccion
MovimientoInventario, Gasto
...

-- NUEVAS TABLAS REQUERIDAS
ProductoVariante
ProductoAddon
FacturaPDF
EstructuraComision
ComisionEmpleado
PropinasDistribucion
CategoriaGasto
PresupuestoMensual
MermaRegistro
AlertaInventario
Asistencia
Permiso
ConceptoNomina
DetalleNomina
Notificacion
EstadoMesaHistorico
InventarioSaldoHistorico
...

-- MATERIALIZED VIEWS (para reportes/performance)
VentaDiaria
ProductoVentas
MeseroVentas
CostosOperacionales
EstadisticasComision
...
```

**Índices Críticos**
```sql
-- Performance
CREATE INDEX idx_ventas_empresa_fecha ON ventas(empresa_id, fecha);
CREATE INDEX idx_detalle_venta_producto ON detalle_ventas(venta_id, producto_id);
CREATE INDEX idx_movimiento_inv_producto ON movimientos_inventario(producto_id, fecha);
CREATE INDEX idx_asistencia_empleado ON asistencia(empleado_id, fecha);
CREATE INDEX idx_comision_empleado_periodo ON comision_empleado(empleado_id, periodo);
```

### APIs a Exponer

**Endpoints Principales (OpenAPI/Swagger)**

```
# VENTAS (POS)
POST   /api/v1/ventas              Crear venta
GET    /api/v1/ventas/{id}         Obtener venta
PUT    /api/v1/ventas/{id}         Actualizar venta
POST   /api/v1/ventas/{id}/cerrar  Cerrar venta (cobro)
POST   /api/v1/ventas/{id}/anular  Anular venta
POST   /api/v1/ventas/{id}/items   Agregar item a venta

# MESAS
GET    /api/v1/mesas               Listar mesas
GET    /api/v1/mesas/estado        Estado real-time todas mesas
PUT    /api/v1/mesas/{id}          Actualizar mesa
POST   /api/v1/mesas/{id}/fusionar Fusionar mesas

# PRODUCTOS
GET    /api/v1/productos           Listar productos
POST   /api/v1/productos           Crear producto
PUT    /api/v1/productos/{id}      Actualizar producto
GET    /api/v1/productos/buscar    Búsqueda + autocomplete

# INVENTARIO
GET    /api/v1/inventario          Saldos actuales
POST   /api/v1/inventario/movimiento Registrar movimiento
GET    /api/v1/inventario/alertas  Productos en riesgo
POST   /api/v1/inventario/auditoria Iniciar recuento

# RECETAS & PRODUCCIÓN
GET    /api/v1/recetas             Listar recetas
POST   /api/v1/recetas             Crear receta
GET    /api/v1/ordenes-produccion  Órdenes pendientes
POST   /api/v1/ordenes-produccion/{id}/listo Marcar como listo

# EMPLEADOS
GET    /api/v1/empleados           Listar empleados
POST   /api/v1/empleados           Crear empleado
GET    /api/v1/asistencia          Registro de entrada/salida

# NÓMINA
POST   /api/v1/nomina              Generar nómina mes
GET    /api/v1/nomina/{id}         Obtener detalle nómina
GET    /api/v1/comisiones          Comisiones empleado

# REPORTES
GET    /api/v1/reportes/ventas     Reporte ventas diarias
GET    /api/v1/reportes/productos  Top productos
GET    /api/v1/reportes/meseros    Desempeño meseros
GET    /api/v1/reportes/rentabilidad Análisis margen
GET    /api/v1/reportes/inventario Stock y rotación
GET    /api/v1/reportes/nomina     Gastos nómina

# DASHBOARD
GET    /api/v1/dashboard/kpis      KPIs principales
GET    /api/v1/dashboard/graficos  Datos para gráficos

# WEBHOOKS (para integraciones)
POST   /api/v1/webhooks/rappi      Nuevas órdenes Rappi
POST   /api/v1/webhooks/ubereats   Nuevas órdenes Uber Eats
```

### Autenticación y Autorización

**Roles y Permisos**
```
ROLES:
├─ Admin (superuser)
│  └─ Acceso total
├─ Gerente (manager)
│  ├─ Reportes
│  ├─ Nómina
│  ├─ Configuración
│  └─ Sin acceso a: Auditoría, Superadmin
├─ Mesero (staff)
│  ├─ Ver mesas
│  ├─ Crear venta
│  ├─ Ver propina + comisión
│  └─ Sin acceso a: Reportes, Nómina, Configuración
├─ Chef (kitchen)
│  ├─ Ver órdenes producción
│  ├─ Marcar como listo
│  └─ Registrar merma
├─ Cocinero (cook)
│  ├─ Ver KDS (Kitchen Display System)
│  └─ Actualizar estado

PERMISOS GRANULARES:
├─ venta:crear
├─ venta:anular
├─ inventario:ver
├─ inventario:editar
├─ nomina:generar
├─ nomina:ver
├─ reporte:ver
├─ configuracion:editar
└─ auditoria:ver
```

**Implementación**
```python
# Decorator para proteger rutas
@app.get("/api/v1/reportes/ventas")
@require_role("admin", "gerente")
@require_permission("reporte:ver")
async def get_reporte_ventas(request: Request, db: Session):
    usuario_id = request.session.get("usuario_id")
    usuario = db.get(Usuario, usuario_id)
    # ... resto de lógica
```

### Caching y Optimización

**Cache Strategy**
```
├─ Redis Layer
│  ├─ Productos: 1 hora (TTL)
│  ├─ Mesas estado: 30 segundos (real-time)
│  ├─ Reportes: 1 hora
│  └─ Sesiones usuario: 24 horas
│
├─ Query Optimization
│  ├─ Eager loading (joinedload)
│  ├─ Materialized views para agregados
│  ├─ Índices en columnas frecuentes
│  └─ Pagination (limit 50 items default)
│
└─ Frontend Cache
   ├─ LocalStorage: productos
   ├─ SessionStorage: carrito temporal
   └─ Service Workers: offline support
```

---

## 🎨 PERSONALIZACIÓN Y CONFIGURACIÓN

### Sistema de Temas

**Qué Debe Ser Configurable sin Código**

```
POR EMPRESA:
├─ Logo (subir imagen)
├─ Colores primario/secundario
├─ Tipografía (seleccionar familia)
├─ Favicon
├─ Moneda símbolo
├─ Idioma (ES, EN, FR, PT)
├─ Zona horaria
├─ Número de IVA (impuesto local)
└─ Formato de facturación local

POR UBICACIÓN (Sucursal):
├─ Nombre mostrador
├─ Dirección
├─ Teléfono
├─ Horarios apertura/cierre
├─ Layout de mesas
├─ Categorías de gastos
└─ Estructura de comisiones local

POR USUARIO:
├─ Idioma preferencia
├─ Tema claro/oscuro
├─ Notificaciones on/off
├─ Densidad de interfaz
└─ Atajos de teclado
```

**Tabla de Configuración**
```python
class Configuracion(Base):
    __tablename__ = "configuraciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    
    # Tema
    color_primario: Mapped[str] = mapped_column(String(7))
    color_secundario: Mapped[str] = mapped_column(String(7))
    tipografia_primaria: Mapped[str]  # "Inter", "Roboto", etc
    
    # Moneda
    simbolo_moneda: Mapped[str] = mapped_column(String(5))
    posicion_simbolo: Mapped[str]  # "izquierda" | "derecha"
    decimales: Mapped[int] = mapped_column(default=2)
    
    # Impuestos
    porcentaje_iva: Mapped[Decimal] = mapped_column(default=0)
    incluir_iva_precio: Mapped[bool] = mapped_column(default=False)
    
    # Localization
    idioma: Mapped[str] = mapped_column(default="es")
    zona_horaria: Mapped[str] = mapped_column(default="America/Bogota")
    
    # Facturación
    prefijo_factura: Mapped[str]
    formato_numeracion: Mapped[str]  # JSON template
    
    campos_adicionales: Mapped[str] = mapped_column(Text)  # JSON
```

### Datos Multi-Empresa

**Estructura de Tenant**

```
EMPRESA (Raíz)
├─ Empresa 1: "Café Monteblanco"
│  ├─ Sucursal 1A: Centro
│  │  ├─ Mesas, inventario, empleados
│  │  ├─ Ventas
│  │  └─ Nómina
│  └─ Sucursal 1B: Zona Rosa
│     └─ [Misma estructura]
│
└─ Empresa 2: "Pizzería Italia"
   └─ [Similar]

DATO CLAVE: Toda tabla tiene empresa_id para multi-tenancy
```

---

## 📊 MÉTRICAS DE ÉXITO

### Enterprise-Readiness Checklist

```
SEGURIDAD (40 puntos)
☐ [10] Autenticación MFA (multi-factor)
☐ [10] Encriptación de datos en tránsito (HTTPS)
☐ [10] Auditoría completa de todos los cambios
☐ [10] Backup automático diario
          → TOTAL: 40/40

ESCALABILIDAD (30 puntos)
☐ [10] Pagination en todas las listas (no timeouts)
☐ [10] Caching estratégico (Redis)
☐ [10] Database indices en columnas críticas
          → TOTAL: 30/30

CONFIABILIDAD (20 puntos)
☐ [5]  Test coverage > 80%
☐ [5]  Rate limiting implementado
☐ [5]  Error handling robusto
☐ [5]  Logging centralizado
          → TOTAL: 20/20

USABILIDAD (10 puntos)
☐ [5]  Interfaz responsive (mobile, tablet, desktop)
☐ [5]  Tiempo de carga < 2 segundos
          → TOTAL: 10/10

TOTAL ENTERPRISE-READY: 100/100
```

### KPIs de Calidad

```
PERFORMANCE
├─ Tiempo respuesta API: < 200ms (p95)
├─ Tiempo carga página: < 2s (FirstContentfulPaint)
├─ Database query: < 100ms (p95)
└─ WebSocket latency: < 100ms

CONFIABILIDAD
├─ Uptime: > 99.5% mensual
├─ Error rate: < 0.5%
├─ Test coverage: > 80%
└─ Mean time to recovery: < 1 hora

USABILIDAD
├─ NPS (Net Promoter Score): > 50
├─ User satisfaction: > 4/5 estrellas
├─ Task completion rate: > 95%
└─ Error rate por usuario: < 2%

NEGOCIO
├─ ROI: Implementación paga en 6 meses
├─ Adopción: > 90% usuarios usando sistema
├─ Retención: < 5% churn mensual
└─ Crecimiento: +20% revenue vs sin sistema
```

### Benchmarks de Rendimiento

```
PRODUCCIÓN (Meta)
├─ Hasta 1,000 transacciones/día: ✅ Soporta
├─ Hasta 5 sucursales: ✅ Soporta
├─ Hasta 100 empleados: ✅ Soporta
├─ Hasta 10,000 productos: ✅ Soporta
└─ Hasta 100GB datos: ✅ Soporta (PostgreSQL)

SERVIDOR RECOMENDADO
├─ CPU: 2 cores (4 cores para 3+ sucursales)
├─ RAM: 4GB (8GB si 5+ sucursales)
├─ Disco: 50GB SSD
├─ BD: PostgreSQL 14+
└─ App Server: 2-4 procesos Uvicorn
```

### Criterios de Aceptación por Fase

```
FASE 1 COMPLETA cuando:
☐ POS genera facturas sin errores
☐ Cálculos de impuesto correctos (auditoría)
☐ Mesas actualización real-time < 1s
☐ Búsqueda productos funciona (50+ items)
☐ 100 transacciones/hora sin lag

FASE 2 COMPLETA cuando:
☐ Inventario consistency 99.9%
☐ KDS muestra órdenes en < 500ms
☐ Alertas de stock funcionan
☐ Recuentos registran diferencias < 5%
☐ Reportes se generan en < 5s

FASE 3 COMPLETA cuando:
☐ Nómina calcula correcta sin errores
☐ Comisiones automáticas coinciden manual
☐ Asistencia registra eventos correctamente
☐ PDF nómina lista para imprenta
☐ Auditoría de nómina completa

FASE 4 COMPLETA cuando:
☐ Reportes ejecutivos > 95% exactitud
☐ Dashboard KPI actualización real-time
☐ Gráficos interactivos funcionan
☐ ML predictions en rango aceptable
☐ Performance reportes < 5s

FASE 5 COMPLETA cuando:
☐ App móvil funciona en iOS y Android
☐ WebSocket notificaciones < 100ms
☐ KDS mejoras implementadas
☐ Push notifications entregadas > 95%
☐ Offline mode funciona correctamente
```

---

## 🚨 RIESGOS Y MITIGACIONES

```
RIESGO 1: SCOPE CREEP (ALTO)
├─ Descripción: Agregar funcionalidades "quick win" desviando tiempo
├─ Probabilidad: 80%
├─ Impacto: +200 horas, retraso 5 semanas
└─ Mitigación:
    ├─ Roadmap congelado (no cambios sin re-estimación)
    ├─ Sprint reviews semanales
    ├─ Backlog de "nice-to-have" para post-MVP
    └─ Decisión ejecutiva: velocidad > perfeccionismo

RIESGO 2: PERFORMANCE EN PRODUCCIÓN (ALTO)
├─ Descripción: Queries N+1, sin cache, sin índices
├─ Probabilidad: 60%
├─ Impacto: Sistema inutilizable con 1000+ transacciones
└─ Mitigación:
    ├─ Load testing semana 8 con datos reales
    ├─ APM tool (Sentry) desde semana 1
    ├─ Índices y cache layer obligatorio en checklist
    └─ Refactor DB queries si benchmark falla

RIESGO 3: INCOMPLETITUD DE REQUISITOS (MEDIO)
├─ Descripción: Requisitos mal especificados = rework
├─ Probabilidad: 50%
├─ Impacto: +100 horas refactoring
└─ Mitigación:
    ├─ Documentación PRD exhaustiva (este doc)
    ├─ Wireframes aprobados pre-desarrollo
    ├─ Demos interactivos cada 2 semanas
    └─ UAT (User Acceptance Testing) en fase 4

RIESGO 4: INTEGRACIÓN DE MÓDULOS (MEDIO)
├─ Descripción: Módulos desarrollados en paralelo no encajan
├─ Probabilidad: 40%
├─ Impacto: +80 horas integración/fixes
└─ Mitigación:
    ├─ API contract testing (mock endpoints)
    ├─ Shared models en BD desde inicio
    ├─ Integration tests bi-semanales
    └─ Equipo lead revisa interfaces cada fase

RIESGO 5: RECURSOS LIMITADOS (MEDIO)
├─ Descripción: Enfermedad, rotación de personal
├─ Probabilidad: 30%
├─ Impacto: +50 horas (retraso 1 semana)
└─ Mitigación:
    ├─ Documentación exhaustiva (código auto-explicado)
    ├─ Pair programming crítico camino
    ├─ Buffer de 10% horas planificadas
    └─ Cross-training en módulos principales

RIESGO 6: CAMBIOS REGULATORIOS (BAJO)
├─ Descripción: Nuevos requisitos DIAN, hacienda
├─ Probabilidad: 20%
├─ Impacto: +40 horas compliance
└─ Mitigación:
    ├─ Seguir cambios normativos
    ├─ Arquitectura modular para reglas negocio
    └─ Versioning de facturación
```

---

## 👥 CASOS DE USO POR ROL

### ADMINISTRADOR

```
Mañana tipical del Admin "Rodrigo"
09:00 ├─ Llega a oficina, abre dashboard
      ├─ "Ayer vendimos $580k, 18% más que martes"
      ├─ "Stock bajo en Café Gourmet - Generar orden compra"
      └─ "Carlos tiene 3 retardos este mes - Revisar"

10:00 ├─ Entra módulo de Nómina
      ├─ Revisa comisiones calculadas automáticas
      ├─ "Juan: $8.5k, Carlos: $7.2k, María: $9.1k"
      └─ Aprueba nómina del mes

11:00 ├─ Auditoría de inventario física
      ├─ Recuento mesas: 50 items, 3 diferencias
      ├─ Sistema ajusta automático
      └─ Reporte generado

14:00 ├─ Reporte de productos
      ├─ "Capuchino: 127 ventas, $1.08M ingreso"
      ├─ "Croissant: rotación lenta, considerar promo"
      └─ Ajusta precios en sistema

16:00 ├─ Cierre de caja
      ├─ Verifica: transacciones, cálculos, total
      ├─ Genera reporte de cierre
      └─ Backups automáticos completados
```

### MESERO

```
Tarde tipical de "Juan" (Mesero)

12:00 ├─ Check-in: "Llegué a trabajar"
      ├─ App marca: 12:00 PM, Location saved
      └─ Dashboard: "2 meseros presentes, 1 cliente esperando"

12:05 ├─ Cliente se sienta en Mesa 5
      ├─ Abre carrito: Capuchino + Croissant
      ├─ Agrega notas: "Sin azúcar, con leche descremada"
      └─ Cliente ve prep en 15 min aprox

12:15 ├─ Notificación: "Capuchino y Croissant listos!"
      ├─ Entrega items
      └─ Cliente marca: "Satisfecho" ⭐⭐⭐⭐⭐

12:45 ├─ Cliente pide la cuenta
      ├─ Cierra venta: $16.5k
      ├─ Cliente agrega propina: +$2k
      ├─ App muestra: "Comisión hoy: $2.8k"
      └─ Cliente se va

14:00 ├─ Check-out: "Termino turno"
      ├─ App marca: 14:00 PM
      ├─ Resumen: 8 mesas, $148k vendidas, $4.8k comisión
      └─ Excelente día! 🎉
```

### CHEF/COCINERO

```
Tarde de "Carlos" (Chef en Cocina)

12:00 ├─ Llega a cocina
      ├─ Revisa KDS (Kitchen Display)
      ├─ "3 cappuccinos, 2 croissants, 1 sándwich"
      └─ Comienza preparación

12:05 ├─ Prepara primer cappuccino
      ├─ Registra: "Usando Café Gourmet 20g"
      ├─ Sistema descuenta inventario
      └─ Marca como "Listo"

12:08 ├─ Mesero recibe notificación: "Cappuccino listo!"
      ├─ Entrega a cliente
      └─ KDS actualiza estado

13:00 ├─ Recuento merma del día
      ├─ "Leche desechada: 150ml (vs esperado 200ml)"
      ├─ Sistema: "Eficiencia: 125% (mejor que esperado!)"
      └─ Bono potencial por mejora

16:00 ├─ Dashboard personal
      ├─ "Hoy preparé 45 items, 100% satisfacción"
      ├─ "Comisión: $2.2k"
      └─ Ranking: Posición 1 entre chefs 🏆
```

### GERENTE GENERAL

```
Viernes por la tarde - "María" (Gerente)

17:00 ├─ REPORTES EJECUTIVOS
      ├─ Semana: $3.2M vendidas (+15% vs semana anterior)
      ├─ Margen: 62% (↓ 2% por promoción de croissants)
      ├─ Ocupación mesas: 78% promedio (↑ 8%)
      └─ Satisfacción cliente: 4.6/5 estrellas

17:15 ├─ ANÁLISIS DE PERSONAL
      ├─ Mejor mesero: Carlos ($8.9k comisión)
      ├─ Asistencia: 98.2% (excelente!)
      ├─ Retardos: 3 personas con alertas
      └─ Nómina próxima: $95k (dentro de presupuesto)

17:30 ├─ PREDICCIONES
      ├─ ML predice: "Sábado: +25% demanda por clima"
      ├─ Recomendación: "Prepara 50 cappuccinos extra"
      ├─ Stock: Suficiente (sin urgencias)
      └─ Riesgo: Baja en productos gourmet

17:45 ├─ DECISIÓN
      ├─ Autoriza: Contratación de 1 mesero temporal
      ├─ Aprueba: Promoción croissants fin de semana
      ├─ Requiere: Auditoría de merma en cocina
      └─ Genera: Orden de compra automática

18:00 ├─ EMAIL AUTOMÁTICO
      ├─ Resumen ejecutivo enviado a CEO
      ├─ Datos: Ingresos, márgenes, KPIs
      ├─ Alertas: 2 items requieren acción
      └─ Pronostico: Fin de mes proyectado $9.8M
```

---

## 📱 MOCKUPS CONCEPTUALES DESCRITOS

### Dashboard Principal (Versión Premium Actual)

```
┌──────────────────────────────────────────────────────────────┐
│  CAFBARDLA                 14:32    [👤 Juan]  [⚙️]  [🔔]    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Bienvenido, Juan                                            │
│  Hoy está siendo un excelente día para el negocio ☀️         │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ HOY                                                     │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │                                                        │ │
│  │  📊 $580,000        📈 +18% vs ayer                   │ │
│  │  Ingresos           Variación                         │ │
│  │                                                        │ │
│  │  🛒 125 transacciones    💰 $4,640 promedio ticket    │ │
│  │                                                        │ │
│  │  ⚙️ Gastos: $120,000    📈 Margen: 62%               │ │
│  │                                                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ GRÁFICOS                                                │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │                                                        │ │
│  │  [Línea: Ventas por hora]  [Pastel: Por categoría]   │ │
│  │  +500k ▂▃▅▆█▇▅▃▂           ▓ Bebidas: 45%             │ │
│  │  +400k ▂▃▅▆█▇▅▃▂           ▓ Comidas: 35%             │ │
│  │  +300k ▂▃▅▆█▇▅▃▂           ▓ Postres: 20%             │ │
│  │        09h 12h 15h 18h                                  │ │
│  │                                                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  [🔍 Ver más] [📥 Descargar reporte] [⚙️ Configurar]       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Módulo POS (Interfaz Tablet)

```
┌─────────────────────────────────────────────┐
│ MESA 5 │ 14:32 │ Juan       [Menu▼]        │
├─────────────────────────────────────────────┤
│                                             │
│ [🔍 Buscar producto]                        │
│                                             │
│ CARRITO (60%)      │ PRODUCTOS (40%)        │
│                    │                        │
│ [×] Capuchino      │ [BEBIDAS] [COMIDAS]   │
│     2 × $8.5k      │ Capuchino    $8.5k    │
│                    │ Latte        $9.0k    │
│ [×] Croissant      │ Americano    $7.5k    │
│     1 × $7.0k      │                        │
│                    │ [COMIDAS]              │
│ Notas: Sin azúcar  │ Croissant    $7.0k    │
│                    │ Sándwich    $12.0k    │
│ ─────────────────┼─────────────────────────│
│ Subtotal: $24.0k  │ [+ Agregar otro]      │
│ Impuesto: +$1.9k  │ [🔄 Limpiar carrito]  │
│ TOTAL:    $25.9k  │                        │
│                    │                        │
│ [💳 Cobrar]        │                        │
│ [⏸ Espera]         │                        │
│ [❌ Cancelar]      │                        │
│                    │                        │
└─────────────────────────────────────────────┘
```

### Sistema de Órdenes Producción (KDS)

```
┌──────────────────────────────────────────────┐
│ COCINA - 14:45 | [Carlos] [Configurar]      │
├──────────────────────────────────────────────┤
│                                              │
│ [PENDIENTES] [EN PREP] [LISTOS]             │
│                                              │
│ ┌──────────────┐  ┌──────────────┐          │
│ │ Capuchino    │  │ Latte        │          │
│ │ Mesa 5       │  │ Mesa 3       │          │
│ │ 14:32 ⏱ 2'  │  │ 14:35 ⏱ 5'  │          │
│ │ Sin azúcar   │  │ Extra shot   │          │
│ │ Frío         │  │              │          │
│ │ [▶ INICIAR]  │  │ [✅ LISTO]   │          │
│ └──────────────┘  └──────────────┘          │
│                                              │
│ ┌──────────────┐                            │
│ │ Sándwich     │                            │
│ │ Mesa 7       │                            │
│ │ 14:38 ⏱ 15' │                            │
│ │ Con queso +1 │                            │
│ │ [▶ INICIAR]  │                            │
│ └──────────────┘                            │
│                                              │
│ Totales: 3 pend | 2 prep | 1 listo        │
│                                              │
└──────────────────────────────────────────────┘
```

### Reporte de Nómina

```
┌────────────────────────────────────────────────────┐
│ NÓMINA - JULIO 2026                               │
├────────────────────────────────────────────────────┤
│                                                    │
│ TOTAL A PAGAR: $285,400                           │
│                                                    │
│ ┌──────────────────────────────────────────────┐  │
│ │ Empleado    │ Salario │ Comis. │ Desc. │ Neto │ │
│ ├──────────────────────────────────────────────┤  │
│ │ Carlos      │ $75,000 │ $8,500 │ $6,650 │ $76,850 │
│ │ Juan        │ $70,000 │ $4,200 │ $5,920 │ $68,280 │
│ │ María       │ $65,000 │ $5,100 │ $5,610 │ $64,490 │
│ │ Laura       │ $60,000 │ $3,800 │ $5,280 │ $58,520 │
│ │ José        │ $75,000 │ $6,900 │ $6,910 │ $74,990 │
│ └──────────────────────────────────────────────┘  │
│                                                    │
│ RESUMEN:                                          │
│ Salarios:      $345,000                           │
│ Comisiones:    +$28,500                           │
│ Descuentos:    -$30,100 (AFILIACIÓN, EPS)        │
│ ═══════════════════════════════════               │
│ NETO A PAGAR:  $343,400                           │
│                                                    │
│ [📥 Descargar Excel] [🖨 Imprimir] [✅ Autorizar]│
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 📋 DEFINICIÓN DE ÉXITO FINAL

El proyecto se considera **COMPLETADO Y EXITOSO** cuando:

### Criterios Técnicos ✅
- [ ] Todas 5 fases implementadas y testeadas
- [ ] Test coverage > 80%
- [ ] Performance: API < 200ms (p95)
- [ ] Uptime > 99.5% en producción
- [ ] Zero critical security issues

### Criterios Funcionales ✅
- [ ] POS genera facturas sin errores (100 transacciones/día)
- [ ] Inventario consistency > 99.9%
- [ ] Nómina calcula correctamente (auditoría manual = sistema)
- [ ] Reportes exactitud > 95%
- [ ] Notificaciones real-time < 100ms latency

### Criterios de Negocio ✅
- [ ] ROI demostrable (sistema paga en 6 meses)
- [ ] Adopción > 90% del equipo
- [ ] NPS > 50 (usuarios satisfechos)
- [ ] Reducción de errores > 80%
- [ ] Incremento de eficiencia operativa > 30%

### Criterios de Documentación ✅
- [ ] README completo con instrucciones setup
- [ ] OpenAPI/Swagger documentado 100%
- [ ] Guías de usuario por módulo
- [ ] Procedimientos operacionales (manual)
- [ ] Guía de troubleshooting

---

## 🚀 SIGUIENTES PASOS

### Semana 0 (Pre-desarrollo)
1. Aprobación de este PRD
2. Setup de repositorio (Git) y CI/CD
3. Configuración de ambiente (BD, testing, staging)
4. Onboarding del equipo

### Semana 1-2 (FASE 1 - CORE)
- Comenzar con **POS Premium** (prioridad máxima)
- Implementar esquema validaciones Pydantic
- Setup de tests e integración continua

### Seguimiento Bi-semanal
- Sprint reviews con stakeholders
- Demos de funcionalidades terminadas
- Ajustes basados en feedback

---

**Fin del PRD Maestro Estratégico**

*Documento preparado para implementación profesional de 400 horas en 10 semanas*
*Todos los tiempos incluyen desarrollo, testing y documentación*
*Sujeto a cambios basados en feedback ejecutivo*
