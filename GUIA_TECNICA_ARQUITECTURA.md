# 🔧 GUÍA TÉCNICA: ARQUITECTURA + ESTRUCTURAS DE CÓDIGO

## I. ESTRUCTURA DE CARPETAS RECOMENDADA

```
d:\CafBarDLA\
├── alembic/                    # Migraciones BD
│   ├── versions/               # Scripts de migración
│   ├── env.py
│   └── script.py.mako
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + lifespan
│   ├── config.py               # Settings + logging
│   ├── database.py             # SQLAlchemy setup
│   │
│   ├── models/                 # ✨ NUEVA CARPETA
│   │   ├── __init__.py
│   │   ├── base.py             # BaseModel clase base
│   │   ├── empresa.py          # Empresa, Configuracion
│   │   ├── ventas.py           # Venta, DetalleVenta, FacturaPDF
│   │   ├── mesas.py            # Zona, Mesa, EstadoMesaHistorico
│   │   ├── productos.py        # Producto, Variante, Addon, Categoria
│   │   ├── inventario.py       # MovimientoInventario, etc
│   │   ├── recetas.py          # Receta, RecetaDetalle, OrdenProduccion
│   │   ├── empleados.py        # Empleado, Usuario, Asistencia, Permiso
│   │   ├── nomina.py           # Nomina, DetalleNomina, etc
│   │   ├── gastos.py           # Gasto, CategoriaGasto
│   │   ├── comisiones.py       # Comision, Propina
│   │   ├── notificaciones.py   # Notificacion
│   │   └── auditoria.py        # Audit logs
│   │
│   ├── schemas/                # ✨ MEJORADA
│   │   ├── __init__.py
│   │   ├── base.py             # Schemas base
│   │   ├── ventas.py           # VentaCreate, VentaResponse, etc
│   │   ├── productos.py
│   │   ├── mesas.py
│   │   ├── inventario.py
│   │   ├── empleados.py
│   │   ├── nomina.py
│   │   └── [otros].py
│   │
│   ├── routes/                 # ✨ NUEVA CARPETA (endpoints)
│   │   ├── __init__.py
│   │   ├── api_v1.py           # Importa subrutas
│   │   ├── ventas.py           # router.post("/ventas"), etc
│   │   ├── productos.py
│   │   ├── mesas.py
│   │   ├── inventario.py
│   │   ├── empleados.py
│   │   ├── nomina.py
│   │   ├── reportes.py
│   │   ├── dashboard.py
│   │   ├── websocket.py        # WebSocket endpoints
│   │   └── [otros].py
│   │
│   ├── services/               # ✨ NUEVA CARPETA (lógica negocio)
│   │   ├── __init__.py
│   │   ├── venta_service.py    # Calcular impuestos, generar factura
│   │   ├── inventario_service.py # Decrementar stock, alertas
│   │   ├── nómina_service.py   # Calcular nómina, comisiones
│   │   ├── receta_service.py   # Cálculo de costos, merma
│   │   ├── reporte_service.py  # Generación de reportes
│   │   ├── notificacion_service.py # Enviar notificaciones
│   │   └── [otros].py
│   │
│   ├── utils/                  # ✨ MEJORADA
│   │   ├── __init__.py
│   │   ├── validaciones.py     # Custom validators
│   │   ├── formatos.py         # Formatear moneda, fecha
│   │   ├── calculos.py         # Calcular UVT, retención
│   │   ├── errores.py          # Custom exceptions
│   │   ├── decoradores.py      # @require_role, @require_permission
│   │   ├── exportadores.py     # Generar Excel, PDF
│   │   └── autenticacion.py    # JWT helpers
│   │
│   ├── tasks/                  # ✨ NUEVA CARPETA (background jobs)
│   │   ├── __init__.py
│   │   ├── actualizaciones_nocturas.py # Recalcular vistas, backups
│   │   └── alertas.py          # Enviar alertas de stock
│   │
│   ├── static/                 # Frontend (ya existe)
│   │   ├── css/
│   │   │   ├── design-system.css
│   │   │   ├── layout.css
│   │   │   ├── dashboard.css
│   │   │   ├── components.css
│   │   │   └── app-additional.css
│   │   │
│   │   └── js/
│   │       ├── app.js          # Inicialización global
│   │       ├── components/     # ✨ NUEVA CARPETA
│   │       │   ├── Modal.js
│   │       │   ├── Table.js
│   │       │   ├── Form.js
│   │       │   ├── Notification.js
│   │       │   └── [otros].js
│   │       │
│   │       ├── services/       # ✨ NUEVA CARPETA
│   │       │   ├── api.js      # Fetch wrapper
│   │       │   ├── websocket.js
│   │       │   ├── storage.js  # LocalStorage helpers
│   │       │   └── notify.js   # Notificaciones
│   │       │
│   │       └── pages/          # ✨ NUEVA CARPETA
│   │           ├── pos.js
│   │           ├── productos.js
│   │           ├── mesas.js
│   │           ├── reportes.js
│   │           ├── dashboard.js
│   │           └── [otros].js
│   │
│   └── templates/              # Frontend HTML (ya existe)
│       ├── base.html           # Versión vieja
│       ├── base_premium.html   # ✨ Nueva (usar siempre esta)
│       ├── dashboard.html
│       ├── pos.html
│       ├── productos.html
│       ├── mesas.html
│       ├── reportes.html
│       └── [otros].html
│
├── tests/                      # ✨ NUEVA CARPETA
│   ├── conftest.py             # Fixtures pytest
│   ├── test_models.py
│   ├── test_schemas.py
│   ├── test_routes/
│   │   ├── test_ventas.py
│   │   ├── test_productos.py
│   │   ├── test_mesas.py
│   │   └── [otros].py
│   ├── test_services/
│   │   ├── test_venta_service.py
│   │   ├── test_nomina_service.py
│   │   └── [otros].py
│   └── test_integration/
│       └── test_flujo_completo.py
│
├── docs/                       # Documentación (ya existe)
│   ├── INSTALACION.md
│   ├── MANUAL_TECNICO.md
│   ├── API.md                  # ✨ NEW
│   └── [otros].md
│
├── .github/
│   └── workflows/
│       ├── tests.yml           # CI: pytest
│       ├── lint.yml            # CI: black, flake8
│       └── deploy.yml          # CD: deploy to prod
│
├── .env.example                # ✨ NEW
├── requirements.txt            # ✨ MEJORADO (agregar: slowapi, pandas, etc)
├── requirements-dev.txt        # ✨ NEW (pytest, black, etc)
├── pytest.ini                  # ✨ NEW
├── .gitignore                  # ✨ MEJORADO
├── docker-compose.yml          # ✨ MEJORADO
└── PRD_MAESTRO_ESTRATEGICO.md  # ✨ Este documento
```

