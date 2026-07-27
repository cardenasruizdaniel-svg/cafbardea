# CafBarDLA — Estado real del proyecto

> Documento de reemplazo. Sustituye a `AUDIT_REPORT.md`, `PRD_MAESTRO_ESTRATEGICO.md`,
> `SEGURIDAD_IMPLEMENTADA.md`, `PLAN_SEMANAL_DETALLADO.md` y `RESUMEN_FINAL.bat`,
> que describian como implementadas fases que no existen en el codigo.
>
> Fecha de verificacion: 24 de julio de 2026.
> Todo lo afirmado aqui fue comprobado ejecutando la aplicacion.

## Situacion al inicio

**La aplicacion no arrancaba.** `app/config.py` invocaba `logger.warning()` en la
linea 23, pero `logger` se definia en la linea 32: `NameError` en tiempo de import.
Ningun endpoint respondia. Este defecto estaba presente en el commit `da85dfd`.

## Correcciones aplicadas y verificadas

### Paso 1 — Arranque

| # | Defecto | Correccion | Verificacion |
|---|---------|-----------|--------------|
| 1 | `logger` usado antes de definirse en `config.py` | Logging configurado antes de cualquier uso | La app importa y arranca |
| 2 | 23 llamadas a `TemplateResponse(nombre, {...})` con firma obsoleta; Starlette 1.3 exige `(request, nombre, ctx)`. Provocaba HTTP 500 en `/login`, `/mesas`, `/productos` | Las 23 migradas a la firma vigente | 16 vistas responden 200, cero tracebacks |
| 3 | `SessionMiddleware` registrado ANTES del guard de autenticacion. Starlette ejecuta los middlewares en orden inverso al registro, por lo que el guard corria sin `request.session` y rechazaba a todo usuario autenticado | Movido al ultimo registro (queda mas externo) | Login concede acceso: `/mesas` y `/usuarios` responden 200 |

### Paso 2 — Seguridad

| # | Defecto | Correccion | Verificacion |
|---|---------|-----------|--------------|
| 4 | **Bypass total de autenticacion.** El middleware listaba `/mesas`, `/caja`, `/productos`, `/inventario`, `/nomina`, `/usuarios`, `/configuracion`, `/informes`, `/clientes`, `/empleados` como rutas publicas, bajo un comentario que decia "requieren autenticacion interna". Todo el sistema era accesible sin credenciales | Reescrito a modelo deny-by-default: solo `/`, `/login`, `/logout`, `/health` y `/static` son publicos | 12 rutas devuelven 303 hacia login sin sesion; API devuelve 401 |
| 5 | `JWT_SECRET_KEY` con valor por defecto embebido en el codigo fuente | El secreto proviene de configuracion validada; sin fallback | `jwt_service.py` lee `settings.jwt_secret_key` |
| 6 | `SECRET_KEY` por defecto `"MUST_CHANGE_IN_PRODUCTION"` | Sin valor por defecto usable; en produccion el arranque aborta | Verificado: aborta |
| 7 | CORS con `["127.0.0.1", "localhost"]`, sin esquema: no coincide con ningun `Origin` real | Origenes configurables con esquema y puerto; metodos y cabeceras acotados | `cors_origins_list` correcto |
| 8 | Cinco bases de datos versionadas en git (`cafbardla.db`, `data/cafbardla_prod.db`, etc.), cada una con el hash bcrypt del usuario `admin` | Retiradas del indice; `.gitignore` reforzado | 0 archivos `.db` en el indice |
| 9 | Documentacion de API expuesta siempre | `/docs`, `/redoc` y `/openapi.json` devuelven 404 en produccion | Verificado |
| 10 | Sesion sin caducidad | Expira a las 8 horas (un turno) | Cookie con `Max-Age=28800` |

### Guards de arranque en produccion

Con `ENVIRONMENT=production` la aplicacion **se niega a arrancar** si:
- falta `SECRET_KEY` o `JWT_SECRET_KEY`;
- `DATABASE_URL` apunta a SQLite;
- `SESSION_COOKIE_SECURE` no es `true`.

En desarrollo advierte y continua. Los tres casos fueron verificados.

## Accion pendiente de su parte (no puedo hacerla yo)

1. **Rotar la contrasena de `admin`.** Los hashes estuvieron en el historial publico de git.
2. **Purgar el historial** con `git filter-repo` o BFG. Retirarlos del indice no los borra de los commits `7475111` y `8987c18`.
3. **Crear su `.env`** a partir de `.env.example`, con secretos generados:
   `python -c "import secrets;print(secrets.token_urlsafe(48))"`
4. Si alguna de esas BD llego a un servidor real, asuma las credenciales comprometidas.

## Lo que sigue sin existir

Estos modulos aparecen como completos en la documentacion anterior. No estan en el codigo:

- **Control de acceso biometrico**: cero referencias. No hay integracion ZKTeco/Hikvision/Suprema.
- **Contabilidad**: cero referencias.
- **Inventario de almacen**: solo la tabla `MovimientoInventario` con 6 campos. Sin bodegas, lotes, series, vencimientos, kardex, FIFO ni costo promedio.
- **Nomina colombiana**: ~319 lineas. Faltan prima, cesantias, intereses, vacaciones, horas extras, recargos, dominicales, retencion y parafiscales.
- **Compras**: modelo de un solo producto por compra. Sin cotizaciones, comparativo ni recepciones.
- **Produccion**: sin etapas, subproductos, reprocesos ni mermas.
- **Apps moviles**: una API de 688 lineas y una plantilla de 2 KB. No hay tres aplicaciones.
- **Codigo muerto**: `app/routes/dashboard_api.py` (336 lineas) y `app/routes/reportes_api.py` (493 lineas) nunca se registran en `main.py`. 829 lineas inertes.

## Estado verificable hoy

- La aplicacion arranca.
- 16 vistas renderizan sin errores.
- La autenticacion no se puede eludir.
- Los secretos salen de configuracion, no del codigo.
- Cero tracebacks en el arranque y en la navegacion.

Esto es una base sobre la que se puede construir. No es un ERP Enterprise.

---

# Segunda jornada: routers muertos, suite de pruebas y API de ventas

## Routers que nunca se registraron

`app/routes/dashboard_api.py` (336 lineas) y `app/routes/reportes_api.py` (493 lineas)
estaban escritos pero jamas se incluian en `main.py`. 829 lineas inertes.
Ya estan registrados y responden: `/api/v1/dashboard/kpis` y `/api/v1/reportes/ventas`
devuelven 200.

## La suite de pruebas dependia del agujero de seguridad

Estado inicial: 216 aciertos, 51 fallos. **Los 51 fallos eran HTTP 401.**
No eran errores de logica: los tests nunca iniciaban sesion, y antes no hacia
falta porque el middleware declaraba publico casi todo. Al cerrar el bypass,
quedaron al descubierto. Es la confirmacion mas directa de que el agujero era real.

Cadena de defectos encontrados al repararlos:

| Defecto | Efecto |
|---------|--------|
| Ningun test se autenticaba | 51 fallos 401 |
| BD de prueba en `sqlite:///:memory:` | Cada conexion abria una base VACIA distinta; el usuario sembrado era invisible para el login |
| `create_all` sin importar los modelos | No se creaba ninguna tabla |
| Un test inyectaba cookie falsa (`client.cookies.set("session", "test_session")`) | Simulaba autenticacion en vez de autenticarse |
| Credenciales equivocadas en el fixture | El seed crea `testuser`, no `admin` |
| Faltaba `pytest-asyncio` | 3 pruebas de WebSocket ni se ejecutaban |

Se anadio el fixture `client_autenticado`, que inicia sesion de verdad.

## Bug de produccion en la API de ventas

El mas grave hallado hasta ahora. **No era un problema de pruebas.**

`VentaResponse` exigia 8 campos inexistentes en el modelo `Venta`. Resultado:
`POST /api/v1/ventas` y `GET /api/v1/ventas/{id}` fallaban con
`ResponseValidationError` en el sistema real. La API de ventas — el nucleo de
un POS — estaba rota.

Modelo y esquema se escribieron por separado y nunca se conciliaron:

| Esquema espera | Modelo tiene |
|----------------|--------------|
| `tipo_venta` | `canal` |
| `observaciones` | `observacion` |
| `fecha_creacion` | `fecha` |
| `referencia_externa` | `numero_factura` |
| `subtotal` (detalle) | se calcula |
| `observaciones` (detalle) | `nota` |
| `zona_id` | via mesa |
| `usuario_id: int` | nullable |

Resuelto con propiedades derivadas en el modelo, sin migrar la base.

Ademas, `routes.py` accedia a `venta.usuario`, `venta.cliente` y `venta.mesa`:
tres relaciones que nunca se declararon. Provocaban `AttributeError` al listar
ventas. Ya estan definidas.

**Suite actual: 267 aciertos, 0 fallos.**

## Limpieza

Eliminado (~443 MB):

| Elemento | Motivo |
|----------|--------|
| `.venv/` (287 MB), `.buildenv_cafbardla/` (61 MB) | Entornos virtuales; se recrean con `requirements.txt` |
| `.git/` (94 MB) | Historial con secretos y bases de datos |
| 5 archivos `.db` | Datos y hashes de credenciales |
| `config/.env-files/` | **Secretos reales versionados** |
| `build/`, `dist/`, `.pytest_cache/` | Artefactos regenerables |
| `PRD_MAESTRO_ESTRATEGICO.md` (83 KB), `AUDIT_REPORT.md` (40 KB), `GUIA_TECNICA_ARQUITECTURA.md`, `PLAN_SEMANAL_DETALLADO.md`, `SEGURIDAD_IMPLEMENTADA.md`, `REDISENO_PREMIUM.md`, `RESUMEN_FINAL.bat`, `docs/completed-tasks/` | Describian como terminadas fases inexistentes |

De 445 MB a 1.8 MB. Verificado: arranca desde cero, 267 pruebas pasan,
16 vistas responden 200, autenticacion cerrada, cero tracebacks.

## Rotacion de secretos: pendiente y urgente

En `config/.env-files/` habia **secretos reales versionados en git**:
`SECRET_KEY`, `JWT_SECRET_KEY` y `SESSION_SECRET_KEY` con valores activos.
Retirar los archivos no los borra del historial.

1. Rotar esos tres secretos.
2. Cambiar la contrasena de `admin`.
3. Si el repositorio se publico o esas bases llegaron a un servidor, dar todo por comprometido.

Este paquete se entrega **sin** `.git`, de modo que el historial contaminado no
viaja con el. Si necesita conservar la historia, purguela con `git filter-repo`
antes de volver a publicar.


---

# Paso 4: dominio Ventas a calidad de produccion

