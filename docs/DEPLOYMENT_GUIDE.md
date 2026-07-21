# ============================================================================
# CafBarDLA - Guía de Deployment en Producción
# ============================================================================
# Pasos para desplegar CafBarDLA en producción de forma segura
# Tiempo estimado: 2-3 horas para setup completo
# ============================================================================

## PREREQUISITOS

Antes de comenzar, verifica que tengas instalados:

```powershell
# Verificar Python
python --version  # 3.9+

# Verificar PostgreSQL
psql --version  # 13+

# Verificar PyInstaller (opcional)
pyinstaller --version

# Verificar NSIS (optional para Windows installer)
"C:\Program Files (x86)\NSIS\makensis.exe" /VERSION

# Instalar uvicorn y alembic
pip install uvicorn alembic sqlalchemy psycopg2-binary
```

---

## EJECUCIÓN PASO A PASO

### PASO 1: Configuración de Ambiente (.env.production)

**Ya está listo:** El archivo `.env.production` ha sido creado con valores de ejemplo.

**Qué debes cambiar:**
```powershell
# Abrir archivo de configuración
notepad .env.production

# Cambiar estos valores:
# 1. DATABASE_URL - URL de conexión PostgreSQL
# 2. JWT_SECRET_KEY - Clave segura generada
# 3. SESSION_SECRET_KEY - Clave segura generada
# 4. ALLOWED_ORIGINS - Dominios permitidos
# 5. EMPRESA_NOMBRE - Nombre de tu restaurante
# 6. EMPRESA_NIT - NIT de tu empresa
# 7. SMTP_* - Configuración de email (opcional)
```

**Guardar archivo cuando termines.**

---

### PASO 2: Setup de PostgreSQL

**Ejecutar script de setup:**
```powershell
cd d:\CafBarDLA
.\scripts\setup_postgres_production.ps1
```

**Qué hace:**
- ✓ Verifica instalación de PostgreSQL
- ✓ Crea usuario `cafbar_user` con contraseña segura
- ✓ Crea base de datos `cafbardla_prod`
- ✓ Configura permisos de usuario
- ✓ Valida conexión

**Resultado esperado:**
```
Setup PostgreSQL Completado ✓
Conexión de cadena para .env.production:
DATABASE_URL=postgresql://cafbar_user:...@localhost:5432/cafbardla_prod
```

---

### PASO 3: Ejecutar Migraciones Alembic

**Ejecutar script de migraciones:**
```powershell
.\scripts\run_migrations_production.ps1
```

**Qué hace:**
- ✓ Carga variables de `.env.production`
- ✓ Verifica conexión a base de datos
- ✓ Ejecuta `alembic upgrade head`
- ✓ Crea todas las tablas y esquemas

**Resultado esperado:**
```
[3/3] Ejecutando migraciones Alembic...
✓ Migraciones completadas exitosamente

Migraciones Completadas ✓
Base de datos lista para producción
```

---

### PASO 4: Configurar Backups Automáticos

#### 4.1 Ejecutar backup manual (prueba)
```powershell
.\scripts\backup_postgres_production.ps1
```

#### 4.2 Programar tarea automática (debe ejecutarse como Admin)

```powershell
# Abrir PowerShell como Administrador

# Luego ejecutar:
.\scripts\schedule_backup_task.ps1
```

**Qué hace:**
- ✓ Crea tarea en Windows Task Scheduler
- ✓ Programa backup para las 2:00 AM diariamente
- ✓ Limpia backups antiguos (> 30 días)

**Verificar tarea creada:**
```powershell
Get-ScheduledTask -TaskName 'CafBarDLA-Backup'
```

---

### PASO 5: Pruebas Pre-Producción

#### 5.1 Ejecutar suite de tests
```powershell
# Todos los tests
python -m pytest tests/ -v

# Solo tests de producción
python -m pytest tests/enterprise/ -v
```

**Resultado esperado:**
```
222 passed in 9.02s ✓
```

#### 5.2 Iniciar servidor FastAPI
```powershell
# Modo desarrollo (con debug)
python -m uvicorn app.main:app --reload

# Modo producción (sin reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 5.3 Validar endpoints
```powershell
# Abrir nueva terminal PowerShell

# Health check
curl http://localhost:8000/health

# API documentation
Start-Process http://localhost:8000/docs