---

## II. PATRONES DE CÓDIGO

### A. Modelo SQLAlchemy (Ejemplo: Venta)

```python
# app/models/ventas.py

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Boolean, Text, JSON, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Venta(Base):
    __tablename__ = "ventas"
    
    # Campos de identidad
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    mesa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mesas.id"), nullable=True)
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    empleado_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    
    # Timestamps
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Estado
    estado: Mapped[str] = mapped_column(
        String(20),
        default="abierta",
        CheckConstraint("estado IN ('abierta', 'cerrada', 'anulada', 'en_espera')")
    )
    
    # Dinero
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    descuento_pesos: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    descuento_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5,2), default=0)
    impuesto_value: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    propina_pesos: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    total_pago: Mapped[Decimal] = mapped_column(Numeric(14,2), default=0)
    
    # Facturación
    numero_factura: Mapped[Optional[str]] = mapped_column(String(40), unique=True, nullable=True)
    medio_pago: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    
    # Anulación
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    anulada_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    fecha_anulacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    canal: Mapped[str] = mapped_column(String(20), default="mesa")
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    detalles: Mapped[List["DetalleVenta"]] = relationship(
        back_populates="venta",
        cascade="all, delete-orphan",
        lazy="joined"  # Eager loading
    )
    
    # Computed Properties
    @property
    def total_items(self) -> int:
        return sum(int(d.cantidad) for d in self.detalles)
    
    @property
    def margen_porcentaje(self) -> Decimal:
        if self.subtotal == 0:
            return Decimal(0)
        costo_total = sum(
            d.cantidad * d.costo_unitario for d in self.detalles
        )
        return ((self.subtotal - costo_total) / self.subtotal) * 100
    
    def __repr__(self):
        return f"<Venta id={self.id} mesa={self.mesa_id} total={self.total_pago}>"
```