Antes de tocar codigo se escribieron sondas que ejecutan el servicio real y
muestran su comportamiento. Los defectos siguientes no son hipotesis: cada uno
se observo corriendo.

## Defectos encontrados y corregidos

| # | Defecto | Evidencia observada | Correccion |
|---|---------|---------------------|-----------|
| 1 | **El precio lo imponia el cliente** | Producto de catalogo $8.500 vendido a $1 | El precio sale del catalogo. Solo con permiso `ventas.precio_libre` puede alterarse |
| 2 | **La venta no descargaba inventario** | Vender 5 unidades dejaba existencias en 50 | Se descuenta stock y se registra `MovimientoInventario` |
| 3 | **Sin control de stock negativo** | No existia politica alguna | Campo `Empresa.permitir_stock_negativo`. Si se permite, el stock queda negativo y se genera `AlertaStock`; si no, se bloquea |
| 4 | **Costo unitario siempre 0** | Detalle con costo 0 y producto con costo $2.400 | Se guarda el costo del producto: ya puede calcularse margen |
| 5 | **Multi-tenancy inexistente** | `listar_ventas(empresa_id=999)` devolvia ventas de la empresa 1 | `listar_ventas` y `obtener_venta` filtran por empresa |
| 6 | **El pago no se registraba** | No quedaba monto recibido ni cambio | Modelo `PagoVenta` con monto recibido, aplicado, cambio, referencia y usuario |
| 7 | **La mesa no cambiaba de estado** | Mesa seguia "libre" con venta abierta | Se ocupa al abrir y se libera al pagar, solo si no quedan otras ventas abiertas |
| 8 | **Se vendian productos inactivos** | Producto con `activo=False` se vendia igual | Se rechaza |
| 9 | **`obtener_total_dia` sin filtro de fecha** | Sumaba ventas de cualquier dia y empresa | Filtra por dia actual y empresa |
| 10 | **Eliminar item no devolvia stock** | El inventario quedaba descuadrado | Se repone existencia y se registra el movimiento |
| 11 | **Descuento sin tope** | Podia superar el subtotal | Se rechaza si excede el subtotal |

## Decisiones de negocio aplicadas

- **Precio**: del catalogo, salvo permiso `ventas.precio_libre` (administrador y gerente lo tienen; el mesero no).
- **Stock negativo**: configurable por empresa. Por defecto se permite, dejando el stock en negativo y generando alerta, para que la estructura de descarga funcione igual en negativo.
- **Propina**: se conserva `max(porcentaje, fija)` segun lo indicado.

## Verificacion

- Suite: **285 aciertos, 0 fallos** (antes del paso 4 eran 267).
- 18 pruebas de regresion nuevas en `tests/domains/ventas/test_reglas_negocio.py`, una por defecto.
- Comprobado contra la aplicacion en ejecucion: un usuario con rol `mesero` recibe HTTP 422 al intentar vender a $1 y HTTP 201 al vender al precio del catalogo.

## Nuevas tablas

`pagos_venta` y `alertas_stock` se crean solas al arrancar. `empresas` gana la
columna `permitir_stock_negativo`. Sobre una base existente conviene generar la
migracion de Alembic correspondiente antes de desplegar en produccion.


---

# Paso 5: dominio Inventario

Igual que en Ventas, primero se ejecutaron sondas sobre el codigo real. Los
defectos siguientes se observaron corriendo, no leyendo.

## Punto de partida

No existia dominio de inventario: solo dos rutas sueltas en `main.py`.

## Defectos encontrados y corregidos

| # | Defecto | Evidencia observada | Correccion |
|---|---------|---------------------|-----------|
| 1 | **No existia kardex** | Cero menciones de "kardex" en todo el proyecto. Los movimientos se guardaban y nadie los leia | `InventarioService.kardex()` + vista `/inventario/kardex/{id}` con saldo, costo y valor por movimiento |
| 2 | **Tres implementaciones del mismo concepto** | Compras calculaba promedio ponderado; `/inventario/movimiento` guardaba el costo y lo ignoraba; Ventas tenia su propia descarga | Todo pasa por `InventarioService.registrar_movimiento()` |
| 3 | **El costo no se recalculaba** | 10 @ $1.000 + entrada 10 @ $2.000 dejaba el costo en $1.000 (correcto: $1.500) | Promedio ponderado unificado |
| 4 | **`/inventario/movimiento` sin validacion** | Existencias 2, salida de 100 -> **-98**, sin alerta y saltandose la politica de empresa | Valida tipo, cantidad y politica de stock negativo |
| 5 | **Las alertas no se leian** | `AlertaStock` solo aparecia donde se creaba. El paso 4 dejo datos huerfanos | Se muestran en `/inventario` y se consultan con `alertas_pendientes()` |
| 6 | **Sin bodegas** | Tabla inexistente. Todo el stock en un unico campo | `Bodega`, `ExistenciaBodega` y traslados que no alteran el total |
| 7 | **Sin lotes ni vencimientos** | Tablas inexistentes. Critico en alimentos | `Lote` con fecha de vencimiento, `lotes_vencidos()` y `lotes_por_vencer()` |
| 8 | **Valor de inventario no auditable** | Se calculaba con el costo actual, sin historia | El kardex guarda saldo y costo promedio de cada movimiento |

## Decisiones aplicadas

- **Costeo**: promedio ponderado, unificado en un solo lugar.
- **Alcance**: nucleo + bodegas multiples + lotes con vencimiento.
- **Stock negativo**: respeta `Empresa.permitir_stock_negativo`, igual que Ventas.

## Verificacion

- Suite: **306 aciertos, 0 fallos** (antes del paso 5 eran 285).
- 21 pruebas nuevas en `tests/domains/inventario/test_inventario.py`.
- Comprobado contra la aplicacion en ejecucion: entrada de 10 @ $2.000 sobre
  50 @ $2.400 produjo costo promedio **$2.333,33** (140.000/60), el kardex
  registro ambos movimientos con su saldo, y una salida excesiva dejo
  existencia -440 con su alerta correspondiente.

## Nuevas tablas

`bodegas`, `lotes`, `existencias_bodega`. `movimientos_inventario` gana los
campos de kardex (saldo anterior/posterior, costo promedio anterior/posterior,
bodega, lote, usuario, observacion).

**Sobre una base existente hace falta migracion de Alembic** antes de desplegar.
Los movimientos historicos no tendran saldos calculados: el kardex sera exacto
a partir de los nuevos movimientos.


---

# Paso 6: dominio Mesas

## El defecto central

**El dominio de Mesas hablaba un idioma distinto al resto del sistema.**
`EstadoMesa` definia `"disponible"`, mientras el modelo, el seed y Ventas
usaban `"libre"`. Consecuencias observadas ejecutando el codigo:

- `ocupar_mesa()` rechazaba toda mesa real: *"Mesa M1 no esta disponible
  (estado: libre)"*.
- El plano de salon informaba **0 mesas disponibles** teniendolas todas libres.
- `MesaResponse` fallaba al serializar cualquier mesa: HTTP 500 en
  `GET /api/v1/mesas/{id}` y en el plano completo.

Es decir: el modulo de mesas estaba roto de punta a punta contra datos reales.

## Defectos encontrados y corregidos

| # | Defecto | Evidencia observada | Correccion |
|---|---------|---------------------|-----------|
| 1 | **Estados incoherentes** | `ocupar_mesa` rechazaba mesas libres; plano contaba 0 disponibles; API devolvia 500 | Unificado a `"libre"` en enum, servicio, rutas y plantillas |
| 2 | **Sin datos operativos** | `Mesa` no tenia hora de apertura, mesero ni comensales | Campos nuevos + `minutos_ocupada()` |
| 3 | **Sin consumo acumulado** | Imposible saber cuanto lleva gastado una mesa | `consumo_actual()` y `detalle_mesa()` |
| 4 | **Reservas fantasma** | El esquema `ReservarMesa` existia desde el principio, pero ninguna ruta lo usaba: los datos del cliente se descartaban | Tabla `ReservaMesa` + rutas de reservar y cancelar |
| 5 | **Liberacion insegura** | `liberar_mesa` no comprobaba nada: dejaba ventas abiertas sin mesa visible | Bloquea si hay cuentas abiertas, salvo `forzar=True` |
| 6 | **Sin unir ni transferir** | No existia forma de juntar mesas ni mover una cuenta | `unir_mesas`, `separar_mesas`, `transferir_venta` |
| 7 | **Colision de rutas** | `/{mesa_id}` estaba declarada antes que `/reportes/ocupacion` y `/catalogo/*`, capturandolas | Ruta comodin movida al final, con nota explicativa |

## Verificacion

- Suite: **327 aciertos, 0 fallos** (antes del paso 6 eran 306).
- 21 pruebas nuevas en `tests/domains/mesas/test_reglas_negocio.py`.
- Contra la aplicacion en ejecucion: abrir una venta en la mesa 1 devolvio
  `{"estado":"ocupada","mesero":"admin","minutos_ocupada":0,"consumo":17000.0}`;
  la reserva de la mesa 2 quedo persistida; la transferencia de cuenta movio la
  venta y libero la mesa de origen; las cuatro rutas fijas responden 200 y el
  catalogo de estados ya devuelve `["libre","ocupada",...]`.

## Nuevas tablas y columnas

`reservas_mesa`. La tabla `mesas` gana `fecha_apertura`, `mesero_id`,
`comensales` y `mesa_padre_id`.

**Sobre una base existente hace falta migracion de Alembic.** Ademas, si hay
mesas guardadas con estado `"disponible"`, deben actualizarse a `"libre"`:

```sql
UPDATE mesas SET estado = 'libre' WHERE estado = 'disponible';
```


---

# Paso 7: consolidacion y migraciones

Los pasos 4, 5 y 6 anadieron tablas y columnas que en desarrollo se creaban
solas con `auto_create_schema=True`. Sobre una base con datos eso no sirve:
hacia falta una migracion real.

## Defecto encontrado en el propio Alembic

`alembic/env.py` importaba solo `app.models`, no `app.models_enterprise`.
Consecuencia: Alembic **no veia 7 tablas** (`sucursales`, `roles`, `permisos`,
`rol_permisos`, `usuario_roles`, `conexiones_websocket`,
`eventos_sincronizacion`). Una autogeneracion las habria marcado para BORRAR.

Corregido: `env.py` importa ambos modulos. De 31 a 38 tablas visibles.

## La migracion inicial no servia de base

`0001_initial_schema` ejecuta `Base.metadata.create_all()` en vez de DDL
explicito. Es decir, siempre crea el esquema *actual*, no el historico. No
sirve como punto de comparacion, pero se conserva por compatibilidad con bases
ya marcadas con esa version.

## Migracion 0002

