# Guía de migración — pasos 4, 5 y 6

Aplica los cambios de esquema de Ventas, Inventario y Mesas sobre una base
de datos que ya tiene información.

**Verificado**: se probó sobre una base con el esquema anterior y datos reales.
Aplica, revierte y vuelve a aplicar sin pérdida de información.

---

## Antes de empezar: respaldo

No es opcional.

**SQLite**
```powershell
copy cafbardla.db cafbardla.db.respaldo
```

**PostgreSQL**
```bash
pg_dump -U usuario -d cafbardla > respaldo_antes_migracion.sql
```

---

## 1. Ver qué falta

```powershell
python scripts/verificar_migracion.py
```

Muestra qué tablas y columnas faltan, en qué versión está la base y si hay
mesas con el estado obsoleto `disponible`. No modifica nada.

---

## 2. Si la base nunca usó Alembic

Si el script informa *"SIN control de versiones"*, la base se creó con
`auto_create_schema=True`. Márquela como si tuviera el esquema inicial:

```powershell
python -m alembic stamp 0001_initial_schema
```

Esto solo escribe el número de versión; no toca las tablas.

> **Importante**: la base debe tener ya sus tablas. Si acaba de crear el
> archivo y está vacío, arranque la aplicación una vez (`python -m uvicorn
> app.main:app`) para que `auto_create_schema` genere el esquema, deténgala,
> y entonces ejecute el `stamp`.

---

## 3. Aplicar

```powershell
python -m alembic upgrade head
```

---

## 4. Comprobar

```powershell
python scripts/verificar_migracion.py
```

Debe terminar con *"Todo al día"*. Después, arranque normal:

```powershell
python -m uvicorn app.main:app
```

---

## Qué hace la migración

**Tablas nuevas**

| Tabla | Para qué |
|---|---|
| `pagos_venta` | Monto recibido, aplicado y cambio. Sin esto no se puede cuadrar caja |
| `alertas_stock` | Existencias negativas y bajo mínimo |
| `bodegas` | Almacenes o puntos de existencias |
| `existencias_bodega` | Detalle de stock por ubicación |
| `lotes` | Lotes con fecha de vencimiento |
| `reservas_mesa` | Reservas con datos del cliente |

**Columnas nuevas**

- `empresas.permitir_stock_negativo` — política de inventario
- `mesas` — `fecha_apertura`, `mesero_id`, `comensales`, `mesa_padre_id`
- `movimientos_inventario` — ocho campos de kardex (saldos y costos)

**Transformaciones de datos**

1. Las mesas con estado `disponible` pasan a `libre`. El dominio de mesas usaba
   un valor distinto al del resto del sistema, y eso rompía el módulo entero.
2. Se crea la bodega `PRINCIPAL` y se vuelca en ella el saldo actual de cada
   producto, de modo que el detalle por bodega cuadre con el total.
3. Los movimientos históricos quedan asignados a esa bodega.

---

## Sobre el kardex histórico

Los movimientos anteriores a la migración **no tienen saldos calculados**:
sus campos `saldo_anterior` y `saldo_posterior` quedan en cero, porque esa
información nunca se guardó y no puede reconstruirse con certeza.

El kardex es exacto **a partir de los movimientos nuevos**. Los antiguos
aparecen en el listado con su cantidad y referencia, pero sin saldo corrido.

Si necesita saldos históricos, habría que reconstruirlos partiendo de un
inventario físico y recalculando hacia adelante. Es un trabajo aparte y
conviene hacerlo con un conteo real como punto de partida.

---

## Si algo sale mal

```powershell
python -m alembic downgrade -1
```

Revierte los cambios de esquema. Las tablas nuevas se eliminan con los datos
que contengan; las tablas anteriores no se tocan.

Si la reversión tampoco funciona, restaure el respaldo del paso previo.

---

## Nota sobre PostgreSQL

Todo lo anterior se verificó sobre SQLite. La migración usa operaciones
estándar de Alembic y `batch_alter_table` (necesario en SQLite, inocuo en
PostgreSQL), así que debería aplicarse igual.

Aun así, **pruébela primero sobre una copia** de la base de producción antes
de ejecutarla en el servidor real.