### B. Pydantic Schema (Validaciones)

```python
# app/schemas/ventas.py

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class DetalleVentaCreate(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: Decimal = Field(..., gt=0, decimal_places=3)
    precio_unitario: Decimal = Field(..., gt=0, decimal_places=2)
    notas_especiales: Optional[str] = None
    
    @field_validator('cantidad')
    @classmethod
    def validar_cantidad(cls, v):
        if v > 10000:
            raise ValueError("Cantidad no puede exceder 10000")
        return v

class VentaCreate(BaseModel):
    mesa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    canal: str = Field(default="mesa", pattern="^(mesa|delivery|domicilio|mostrador)$")
    observaciones: Optional[str] = None
    
    @field_validator('mesa_id', 'cliente_id', mode='before')
    @classmethod
    def debe_haber_al_menos_uno(cls, v, info):
        # Mesa o cliente debe existir
        if info.field_name == 'mesa_id' and not v:
            if not info.data.get('cliente_id'):
                raise ValueError("Debe especificar mesa O cliente")
        return v

class VentaResponse(BaseModel):
    id: int
    mesa_id: Optional[int]
    cliente_id: Optional[int]
    total_pago: Decimal
    estado: str
    numero_factura: Optional[str]
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime]
    
    class Config:
        from_attributes = True  # ORM mode
```

### C. Endpoint API (FastAPI)

```python
# app/routes/ventas.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal
from typing import List

from app.database import get_db
from app.models.ventas import Venta, DetalleVenta
from app.schemas.ventas import VentaCreate, VentaResponse, DetalleVentaCreate
from app.services.venta_service import VentaService
from app.utils.decoradores import require_role, require_permission

router = APIRouter(prefix="/api/v1/ventas", tags=["ventas"])

@router.post("", response_model=VentaResponse, status_code=201)
@require_role("mesero", "admin")
@require_permission("venta:crear")
async def crear_venta(
    venta_data: VentaCreate,
    db: Session = Depends(get_db),
    current_usuario = Depends(get_current_usuario)
) -> VentaResponse:
    """
    Crear nueva venta (abre transacción)
    
    - **mesa_id** o **cliente_id** requerido
    - Calcula automáticamente impuestos
    """
    
    # Validar existencia
    if venta_data.mesa_id:
        mesa = db.get(Mesa, venta_data.mesa_id)
        if not mesa:
            raise HTTPException(status_code=404, detail="Mesa no existe")
    
    if venta_data.cliente_id:
        cliente = db.get(Cliente, venta_data.cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no existe")
    
    # Crear venta
    try:
        venta_service = VentaService(db)
        venta = venta_service.crear_venta(venta_data, current_usuario)
        db.commit()
        return VentaResponse.from_orm(venta)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{venta_id}/items", response_model=VentaResponse)
@require_role("mesero", "admin")
async def agregar_item(
    venta_id: int,
    item: DetalleVentaCreate,
    db: Session = Depends(get_db)
) -> VentaResponse:
    """Agregar item a venta abierta"""
    
    venta = db.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no existe")
    
    if venta.estado != "abierta":
        raise HTTPException(status_code=400, detail="Venta no está abierta")
    
    try:
        venta_service = VentaService(db)
        venta_service.agregar_item(venta, item)
        db.commit()
        return VentaResponse.from_orm(venta)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{venta_id}/cerrar", response_model=VentaResponse)
@require_role("mesero", "admin")
@require_permission("venta:cobrar")
async def cerrar_venta(
    venta_id: int,
    medio_pago: str = "efectivo",
    db: Session = Depends(get_db),
    current_usuario = Depends(get_current_usuario)
) -> VentaResponse:
    """Cerrar venta y procesar pago"""
    
    venta = db.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no existe")
    
    try:
        venta_service = VentaService(db)
        venta = venta_service.cerrar_venta(venta, medio_pago, current_usuario)
        db.commit()
        return VentaResponse.from_orm(venta)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{venta_id}/anular", response_model=VentaResponse)
@require_role("admin", "gerente")
@require_permission("venta:anular")
async def anular_venta(
    venta_id: int,
    motivo: str,
    db: Session = Depends(get_db),
    current_usuario = Depends(get_current_usuario)
) -> VentaResponse:
    """Anular venta cerrada (genera nota de crédito)"""
    
    venta = db.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no existe")
    
    if venta.estado != "cerrada":
        raise HTTPException(status_code=400, detail="Solo se pueden anular ventas cerradas")
    
    try:
        venta_service = VentaService(db)
        venta = venta_service.anular_venta(venta, motivo, current_usuario)
        db.commit()
        return VentaResponse.from_orm(venta)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{venta_id}", response_model=VentaResponse)
@require_role("mesero", "admin", "gerente")
async def obtener_venta(
    venta_id: int,
    db: Session = Depends(get_db)
) -> VentaResponse:
    """Obtener detalle de venta"""
    venta = db.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no existe")
    return VentaResponse.from_orm(venta)

@router.get("", response_model=List[VentaResponse])
@require_role("admin", "gerente", "mesero")
async def listar_ventas(
    skip: int = 0,
    limit: int = 50,
    estado: str = None,
    db: Session = Depends(get_db)
) -> List[VentaResponse]:
    """Listar ventas con paginación"""
    
    query = select(Venta).offset(skip).limit(limit)
    
    if estado:
        query = query.where(Venta.estado == estado)
    
    ventas = db.execute(query).scalars().all()
    return [VentaResponse.from_orm(v) for v in ventas]
```