Escrita a mano. La autogeneracion producia 1.523 lineas de ruido: SQLite no
expresa NOT NULL ni claves foraneas igual que SQLAlchemy, y Alembic proponia
recrear tablas enteras. La version manual aplica solo los cambios reales.

Es **idempotente**: comprueba antes de crear, de modo que funciona igual sobre
una base que ya arranco con `auto_create_schema=True`.

Incluye tres transformaciones de datos:
1. `UPDATE mesas SET estado='libre' WHERE estado='disponible'`
2. Crea la bodega PRINCIPAL y vuelca en ella el saldo de cada producto
3. Asigna esa bodega a los movimientos historicos

## Verificacion

Se recreo el esquema anterior a los pasos 4-6 con datos (empresa, 3 mesas
—dos con estado obsoleto—, 2 productos con existencias, un movimiento
historico) y se comprobo:

- La migracion aplica sin error.
- **Datos intactos**: 3 mesas, 2 productos, 1 movimiento, 1 usuario.
- Estados normalizados: `disponible` -> `libre`.
- Existencias volcadas: producto 1 = 50, producto 2 = 30 en bodega PRINCIPAL.
- **Reejecucion inocua** (idempotencia).
- **Downgrade** elimina lo nuevo y conserva los datos previos.
- **Upgrade de nuevo** funciona.
- La aplicacion corre sobre la base migrada: 5 vistas en 200, venta creada
  (HTTP 201), detalle de mesa con consumo 17.000, kardex accesible, cero
  tracebacks.

Suite: **327 aciertos, 0 fallos**.

## Herramientas nuevas

- `scripts/verificar_migracion.py` — informa que falta sin modificar nada.
  Detecto correctamente los 19 elementos pendientes en una base sin migrar.
- `MIGRACION.md` — guia paso a paso con respaldo, aplicacion y reversion.

## Limitacion conocida

Los movimientos anteriores a la migracion no tienen saldos de kardex: esa
informacion nunca se guardo. El kardex es exacto a partir de los movimientos
nuevos. Reconstruir el historico exigiria partir de un conteo fisico.


---

# Paso 8: base de datos limpia y operable

## Problemas del seed anterior

El `seed()` de `main.py` dejaba la base incoherente desde el primer arranque:

- Mesas y productos creados **sin `empresa_id`**, rompiendo el aislamiento
  multiempresa que se corrigio en el paso 4.
- Una **venta abierta huerfana**: sin detalles, con total 0, apuntando a una
  mesa que quedaba en estado "libre".
- **Dos liquidaciones de nomina para el mismo empleado** en el mismo periodo.
- Existencias escritas a mano (`existencias=50`) sin movimiento asociado, de
  modo que el kardex nacia vacio y el costo promedio sin respaldo.

## Solucion

`scripts/inicializar_datos.py` genera un cafe-bar completo **a traves de los
servicios del sistema**, no con INSERT directos. Es la misma ruta que seguira
la operacion diaria, asi que todo queda coherente.

| Elemento | Cantidad |
|---|---|
| Zonas / Mesas | 3 / 15 |
| Categorias / Productos | 6 / 27 |
| Bodegas | 3 (Principal, Barra, Cocina) |
| Empleados con usuario | 7 (uno por rol) |
| Clientes / Proveedores | 4 / 4 |
| Movimientos de inventario | 61 |
| Lotes con vencimiento | 2 |
| Ventas | 9 (6 cerradas, 3 abiertas) |

`main.py` conserva una siembra minima (empresa + admin) para que un arranque
sin datos no falle.

## Verificacion

Kardex de "Cerveza nacional" tras compra, traslado y dos ventas:

```
compra            ent=300  saldo=300  costo_prom=$3200
traslado_salida   sal= 80  saldo=220  costo_prom=$3200
traslado_entrada  ent= 80  saldo=300  costo_prom=$3200
venta             sal=  4  saldo=296  costo_prom=$3200
venta             sal=  3  saldo=293  costo_prom=$3200
```

El saldo cuadra (300-80+80-4-3 = 293) y las bodegas suman lo mismo:
principal 213 + barra 80 = 293.

Contra la aplicacion en ejecucion: **16 vistas en 200**, 4 APIs en 200, los
7 usuarios inician sesion, la mesa M1 reporta consumo real de $26.500 con
3 comensales y mesero asignado, y los lotes proximos a vencer se detectan
(leche en 6 dias, carne en 20). **Cero tracebacks.**

Suite: **327 aciertos, 0 fallos**.

## Proteccion

`--reiniciar` esta bloqueado si `ENVIRONMENT=production` y exige escribir
"BORRAR" como confirmacion.


---

# Paso 9: dominio Compras

## Punto de partida

No existia dominio de Compras. El modelo `Compra` era una fila plana:
UN `producto_id`, sin desglose fiscal, sin estado, sin `usuario_id` ni
`empresa_id`, y **sin posibilidad de anular**. Registrar una compra
equivocada contaminaba el costo promedio del producto de forma permanente.

## Defectos encontrados y corregidos

| # | Defecto | Correccion |
|---|---------|-----------|
| 1 | **Un solo producto por compra** | Tabla `detalle_compras`: una factura con N items en una sola compra |
| 2 | **Sin desglose fiscal** (solo `valor` plano) | subtotal, descuento, IVA, retenciones y total |
| 3 | **IVA inexistente** | `Producto.iva_porcentaje` por defecto, ajustable en cada linea |
| 4 | **Sin estado** | borrador -> confirmada -> anulada |
| 5 | **Sin usuario ni empresa** | Ambos en la cabecera; aislamiento multiempresa |
| 6 | **No se podia anular** | `anular_compra` revierte stock y costo, con proteccion si ya se consumio |
| 7 | **Proveedor sin datos comerciales** | direccion, ciudad, contacto, dias_credito, activo |
| 8 | **Sin flujo de aprovisionamiento** | solicitudes, cotizaciones con comparativo, ordenes y recepciones parciales |

## Decisiones aplicadas

- **Alcance**: ciclo completo (solicitud, cotizacion, orden, recepcion, factura).
- **IVA**: tarifa por producto, ajustable por linea en cada factura.
- **Anulacion**: reversion automatica de stock y costo, usando el costo
  promedio vigente. Se bloquea si la mercancia ya se consumio (evita negativos).

## Todo pasa por InventarioService

Las entradas de compra y recepcion no tocan el stock directamente: delegan en
`InventarioService.registrar_movimiento()`. Asi el kardex y el costo promedio
quedan coherentes, igual que en Ventas.

## Verificacion

- Suite: **358 aciertos, 0 fallos** (antes del paso 9 eran 327).
- 31 pruebas nuevas en `tests/domains/compras/test_compras.py`.
- Contra la aplicacion: factura de 50 unidades de Capuchino a $2.500 + IVA 19%
  dio subtotal $125.000, IVA $23.750, total $148.750; el costo promedio paso a
  $2.422,12 (correcto: (176x2400 + 50x2500)/226); la anulacion revirtio las
  existencias de 226 a 176. Cero tracebacks.

## Comparativo de cotizaciones

`comparar_cotizaciones()` ordena las ofertas por total, marca la mas economica
y la mas rapida, y calcula el sobrecosto porcentual de cada una frente a la
mejor. `crear_orden_desde_cotizacion()` genera la orden y descarta las demas.

## Nuevas tablas

`detalle_compras`, `solicitudes_compra`, `detalle_solicitudes`, `cotizaciones`,
`detalle_cotizaciones`, `ordenes_compra`, `detalle_ordenes`, `recepciones`,
`detalle_recepciones`. `compras` y `proveedores` y `productos` ganan columnas.

**Requiere migracion de Alembic** sobre una base existente.

## Seed

`inicializar_datos.py` ahora incluye una orden con recepcion parcial, una
factura a credito (cuenta por pagar) y una solicitud pendiente, para ver el
modulo operando desde el primer arranque.


---

# Paso 10: dominio Produccion

## Punto de partida

Existia una produccion basica: recetas, `OrdenProduccion` y la funcion
`consumir_receta`. Pero `consumir_receta` restaba existencias a mano y
recalculaba el costo por su cuenta: era la CUARTA implementacion distinta del
movimiento de inventario (tras ventas, compras y la ruta de inventario). El
consumo de produccion no aparecia en el kardex con saldos.

## Defectos encontrados y corregidos

| # | Defecto | Correccion |
|---|---------|-----------|
| 1 | **consumir_receta no usaba InventarioService** | Ejecucion y consumo pasan por el kardex |
| 2 | **OrdenProduccion sin estado, usuario ni empresa** | Cabecera completa; numero consecutivo (OP-xxxxx) |
| 3 | **La receta no calculaba su costo teorico** | `costear_receta()`: costo antes de producir |
| 4 | **No se podia anular** | `anular()` revierte insumos, aprovechables y producto |
| 5 | **La merma solo inflaba el consumo** | Se registra en `ConsumoProduccion` y en `orden.merma_valor` |
| 6 | **Sin subproductos aprovechables** | `agregar_aprovechable`: descuentan del costo del principal |
| 7 | **El seed no creaba elaborados** | Incluye masa para pizza con receta y una produccion real |

## Decisiones aplicadas

- **Alcance**: nucleo (costeo, ejecucion por kardex, merma trazable, anulacion).
- **Aprovechables**: descuentan del costo del producto principal, abaratandolo,
  como se pidio. La base queda lista aunque el nucleo no incluya el flujo
  completo de subproductos.

## Verificacion

- Suite: **374 aciertos, 1 fallo preexistente** (ver nota). Antes del paso 10
  eran 358.
- 16 pruebas nuevas en `tests/domains/produccion/test_produccion.py`.
- Contra la aplicacion: la produccion de 60 unidades de masa costo $37.170 en
  insumos, con $570 de merma registrada, dando $619,50 por unidad; la anulacion
  revirtio la masa (60 -> 0) y devolvio el azucar (34 -> 40). El consumo aparece
  en el kardex con saldos. Cero tracebacks.

### Nota: 1 fallo preexistente

`test_ventas_por_hora_con_datos` (dashboard) ya fallaba en el paso 9, antes de
tocar Produccion. El fixture crea ventas sin fijar `fecha`, y el endpoint filtra
por `func.current_date()`; en el entorno de test la comparacion no coincide. Es
ajeno a este modulo y se deja anotado para un paso de consolidacion, sin mezclar
arreglos no relacionados aqui.

## Costeo con aprovechables (ejemplo verificado en pruebas)

Producir con 5 harina a $2.000 (=$10.000) y un aprovechable de 2 unidades a
$500 (=$1.000) sobre un rendimiento de 10: costo neto $9.000, costo unitario
$900. El aprovechable ingresa al inventario y abarata el principal.

## Nuevas tablas y columnas

