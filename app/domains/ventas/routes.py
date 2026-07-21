"""
Rutas (Endpoints) para módulo Ventas - API v1
Incluye nuevas endpoints optimizadas para POS Premium
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import logging

from app.database import get_db
from app.models import Usuario
from .schemas import (
    VentaCreate, VentaResponse, DetalleVentaCreate, DetalleVentaResponse,
    PagoCreate, VentaSuspendidaResponse, FiltroVentas, ReporteVentaResponse,
    EstadoVenta, TipoVenta
)
from .services import VentaService
from app.config import settings, logger

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

router = APIRouter(
    prefix="/ventas",
    tags=["ventas"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado"},
        404: {"description": "No encontrado"},
        422: {"description": "Validación fallida"}
    }
)

# ============================================================================
# DEPENDENCIAS
# ============================================================================

def get_usuario_actual(request: Request) -> Usuario:
    """Obtener usuario autenticado desde sesión"""
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        raise HTTPException(status_code=401, detail="No autenticado")
    # En producción: obtener del DB y validar
    return type('Usuario', (), {'id': usuario_id, 'empresa_id': request.session.get('empresa_id')})()


def validar_empresa(request: Request, db: Session = Depends(get_db)):
    """Validar que usuario pertenece a empresa"""
    usuario_id = request.session.get("usuario_id")
    empresa_id = request.session.get("empresa_id")
    if not usuario_id or not empresa_id:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    return empresa_id


# ============================================================================
# CREAR VENTA
# ============================================================================

@router.post(
    "",
    response_model=VentaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva venta",
    description="Crear venta con validaciones de negocio (POS Premium)"
)
def crear_venta(
    venta_data: VentaCreate,
    request: Request,
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """
    **Crear nueva venta**
    
    - Valida productos, mesa, cliente
    - Calcula montos (subtotal, descuento, impuesto, propina)
    - Crea detalles automáticamente
    - Retorna venta con estado 'abierta'
    
    Ejemplo:
    ```json
    {
        "tipo_venta": "en_mesa",
        "mesa_id": 1,
        "detalles": [
            {"producto_id": 5, "cantidad": 2, "precio": 8500}
        ]
    }
    ```
    """
    try:
        usuario_id = request.session.get("usuario_id")
        service = VentaService(db)
        venta = service.crear_venta(venta_data, usuario_id, empresa_id)
        
        logger.info(f"Venta creada - ID: {venta.id}, Total: {venta.total}, Usuario: {usuario_id}")
        return venta
        
    except ValueError as e:
        logger.warning(f"Validación en crear_venta: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error en crear_venta: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creando venta")


# ============================================================================
# OBTENER VENTA
# ============================================================================

@router.get(
    "/{venta_id}",
    response_model=VentaResponse,
    summary="Obtener detalles de venta",
    description="Obtener venta con todos sus detalles por ID"
)
def obtener_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """Obtener venta completa por ID"""
    service = VentaService(db)
    venta = service.obtener_venta(venta_id, empresa_id)
    
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    return venta


# ============================================================================
# LISTAR VENTAS
# ============================================================================

@router.get(
    "",
    response_model=List[ReporteVentaResponse],
    summary="Listar ventas",
    description="Listar ventas con filtros y paginación"
)
def listar_ventas(
    estado: Optional[EstadoVenta] = Query(None, description="Filtrar por estado"),
    tipo_venta: Optional[TipoVenta] = Query(None, description="Filtrar por tipo"),
    mesa_id: Optional[int] = Query(None, description="Filtrar por mesa"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """
    Listar ventas con filtros
    
    Parámetros:
    - `estado`: abierta, cerrada, suspendida, cancelada, facturada
    - `tipo_venta`: en_mesa, para_llevar, domicilio, mostrador
    - `mesa_id`: filtrar por mesa
    """
    service = VentaService(db)
    estado_str = estado.value if estado else None
    
    ventas = service.listar_ventas(
        empresa_id=empresa_id,
        estado=estado_str,
        limit=limit,
        offset=offset
    )
    
    # Convertir a ReporteVentaResponse para listado resumido
    return [
        ReporteVentaResponse(
            id=v.id,
            mesa_id=v.mesa_id,
            tipo_venta=v.tipo_venta,
            total=v.total,
            items_count=len(v.detalles),
            estado=v.estado,
            fecha=v.fecha_creacion,
            usuario_nombre=getattr(v.usuario, 'nombre', 'Sistema'),
            cliente_nombre=getattr(v.cliente, 'nombre', None) if v.cliente else None
        )
        for v in ventas
    ]


# ============================================================================
# AGREGAR DETALLE A VENTA
# ============================================================================

@router.post(
    "/{venta_id}/detalles",
    response_model=VentaResponse,
    summary="Agregar item a venta",
    description="Agregar producto a venta abierta y recalcular totales"
)
def agregar_detalle(
    venta_id: int,
    detalle_data: DetalleVentaCreate,
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """
    Agregar item a venta abierta
    
    - Solo funciona con ventas en estado 'abierta'
    - Recalcula automáticamente subtotal y total
    - Valida stock disponible
    """
    try:
        service = VentaService(db)
        venta = service.agregar_detalle(venta_id, detalle_data, empresa_id)
        logger.info(f"Detalle agregado a venta {venta_id}")
        return venta
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error agregando detalle: {str(e)}")
        raise HTTPException(status_code=500, detail="Error agregando item")


# ============================================================================
# ELIMINAR DETALLE DE VENTA
# ============================================================================

@router.delete(
    "/{venta_id}/detalles/{detalle_id}",
    response_model=VentaResponse,
    summary="Eliminar item de venta",
    description="Eliminar producto de venta abierta"
)
def eliminar_detalle(
    venta_id: int,
    detalle_id: int,
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """
    Eliminar item de venta abierta
    
    - Solo funciona con ventas en estado 'abierta'
    - Recalcula montos automáticamente
    """
    try:
        service = VentaService(db)
        venta = service.eliminar_detalle(venta_id, detalle_id, empresa_id)
        logger.info(f"Detalle {detalle_id} eliminado de venta {venta_id}")
        return venta
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error eliminando detalle: {str(e)}")
        raise HTTPException(status_code=500, detail="Error eliminando item")


# ============================================================================
# PROCESAR PAGO Y CERRAR VENTA
# ============================================================================

@router.post(
    "/{venta_id}/pagar",
    response_model=VentaResponse,
    summary="Procesar pago y cerrar venta",
    description="Registrar pago, cerrar venta, descontar inventario"
)
def procesar_pago(
    venta_id: int,
    pago_data: PagoCreate,
    request: Request,
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """
    Procesar pago y cerrar venta
    
    - Valida monto suficiente
    - Cambia estado a 'cerrada'
    - Registra método de pago (en producción)
    - Descuenta inventario automáticamente
    - Genera comisión para mesero/vendedor
    
    Métodos soportados:
    - efectivo
    - tarjeta_credito
    - tarjeta_debito
    - transferencia
    - billetera_digital
    - cheque
    """
    try:
        service = VentaService(db)
        venta = service.procesar_pago(venta_id, pago_data, empresa_id)
        
        usuario_id = request.session.get("usuario_id")
        logger.info(
            f"Pago procesado - Venta: {venta_id}, "
            f"Monto: {pago_data.monto}, "
            f"Método: {pago_data.tipo_pago}, "
            f"Usuario: {usuario_id}"
        )
        
        return venta
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error procesando pago: {str(e)}")
        raise HTTPException(status_code=500, detail="Error procesando pago")


# ============================================================================
# SUSPENDER VENTA
# ============================================================================

@router.post(
    "/{venta_id}/suspender",
    response_model=VentaSuspendidaResponse,
    summary="Suspender venta",
    description="Pausar venta para continuar después"
)
def suspender_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """
    Suspender venta
    
    - Genera código de suspensión para recuperar después
    - Útil para cambios de turno, interrupciones, etc.
    - Venta puede ser recuperada dentro de 24 horas
    """
    try:
        service = VentaService(db)
        venta, codigo = service.suspender_venta(venta_id, empresa_id)
        
        logger.info(f"Venta {venta_id} suspendida - Código: {codigo}")
        
        return VentaSuspendidaResponse(
            venta_id=venta_id,
            codigo_suspension=codigo,
            mensaje="Venta suspendida correctamente. Puede recuperarla cuando esté listo."
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error suspendiendo venta: {str(e)}")
        raise HTTPException(status_code=500, detail="Error suspendiendo venta")


# ============================================================================
# ESTADÍSTICAS DEL DÍA
# ============================================================================

@router.get(
    "/reportes/dia",
    summary="Estadísticas del día",
    description="Resumen de ventas del día actual"
)
def estadisticas_dia(
    db: Session = Depends(get_db),
    empresa_id: int = Depends(validar_empresa)
):
    """
    Obtener estadísticas de ventas del día
    
    Retorna:
    - Total de ventas cerradas
    - Monto total
    - Promedio por venta
    - Cantidad de items vendidos
    """
    service = VentaService(db)
    stats = service.obtener_stats_dia(empresa_id)
    
    return {
        **stats,
        "fecha": str(__import__('datetime').datetime.now().date()),
        "empresa_id": empresa_id
    }


# ============================================================================
# ESTADOS DE VENTA (Catálogo)
# ============================================================================

@router.get(
    "/catalogo/estados",
    response_model=List[str],
    summary="Estados disponibles",
    description="Lista de estados posibles para una venta"
)
def obtener_estados():
    """Estados válidos para una venta"""
    return [estado.value for estado in EstadoVenta]


@router.get(
    "/catalogo/tipos",
    response_model=List[str],
    summary="Tipos de venta disponibles",
    description="Lista de tipos de venta soportados"
)
def obtener_tipos_venta():
    """Tipos de venta disponibles"""
    return [tipo.value for tipo in TipoVenta]


@router.get(
    "/catalogo/pagos",
    response_model=List[str],
    summary="Métodos de pago disponibles",
    description="Lista de métodos de pago soportados"
)
def obtener_metodos_pago():
    """Métodos de pago disponibles"""
    from .schemas import TipoPago
    return [tipo.value for tipo in TipoPago]
