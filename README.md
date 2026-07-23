# CafBarDLA POS

Desarrollado por **DLA Tecnología – Software – Ciberseguridad**.

Sistema base para café, bar y restaurante: ventas por mesa, inventario, producción, gastos, cartera, empleados, turnos e informes. Está desarrollado con **Python/FastAPI**, **PostgreSQL** y una interfaz web adaptable a computadores, tabletas y móviles.

Consulte la documentación en [`docs/`](docs/).

## Arranque rápido en Windows

1. Copie `.env.windows.example` como `.env` y configure `DATABASE_URL` apuntando a PostgreSQL.
2. Ejecute `scripts\run_windows.ps1` desde PowerShell.
3. Para crear el ejecutable e instalador: `scripts\build_windows_installer.ps1`. El instalador requiere [Inno Setup](https://jrsoftware.org/isinfo.php) y genera un `Setup.exe` cuando está disponible.

## Deployment con Docker (producción)

1. Copie `.env.production.example` como `.env.production` y configure al menos:
	- `SECRET_KEY`
	- `POSTGRES_PASSWORD` (variable de entorno del sistema o en shell)

2. Levante servicios:

	```bash
	docker-compose up -d --build
	```

3. Verifique estado:

	```bash
	docker-compose ps
	docker-compose logs -f web
	```

4. Acceso:
	- App: `http://localhost:8000`
	- API docs: `http://localhost:8000/docs`

5. Detener servicios:

	```bash
	docker-compose down
	```

6. Validacion automatizada (opcional, recomendada):

	```powershell
	powershell -ExecutionPolicy Bypass -File scripts/validate_docker_production.ps1
	```

## Deployment en Render

1. Publica el repositorio en GitHub o GitLab.
2. En Render, crea un nuevo servicio desde Blueprint y selecciona `render.yaml`.
3. Crea o adjunta una base PostgreSQL y configura `DATABASE_URL` en el servicio.
4. Asegura `SECRET_KEY` y `ENVIRONMENT=production`.
5. Revisa la guía detallada en [`docs/DEPLOYMENT_RENDER.md`](docs/DEPLOYMENT_RENDER.md).
6. Si el servicio ya existe, usa `Manual Deploy` para actualizar el despliegue con el último commit.