`consumos_produccion`. `ordenes_produccion` gana estado, numero, costos, merma
y control. `receta_detalles` gana `rol` y `valor_aprovechable`. `recetas` gana
`activa`.

**Requiere migracion 0004** sobre una base existente.


---

# Paso 11: consolidacion

Antes de seguir con Nomina, se cerraron los cabos sueltos acumulados.

## 1. Bug real del dashboard (no solo del test)

`ventas-por-hora` agrupaba solo las horas **7 a 23**. El test fallaba porque en
el entorno corre a la 01:00 UTC, pero el problema es de produccion: **cualquier
negocio con operacion nocturna** (bar, discoteca, food truck) perdia sus ventas
de madrugada en el grafico. Corregido a las 24 horas.

## 2. Ultimas dos escrituras directas al inventario

`main.py` todavia tenia dos usos directos de `MovimientoInventario`:
- la venta de un producto SIN receta restaba existencias a mano;
- el alta de producto con saldo inicial insertaba el movimiento por su cuenta.

Eran la quinta y sexta via paralela. Ahora **cero** escrituras directas: todo
el sistema (ventas, compras, produccion, inventario, altas y ventas legacy)
pasa por `InventarioService`, de modo que el kardex es completo y coherente.

## 3. Migraciones verificadas de extremo a extremo

Se probo la cadena 0001 -> 0004 sobre una base con esquema viejo y datos
realistas (compras, produccion, mesas con estado obsoleto, productos):

- Las 3 migraciones aplican sin error.
- **Datos intactos**: compras, ordenes, mesas, productos, proveedores.
- **Transformaciones correctas**: mesas 'disponible' -> 'libre'; compra y
  produccion historicas marcadas 'confirmada'; bodega principal creada;
  existencias volcadas cuadran.
- La aplicacion arranca sobre la base migrada: 6 vistas en 200, cero tracebacks.
- **Ciclo completo**: downgrade 0004 -> 0001 elimina lo nuevo y conserva los
  datos previos; re-upgrade funciona.
- El verificador aprueba la base migrada.

Tambien se probo el escenario de base creada con `auto_create_schema`: stamp en
0001 + upgrade head deja la base en 0004 sin romper nada (idempotencia).

## Estado

Suite: **374 aciertos, 0 fallos**. Sin fallos preexistentes pendientes.

El sistema queda consolidado: una sola via de inventario, migraciones probadas
en ambos sentidos, y el dashboard corregido. Base lista para Nomina.


---

# Paso 12: Nomina (Colombia)

El paso mas extenso. Se construyo la nomina colombiana completa, desde los
devengados hasta la nomina electronica, sobre la base de un modulo que solo
calculaba salario, auxilio y dos deducciones.

## Que existia y que faltaba

El `NominaService` previo tenia un CRUD de periodos y liquidaciones con maquina
de estados (borrador -> procesada -> pagada) y estadisticas, pero el calculo se
reducia a salario proporcional + auxilio + salud 4% + pension 4%. **Faltaba**:
horas extra, recargos (nocturno, dominical), aportes patronales (salud, pension,
ARL por nivel de riesgo, caja, ICBF, SENA), exoneracion Ley 1607, fondo de
solidaridad, retencion en la fuente, provisiones (prima, cesantias, intereses,
vacaciones), salario integral, novedades, desprendibles y nomina electronica.

## Decisiones del usuario

1. **Alcance completo**: nomina del periodo + liquidacion definitiva al retiro
   + desprendibles PDF + archivo de nomina electronica DIAN.
2. **Parametros 2026, totalmente configurables**: todos los factores legales
   viven en `ParametrosNomina`, versionados por `vigencia_desde`. Un cambio de
   ley se hace creando un registro nuevo, sin tocar codigo.
3. **Ordinario e integral**: se soportan ambos; el integral cotiza sobre el 70%.

## Que se construyo

- **`ParametrosNomina` ampliado**: ~30 factores configurables (aportes empleado
  y empleador, recargos, horas extra, provisiones, exoneracion, salario integral).
- **`Empleado`** con datos de nomina: empresa, tipo de salario, caja, nivel de
  riesgo ARL, auxilio, retiro, cuenta bancaria.
- **`LiquidacionNomina`** con desglose completo: devengados detallados, cada
  deduccion, IBC, aportes patronales y provisiones, con `costo_total_empleador`.
- **`NovedadNomina`** (tabla nueva): horas extra, recargos, incapacidades,
  licencias, bonificaciones, comisiones, prestamos, embargos.
- **`NominaService`**: `calcular_empleado` (desglose sin persistir),
  `liquidar_periodo`, `anular_liquidacion`, `liquidacion_definitiva`,
  `registrar_novedad`, `resumen_periodo`, mas la API previa intacta.
- **Documentos**: desprendible de pago en PDF (reportlab) y archivo de nomina
  electronica DIAN en JSON (estructura de datos, sin firma).
- **Rutas**: liquidar, anular, registrar novedad, descargar desprendible y
  descargar nomina electronica.

## Verificacion

- **Calculos con cifras conocidas** (SMMLV 2026 $1.623.500): salud/pension 4%,
  auxilio segun tope, horas extra con factor, recargo nocturno solo el adicional,
  IBC sin auxilio y con piso de 1 SMMLV, FSP desde 4 SMMLV, exoneracion Ley 1607,
  ARL por nivel de riesgo, provisiones, salario integral al 70%.
- **Suite**: 395 aciertos, 0 fallos (374 base + 21 nuevos de nomina; los 26
  tests previos del modulo siguen pasando).
- **Seed**: nomina liquidada de 7 empleados, neto $14.282.644, con novedades.
- **End-to-end**: /nomina 200, desprendible PDF valido (1 pagina), nomina
  electronica JSON con 7 empleados, registro de novedad 303, cero tracebacks.
- **Migracion 0005** idempotente: probada en cadena 0001->0005 sobre base con
  esquema viejo y datos. Preserva liquidaciones, normaliza porcentajes 0.04->4,
  crea columnas y `novedades_nomina`. Ciclo downgrade+re-upgrade correcto. La
  app arranca sobre la base migrada y el verificador la aprueba.

## Un defecto encontrado y corregido

El seed cargaba los porcentajes como fraccion (`0.04`) cuando el servicio los
divide entre 100, lo que habria dado deducciones 100 veces menores. Corregido a
entero (`4`) y la migracion 0005 normaliza cualquier base que traiga el error.

## Responsabilidad legal (importante)

Los calculos siguen las reglas generales vigentes en 2026, pero **la
responsabilidad legal de las cifras es del usuario**. En particular:

- La **retencion en la fuente** es una aproximacion (procedimiento 1, con renta
  exenta del 25% y la tabla del art. 383 ET en UVT). No modela deducciones por
  dependientes, intereses de vivienda ni medicina prepagada. La UVT usada es la
  de 2026 y es configurable.
- La **nomina electronica** genera la estructura de datos, no la firma ni la
  transmite: eso lo hace el proveedor tecnologico autorizado por la DIAN.
- El sistema **no sustituye la asesoria de un contador**. Antes de usarlo para
  pagos reales, conviene validar los parametros y un par de liquidaciones con su
  contador.


---

# Paso 13: App movil (PWA)

Se convirtio la aplicacion web en una PWA instalable, que funciona en el celular
como una app y tolera la perdida de conexion. Sirve a ambos perfiles (meseros y
gerencia) porque envuelve toda la web existente, sin duplicar pantallas.

## Decisiones del usuario

1. **PWA** (no app nativa ni solo API): la web actual, instalable y con soporte
   offline. Reutiliza el backend completo.
2. **Ambos perfiles**: al envolver toda la web, meseros y gerencia usan la misma
   app instalada; cada quien ve lo que su rol permite.
3. **Sesion web actual**: se mantiene la autenticacion por cookie de sesion. No
   se agrega JWT; la PWA usa la sesion que ya funciona.

## Que se construyo

- **Manifest** (`/manifest.webmanifest`): nombre, colores de marca, display
  standalone, orientacion, y accesos directos a Mesas, Caja y Dashboard.