### D. Service (Lógica de Negocio)

```python
# app/services/venta_service.py

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.ventas import Venta, DetalleVenta
from app.models.productos import Producto
from app.models.empresa import Empresa
from app.utils.calculos import calcular_impuesto

class VentaService:
    def __init__(self, db: Session):
        self.db = db
    
    def crear_venta(self, venta_data, usuario_actual) -> Venta:
        """Crear nueva venta"""
        venta = Venta(
            mesa_id=venta_data.mesa_id,
            cliente_id=venta_data.cliente_id,
            empleado_id=usuario_actual.empleado_id,
            empresa_id=usuario_actual.empresa_id,
            canal=venta_data.canal
        )
        self.db.add(venta)
        self.db.flush()
        return venta
    
    def agregar_item(self, venta: Venta, item_data) -> None:
        """Agregar item a venta"""
        
        # Validar producto
        producto = self.db.get(Producto, item_data.producto_id)
        if not producto:
            raise ValueError("Producto no existe")
        
        # Validar stock
        if item_data.cantidad > producto.existencias:
            raise ValueError(f"Stock insuficiente. Disponible: {producto.existencias}")
        
        # Crear detalle
        detalle = DetalleVenta(
            venta_id=venta.id,
            producto_id=producto.id,
            cantidad=item_data.cantidad,
            precio=item_data.precio_unitario,
            costo_unitario=producto.costo,
            notas_especiales=item_data.notas_especiales
        )
        
        venta.detalles.append(detalle)
        
        # Recalcular totales
        self._recalcular_totales(venta)
    
    def cerrar_venta(self, venta: Venta, medio_pago: str, usuario_actual) -> Venta:
        """Cerrar venta y generar factura"""
        
        if not venta.detalles:
            raise ValueError("Venta sin items no puede cerrarse")
        
        # Generar número de factura
        empresa = self.db.get(Empresa, venta.empresa_id)
        venta.numero_factura = self._generar_numero_factura(empresa)
        
        # Marcar como cerrada
        venta.estado = "cerrada"
        venta.fecha_cierre = datetime.utcnow()
        venta.medio_pago = medio_pago
        
        # Decrementar inventario
        for detalle in venta.detalles:
            producto = detalle.producto  # Ya cargado lazy
            producto.existencias -= detalle.cantidad
            
            # Registrar movimiento
            self._registrar_movimiento_inventario(
                producto=producto,
                cantidad=-detalle.cantidad,
                tipo="venta",
                referencia=f"venta_{venta.id}"
            )
        
        # Actualizar saldo cliente si crédito
        if venta.cliente_id:
            cliente = venta.cliente
            if cliente.cupo_credito > 0:
                cliente.saldo_cartera += venta.total_pago
        
        return venta
    
    def anular_venta(self, venta: Venta, motivo: str, usuario_actual) -> Venta:
        """Anular venta y reversionar todo"""
        
        venta.estado = "anulada"
        venta.motivo_anulacion = motivo
        venta.anulada_por_id = usuario_actual.id
        venta.fecha_anulacion = datetime.utcnow()
        
        # Reversionar inventario
        for detalle in venta.detalles:
            producto = detalle.producto
            producto.existencias += detalle.cantidad  # Devolver stock
            
            # Registrar movimiento reversa
            self._registrar_movimiento_inventario(
                producto=producto,
                cantidad=detalle.cantidad,
                tipo="devolución",
                referencia=f"anulación_venta_{venta.id}"
            )
        
        # Reversar saldo cliente
        if venta.cliente_id:
            cliente = venta.cliente
            cliente.saldo_cartera -= venta.total_pago
        
        return venta
    
    def _recalcular_totales(self, venta: Venta) -> None:
        """Recalcular totales (subtotal, impuesto, total)"""
        venta.subtotal = sum(
            d.cantidad * d.precio for d in venta.detalles
        )
        
        empresa = self.db.get(Empresa, venta.empresa_id)
        venta.impuesto_value = calcular_impuesto(
            venta.subtotal,
            empresa.impuesto_porcentaje
        )
        
        venta.total_pago = venta.subtotal + venta.impuesto_value - venta.descuento_pesos + venta.propina_pesos
    
    def _generar_numero_factura(self, empresa: Empresa) -> str:
        """Generar número de factura único"""
        # Ejemplo: "POS-000001"
        numero = empresa.consecutivo_factura
        empresa.consecutivo_factura += 1
        return f"{empresa.prefijo_factura}-{numero:06d}"
    
    def _registrar_movimiento_inventario(self, producto, cantidad, tipo, referencia):
        """Registrar movimiento en auditoría"""
        from app.models.inventario import MovimientoInventario
        
        movimiento = MovimientoInventario(
            producto_id=producto.id,
            cantidad=cantidad,
            tipo=tipo,
            costo_unitario=producto.costo,
            referencia=referencia,
            fecha_movimiento=datetime.utcnow()
        )
        self.db.add(movimiento)
```

