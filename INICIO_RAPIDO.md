# Café Bar DLA — Puesta en marcha

## Instalación

```powershell
cd D:\PROGRAMAS\CafBarDLA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Copie `.env.example` a `.env` y genere los secretos:

```powershell
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))"
```

Pegue ambos valores en `.env` junto con:

```
ENVIRONMENT=development
DATABASE_URL=sqlite:///./cafbardla.db
CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
LOG_LEVEL=INFO
```

## Cargar datos de demostración

```powershell
python scripts\inicializar_datos.py --reiniciar
```

Pedirá que escriba `BORRAR` para confirmar. Crea un café-bar completo:

| | |
|---|---|
| 3 zonas, 15 mesas | Salón, Terraza y Barra, con posiciones en el plano |
| 27 productos | Café, bebidas, licores, comidas, postres e insumos |
| 3 bodegas | Principal, Barra y Cocina, con traslados reales |
| 7 empleados | Uno por cada rol del sistema |
| 61 movimientos | Compras, traslados y ventas con kardex coherente |
| 2 lotes | Con fecha de vencimiento, uno próximo a vencer |
| 9 ventas | 6 cerradas y 3 cuentas abiertas en mesa |
| 1 reserva | Para ver el flujo completo |

Las existencias entran **por compra**, no escritas a mano, así que el costo
promedio y el kardex quedan correctos desde el inicio.

## Arrancar

```powershell
python -m uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000

## Usuarios

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin123*` | Administrador |
| `gerente` | `Demo123*` | Gerente |
| `cajero` | `Demo123*` | Cajero |
| `mesero1` | `Demo123*` | Mesero |
| `mesero2` | `Demo123*` | Mesero |
| `cocina` | `Demo123*` | Cocinero |
| `barra` | `Demo123*` | Bartender |

**Cámbielas antes de operar en producción.**

Pruebe la diferencia de permisos: con `mesero1`, intente vender por debajo del
precio de catálogo. El sistema lo rechaza. Con `admin` o `gerente`, lo permite.

## Verificar

```powershell
python -m pytest tests -q
```

Esperado: **327 aciertos**.

## Si ya tiene datos reales

No use `--reiniciar`: borraría todo. Lea `MIGRACION.md` y aplique:

```powershell
python scripts\verificar_migracion.py
python -m alembic upgrade head
```

## Notas

- En producción (`ENVIRONMENT=production`) la aplicación **se niega a
  arrancar** sin secretos, con SQLite, o sin `SESSION_COOKIE_SECURE=true`.
- `--reiniciar` está bloqueado en producción.
- Consulte `ESTADO_REAL.md` para el inventario honesto de lo que existe
  y lo que aún no.
