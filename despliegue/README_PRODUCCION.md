# Puesta en marcha de CafBarDLA en producción

Guía para dejar el sistema operando de forma segura con datos reales.

## Resumen de lo que hay que hacer

1. Preparar el servidor (Python, PostgreSQL)
2. Configurar el `.env` de producción con secretos nuevos
3. Crear la base de datos y aplicar migraciones
4. Sembrar los datos iniciales y crear el administrador real
5. Configurar HTTPS con un proxy inverso
6. Programar las copias de seguridad
7. Verificar

---

## 1. Preparar el servidor

- Python 3.11 o superior.
- PostgreSQL 14+ (SQLite **no** se admite en producción; la app no arranca con él).
- Las herramientas de PostgreSQL (`pg_dump`) en el PATH, para los backups.

Instala las dependencias del proyecto:

    pip install -r requirements.txt

Crea la base de datos en PostgreSQL:

    createdb cafbardla

---

## 2. Configurar el .env de producción

Copia `despliegue/.env.produccion.example` como `.env` en la raíz del proyecto
y complétalo. **Genera secretos nuevos**, no reutilices ninguno anterior:

    python -c "import secrets; print(secrets.token_urlsafe(48))"

Ejecuta ese comando tres veces, una por cada secreto (SECRET_KEY,
JWT_SECRET_KEY, SESSION_SECRET_KEY). Pon tu cadena real de PostgreSQL en
DATABASE_URL y tu dominio en CORS_ORIGINS.

Deja `SESSION_COOKIE_SECURE=true` y `HSTS_ENABLED=true` (los usarás con HTTPS,
paso 5).

---

## 3. Aplicar migraciones

Con el `.env` configurado, crea el esquema:

    python -m alembic upgrade head

Esto crea las 53 tablas del sistema. Verifica con:

    python scripts/verificar_migracion.py

---

## 4. Sembrar datos y crear el administrador real

El sembrado crea los roles, permisos y parámetros de nómina. Para producción,
**crea tu propio administrador** en vez de usar el de demostración.

Siembra los datos base (roles, permisos, parámetros):

    python scripts/inicializar_datos.py

Luego cambia de inmediato la contraseña del administrador y, si el seed creó
usuarios de demostración, desactívalos o elimínalos. Nunca dejes en producción
las contraseñas de ejemplo (Admin123*, Demo123*).

---

## 5. HTTPS con proxy inverso

La app corre en HTTP en el puerto 8000; el proxy le pone HTTPS delante. Sin
HTTPS la PWA no funciona y las cookies viajan expuestas.

Arranca la app:

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Elige un proxy:

**Opción A — Caddy (más simple, certificado automático):**
Usa `despliegue/Caddyfile`, reemplaza el dominio, y corre:

    caddy run --config despliegue/Caddyfile

**Opción B — Nginx + certbot:**
Copia `despliegue/nginx-cafbardla.conf` a `/etc/nginx/sites-available/`,
reemplaza el dominio, actívalo y obtén el certificado:

    sudo certbot --nginx -d pos.tunegocio.com

Ambos pasan la IP real del cliente por `X-Forwarded-For`, que el sistema usa
para el rate limit y la auditoría.

---

## 6. Programar las copias de seguridad

El sistema hace copias comprimidas y verificadas. Además del botón en la app
(Copias de seguridad), programa una copia automática diaria.

**Windows (Programador de tareas):** crea una tarea diaria que ejecute:

    python D:\ruta\CafBarDLA\scripts\backup.py --retencion 30

**Linux (cron):** agrega a `crontab -e` una copia diaria a las 2am:

    0 2 * * *  cd /ruta/CafBarDLA && python scripts/backup.py --retencion 30

`--retencion 30` conserva las últimas 30 copias. Guarda una copia también fuera
del servidor (disco externo o nube): si el servidor falla, no pierdes todo.

Para restaurar una copia:

    python scripts/backup.py --restaurar NOMBRE_DE_LA_COPIA

---

## 7. Verificar

- Entra por HTTPS: el navegador debe mostrar el candado.
- Inicia sesión con tu administrador real.
- Comprueba que un rol limitado (ej: mesero) no ve los módulos restringidos.
- Crea una copia de seguridad desde la app y confirma que aparece como íntegra.
- Revisa la pantalla de Auditoría: deben verse tus accesos.

---

## Pendientes de seguridad (importantes)

Estos puntos dependen de ti y de tu entorno de código:

1. **Rota los secretos** que hayan estado en archivos de configuración y la
   contraseña de admin (ya cubierto si generaste nuevos en el paso 2).

2. **Purga el historial de git** si el repositorio tuvo bases de datos o
   secretos en commits anteriores. Usa BFG o git-filter-repo. Aunque el código
   actual esté limpio, el historial conserva lo viejo.

3. **Mantén PostgreSQL respaldado** también a nivel de servidor si tu
   infraestructura lo permite (además de los backups de la app).
