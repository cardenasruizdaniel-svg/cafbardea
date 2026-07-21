# 🌐 GUÍA DE DEPLOYMENT EN LA NUBE - CafBarDLA POS

## 📋 Tabla de Contenidos
1. [Opciones de Deployment](#opciones)
2. [Docker & Docker Compose](#docker)
3. [Heroku](#heroku)
4. [AWS](#aws)
5. [Azure](#azure)
6. [DigitalOcean](#digitalocean)
7. [Monitoreo y Mantenimiento](#monitoreo)

---

## 🎯 Opciones de Deployment {#opciones}

| Plataforma | Costo | Dificultad | Escalabilidad | Recomendado para |
|-----------|-------|-----------|---------------|-----------------|
| **Docker (VPS)** | $5-20/mes | Media | Alta | Pequeñas cafeterías |
| **Heroku** | $7-50/mes | Baja | Media | Startups/pruebas |
| **AWS** | $20-100+/mes | Alta | Muy Alta | Grandes cadenas |
| **Azure** | $15-100+/mes | Alta | Muy Alta | Empresas Microsoft |
| **DigitalOcean** | $5-40/mes | Media | Alta | RECOMENDADO ⭐ |

---

## 🐳 Docker & Docker Compose (RECOMENDADO - Local/VPS) {#docker}

### Prerequisitos
- Docker Desktop instalado (https://www.docker.com/products/docker-desktop)
- Docker Compose (incluido en Docker Desktop)

### Paso 1: Preparar configuración

```bash
# Copiar configuración de ejemplo
cp .env.production.example .env.production

# Editar variables de entorno
# - Cambiar ALLOWED_ORIGINS a tu dominio
# - Configurar rutas de backup
nano .env.production
```

### Paso 2: Construir imagen Docker

```bash
# Construir imagen local
docker build -t cafbardla:latest .

# Verificar imagen creada
docker images | grep cafbardla
```

### Paso 3: Ejecutar con Docker Compose

```bash
# En el directorio del proyecto (donde está docker-compose.yml)
docker-compose up -d

# Verificar que está corriendo
docker-compose ps
docker-compose logs -f app

# La aplicación estará en: http://localhost:8000
```

### Paso 4: Configurar base de datos en contenedor

```bash
# PostgreSQL automáticamente inicia en el contenedor
# Verificar conexión
docker-compose exec app python -c "
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Base de datos lista')
"

# O ejecutar migraciones
docker-compose exec app alembic upgrade head
```

### Paso 5: Backups automáticos en Docker

```bash
# Crear script de backup para contenedor Docker
docker-compose exec db pg_dump -U cafbardla -d cafbardla > backup_$(date +%Y%m%d_%H%M%S).sql

# O con script cron en el contenedor
docker-compose exec app crontab -e
# Agregar: 0 2 * * * /path/to/backup_script.sh
```

### Detener la aplicación

```bash
docker-compose down

# Con borrado de volúmenes (CUIDADO - borra BD)
docker-compose down -v
```

---

## 🚀 Heroku Deployment {#heroku}

### Prerequisitos
- Cuenta Heroku (https://www.heroku.com)
- Heroku CLI instalado

### Paso 1: Crear aplicación Heroku

```bash
# Login
heroku login

# Crear aplicación
heroku create cafbardla-pos
heroku stack:set heroku-22

# Agregar PostgreSQL (plan gratuito)
heroku addons:create heroku-postgresql:mini
```

### Paso 2: Configurar variables de entorno

```bash
# Copiar desde .env.production
heroku config:set ENVIRONMENT=production
heroku config:set JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
heroku config:set SESSION_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Base de datos (automática)
# La variable DATABASE_URL es creada por PostgreSQL addon
```

### Paso 3: Crear Procfile

Crear archivo `Procfile` en la raíz:

```
web: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
worker: python scripts/backup_heroku.py
```

### Paso 4: Crear requirements-heroku.txt

```bash
# Copiar requirements.txt y agregar gunicorn
cp requirements.txt requirements-heroku.txt
echo "gunicorn==21.2.0" >> requirements-heroku.txt
echo "uvicorn[standard]==0.32.1" >> requirements-heroku.txt
```

### Paso 5: Deploy

```bash
# Push a Heroku (automáticamente detecciona Python)
git push heroku main

# Ver logs
heroku logs --tail

# La aplicación estará en: https://cafbardla-pos.herokuapp.com
```

### Monitoreo en Heroku

```bash
# Verificar estado
heroku status

# Escalar dynos (pagar)
heroku ps:scale web=2

# Ejecutar migraciones
heroku run alembic upgrade head
```

---

## ☁️ AWS Deployment (EC2 + RDS) {#aws}

### Arquitectura
```
Internet Gateway
    ↓
Load Balancer (ALB)
    ↓
EC2 Instance (FastAPI App)
    ↓
RDS PostgreSQL (Managed DB)
```

### Paso 1: Crear instancia EC2

```bash
# En AWS Console o CLI
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t3.micro \
    --key-name my-keypair \
    --security-groups default \
    --region us-east-1

# Guardar ID de instancia
# Conectar: ssh -i my-keypair.pem ec2-user@<IP-PUBLICA>
```

### Paso 2: Instalar dependencias en EC2

```bash
# SSH a instancia
ssh -i my-keypair.pem ec2-user@<IP-PUBLICA>

# Actualizar sistema
sudo yum update -y
sudo yum install -y python3.11 python3.11-pip git postgresql

# Crear usuario para la app
sudo useradd cafbardla
sudo usermod -aG docker cafbardla
```

### Paso 3: Crear RDS PostgreSQL

```bash
# En AWS Console:
# - Engine: PostgreSQL 16
# - Instancia: db.t3.micro
# - Storage: 20 GB
# - Multi-AZ: No (para producción, sí)
# - Backup: 30 días

# Anotar endpoint: cafbardla-db.xxxxx.rds.amazonaws.com
# Username: admin (o personalizado)
# Password: GUARDAR EN SECRETO
```

### Paso 4: Configurar aplicación

```bash
# En EC2, clonar repositorio
git clone https://github.com/tuusuario/CafBarDLA.git
cd CafBarDLA

# Crear .env con RDS endpoint
cat > .env.production << EOF
DATABASE_URL=postgresql://admin:PASSWORD@cafbardla-db.xxxxx.rds.amazonaws.com:5432/cafbardla
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=4
JWT_SECRET_KEY=<GENERAR>
SESSION_SECRET_KEY=<GENERAR>
EOF

# Instalar dependencias
pip3 install -r requirements.txt
```

### Paso 5: Ejecutar con systemd

```bash
# Crear servicio
sudo cat > /etc/systemd/system/cafbardla.service << EOF
[Unit]
Description=CafBarDLA POS API
After=network.target

[Service]
User=cafbardla
WorkingDirectory=/home/cafbardla/CafBarDLA
Environment="PATH=/home/cafbardla/.venv/bin"
ExecStart=/home/cafbardla/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
EOF

# Iniciar
sudo systemctl daemon-reload
sudo systemctl enable cafbardla
sudo systemctl start cafbardla
sudo systemctl status cafbardla
```

### Paso 6: Configurar Security Group

```bash
# En AWS Console, permitir:
# - HTTP (80) desde Internet
# - HTTPS (443) desde Internet
# - PostgreSQL (5432) solo desde EC2
```

### Paso 7: SSL con Let's Encrypt

```bash
# Instalar certbot
sudo yum install certbot python3-certbot-nginx -y

# Obtener certificado
sudo certbot certonly --standalone -d cafbardla.tudominio.com

# Configurar Nginx como reverse proxy
sudo yum install nginx -y
sudo systemctl start nginx

# Actualizar nginx.conf para proxy a :8000
```

---

## 🔵 Azure Deployment (App Service) {#azure}

### Paso 1: Crear App Service

```bash
# Login
az login

# Crear grupo de recursos
az group create --name cafbardla-rg --location eastus

# Crear App Service Plan
az appservice plan create \
    --name cafbardla-plan \
    --resource-group cafbardla-rg \
    --sku B1 \
    --is-linux

# Crear App Service
az webapp create \
    --resource-group cafbardla-rg \
    --plan cafbardla-plan \
    --name cafbardla-pos \
    --runtime "PYTHON|3.11"
```

### Paso 2: Crear base de datos Azure

```bash
# PostgreSQL Flexible Server
az postgres flexible-server create \
    --resource-group cafbardla-rg \
    --name cafbardla-db \
    --location eastus \
    --admin-user admin \
    --admin-password <PASSWORD> \
    --sku-name Standard_B1ms \
    --tier Burstable
```

### Paso 3: Configurar y deploy

```bash
# Clonar repo en local
git clone https://github.com/tuusuario/CafBarDLA.git
cd CafBarDLA

# Crear .env con Azure PostgreSQL
# Obtener connection string de Azure Portal

# Crear startup script (startup.sh)
cat > startup.sh << EOF
#!/bin/bash
pip install -r requirements.txt
alembic upgrade head
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:\$PORT
EOF

chmod +x startup.sh

# Push a Azure (git integration)
git remote add azure <URL-Azure-Git>
git push azure main
```

---

## 🌊 DigitalOcean Deployment ⭐ (RECOMENDADO) {#digitalocean}

### ¿Por qué DigitalOcean?
- Precio: $4-6/mes (básico)
- Simplicidad: Interfaz muy intuitiva
- Documentación: Excelente
- Docker: Soporte nativo
- Escalabilidad: Fácil agregar recursos

### Paso 1: Crear Droplet

```bash
# En DigitalOcean Console:
# - OS: Ubuntu 22.04 LTS
# - Plan: Basic ($4/mes)
# - Region: Closest to you
# - Authentication: SSH key (recomendado)
```

### Paso 2: Configuración inicial

```bash
# SSH a droplet
ssh root@<DROPLET-IP>

# Crear usuario no-root
adduser cafbardla
usermod -aG sudo cafbardla
su - cafbardla

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker cafbardla

# Instalar docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Paso 3: Configurar UFW Firewall

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Paso 4: Clonar y ejecutar

```bash
# Clonar repositorio
git clone https://github.com/tuusuario/CafBarDLA.git
cd CafBarDLA

# Crear .env.production
cp .env.production.example .env.production
nano .env.production  # Editar ALLOWED_ORIGINS, etc.

# Ejecutar con Docker Compose
docker-compose up -d

# Verificar
docker-compose ps
docker-compose logs -f app
```

### Paso 5: SSL con Nginx

```bash
# Instalar Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Obtener certificado
sudo certbot certonly --standalone -d cafbardla.tudominio.com

# Configurar Nginx (ver abajo)
sudo nano /etc/nginx/sites-available/cafbardla

# Activar
sudo ln -s /etc/nginx/sites-available/cafbardla /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Nginx Reverse Proxy Config

```nginx
# /etc/nginx/sites-available/cafbardla

upstream fastapi_app {
    server localhost:8000;
}

server {
    listen 80;
    server_name cafbardla.tudominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name cafbardla.tudominio.com;

    ssl_certificate /etc/letsencrypt/live/cafbardla.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cafbardla.tudominio.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://fastapi_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Configurar Automatic Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Agregar a cron
sudo crontab -e
# Agregar: 0 2 * * * certbot renew --quiet
```

### Backups en DigitalOcean

```bash
# Usar DO Spaces (S3-compatible)
# 1. Crear Space en DigitalOcean Console
# 2. Configurar en .env:
#    BACKUP_S3_KEY=xxxx
#    BACKUP_S3_SECRET=xxxx
#    BACKUP_S3_ENDPOINT=nyc3.digitaloceanspaces.com
#    BACKUP_S3_BUCKET=cafbardla-backups

# Instalar boto3
pip install boto3

# Script de backup automático
cat > /home/cafbardla/backup_to_s3.sh << 'EOF'
#!/bin/bash
BACKUP_NAME="cafbardla_$(date +%Y%m%d_%H%M%S).sql"
docker-compose exec -T db pg_dump -U cafbardla -d cafbardla > /tmp/$BACKUP_NAME
aws s3 cp /tmp/$BACKUP_NAME s3://cafbardla-backups/ --endpoint-url https://nyc3.digitaloceanspaces.com
rm /tmp/$BACKUP_NAME
EOF

chmod +x /home/cafbardla/backup_to_s3.sh

# Agregar a cron para ejecutar cada 6 horas
0 */6 * * * /home/cafbardla/backup_to_s3.sh
```

---

## 📊 Monitoreo y Mantenimiento {#monitoreo}

### Health Checks

```bash
# Monitorear desde local
while true; do
    curl -s http://cafbardla-pos.tudominio.com/health | jq .
    sleep 30
done

# O configurar en DigitalOcean Health Checks
# https://docs.digitalocean.com/products/monitoring/dashboards/how-to/set-up-alerts/
```

### Logs

```bash
# Ver logs en tiempo real
docker-compose logs -f app

# Buscar errores
docker-compose logs app | grep ERROR

# Guardar en archivo
docker-compose logs app > logs.txt
```

### Mantenimiento

```bash
# Limpiar Docker
docker system prune -a --volumes

# Actualizar contenedores
docker-compose pull
docker-compose up -d --build

# Verificar versión
curl http://localhost:8000/api/v1/info

# Ejecutar migraciones nuevas
docker-compose exec app alembic upgrade head
```

### Monitoreo Avanzado

```bash
# Instalar Prometheus + Grafana (opcional)
docker run -d --name prometheus -p 9090:9090 prom/prometheus

# Configurar alertas
# - CPU > 80%
# - Memoria > 85%
# - Errores de API > 5%
# - Base de datos sin respuesta > 10s
```

---

## 🔐 Seguridad en Producción

### Checklist

- [ ] HTTPS/SSL habilitado
- [ ] Firewall configurado (solo puertos necesarios)
- [ ] Backups automáticos configurados
- [ ] Variables de entorno seguras (no en .git)
- [ ] Logs centralizados (CloudWatch, DataDog, etc)
- [ ] Monitoreo de uptime
- [ ] Rate limiting en API
- [ ] CORS configurado correctamente
- [ ] Database backup encriptado
- [ ] Credentials rotadas cada 90 días

### Secrets Management

```bash
# NUNCA hacer esto:
DATABASE_PASSWORD=mipassword123  # ❌ NUNCA

# Usar Variables de Entorno:
export DATABASE_PASSWORD=$(aws secretsmanager get-secret-value --secret-id cafbardla/db-password)

# O DigitalOcean Secrets
# O HashiCorp Vault
```

---

## 📞 Soporte y Recursos

- Documentación FastAPI: https://fastapi.tiangolo.com
- Docker: https://docs.docker.com
- DigitalOcean: https://docs.digitalocean.com
- AWS: https://docs.aws.amazon.com
- PostgreSQL: https://www.postgresql.org/docs

---

**Última actualización:** 2026-07-20  
**Versión:** 1.0  
**Mantenedor:** DLA Tecnología
