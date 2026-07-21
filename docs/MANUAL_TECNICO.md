# Manual técnico y de programación

## Arquitectura

```
Navegador (POS / tableta) → FastAPI + Jinja → SQLAlchemy → PostgreSQL
                                  └→ Docker / servicio cloud
```

- `app/main.py`: rutas HTTP, reglas de venta y datos iniciales.
- `app/models.py`: entidades persistentes.
- `app/database.py`: motor y sesiones SQLAlchemy.
- `app/templates/`: vistas HTML.
- `app/static/app.css`: diseño responsive y variables de marca.

## Modelo de negocio

Una `Zona` tiene muchas `Mesas`. Una `Venta` puede pertenecer a una mesa y contiene `DetalleVenta`. Al cobrar, la venta pasa a `pagada`, libera la mesa y crea un `MovimientoInventario` de salida por cada detalle. Productos, clientes, gastos, empleados y turnos están normalizados para extender los módulos.

## Desarrollo

Ejecute el servidor en modo recarga: `uvicorn app.main:app --reload`. La documentación de API queda disponible en `/docs`. Para cambios de estructura en ambientes reales, cree revisiones con Alembic; `create_all` se conserva como mecanismo de arranque de la demostración, no como estrategia de migración de producción.

## Pruebas recomendadas

- Cobrar una comanda y verificar la reducción de existencias.
- Validar que no se permitan ventas duplicadas abiertas para una mesa.
- Probar navegación táctil en 360 px, 768 px y escritorio.
- Probar backup/restore de PostgreSQL con `pg_dump`/`pg_restore`.
- Implementar pruebas unitarias para impuestos, descuentos, propinas, recetas y permisos antes de ponerlos en operación.

## Seguridad pendiente para salida a producción

Se debe incorporar OAuth o inicio de sesión local con contraseñas cifradas, RBAC por sucursal/rol, CSRF para formularios, registro de auditoría, rotación de secretos, cifrado de respaldos y límites de acceso a la API. También se debe evaluar la normativa de facturación electrónica y protección de datos aplicable al país de operación.