# Test mobile login
$body = @{ usuario = "admin"; password = "admin" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/api/v1/mobile/auth/login `
  -Method Post -Body $body -ContentType "application/json"
```

---

### PASO 6: Validación de Producción

**Ejecutar suite completa de validación:**
```powershell
.\scripts\validate_production.ps1
```

**Qué valida:**
- ✓ Conexión a base de datos
- ✓ Servidor FastAPI respondiendo
- ✓ API documentation disponible
- ✓ Endpoints REST funcionando
- ✓ WebSocket disponible
- ✓ Response times aceptables

**Resultado esperado:**
```
Resultados de Validación
════════════════════════
✓ Pasados: 7
✗ Fallidos: 0

PRODUCCIÓN LISTA ✓
```

---

### PASO 7: Build del Instalador Windows (Opcional)

**Para crear ejecutable distribuible:**

#### 7.1 Instalar dependencias de build
```powershell
pip install pyinstaller
# Descargar e instalar NSIS desde https://nsis.sourceforge.io/
```

#### 7.2 Crear instalador
```powershell
.\scripts\build_windows_installer_production.ps1 -Version "1.0.0"
```

**Resultado:**
```
Build Completado ✓
Instalador: CafBarDLA-Setup-1.0.0.exe
Tamaño: ~200 MB
```

---

### PASO 8: Deployment con Nginx (Recomendado)

#### 8.1 Instalar y configurar Nginx
```powershell
# En Windows o Linux
# Copiar config
Copy-Item config\nginx_cafbardla_production.conf C:\nginx\conf\sites-available\

# Probar configuración
nginx -t

# Iniciar Nginx
Start-Service nginx
# o
.\nginx.exe
```

#### 8.2 Configurar certificado SSL (Let's Encrypt)
```bash
# En Linux/WSL:
certbot certonly --standalone -d tudominio.com

# Renovación automática cada 3 meses:
certbot renew --quiet --no-self-upgrade
```

---

### PASO 9: Deployment con Docker (Alternativa)

**Si prefieres usar Docker:**

#### 9.1 Construir imágenes
```powershell
docker-compose -f docker-compose.prod.yml build
```

#### 9.2 Iniciar servicios
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

#### 9.3 Verificar estado
```powershell
docker-compose -f docker-compose.prod.yml ps

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f app
```

---

### PASO 10: Checklist Pre Go-Live

**Antes de activar en producción:**

Abrir documento y completar checklist:
```powershell
notepad docs\GO_LIVE_CHECKLIST.md
```

**Puntos críticos:**
- [ ] Todas las variables en `.env.production` configuradas
- [ ] Base de datos conectada y migraciones ejecutadas
- [ ] Backups programados y probados
- [ ] SSL/TLS configurado (si usando Nginx)
- [ ] Suite de validación pasando completamente
- [ ] 222 tests pasando en local
- [ ] Documentación leída y entendida

---

## VERIFICACIONES POST-DEPLOYMENT

### Inmediatamente después del go-live (Primeras 24 horas)

```powershell
# 1. Verificar aplicación disponible
curl https://tudominio.com/health

# 2. Verificar logs por errores
Get-Content .\logs\cafbardla.log -Tail 50

# 3. Verificar base de datos
psql -U cafbar_user -d cafbardla_prod -c "SELECT COUNT(*) FROM usuarios;"

# 4. Verificar backup
Get-ChildItem D:\Backups\CafBarDLA\

# 5. Test mobile login en producción
$token = (Invoke-RestMethod -Uri "https://tudominio.com/api/v1/mobile/auth/login" `
  -Method Post `
  -Body (@{usuario="admin"; password="admin"} | ConvertTo-Json) `
  -ContentType "application/json").access_token

# 6. Test endpoint protegido
Invoke-RestMethod -Uri "https://tudominio.com/api/v1/mobile/mesas" `
  -Headers @{"Authorization"="Bearer $token"}
```

---

## TROUBLESHOOTING

### Error: "No se puede conectar a PostgreSQL"
```powershell
# Verificar servicio está corriendo
Get-Service -Name postgresql-x64-*

# Iniciar servicio
Start-Service -Name postgresql-x64-13
```

### Error: "JWT_SECRET_KEY debe tener 32 caracteres"
```powershell
# Generar nueva clave
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Actualizar .env.production
```

### Error: "Port 8000 already in use"
```powershell
# Encontrar proceso usando puerto
netstat -ano | findstr :8000

# Matar proceso (reemplazar PID)
taskkill /PID <PID> /F
```

### WebSocket no conecta desde cliente móvil
```powershell
# Verificar Nginx tiene upgrade WebSocket
# En nginx config debe estar:
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# Reiniciar Nginx
nginx -s reload
```

---

## MONITOREO CONTINUO

### Logs
```powershell
# Ver últimas 50 líneas
Get-Content .\logs\cafbardla.log -Tail 50

# En tiempo real (Windows)
Get-Content .\logs\cafbardla.log -Tail 1 -Wait

# Buscar errores
Select-String "ERROR" .\logs\cafbardla.log
```

### Performance
```powershell
# CPU y memoria
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Conexiones base de datos
psql -U cafbar_user -d cafbardla_prod -c "SELECT count(*) FROM pg_stat_activity;"
```

### Backups
```powershell
# Listar backups recientes
Get-ChildItem D:\Backups\CafBarDLA\ | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

---

## SOPORTE Y ESCALABILIDAD

### Para aumentar capacidad:
1. Agregar workers en Uvicorn (Paso 6, `--workers 8+`)
2. Aumentar pool de conexiones PostgreSQL
3. Usar Redis para caching
4. Load balancer para múltiples instancias

### Contacto técnico:
- Documentación: `docs/MANUAL_TECNICO.md`
- API Docs: `https://tudominio.com/docs`
- Logs: `./logs/cafbardla.log`

---

**Guía versión: 1.0**
**Última actualización: 2026-07-20**
**Repositorio:** d:\CafBarDLA
