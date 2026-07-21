# FASE 8+ : Testing & Production Guide

## 1. Pruebas End-to-End Manual

### 1.1 Preparar Ambiente
```bash
# Activar entorno virtual
.\\.buildenv\\Scripts\\Activate.ps1

# Iniciar servidor
python app/main.py

# El servidor estará en http://127.0.0.1:8000
```

### 1.2 Test: Mobile App Login Flow

**Endpoint:** `POST /api/v1/mobile/auth/login`

```json
{
  "usuario": "mesero_test",
  "password": "MeseroTest123*",
  "device_id": "mobile-001",
  "device_type": "app_mesero"
}
```

**Response esperada (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "usuario_id": 1,
  "usuario_nombre": "Mesero Test",
  "sucursal_id": 1,
  "empresa_id": 1,
  "rol": "mesero",
  "dispositivo": "app_mesero"
}
```

### 1.3 Test: Get Mesas (con JWT token)

**Endpoint:** `GET /api/v1/mobile/mesas`

**Headers:**
```
Authorization: Bearer <token_from_login>
```

**Response esperada (200 OK):**
```json
[
  {
    "id": 1,
    "numero": "M1",
    "estado": "libre",
    "capacidad": 4,
    "venta_id": null
  }
]
```

### 1.4 Test: Create Order (Comanda)

**Endpoint:** `POST /api/v1/mobile/comandas`

**Headers:**
```
Authorization: Bearer <token>
```

**Body:**
```json
{
  "mesa_id": 1,
  "productos": [
    {
      "producto_id": 1,
      "cantidad": 2,
      "notas": "Sin azúcar"
    }
  ]
}
```

**Response esperada (200 OK):**
```json
{
  "venta_id": 1,
  "mesa_id": 1,
  "mesa_numero": "M1",
  "estado": "abierta",
  "productos": [
    {
      "producto_id": 1,
      "nombre": "Café",
      "cantidad": 2,
      "precio_unitario": 5000.0,
      "subtotal": 10000.0,
      "notas": "Sin azúcar",
      "estado": "pendiente"
    }
  ],
  "subtotal": 10000.0,
  "impuesto": 800.0,
  "total": 10800.0,
  "fecha_creacion": "2026-07-20T...",
  "ultima_actualizacion": "2026-07-20T..."
}
```

### 1.5 Test: KDS Login

**Endpoint:** `POST /api/v1/kds/auth/login`

```json
{
  "usuario": "chef_test",
  "password": "ChefTest123*",
  "device_id": "kds-cocina-1"
}
```

### 1.6 Test: Get Kitchen Orders (KDS)

**Endpoint:** `GET /api/v1/kds/pedidos`

**Headers:**
```
Authorization: Bearer <kds_token>
```

**Response esperada:**
```json
[
  {
    "venta_id": 1,
    "mesa_id": 1,
    "mesa_numero": "M1",
    "estado": "abierta",
    "prioridad": "normal",
    "items": [
      {
        "producto_id": 1,
        "codigo": "CAF-001",
        "nombre": "Café",
        "cantidad": 2,
        "estado": "pendiente",
        "notas": "Sin azúcar",
        "mesa_numero": "M1"
      }
    ],
    "tiempo_llegada": "2026-07-20T...",
    "notas_especiales": null,
    "cocinero_asignado": null
  }
]
```

### 1.7 Test: Update Order Status (KDS)

**Endpoint:** `PUT /api/v1/kds/pedidos/1/estado`

**Headers:**
```
Authorization: Bearer <kds_token>
```

**Body:**
```json
{
  "estado": "preparando"
}
```

**Response esperada (200 OK):**
```json
{
  "status": "updated",
  "venta_id": 1,
  "estado": "preparando"
}
```

### 1.8 Test: WebSocket Notifications

**URL:** `ws://127.0.0.1:8000/ws/1/app_mesero`

```json
// Cuando se actualiza estado en KDS, mobile recibe:
{
  "tipo": "evento",
  "evento": "pedido.actualizado",
  "datos": {
    "venta_id": 1,
    "estado": "preparando",
    "mesa_id": 1,
    "mesa_numero": "M1"
  }
}
```

---

## 2. Configuración para Producción

### 2.1 Variables de Entorno

Crear `.env.production`:

```bash
# FastAPI
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:password@localhost/cafbardla_prod

# JWT
JWT_SECRET_KEY=tu-clave-secreta-super-segura-32-chars-min

# CORS
ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://tu-dominio.com

# Session
SESSION_SECRET_KEY=otra-clave-secreta-diferente

# WebSocket
WS_CLIENTS_MAX=100
WS_PING_INTERVAL=30
WS_PING_TIMEOUT=10

# Backup
BACKUP_PATH=/backups/cafbardla
BACKUP_RETENTION_DAYS=30
```

### 2.2 Database Setup