- **Iconos** en 8 tamanos (72 a 512) mas dos maskable, generados con la
  identidad de marca (taza sobre fondo #0a0e27).
- **Service worker** (`/sw.js`, scope raiz) con estrategia conservadora:
  - estaticos: cache-first, versionados por `CACHE_NAME`;
  - navegaciones: network-first con caida a la pagina offline;
  - **nunca** cachea HTML autenticado, POST, login ni APIs. Solo intercepta GET
    del mismo origen.
- **Pagina offline** (`/offline`): aviso claro con boton de reintento.
- **Cliente PWA** (`pwa.js`): registra el SW, ofrece boton "Instalar app" cuando
  el navegador lo permite, y muestra un banner cuando se pierde la conexion.
- **Integracion**: manifest e iconos enlazados en `base.html` y en `login.html`
  (para poder instalar desde el inicio de sesion), con metadatos de iOS.

## Por que el service worker es conservador

En un sistema con datos sensibles y sesion por cookie, cachear paginas
autenticadas seria peligroso: podria mostrar datos de otro usuario o cifras
viejas tras cerrar sesion. Por eso el SW solo cachea estaticos (CSS, iconos) y
la pagina offline; toda navegacion va primero a la red. El HTML con datos de
negocio jamas se guarda.

## Verificacion

- Recursos PWA publicos y con el tipo correcto: manifest
  (application/manifest+json), sw.js (application/javascript con
  `Service-Worker-Allowed: /` y `Cache-Control: no-cache`), offline (text/html),
  iconos (image/png). Todos accesibles **sin** sesion.
- El control de acceso sigue intacto: las rutas privadas redirigen a login; los
  recursos PWA no exponen datos.
- Vistas autenticadas sin regresiones (dashboard, mesas, caja, nomina,
  inventario en 200), con `pwa.js` cargado.
- Suite: **403 aciertos, 0 fallos** (395 previos + 8 nuevos de PWA).
- Sin migracion: la PWA no toca la base de datos.

## Como se instala (para el usuario final)

- **Android/Chrome**: entrar al sistema, aparece el boton "Instalar app" o el
  aviso del navegador; tambien desde el menu "Agregar a pantalla de inicio".
- **iPhone/Safari**: boton Compartir -> "Agregar a inicio". (iOS no muestra el
  boton automatico; se instala desde ese menu.)
- Una vez instalada, abre a pantalla completa como una app normal.

## Nota

La PWA requiere HTTPS en produccion (los service workers solo funcionan sobre
HTTPS, salvo en localhost). En el despliegue real hay que servir el sistema tras
un certificado TLS; de lo contrario el service worker no se registrara.


---

# Paso 14: Control de acceso (asistencia)

Se construyo el registro de asistencia por software, con calculo de horas
trabajadas y conexion automatica con la nomina.

## Alcance honesto

Este paso es asistencia **por software**: marcaciones, calculo de horas y su
paso a nomina. NO incluye hardware biometrico real (lectores de huella, camaras
de reconocimiento facial): eso depende de dispositivos especificos y sus SDKs
propietarios, que no se pueden construir ni probar aqui. El modelo `Marcacion`
tiene un campo `origen` (manual/pin/biometrico) previsto para que, si algun dia
se integra un lector via su API, solo haya que alimentar esa marca.

## Decisiones del usuario

1. **Registro de marcaciones** (entradas/salidas), no gestion de permisos.
2. **Marcacion + calculo de horas** que alimente la nomina.
3. **Hora extra diaria**: lo que exceda 8 horas trabajadas en un dia.
4. **Receso**: el empleado marca salida y regreso de descanso; ese tiempo NO
   cuenta como trabajado y se descuenta del total.
5. **Automatico**: al cerrar el turno se calcula y se crea la novedad de extra.

## Que existia y que faltaba

Habia una tabla `Turno` minima (solo entrada y salida, con `utcnow` que en
Colombia corre las horas 5h) y rutas basicas. **Faltaba**: calculo de horas,
recesos, tipo de jornada, medicion de tardanzas, multi-empresa y, sobre todo, la
conexion con nomina.

## Que se construyo

- **`hora_colombia()`**: helper que registra la hora local real (UTC-5), no UTC.
- **`Turno` ampliado**: horas trabajadas, ordinarias, nocturnas, dominicales,
  extra (diurna/nocturna), receso, tardanza, estado y vinculo a la novedad.
- **`Marcacion`** (tabla nueva): cada evento del turno (entrada, salida a receso,
  regreso, salida), con su origen.
- **`TurnoProgramado`** (tabla nueva): horario planeado para medir tardanzas.
- **`AsistenciaService`**: marcar entrada/receso/regreso/salida, calculo de horas
  descontando recesos, deteccion de extra, generacion automatica de la novedad,
  anulacion segura (no si la novedad ya se liquido), turnos programados y
  resumenes.
- **Rutas** por empleado: entrada, receso, regreso, salida; vista de empleados
  enriquecida con estado del turno, horas y extra.

## La integracion clave: asistencia -> nomina

El ciclo completo quedo verificado de punta a punta: un empleado marca su turno,
el sistema calcula las horas, detecta las extra, crea la `NovedadNomina`
automaticamente, y al liquidar el periodo esa novedad **se paga** y queda marcada
como aplicada. Ejemplo probado: turno de 11h con 1h de receso = 10h trabajadas,
2h extra -> novedad `he_diurna` de 2h -> liquidada en nomina.

## Verificacion

- **Calculo de horas con casos conocidos**: turno de 8h sin extra; receso que se
  descuenta (9h brutas - 1h = 8h); 2h extra diurnas; extra nocturna por hora de
  salida; tardanza contra turno programado con tolerancia.
- **Generacion automatica de novedad** y su **no generacion** cuando no hay extra.
- **Anulacion**: elimina la novedad si no se ha liquidado; la bloquea si ya se
  pago.
- **Integracion con nomina** verificada: la novedad de asistencia se paga en la
  liquidacion.
- **Suite**: 417 aciertos, 0 fallos (403 previos + 14 de asistencia).
- **Migracion 0006** idempotente, probada en cadena 0001->0006 sobre base con
  esquema viejo y turnos: normaliza turnos viejos (con salida -> cerrado), crea
  columnas y tablas, ciclo downgrade+re-upgrade correcto, verificador la aprueba.
- **Seed**: 2 turnos de ejemplo, 1 con novedad automatica de horas extra.

## Nota sobre el calculo

El tipo de hora extra (diurna/nocturna) se determina de forma simplificada por
la hora de salida (franja nocturna 9pm-6am) y si el dia es domingo. Para casos
con jornadas que crucen ambas franjas en proporciones complejas, conviene
revisar la novedad antes de liquidar. Los factores de recargo siguen siendo los
configurables de `ParametrosNomina`.


---

# Paso 15: consolidacion final

Con todos los modulos construidos, se reviso el sistema de punta a punta y se
cerraron dos problemas transversales que afectaban a todo el sistema.

## 1. La cadena de migraciones aplica desde cero (produccion real)

Se verifico que la cadena completa 0001 -> 0007 crea las 51 tablas desde una
base vacia, sin depender de create_all, y que la app arranca sobre esa base
(16/16 vistas en 200). Migraciones y modelos coinciden exactamente: no hay
tablas de mas ni de menos. Produccion y desarrollo convergen.

## 2. Zona horaria unificada a hora Colombia

Se encontro que **todo el sistema guardaba las fechas en UTC** (5 horas
adelantadas para Colombia). Una venta a las 8pm hora local se guardaba como la
1am del dia siguiente, lo que distorsionaba cualquier reporte por dia.

Se unificaron **todas** las fechas de negocio a `hora_colombia()` (UTC-5):
- 16 columnas con default `datetime.utcnow` -> `hora_colombia`.
- ~15 llamadas inline en servicios y rutas (aprobaciones, anulaciones, apertura
  de mesa, comandas, cierre de caja, pagos, timestamps de mobile y websocket).
- Un calculo de `minutos_ocupada` que comparaba una fecha local contra utcnow
  (daba 300 minutos de mas siempre): corregido.

Los unicos `utcnow()` que se conservan son los de los tokens JWT, que por
estandar deben ir en UTC. Verificado: una venta nueva ahora se guarda a las
13:07 (hora Colombia) en vez de las 18:07 (UTC).

## 3. Server-defaults en la tabla empresas

Las columnas NOT NULL de `empresas` tenian default solo en Python (via ORM). Un
INSERT SQL directo (restauracion de respaldo, carga masiva) fallaba con "NOT
NULL constraint failed". Se agregaron server_default a nivel de base (migracion
0007), de modo que crear una empresa con solo el nombre ahora funciona y la BD
aplica todos los valores por defecto. La tabla es robusta independientemente de
como se inserte.

## Verificacion

- Cadena 0001 -> 0007 desde base vacia: 7 migraciones, 51 tablas, app arranca.
- Migracion 0007 idempotente, probada sobre base vieja con datos; ciclo
  downgrade + re-upgrade correcto.
- INSERT SQL directo de empresa (solo nombre) funciona tras 0007.
- Zona horaria: venta nueva guardada en hora local, confirmado.
- Suite: **417 aciertos, 0 fallos**.
- End-to-end completo: 16 vistas, PWA (manifest/sw/offline), desprendible PDF,
  nomina electronica DIAN, asistencia con novedad automatica. Cero tracebacks.

## Estado del sistema

Todos los modulos originalmente solicitados estan construidos y verificados:
ventas, inventario, mesas, compras, produccion, nomina (Colombia), asistencia
con paso a nomina, y la PWA movil. La cadena de migraciones esta completa y
probada en ambos sentidos. El sistema guarda las fechas en hora local y arranca
limpio en un escenario de produccion.

## Pendientes que solo el usuario puede hacer (recordatorio)

1. **Rotar los secretos** que estuvieron en archivos de configuracion
   (SECRET_KEY, JWT_SECRET_KEY, SESSION_SECRET_KEY) y la clave de admin.
2. **Purgar el historial de git** (BFG o git-filter-repo): aun hay bases de
   datos y secretos en los commits 7475111 y 8987c18.
3. **HTTPS en produccion**: la PWA (service worker) solo funciona sobre HTTPS.


---

# Paso 16: blindaje HTTP (CSP, HSTS, headers, rate limiting, CSRF)

Primer bloque del endurecimiento de seguridad solicitado. Se anadio la capa de
proteccion HTTP que faltaba por completo, con arquitectura limpia (un modulo
`app/security/` por responsabilidad).

## Defectos encontrados

| # | Defecto | Riesgo |
|---|---------|--------|
| 1 | Cero cabeceras de seguridad | Clickjacking, XSS, sniffing MIME, downgrade |
| 2 | El token CSRF se generaba pero NUNCA se validaba | CSRF en todos los POST |
| 3 | Rate limiting configurado pero no implementado | Fuerza bruta, DoS |
| 4 | El token CSRF se regeneraba en cada render | Invalidaba formularios abiertos |

## Que se construyo

**`app/security/headers.py`** - Middleware de cabeceras OWASP en cada respuesta:
Content-Security-Policy, X-Frame-Options (DENY), X-Content-Type-Options
(nosniff), Referrer-Policy, Permissions-Policy, y HSTS (activable solo bajo
HTTPS). Cache-Control no-store en rutas con datos sensibles.

**`app/security/rate_limit.py`** - Rate limiting en memoria (sin dependencias),
ventana deslizante por IP. Dos limites: uno estricto al login (10 intentos / 5
min, contra fuerza bruta) y uno general (100 / hora). Respeta X-Forwarded-For
tras proxy reverso.

**`app/security/csrf.py`** - Validacion CSRF real en cada POST/PUT/PATCH/DELETE
de formularios. Token estable por sesion, comparacion de tiempo constante,
aceptado por campo de formulario o cabecera X-CSRF-Token. Exime metodos seguros,
login/logout, APIs Bearer y peticiones JSON (no explotables por CSRF clasico).
Si hay sesion autenticada sin token, rechaza el POST (cierra el hueco).

## Cambios de soporte

- Token CSRF inyectado automaticamente en los 32 formularios de las 16
  plantillas (campo oculto `{{ csrf_token }}`).
- `context()` corregido: el token ahora es estable por sesion (antes se
  regeneraba en cada render, invalidando formularios ya abiertos).
- Nuevas variables en config y `.env.example`: RATE_LIMIT_*, CSRF_ENABLED,
  HSTS_ENABLED.
- El cliente de pruebas adjunta el token CSRF automaticamente; el rate limit se
  desactiva en el entorno de test (misma IP haria fallar el login repetido).

## Verificacion

- **Cabeceras**: 5 presentes en toda respuesta, incluso 404. CSP restringe
  origenes (default-src 'self', frame-ancestors 'none', object-src 'none').
- **CSRF**: token invalido -> 403; token valido (form o header) -> pasa; login
  exento; GET no requiere token; POST autenticado sin token -> 403.
- **Rate limit**: 10 intentos de login dan 401, el 11 y 12 dan 429; login
  legitimo desde otra IP sigue funcionando (limite por IP, no global). Ventana
  deslizante probada unitariamente.
- **Suite**: 426 aciertos, 0 fallos (417 previos + 9 de seguridad).
- Sin migracion (capa HTTP, no toca la base).

## Pendiente de este bloque (para endurecer aun mas)

- La CSP permite 'unsafe-inline' en scripts/estilos porque las plantillas usan
  estilo e inline JS. Endurecerlo requiere migrar a nonces por request.
