# Instalación y despliegue

## Requisitos

- Docker Desktop 24 o superior (recomendado), o Python 3.12 y PostgreSQL 16.
- Puerto 8000 disponible para la aplicación y 5432 si se expone PostgreSQL.

## Instalación local con Docker

1. Abra una terminal en la carpeta del proyecto.
2. Revise `.env` y reemplace `SECRET_KEY` por una clave larga y privada.
3. Ejecute `docker compose up --build -d`.
4. Abra `http://localhost:8000`.

La primera ejecución crea la base `cafenexus`, el esquema y datos de ejemplo. Para detenerla use `docker compose down`. Los datos permanecen en el volumen `postgres_data`.

## Instalador Windows

El proyecto incluye `scripts\build_windows_installer.ps1`, que crea la carpeta ejecutable `dist\CafeNexus` con PyInstaller y, si está instalado Inno Setup, genera `installer\Output\CafeNexus-Setup.exe`.

1. Instale Python 3.12, PostgreSQL 16 e Inno Setup en el equipo de construcción.
2. Ejecute `scripts\build_windows_installer.ps1` desde PowerShell.
3. Instale el `Setup.exe` creado.
4. Antes del primer arranque, edite `{carpeta de instalación}\.env` con los datos de PostgreSQL y una clave secreta propia.

El ejecutable abre la aplicación en el navegador predeterminado. Para tabletas o móviles en la misma red, despliegue el servicio con Docker/servidor y habilite acceso controlado por HTTPS; el ejecutable local escucha únicamente en el propio equipo.

## Ejecución sin Docker

1. Cree la base y usuario PostgreSQL:
   ```sql
   CREATE USER cafenexus WITH PASSWORD 'una-clave-segura';
   CREATE DATABASE cafenexus OWNER cafenexus;
   ```
2. Cree y active un entorno virtual: `python -m venv .venv`.
3. Instale: `.venv\Scripts\pip install -r requirements.txt` (Windows) o `source .venv/bin/activate && pip install -r requirements.txt`.
4. Copie `.env.example` a `.env` y ajuste `DATABASE_URL` para apuntar a PostgreSQL.
5. Ejecute `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

## Nube y producción

La imagen Docker se puede publicar en cualquier servicio que ejecute contenedores (AWS ECS, Azure Container Apps, Google Cloud Run, DigitalOcean o VPS). Use una base PostgreSQL administrada, defina `DATABASE_URL` y `SECRET_KEY` como secretos y active HTTPS a través de un proxy (Nginx, Caddy o el proveedor). No exponga la base de datos a Internet. Programe respaldos diarios y pruebe una restauración periódicamente.

Antes de producción se recomienda añadir autenticación/roles, facturación electrónica conforme a la jurisdicción, auditoría, copias de seguridad y migraciones Alembic en su canal de despliegue.

## Migraciones y respaldos

En desarrollo, `AUTO_CREATE_SCHEMA=true` crea el esquema inicial automáticamente. En producción defina `AUTO_CREATE_SCHEMA=false` y ejecute antes de arrancar una nueva versión:

```powershell
alembic upgrade head
```

Para cambios futuros del modelo: `alembic revision --autogenerate -m "descripcion del cambio"` y revise siempre el archivo generado antes de aplicarlo. Realice un respaldo antes de cada actualización:

```powershell
.\scripts\backup_postgres.ps1 -DatabaseUrl "postgresql://usuario:clave@servidor:5432/cafenexus" -OutputDirectory ".\backups"
```

Pruebe la restauración en una base distinta antes de depender del respaldo en producción.
