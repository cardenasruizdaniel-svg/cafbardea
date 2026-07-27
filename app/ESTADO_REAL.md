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