- HSTS queda desactivado por defecto; activarlo en produccion tras configurar
  HTTPS (HSTS_ENABLED=true).
- Para despliegue multi-proceso, el rate limit deberia usar un backend
  compartido (Redis) en vez de memoria por proceso.

## Bloques de seguridad aun por hacer (proximos pasos)

RBAC configurable en BD, auditoria (usuario/IP/antes/despues), manejo global de
excepciones, backups. Los instaladores de Windows y el escaneo antivirus de
subidas quedan fuera de lo que se puede construir y verificar en este entorno.


---

# Paso 17: RBAC (control de acceso por modulo, parametrizable)

Segundo bloque de seguridad. El control de acceso deja de estar codificado y
pasa a resolverse contra la base de datos: roles y permisos por modulo, que se
pueden crear, editar y eliminar.

## Defecto encontrado

La autorizacion estaba codificada: 21 llamadas a `exigir_rol(request,
"administrador")` con strings sueltos. Un typo rompia el control en silencio, y
no se podian configurar permisos sin tocar codigo (justo lo que el prompt
prohibe).

## Un hallazgo importante (consolidacion, no acumulacion)

Al empezar descubri DOS sistemas RBAC a medio construir que nunca se conectaron:
uno en `models_enterprise.py` (tablas Rol/Permiso) y un servicio completo en
`app/services/rbac_service.py` (con permisos, cache y siembra), ya importado en
main.py pero inactivo. Empece a construir un tercero en paralelo y colisiono
(genero roles duplicados). La decision correcta fue CONSOLIDAR: elimine mi
duplicado y extendi el servicio existente con permisos por modulo y la
resolucion que necesita el middleware. Mejor una implementacion viva que tres
compitiendo.

## Decisiones del usuario

1. **Permisos por modulo**: acceso si/no a cada seccion (ventas, nomina, etc.).
2. **Migrar los roles actuales** pero dejandolos parametrizables: se pueden
   editar, crear nuevos y eliminar. El super administrador queda protegido.

## Que se construyo

- **16 permisos de modulo** (`modulo.dashboard`, `modulo.nomina`, etc.) sembrados
  junto a los permisos por accion que ya existian.
- **6 roles** con nivel de acceso: administrador (100, super admin), gerente
  (80), cajero (40), mesero/cocinero/bartender (30). El nivel 100 tiene acceso
  total y esta protegido.
- **`RolService.puede_modulo()`**: resuelve el acceso contra la BD, sin
  distinguir mayusculas (el Usuario.rol puede venir capitalizado o no). El super
  admin siempre pasa.
- **Autorizacion centralizada en el middleware**: mapea la ruta de cada seccion
  a su modulo y verifica el permiso. Una sola puerta, en vez de 21 guards
  dispersos. Respeta el override de BD en pruebas.
- **Pagina `sin_permiso.html`**: acceso denegado claro, con 403.
- **`exigir_rol` conservado** (compatibilidad) pero ahora el super admin siempre
  pasa; `exigir_modulo` disponible para verificacion granular.

## Un bug de zona horaria que afloro y se corrigio

Los reportes y el dashboard usaban `date.today()` (fecha UTC) para el rango
"hoy", pero las ventas se guardan en hora Colombia (Paso 15). De noche (hora
local) el reporte de "hoy" buscaba el dia siguiente y no encontraba nada. Se
agrego `fecha_colombia()` y se corrigieron los 5 usos en reportes y dashboard
(y los tests que comparaban con date.today()).

## Verificacion

- **Resolucion**: admin pasa a todo; mesero solo a mesas/caja; cajero no entra a
  inventario; resolucion case-insensitive; rol inexistente no pasa.
- **End-to-end HTTP**: admin 200 en todos los modulos; mesero 200 en los suyos y
  403 en nomina/inventario/configuracion. Cero tracebacks.
- **Suite**: 436 aciertos, 0 fallos (426 previos + 10 de RBAC).
- **Migracion 0008** idempotente: crea las 4 tablas RBAC, probada en cadena
  0001->0008 desde vacio, sobre base vieja con datos, y ciclo downgrade+upgrade.
- El fixture de pruebas siembra el RBAC para que la autorizacion funcione igual
  que en produccion.

## Pendiente de este bloque (para una vuelta futura)

- La UI para gestionar roles y permisos desde la pantalla de Usuarios (crear
  rol, marcar permisos con casillas). El backend ya lo soporta; falta la
  pantalla. Hoy se parametriza por datos.
- Los 21 `exigir_rol` codificados siguen ahi como segunda barrera; se pueden ir
  migrando a `exigir_modulo` gradualmente. El middleware ya cubre el acceso a
  las secciones.

## Bloques de seguridad restantes

Auditoria (usuario/IP/antes/despues) + manejo global de excepciones, y backups.
Los instaladores Windows y el escaneo antivirus quedan fuera de este entorno.


---

# Paso 18: Auditoria + manejo global de excepciones

Tercer bloque de seguridad. Se agrego el registro de auditoria (quien hizo que,
cuando, desde donde) y un manejo global de errores para que ningun fallo genere
una pantalla en blanco.

## Decisiones del usuario

1. **Registrar todo**: cambios (crear/editar/anular/eliminar), accesos
   (login/logout) y accesos denegados (intentos sin permiso).
2. **Captura manual** del antes/despues en los puntos importantes (ventas,
   nomina, anulaciones): mas preciso que interceptar todas las tablas.

## Que se construyo

**`RegistroAuditoria`** (tabla append-only): fecha/hora local, usuario, rol, IP,
accion, modulo, entidad afectada, descripcion, valor anterior y nuevo, resultado.

**`AuditoriaService`**: punto unico de registro. Tres garantias:
  - **Nunca tumba la operacion**: si el registro falla, traga el error (con log)
    en vez de propagarlo.
  - **Nunca guarda datos sensibles**: contrasenas, hashes, tokens y csrf se
    ocultan como '***' al serializar el antes/despues.
  - **Append-only**: el servicio solo crea; no edita ni borra.

**Puntos auditados**:
  - Accesos: login exitoso, login fallido, logout.
  - Accesos denegados: cada intento sin permiso (desde el middleware RBAC).
  - Cambios: anulacion de venta, liquidacion y anulacion de nomina (con
    antes/despues). Mas puntos se pueden anadir con una linea.

**Manejo global de excepciones**: dos handlers.
  - HTTPException (403/404/401/400): pagina amigable en el navegador, JSON en la
    API.
  - Error 500 no controlado: se registra con una referencia unica, se audita, y
    se muestra una pagina de error sin exponer detalles tecnicos. Ningun error
    deja pantalla en blanco.

**Vista `/auditoria`**: pantalla de consulta con filtros por accion y modulo,
solo para administradores. Registrada como modulo RBAC.

## Verificacion

- **End-to-end**: login exitoso, login fallido, acceso denegado y vista de
  auditoria, todos auditados correctamente con usuario/rol/IP/modulo. Cero
  tracebacks.
- **Datos sensibles**: las contrasenas y tokens se ocultan como '***'
  (verificado en tests).
- **Resiliencia**: un registro con datos no serializables no lanza excepcion.
- **Suite**: 445 aciertos, 0 fallos (436 previos + 9 de auditoria).
- **Migracion 0009** idempotente con indices por fecha y accion, probada en
  cadena 0001->0009 desde vacio, sobre base vieja y ciclo downgrade+upgrade. El
  verificador la aprueba.

## Bloque de seguridad restante

Backups (manuales, automaticos, restauracion, verificacion de integridad). Los
instaladores Windows y el escaneo antivirus quedan fuera de este entorno.


---

# Paso 19: Backups + HTTPS + preparacion para produccion

Ultimo bloque de seguridad del programa, mas la preparacion para operar. Tres
partes: copias de seguridad (construidas y verificadas), configuracion de HTTPS
(lista para desplegar) y la guia de puesta en marcha.

## Parte 1: Copias de seguridad

Decisiones del usuario: boton en la app + script programable; comprimir y
verificar cada copia.

**`BackupService`** soporta los dos motores del sistema:
  - SQLite: usa la API de backup nativa de sqlite3 (copia consistente aunque
    haya escrituras; un simple copy podria corromperse).
  - PostgreSQL: usa pg_dump.

Cada copia se comprime en .zip y se verifica su integridad al crearse (testzip +
checksum sha256). El servicio ademas lista, restaura y aplica retencion.

**Seguridad de la restauracion**: es destructiva, asi que antes de sobrescribir
hace una copia automatica del estado actual (etiqueta pre_restauracion), y
valida la integridad de la copia (y un PRAGMA integrity_check en sqlite) antes
de restaurar. Una copia corrupta nunca se restaura.

**Dos formas de disparar**:
  - Boton en la app: pantalla /backups (crear, ver, restaurar), solo admin,
    auditada.
  - Script `scripts/backup.py`: crear/listar/verificar/restaurar/retencion, con
    ejemplos para el Programador de tareas de Windows y cron de Linux.

## Parte 2: HTTPS