### E. Decoradores Personalizados

```python
# app/utils/decoradores.py

from functools import wraps
from fastapi import HTTPException, status, Depends
from app.models.empleados import Usuario

def require_role(*roles: str):
    """
    Verificar que usuario tiene uno de los roles especificados
    
    @require_role("admin", "gerente")
    async def admin_endpoint(...):
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_usuario = kwargs.get('current_usuario')
            if current_usuario is None:
                raise HTTPException(status_code=401, detail="No autenticado")
            
            if current_usuario.rol not in roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Acceso denegado. Roles requeridos: {', '.join(roles)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_permission(permission: str):
    """
    Verificar permisos granulares
    
    @require_permission("venta:cobrar")
    async def endpoint(...):
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_usuario = kwargs.get('current_usuario')
            if not current_usuario.tiene_permiso(permission):
                raise HTTPException(status_code=403, detail="Permiso denegado")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
```

### F. Tests (pytest)

```python
# tests/test_routes/test_ventas.py

import pytest
from decimal import Decimal
from app.schemas.ventas import VentaCreate, DetalleVentaCreate
from app.models.ventas import Venta

@pytest.mark.asyncio
async def test_crear_venta_basica(client, db_session, usuario_mesero, mesa_1):
    """Test: Crear venta nueva"""
    
    venta_data = VentaCreate(mesa_id=mesa_1.id, canal="mesa")
    
    response = client.post(
        "/api/v1/ventas",
        json=venta_data.model_dump(),
        headers={"Authorization": f"Bearer {usuario_mesero.token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["mesa_id"] == mesa_1.id
    assert data["estado"] == "abierta"
    assert data["total_pago"] == "0.00"

@pytest.mark.asyncio
async def test_agregar_item_a_venta(client, db_session, usuario_mesero, venta_abierta, producto_capuchino):
    """Test: Agregar producto a venta"""
    
    item_data = DetalleVentaCreate(
        producto_id=producto_capuchino.id,
        cantidad=Decimal("1"),
        precio_unitario=Decimal("8500")
    )
    
    response = client.post(
        f"/api/v1/ventas/{venta_abierta.id}/items",
        json=item_data.model_dump(),
        headers={"Authorization": f"Bearer {usuario_mesero.token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["detalles"]) == 1
    assert data["subtotal"] == "8500.00"

@pytest.mark.asyncio
async def test_cerrar_venta_sin_items(client, db_session, usuario_mesero, venta_abierta):
    """Test: No puede cerrar venta sin items"""
    
    response = client.post(
        f"/api/v1/ventas/{venta_abierta.id}/cerrar",
        headers={"Authorization": f"Bearer {usuario_mesero.token}"}
    )
    
    assert response.status_code == 400
    assert "sin items" in response.json()["detail"]

@pytest.mark.asyncio
async def test_stock_insuficiente(client, db_session, usuario_mesero, venta_abierta, producto_bajo_stock):
    """Test: Rechazar item si stock insuficiente"""
    
    item_data = DetalleVentaCreate(
        producto_id=producto_bajo_stock.id,
        cantidad=Decimal("1000"),  # Más que stock disponible
        precio_unitario=Decimal("5000")
    )
    
    response = client.post(
        f"/api/v1/ventas/{venta_abierta.id}/items",
        json=item_data.model_dump(),
        headers={"Authorization": f"Bearer {usuario_mesero.token}"}
    )
    
    assert response.status_code == 400
    assert "Stock insuficiente" in response.json()["detail"]
```

