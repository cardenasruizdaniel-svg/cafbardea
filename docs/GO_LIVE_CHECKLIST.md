# ============================================================================
# CafBarDLA - Production Go-Live Checklist
# ============================================================================
# IMPORTANTE: Completar TODOS los items antes de go-live
# Cada sección tiene sub-items para validar
# ============================================================================

## 1. SEGURIDAD & CREDENCIALES ✓ VERIFICAR

### 1.1 Claves y Secretos
- [ ] JWT_SECRET_KEY: Generada con secrets.token_urlsafe(32)
- [ ] SESSION_SECRET_KEY: Generada con secrets.token_urlsafe(32)
- [ ] Ambas claves: Mínimo 32 caracteres
- [ ] Claves: Guardadas en .env.production (NO en versión control)
- [ ] .env.production: Añadida a .gitignore
- [ ] .env.production.example: NO contiene valores reales

### 1.2 Base de Datos
- [ ] Credenciales PostgreSQL cambiadas de defaults
- [ ] Contraseña cafbar_user: Mínimo 12 caracteres
- [ ] Base de datos: Creada con encoding UTF8
- [ ] Conexión: Verificada con usuario de aplicación
- [ ] Backup automático: Programado en Task Scheduler

### 1.3 SSL/TLS
- [ ] Certificado SSL: Instalado y válido
- [ ] Nginx: Configurado para HTTPS
- [ ] HTTP a HTTPS: Redirect configurado
- [ ] Protocolos: TLSv1.2+, Ciphers modernos
- [ ] HSTS: Habilitado con max-age=31536000
- [ ] Certificado: Válido por mínimo 30 días

### 1.4 CORS & Headers
- [ ] ALLOWED_ORIGINS: Configurados correctamente
- [ ] Headers de seguridad: Habilitados en Nginx
  - X-Frame-Options: SAMEORIGIN
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Strict-Transport-Security: enabled
- [ ] CSRF Protection: Habilitada

## 2. BASE DE DATOS ✓ VERIFICAR

### 2.1 Setup PostgreSQL
- [ ] PostgreSQL 13+: Instalado
- [ ] Servicio PostgreSQL: Activo y iniciado
- [ ] Base de datos: cafbardla_prod creada
- [ ] Usuario cafbar_user: Creado con permisos
- [ ] Conexión: Testeable desde aplicación

### 2.2 Migraciones
- [ ] Alembic: Versión compatible instalada
- [ ] Migraciones: Ejecutadas (alembic upgrade head)
- [ ] Tablas: Creadas sin errores
- [ ] Esquema: Validado contra models.py
- [ ] Datos iniciales: Usuarios admin creados
- [ ] Empresas: Mínimo 1 empresa en datos iniciales

### 2.3 Backups
- [ ] Directorio de backups: Creado (D:\Backups\CafBarDLA)
- [ ] Backup automático: Script configurado
- [ ] Task Scheduler: Tarea "CafBarDLA-Backup" activa
- [ ] Prueba de backup: Realizada manualmente
- [ ] Retención de backups: 30 días configurado
- [ ] Restauración: Testeable desde backup reciente

## 3. APLICACIÓN FASTAPI ✓ VERIFICAR

### 3.1 Configuración
- [ ] .env.production: Todas las variables configuradas
- [ ] DEBUG: False en producción
- [ ] LOG_LEVEL: INFO o WARN
- [ ] ENVIRONMENT: "production"
- [ ] WORKERS: 4+ para producción
- [ ] RELOAD: False en producción

### 3.2 Dependencias
- [ ] requirements.txt: Versiones pinned
- [ ] Python 3.9+: Versión soportada instalada
- [ ] Virtual environment: Actualizado con pip
- [ ] Pip packages: Todas las dependencias instaladas
- [ ] Importaciones: Sin errores al iniciar app