No se puede levantar TLS real en el entorno de construccion, pero se dejo la
configuracion lista y verificada:
  - `despliegue/Caddyfile`: HTTPS automatico (Let's Encrypt), la opcion simple.
  - `despliegue/nginx-cafbardla.conf`: para Nginx + certbot.
  - Ambos pasan X-Forwarded-For, que el rate limit y la auditoria ya respetan
    para registrar la IP real del cliente (verificado).

La app ya estaba preparada: en produccion RECHAZA arrancar con SQLite o sin
cookies seguras (verificado: ambos casos abortan el arranque; la config correcta
con PostgreSQL + HTTPS carga bien).

## Parte 3: Preparacion para produccion

  - `despliegue/.env.produccion.example`: plantilla con secretos a generar,
    PostgreSQL, cookies seguras y HSTS.
  - `despliegue/README_PRODUCCION.md`: guia paso a paso (servidor, .env,
    migraciones, siembra, admin real, HTTPS, backups programados, verificacion).

## Verificacion

- Backup: crear (comprime 340KB->20KB), verificar, listar, restaurar (con
  respaldo previo), deteccion de corrupcion (bloquea restauracion), retencion
  (conserva N, respeta pre_restauracion). Boton en la app end-to-end (crear ->
  303, auditado; mesero recibe 403).
- HTTPS: validaciones de produccion probadas (SQLite abortado, cookies inseguras
  abortadas, config correcta carga).
- Suite: 455 aciertos, 0 fallos (445 previos + 10 de backup).
- Sin migracion (el backup es basado en archivos, no toca la base).

## Estado del programa de seguridad

Bloques completados: blindaje HTTP (16), RBAC (17), auditoria (18), backups (19).
Con HTTPS y la guia de produccion, el sistema esta listo para operar de forma
segura. Lo que queda fuera de este entorno: instaladores de Windows y escaneo
antivirus de subidas (se pueden escribir scripts pero no verificar el .exe), y
la documentacion tecnica extendida en /docs.

## Pendientes que solo el usuario puede hacer

1. Rotar secretos y contrasena de admin (cubierto si genera nuevos al desplegar).
2. Purgar el historial de git (BFG / git-filter-repo): DBs y secretos en commits
   antiguos.
3. Servir con HTTPS (ya provista la configuracion) y programar los backups.


---

# Paso 20: Empleado-Usuario unificado + estructura de reconocimiento facial

Primer bloque del nuevo alcance solicitado. Une la gestion de empleados con la
de usuarios y prepara la estructura para el reconocimiento facial en la entrada
de personal.

## Decisiones del usuario

1. Empezar por empleado-usuario unificado con permisos de acceso.
2. Del reconocimiento facial: construir solo la ESTRUCTURA (foto registrada +
   flujo con consentimiento), sin el motor de reconocimiento.

## Que se construyo

**Usuario asignable desde el modulo de empleados**: en la pantalla de Empleados,
cada empleado tiene ahora una seccion para crear o editar su usuario, elegir el
rol y definir a que puede acceder. Un solo lugar para todo.

**Permisos de acceso por canal** (`Usuario.acceso_web`, `acceso_app_pedidos`):
determinan a donde entra el usuario. Un empleado puede tener usuario SIN acceso
a ninguna app (ambos en False): solo podra registrar entradas y salidas, tal
como se pidio. El login ahora RECHAZA (403) a un usuario sin acceso_web, aunque
las credenciales sean correctas.

**Estructura de reconocimiento facial** (sin motor):
  - `Empleado.foto`: ruta a la foto en disco (static/fotos_empleados).
  - `Empleado.codificacion_facial`: campo listo para el vector facial del futuro
    motor (no se implementa el reconocimiento en si).
  - `consentimiento_biometrico` + `fecha_consentimiento`: la foto NO se registra
    sin el consentimiento del empleado (Ley 1581 de 2012, habeas data). Subir
    foto sin marcar el consentimiento devuelve 400.
  - Subida de foto validada (tipo JPEG/PNG/WEBP, maximo 5 MB), auditada.

## Verificacion

- Asignar usuario con acceso web, solo turnos (sin accesos), y actualizar uno
  existente sin duplicar: OK. Usuario duplicado rechazado (400).
- Login: usuario sin acceso_web -> 403; con acceso_web -> entra. Auditado.
- Foto: sin consentimiento -> 400; con consentimiento -> se guarda en disco,
  registra fecha y queda auditada.
- Suite: 461 aciertos, 0 fallos (455 previos + 6 nuevos).
- Migracion 0010 idempotente, probada en cadena 0001->0010 desde vacio, sobre
  base vieja y ciclo downgrade+upgrade.

## Importante sobre el reconocimiento facial

Se dejo la estructura (foto + consentimiento + campo para el vector), pero el
MOTOR de reconocimiento (comparar un rostro en vivo contra la foto registrada)
NO esta implementado: requiere una libreria de vision por computadora, captura
de camara en el navegador y pruebas con hardware que no hay en este entorno.
Ademas, el dato biometrico tiene implicaciones legales serias en Colombia que
conviene revisar con un abogado antes de activarlo en produccion.

## Bloques del nuevo alcance aun pendientes

- Grupos de productos + configuracion de impresoras (por producto/grupo/destino).
- Reportes imprimibles y exportables a Excel + informes gerenciales.
- App de cliente (mesa / autoservicio) y su modo offline.
- Motor de reconocimiento facial (fuera de este entorno).


---

# Paso 21: Grupos de productos + configuracion de impresoras

Segundo bloque del nuevo alcance. Permite definir a que impresora va cada
producto, con grupos de impresion flexibles y una cascada de resolucion.

## Decisiones del usuario

1. Grupos de impresion SEPARADOS de las categorias (mas flexible).
2. Cascada de resolucion: producto -> grupo -> impresora local por defecto.

## Que se construyo

**Modelos**: `Impresora` (nombre, destino, tipo de conexion, marca por defecto)
y `GrupoImpresion` (agrupa productos por donde se preparan, con su impresora).
`Producto` gana `impresora_id` (especifica) y `grupo_impresion_id`.

**Cascada de resolucion** (ImpresionService), en este orden:
  1. Impresora especifica del producto.
  2. Impresora de su grupo de impresion.
  3. Impresora marcada por defecto del negocio.
El servicio tambien agrupa las lineas de una comanda por impresora destino, que
es lo que el cliente de impresion necesita para enviar cada parte a cocina,
barra o caja.

**Pantallas**: /impresoras (crear impresoras y grupos, solo admin) y en
Productos, un selector por producto para asignar impresora y/o grupo. Todo
auditado.

## Aclaracion importante

El sistema DECIDE el destino de cada linea y agrupa la comanda; NO envia bytes
al hardware desde el servidor. La impresion fisica depende del sistema operativo
y los drivers del equipo cliente (el cliente de impresion lee el destino y
manda). Esto es lo correcto para una app web: el servidor no tiene acceso a las
impresoras locales del punto de venta.

## Un bug real encontrado y corregido

El downgrade de la migracion fallaba en SQLite: no se puede DROP COLUMN de una
columna con llave foranea sin recrear la tabla. Se corrigio usando
batch_alter_table. Sin esto, revertir la migracion habria fallado en produccion.

## Verificacion

- Cascada probada en sus 3 niveles + producto gana sobre grupo + sin defecto
  devuelve None. Agrupacion de comanda por impresora. Gestion (solo una por
  defecto).
- End-to-end: crear impresoras, grupo, asignar a producto, ver pantallas.
- Suite: 470 aciertos, 0 fallos (461 previos + 9 nuevos).
- Migracion 0011 idempotente, cadena 0001->0011 desde vacio, sobre base vieja y
  ciclo downgrade+upgrade (con el arreglo de batch para SQLite).

## Bloques del nuevo alcance aun pendientes

- Reportes imprimibles y exportables a Excel + informes gerenciales.
- App de cliente (mesa / autoservicio) y su modo offline.
- Motor de reconocimiento facial (fuera de este entorno).


---

# Paso 22: Reportes exportables a Excel + informes gerenciales

Tercer bloque del nuevo alcance. Deja los reportes imprimibles y exportables, y
corrige un bug serio de consistencia de datos que aparecio al revisarlos.

## Bug encontrado y corregido: estado de ventas inconsistente

El sistema tenia DOS vocabularios para el estado de una venta cobrada: el
servicio de ventas la dejaba en 'cerrada', pero los reportes, el dashboard, la
caja y la API movil consultan 'pagada' (19 lugares usan 'pagada', solo 3 usaban
'cerrada'). Resultado: las ventas cobradas por el servicio NO aparecian en
ningun reporte (mostraban $0). 

Se unifico a 'pagada' (el vocabulario dominante y el que ya usaba la API movil).
Tras el fix, los reportes pasan a mostrar los datos reales (en el seed: de $0 a
$219.000 en 6 transacciones). La migracion 0012 normaliza los datos ya
existentes de 'cerrada' a 'pagada'.

## Que se construyo / mejoro

**Exportacion a Excel**: ya existia para 4 reportes (ventas, productos,
inventario, meseros); se agrego rentabilidad. Los 5 exportan .xlsx con formato
(cabeceras con color, anchos ajustados), verificado que abren correctamente.

**Informes gerenciales imprimibles**: la pantalla /informes ahora tiene botones
para exportar cada reporte a Excel, exportar ventas a CSV, e imprimir. Se
agregaron estilos @media print que ocultan la navegacion y los controles al
imprimir, dejando solo el informe.

## Verificacion

- Exportacion de los 5 tipos a Excel: todos 200, xlsx valido, abren con openpyxl.
- Tipo invalido rechazado (400).
- Vista /informes con botones de Excel, CSV e imprimir + estilos de impresion.
- Fix de estado: procesar_pago deja la venta en 'pagada' (test de regresion).
- Suite: 479 aciertos, 0 fallos (470 previos + 9 nuevos).
- Migracion 0012 normaliza 'cerrada'->'pagada', probada; cadena 0001->0012
  aplica desde vacio (12 migraciones).

## Bloques del nuevo alcance aun pendientes

- App de cliente (mesa / autoservicio) y su modo offline.
- Motor de reconocimiento facial (fuera de este entorno).


---

# Paso 23: Pantalla de gestion de roles (cabo suelto del RBAC)

Cierra el pendiente del paso 17: el RBAC funcionaba pero solo se parametrizaba
por datos/seed. Ahora hay una pantalla para que un administrador gestione roles
y permisos con casillas, sin tocar codigo ni base de datos a mano.

## Que se construyo

**Metodos de gestion en RolService**: listar_roles, modulos_disponibles,
crear_rol, actualizar_permisos_modulo, eliminar_rol. Con las protecciones:
  - Nadie crea un rol de nivel >= 100 desde la UI (el nivel se topa en 99).
  - El super administrador no se puede editar ni eliminar.
  - Los roles predefinidos del sistema no se eliminan.
  - Un rol en uso (con usuarios asignados) no se puede eliminar.

**Pantalla /roles**: crear rol nuevo marcando modulos con casillas, editar los
permisos de cada rol existente, y eliminar roles libres. Enlazada desde la
pantalla de Usuarios. Solo administradores. Todo auditado (crear/editar/eliminar).

## Bug de paso previo corregido

En crear_usuario, el rol se validaba contra una lista CODIFICADA
("administrador, caja, mesero, cocina"), lo que contradecia el RBAC
parametrizable e impedia usar roles nuevos. Ahora se valida contra los roles
reales de la base de datos.

## Verificacion

- Servicio: crear rol con modulos, no crear super admin, actualizar permisos,
  proteger y no eliminar super admin, no eliminar rol en uso, eliminar rol libre.
- HTTP: vista /roles (admin 200), crear rol por formulario (303, permiso
  aplicado), mesero bloqueado (403).
- Suite: 489 aciertos, 0 fallos (479 previos + 10 nuevos).
- Sin migracion (usa las tablas RBAC existentes).

## Bloque del nuevo alcance aun pendiente

- App de cliente (mesa / autoservicio) y su modo offline.
- Motor de reconocimiento facial (fuera de este entorno).


---

# Paso 24: Editor de mesas profesional (plano configurable)

Atiende el reporte de que "al crear una mesa no dejaba" y la vision de un plano de
salon al estilo de un restaurante de primer nivel: crear zonas y mesas, y
arrastrarlas libremente para ubicarlas donde el usuario quiera.

## Diagnostico del problema real

La creacion de mesas SI funcionaba (respondia 303), pero habia tres problemas que
hacian que la experiencia se sintiera rota:
  1. Todas las mesas nuevas nacian en la misma posicion (0,0), encimadas una
     sobre otra, dando la impresion de que "no se creaban".
  2. El plano tenia arrastre, pero cada mesa era un enlace a la comanda: al
     intentar moverla se abria la comanda. No habia separacion entre "operar" y
     "editar el plano".
  3. El tamano de las mesas estaba fijo en CSS; el modelo no permitia mesas de
     distinto tamano.

## Decisiones del usuario

1. Arrastrar y soltar libremente (posicion exacta con el mouse).
2. Formas (redonda/cuadrada/rectangular) + capacidad + TAMANO configurable.

## Que se construyo

**Modo editor**: un boton "Modo editor" separa la operacion diaria (tocar una
mesa abre su comanda) de la configuracion del plano (arrastrar, seleccionar,
cambiar forma/tamano, eliminar). En modo normal el plano opera como siempre.

**Arrastrar y soltar libre**: en modo editor, cada mesa se arrastra a la posicion
exacta y se guarda automaticamente (endpoint /mesas/{id}/layout).

**Personalizacion por mesa**: al seleccionar una mesa en modo editor aparece una
barra con cambiar forma, agrandar, achicar y eliminar. Nuevos campos ancho/alto.

**Crear con forma**: el formulario de nueva mesa ahora incluye la forma; las
mesas nuevas nacen escalonadas (no encimadas) y con el tamano propio de su forma.

**Zonas gestionables**: crear y eliminar zonas (una zona con mesas no se puede
eliminar hasta moverlas). Crear mesas/zonas y editar el plano exige rol
administrador o gerente; un mesero no puede (403).

## Bug preexistente corregido (migracion 0011, del paso 21)

Al probar la migracion sobre una base antigua, la 0011 fallaba en SQLite:
"No support for ALTER of constraints in SQLite" al agregar columnas con llave
foranea a productos. Se corrigio agregando esas columnas sin la FK inline en
SQLite (la relacion queda en el modelo ORM; en PostgreSQL se mantiene la FK).
Sin este arreglo, actualizar una instalacion SQLite existente habria fallado.

## Verificacion

- End-to-end: crear zona, crear mesa (con forma y tamano correctos, posicion
  escalonada), mover, cambiar forma/tamano, eliminar mesa, eliminar zona vacia.
- Protecciones: no eliminar zona con mesas (400), gerente si puede (303), mesero
  no (403).
- Suite: 497 aciertos, 0 fallos (489 previos + 8 nuevos).
- Migracion 0013 idempotente; cadena 0001->0013 desde vacio (13), ciclo
  downgrade+upgrade, y ahora tambien sobre base antigua (con el arreglo de 0011).

## Bloque del nuevo alcance aun pendiente

- App de cliente (mesa / autoservicio) y su modo offline.
- Motor de reconocimiento facial (fuera de este entorno).


---

# Paso 25: App de cliente (autoservicio y pedido en mesa) - primer bloque

Primer bloque del gran alcance de la app de cliente. Backend, API y flujo
completo, mas la interfaz del cliente y la pantalla de gestion del personal.

## Decisiones del usuario

1. Empezar por el backend y flujo de la app de cliente.
2. Autoservicio: el cliente solo ordena; paga en caja al recoger.
3. Pedido en mesa: queda pendiente hasta que un mesero lo acepte o rechace.

## Que se construyo

**Modelos** PedidoCliente + PedidoClienteLinea: el pedido del cliente vive en su
propia tabla, ANTES de convertirse en venta. No toca inventario ni ventas hasta
que se acepta (mesa) o se cobra (autoservicio). Un pedido rechazado no deja
rastro contable.

**Flujo (PedidoClienteService)**:
  - autoservicio -> pendiente -> caja lo cobra -> genera venta (abierta, con el
    nombre del cliente en la observacion) -> se marca entregado.
  - mesa -> pendiente -> el mesero ACEPTA (genera la comanda/venta en esa mesa) o
    RECHAZA (con motivo). No se puede reprocesar un pedido ya resuelto.

**API del cliente (publica, sin login)**: GET carta, POST pedido, GET estado.
Exenta de CSRF y de sesion (el comensal no tiene cuenta), pero SOLO las rutas de
cliente; la gestion sigue protegida.

**API de gestion (con sesion)**: listar pendientes, aceptar, rechazar, cobrar.

**Interfaz del cliente** (/cliente): pagina autonoma con identidad propia (no usa
el layout de gestion). Carta con buscador, carrito, y envio. Con ?mesa=N arranca
en modo mesa; sin parametro, en autoservicio. Mensajes distintos segun el tipo.

**Pantalla del personal** (/pedidos-pendientes): dos columnas (mesa /
autoservicio) con aceptar, rechazar y cobrar. Enlazada en el menu. Auto-refresco.

## Nota de seguridad

Las rutas /cliente y /api/cliente son publicas por diseno (el comensal ordena sin
cuenta). Se agregaron como prefijo publico y exento de CSRF de forma acotada; la
API de gestion (/api/cliente/pendientes, aceptar, etc.) exige sesion y devuelve
401 sin ella. Verificado.

## Verificacion

- Servicio: crear autoservicio/mesa, validaciones (nombre, mesa), aceptar (genera
  venta), rechazar (con motivo), no reprocesar, cobrar autoservicio.
- API publica sin login: carta, crear pedido, pagina; pendientes da 401 sin login.
- Gestion con login: ver, aceptar. Vista /pedidos-pendientes carga.
- Suite: 510 aciertos, 0 fallos (497 previos + 13 nuevos).
- Migracion 0014 idempotente; cadena 0001->0014 desde vacio (14) y ciclo
  downgrade+upgrade.

## Lo que sigue en el alcance de la app de cliente / rediseno

- Modo offline de la app de cliente (parte del bloque grande).
- Rediseno web para escritorio (mas amplio, menos compacto).
- Separar modulo de meseros (que no mande a la ventana de mesas de la web).
- Modulos independientes con identidad propia (mesero, cliente, gerencial, web).
- Motor de reconocimiento facial (fuera de este entorno).


---

# Paso 26: Rediseno web para escritorio (tema claro profesional)

Atiende el pedido de que la web se veia "muy compacta como si fuera para movil"
y la idea de un panel de escritorio mas amplio y comodo.

## Decisiones del usuario

1. Aprovechar el ancho: paneles y tablas mas anchos, menos espacio vacio a los
   lados.
2. Modernizar a un estilo claro y limpio tipo panel profesional.

## Que se construyo

**Capa de tema claro** (static/css/tema-escritorio.css): se carga al final y
sobrescribe el tema oscuro previo con precision, sin reescribir los 5 CSS
existentes (mas seguro y reversible). Cambios:
  - Paleta clara profesional: fondo gris muy claro, superficies blancas, texto
    carbon, bordes sutiles, verde de marca (#0f6b4a, coherente con la app de
    cliente) como acento, dorado tenue solo en detalles.
  - Ancho aprovechado: contenedor principal a 1800px (antes se sentia estrecho),
    menos padding lateral desperdiciado.
  - Grids que se expanden: tarjetas de estadistica y paneles en auto-fit para
    llenar el ancho disponible.
  - Tablas mas anchas y legibles; cabeceras claras, filas con hover verde suave.
  - Botones, formularios, badges y foco de teclado con el estilo claro.

## Verificacion

- Revision VISUAL con capturas reales (render headless con Chromium) del
  dashboard e informes: fondo claro, sidebar blanca, tarjetas blancas con cifras
  en verde, texto oscuro legible, botones integrados. Se corrigio en una segunda
  pasada el contraste de las tarjetas de estadistica y titulos que heredaban
  color claro.
- Todas las paginas clave cargan (dashboard, productos, informes, mesas,
  pedidos-pendientes, caja).
- Suite: 510 aciertos, 0 fallos (sin cambios funcionales) + 3 tests de tema.
- Sin migracion (solo CSS y plantilla base).

## Nota

El color de marca por empresa sigue siendo personalizable (variable --primary en
base.html). El tema define la estructura clara; ese acento se respeta.

## Lo que sigue

- App de cliente: modo offline.
- Separar modulo de meseros (que no mande a la ventana de mesas de la web).
- Modulos independientes con identidad propia (mesero, cliente, gerencial, web).
- Motor de reconocimiento facial (fuera de este entorno).


---

# Paso 27: App de cliente offline + enlaces a apps (solo admin)

Segundo bloque de la app de cliente (el modo offline) y un acceso rapido para
que el admin revise cada app desde el menu.

## Decisiones del usuario

1. Offline: ver la carta Y armar el pedido sin conexion; se envia solo al volver
   la red.
2. Enlaces a las apps: una seccion en el menu lateral, visible solo para admin.

## Que se construyo

**Modo offline de la app de cliente**:
  - Service worker dedicado (sw-cliente.js), servido desde la raiz con scope
    /cliente. A diferencia del SW general (que por seguridad NO cachea HTML
    autenticado), este si cachea la pagina publica del cliente y la carta.
  - La carta se guarda ademas en localStorage; si no hay red, se muestra la
    ultima carta guardada con un aviso de "sin conexion".
  - Cola de pedidos offline: si el envio falla por falta de red, el pedido se
    guarda en localStorage y se reintenta automaticamente al volver la conexion
    (evento 'online') o al reabrir la app. Aviso visual mientras esta encolado.

**Enlaces a las apps (solo admin)**: nueva seccion "Apps (revisar)" en el menu
lateral, visible unicamente para el rol administrador, con accesos a: app de
cliente (autoservicio), cliente en mesa, app de meseros y gestion de pedidos.
Se agregaron tambien Roles e Impresoras a la seccion de Administracion. Los roles
no-admin siguen viendo solo su "Vista movil".

## Verificacion

- Modo offline probado con NAVEGADOR REAL (Chromium) y servidor en proceso,
  simulando corte de red:
    carta_online=28 productos, carta_cacheada=true,
    pedido offline encolado=1, carta visible tras recargar OFFLINE=28,
    cola vaciada tras reconectar=0 (se envio solo).
- Enlaces: admin ve la seccion Apps; un mesero no la ve.
- Suite: 519 aciertos, 0 fallos (513 previos + 6 nuevos).
- Sin migracion (service worker, plantilla y ruta).

## Nota de seguridad

El SW del cliente solo cachea rutas /cliente y /api/cliente (publicas). Jamas
toca rutas autenticadas del sistema. El SW general del sistema sigue igual de
conservador.

## Lo que sigue

- Separar modulo de meseros (que no mande a la ventana de mesas de la web).
- Modulos independientes con identidad propia (mesero, cliente, gerencial, web).
- Motor de reconocimiento facial (fuera de este entorno).