---

## III. FLUJO DE DATOS COMPLETO (POS)

```
USUARIO (Mesero)
    ↓
[1] POST /api/v1/ventas  ← Crear venta abierta
    ├─ Validar mesa existe
    ├─ Crear Venta (estado="abierta")
    └─ Return VentaResponse

[2] POST /api/v1/ventas/{id}/items  ← Agregar ítem
    ├─ Validar producto existe
    ├─ Validar stock > 0
    ├─ Crear DetalleVenta
    ├─ Recalcular totales (subtotal, impuesto)
    ├─ WebSocket → Notify cocina (orden nueva)
    └─ Return VentaResponse actualizada

[3] GET /api/v1/mesas/{id}/estado  ← Ver estado mesa
    ├─ Return mesa actual, venta, detalles
    └─ (opcional: WebSocket para updates real-time)

[4] POST /api/v1/ventas/{id}/cerrar  ← Cobrar
    ├─ Generar número factura
    ├─ Marcar estado="cerrada"
    ├─ Decrementar inventario (para c/detalle)
    ├─ Registrar MovimientoInventario
    ├─ Generar PDF factura
    ├─ WebSocket → Notify mesero (venta completada)
    ├─ WebSocket → Notify comisión (comisión calculada)
    └─ Return VentaResponse

BD (PostgreSQL)
    └─ Venta insertada/actualizada
    └─ DetalleVenta insertado
    └─ MovimientoInventario registrado
    └─ Producto.existencias decrementado
    └─ Auditoria de cambios
```

---

## IV. CHECKLIST PRE-IMPLEMENTACIÓN

Antes de escribir código, asegúrate:

- [ ] **Modelos ORM**: Todos los models.py con migrations listas
- [ ] **Schemas**: Pydantic schemas con validaciones exhaustivas
- [ ] **Routes**: API endpoints listados y documentados
- [ ] **Services**: Lógica de negocio separada
- [ ] **Tests**: Tests escritos ANTES de implementar (TDD)
- [ ] **Decoradores**: Autenticación + permisos configurados
- [ ] **Database**: Migraciones actualizadas (alembic)
- [ ] **Docker**: Dockerfile + docker-compose listo
- [ ] **CI/CD**: GitHub Actions para tests + lint
- [ ] **Documentación**: README, API docs, tutorials

---

## V. COMANDOS ÚTILES DE DESARROLLO

```bash
# Setup inicial
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Base de datos
alembic revision --autogenerate -m "Descripción cambio"
alembic upgrade head
alembic downgrade -1  # Revertir última migración

# Tests
pytest                           # Correr todos
pytest tests/test_routes/test_ventas.py  # Específico
pytest --cov=app --cov-report=html  # Con coverage
pytest -v -s                    # Verbose + print statements

# Linting
black app/                       # Formatear código
flake8 app/                      # Linter
isort app/                       # Organizar imports
mypy app/                        # Type checking

# Servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-compose up -d              # Levantar servicios
docker-compose logs -f app        # Ver logs
docker-compose down               # Parar todo

# Pre-commit hooks
pre-commit run --all-files        # Ejecutar hooks manualmente
```

---

**Fin de Guía Técnica**