### 3.3 Endpoints
- [ ] /health: Disponible y respondiendo
- [ ] /api/v1/mobile/*: JWT authentication funcionando
- [ ] /api/v1/kds/*: Role-based access control funcionando
- [ ] /docs: Disponible (Swagger UI)
- [ ] /redoc: Disponible (ReDoc)
- [ ] /openapi.json: Schema API disponible

### 3.4 WebSocket
- [ ] Conexiones WebSocket: Aceptadas
- [ ] Autenticación de dispositivo: Validada
- [ ] Eventos de broadcast: Siendo enviados
- [ ] Reconexión automática: Funcionando
- [ ] Memory leaks: No presentes en conexiones largas

## 4. NGINX REVERSE PROXY ✓ VERIFICAR

### 4.1 Setup
- [ ] Nginx: Instalado y activo
- [ ] Config: nginx_cafbardla_production.conf aplicada
- [ ] Upstream backend: Configurado para puerto 8000
- [ ] Servicio Nginx: Iniciado automáticamente

### 4.2 Funcionalidad
- [ ] HTTP requests: Redirigiendo a HTTPS
- [ ] HTTPS requests: Funcionando
- [ ] WebSocket upgrade: Habilitado
- [ ] Compresión gzip: Activa
- [ ] Static files: Servidos correctamente
- [ ] Rate limiting: Configurado (10r/s)

### 4.3 Performance
- [ ] Response times: < 1 segundo para /health
- [ ] Conexiones simultáneas: Soportadas
- [ ] Memory usage: Estable bajo carga
- [ ] CPU usage: < 80% normal

## 5. DOCKER (Si aplica) ✓ VERIFICAR

### 5.1 Imágenes & Containers
- [ ] docker-compose.prod.yml: Válido
- [ ] Imágenes: Descargadas y buildadas
- [ ] Containers: Se inician correctamente
- [ ] Health checks: Pasando

### 5.2 Volúmenes & Redes
- [ ] Volúmenes: db_data, nginx_logs creados
- [ ] Red cafbardla_net: Funcional
- [ ] Persistencia: Datos sobreviven reinicio

### 5.3 Servicios
- [ ] PostgreSQL container: Sano y en exec
- [ ] FastAPI container: Sano y respondiendo
- [ ] Nginx container: Sano y ruteando
- [ ] Logs: No contienen errores críticos

## 6. MONITOREO & LOGGING ✓ VERIFICAR

### 6.1 Logging
- [ ] Log file: ./logs/cafbardla.log creado
- [ ] Log rotation: Configurado (10 backups, 100MB)
- [ ] Log level: INFO para info, WARN para warnings
- [ ] Errores: Registrados con traceback completo

### 6.2 Monitoreo
- [ ] Health check endpoint: Respondiendo
- [ ] Database monitoring: Conectividad verificada
- [ ] Memory usage: Monitoreado
- [ ] Disk space: > 50% disponible

### 6.3 Alertas (Opcional)
- [ ] Sentry: Configurado (si habilitado)
- [ ] Email alerts: Configurado (si aplica)
- [ ] Datadog: Configurado (si aplica)

## 7. TESTING ✓ VERIFICAR

### 7.1 Suite de Tests
- [ ] pytest: Todas las pruebas pasando (222/222)
- [ ] FASE 1-8: Tests ejecutados exitosamente
- [ ] Coverage: 99%+ de endpoints cubiertos
- [ ] Migraciones: Testeable sin errores

### 7.2 Manual Testing
- [ ] Mobile login: Exitoso con JWT
- [ ] Get mesas: Retorna lista completa
- [ ] Create order: Crea venta en BD
- [ ] KDS login: Solo chef/cocinero
- [ ] Update order status: Propaga cambios
- [ ] WebSocket: Notificaciones en tiempo real

### 7.3 Production Validation
- [ ] validate_production.ps1: Pasando todos los tests
- [ ] API endpoints: Respondiendo correctamente
- [ ] Database queries: Retornando datos esperados
- [ ] Response times: Dentro de SLA

## 8. PERFORMANCE & ESCALABILIDAD ✓ VERIFICAR

### 8.1 Load Testing
- [ ] Usuarios concurrentes: 50+ soportados
- [ ] Requests/segundo: 100+ procesados
- [ ] Response time p95: < 500ms
- [ ] Response time p99: < 1000ms
- [ ] Error rate: < 0.1%

### 8.2 Resource Usage
- [ ] CPU: < 80% bajo carga normal
- [ ] Memoria: < 2GB bajo carga normal
- [ ] Disco: > 50% disponible
- [ ] Conexiones DB: < 50 de 200 máximo

### 8.3 Backup & Recovery
- [ ] Tamaño backup: Razonable (< 500MB comprimido)
- [ ] Tiempo backup: < 5 minutos
- [ ] Tiempo restauración: < 10 minutos
- [ ] Integridad: Verificada

## 9. DOCUMENTACIÓN ✓ VERIFICAR

### 9.1 Operacional
- [ ] README.md: Actualizado con instrucciones prod
- [ ] docs/TESTING_PRODUCTION.md: Accesible y claro
- [ ] docs/MANUAL_TECNICO.md: Actualizado
- [ ] .env.production.example: Documentado

### 9.2 API
- [ ] Swagger (/docs): Accesible
- [ ] ReDoc (/redoc): Accesible
- [ ] OpenAPI schema: Completo

## 10. INSTALADOR WINDOWS ✓ VERIFICAR

### 10.1 Build
- [ ] PyInstaller: Buildeo exitoso
- [ ] Ejecutable: CafBarDLA.exe generado
- [ ] Tamaño: Razonable (< 500MB)
- [ ] NSIS: Script compilado

### 10.2 Instalador
- [ ] Setup.exe: Generado exitosamente
- [ ] Instalación: Completa sin errores
- [ ] Acceso directo: Creado en Inicio
- [ ] Desinstalación: Limpia correctamente
- [ ] Registro Windows: Entradas creadas

## 11. DATOS & USUARIOS ✓ VERIFICAR

### 11.1 Seed Data
- [ ] Empresas: Mínimo 1 creada
- [ ] Usuarios: Admin y otros roles creados
- [ ] Roles: Los 7 roles disponibles
- [ ] Permisos: Asignados correctamente

### 11.2 Usuarios de Prueba
- [ ] admin / admin: Login exitoso
- [ ] Mesero: Puede acceder app_mesero
- [ ] Chef: Puede acceder KDS
- [ ] Gerente: Permisos configurados

## 12. BUSINESS CONTINUITY ✓ VERIFICAR

### 12.1 Disaster Recovery
- [ ] Backup diario: Programado
- [ ] Punto de restauración: Testeable
- [ ] RTO (Recovery Time): < 30 minutos
- [ ] RPO (Recovery Point): < 24 horas

### 12.2 Redundancia
- [ ] Failover: Plan documentado
- [ ] Database replication: Configurada (si aplica)
- [ ] Load balancing: Configurado (si múltiples servidores)

## SIGN-OFF - PRODUCCIÓN LISTA

### Responsables
- [ ] Dev Lead: Aprobó código
- [ ] DevOps: Aprobó infraestructura
- [ ] QA Lead: Aprobó testing
- [ ] Project Manager: Autoriza go-live
- [ ] Business Owner: Aprobó funcionalidad

### Fecha Go-Live
Fecha: _________________
Hora: _________________
Timezone: America/Bogota

### Contacto en Emergencia
- Tech Lead: _________________
- Database Admin: _________________
- System Admin: _________________
- Product Owner: _________________

### Post-Launch Monitoring (Primeras 24h)
- [ ] Logs monitoreados activamente
- [ ] Performance baseline establecido
- [ ] Errores críticos: 0 (tolerancia máxima: 3)
- [ ] Response times: Dentro de SLA
- [ ] Backups: Completados exitosamente

---

## NOTAS Y CAMBIOS

```
[Espacio para notas durante deployment]



```

---

**Documento versión: 1.0**
**Última actualización: 2026-07-20**
**Próxima revisión: Post go-live + 1 semana**