```bash
# 1. Crear base de datos PostgreSQL
psql -U postgres
CREATE DATABASE cafbardla_prod;
CREATE USER cafbar_user WITH PASSWORD 'strong_password';
ALTER ROLE cafbar_user SET client_encoding TO 'utf8';
ALTER ROLE cafbar_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE cafbar_user SET default_transaction_deferrable TO on;
ALTER ROLE cafbar_user SET default_transaction_level TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE cafbardla_prod TO cafbar_user;

# 2. Ejecutar migraciones Alembic
alembic upgrade head

# 3. Seed datos iniciales (roles, permisos)
python -m app.enterprise_init
```

### 2.3 Backup Strategy

**Daily Backup Script** (`scripts/backup_postgres.ps1`):

```powershell
# Ya existe, modificar ruta y programar en Task Scheduler

# Programar en Windows Task Scheduler:
# Tarea: CafBarDLA Daily Backup
# Trigger: Diario a las 02:00 AM
# Action: powershell.exe -ExecutionPolicy Bypass -File C:\path\to\backup_postgres.ps1
```

### 2.4 Windows Installer Build

```bash
# 1. Build ejecutable
pyinstaller --onefile --windowed --icon=app_icon.ico launcher.py

# 2. Ya existe instalador NSIS
# Ubicación: installer/CafBarDLA.iss

# 3. Build instalador
iscc.exe installer/CafBarDLA.iss

# Resultado: dist/CafBarDLA-installer.exe
```

### 2.5 Nginx Reverse Proxy (Production)

Crear `nginx/cafbardla.conf`:

```nginx
upstream fastapi {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirigir HTTP a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws {
        proxy_pass http://fastapi;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2.6 Docker Deployment (Optional)

Crear `Dockerfile.prod`:

```dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.prod.yml`:

```yaml
version: '3.9'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: cafbardla_prod
      POSTGRES_USER: cafbar_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cafbar_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://cafbar_user:${DB_PASSWORD}@db:5432/cafbardla_prod
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      ENVIRONMENT: production
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data

volumes:
  pgdata:
```

Deploy:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 3. Monitoring & Logs

### 3.1 Logging Setup

Logs escriben en `logs/cafbardla.log`:

```python
# app/config.py ya configura logging
# Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Verificar logs
tail -f logs/cafbardla.log

# En Windows PowerShell:
Get-Content logs/cafbardla.log -Tail 20 -Wait
```

### 3.2 Performance Monitoring

```bash
# Verificar recursos de servidor
Get-Process python | Select CPU, Memory, ProcessName

# Monitorear conexiones DB
psql -U cafbar_user -d cafbardla_prod -c "SELECT count(*) FROM pg_stat_activity;"

# WebSocket connections (se registran en logs)
grep "ws_connected\|ws_disconnected" logs/cafbardla.log
```

### 3.3 Health Check Endpoint

**Endpoint:** `GET /health`

```json
{
  "status": "healthy",
  "timestamp": "2026-07-20T10:30:00",
  "database": "connected",
  "version": "1.0.0"
}
```

---

## 4. Security Checklist

- [ ] JWT_SECRET_KEY es único y fuerte (32+ caracteres)
- [ ] SESSION_SECRET_KEY es diferente a JWT_SECRET_KEY
- [ ] Database usa credenciales fuertes
- [ ] SSL/TLS configurado en Nginx
- [ ] CORS solo permite dominios autorizados
- [ ] Backups encriptados y fuera del servidor web
- [ ] Logs no contienen información sensible
- [ ] Rate limiting en endpoints públicos
- [ ] SQL injection protegido (SQLAlchemy ORM)
- [ ] CSRF tokens en formularios (session)

---

## 5. Troubleshooting

### Error: "Token expired"
- Token caduca después de 24 horas
- Cliente debe llamar a `POST /api/v1/mobile/auth/refresh`

### Error: "Database connection failed"
- Verificar DATABASE_URL en .env
- Verificar que PostgreSQL esté corriendo
- Verificar credenciales

### Error: "WebSocket connection refused"
- Verificar que servidor esté corriendo
- Verificar CORS settings
- Verificar firewall permite puerto 8000

### Performance slow
- Monitorear tamaño de logs (rotar si > 100MB)
- Verificar conexiones DB no se quedan abiertas
- Verificar índices de base de datos
- Considerar caching Redis

---

## 6. Deployment Checklist

- [ ] All 222 tests passing
- [ ] Environment variables configuradas
- [ ] Database migrado (alembic upgrade head)
- [ ] Backups automatizados configurados
- [ ] SSL/TLS certificados válidos
- [ ] Nginx reverse proxy configurado
- [ ] Logs rotativos habilitados
- [ ] Monitoreo y alertas activos
- [ ] Health check respondiendo
- [ ] Usuarios/roles iniciales creados
