"""
Sistema RBAC (Role-Based Access Control) - Control de Acceso Basado en Roles
FASE 5: Enterprise Authorization System
"""
import logging
from typing import Optional, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PermisosService:
    """
    Servicio para validar permisos de usuarios.
    
    Uso:
    -----
    permisos = PermisosService(db)
    
    # Validar permiso específico
    if permisos.tiene_permiso(usuario_id, "ventas.crear"):
        # Hacer algo
    
    # Validar múltiples permisos
    if permisos.tiene_alguno(usuario_id, ["caja.abrir", "caja.cerrar"]):
        # Hacer algo
    
    # Obtener todos los permisos de un usuario
    permisos_usuario = permisos.obtener_permisos(usuario_id)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._cache_permisos = {}  # {usuario_id: set(permisos)}
    
    def obtener_permisos_usuario(self, usuario_id: int) -> Set[str]:
        """
        Obtiene todos los permisos de un usuario.
        Utiliza caché para rendimiento.
        """
        if usuario_id in self._cache_permisos:
            return self._cache_permisos[usuario_id]
        
        try:
            # Importar aquí para evitar circular imports
            from ..models_enterprise import UsuarioRol, Rol, Permiso
            
            # Query para obtener permisos
            query = self.db.query(Permiso.codigo).join(
                Rol.permisos
            ).join(
                UsuarioRol, UsuarioRol.rol_id == Rol.id
            ).filter(
                UsuarioRol.usuario_id == usuario_id,
                UsuarioRol.activo == True
            ).distinct()
            
            permisos = {row[0] for row in query.all()}
            self._cache_permisos[usuario_id] = permisos
            
            logger.debug(f"Permisos cargados para usuario {usuario_id}: {permisos}")
            return permisos
            
        except Exception as e:
            logger.error(f"Error obteniendo permisos del usuario {usuario_id}: {e}")
            return set()
    
    def tiene_permiso(self, usuario_id: int, permiso_codigo: str) -> bool:
        """Verifica si un usuario tiene un permiso específico"""
        permisos = self.obtener_permisos_usuario(usuario_id)
        
        # Soporte para permisos comodín: "ventas.*" coincide con "ventas.crear"
        for p in permisos:
            if p == permiso_codigo:
                return True
            if p.endswith('.*'):
                prefijo = p[:-2]  # Quitar el ".*"
                if permiso_codigo.startswith(prefijo + '.'):
                    return True
        
        return False
    
    def tiene_alguno(self, usuario_id: int, permisos: list) -> bool:
        """Verifica si el usuario tiene al menos uno de los permisos"""
        for p in permisos:
            if self.tiene_permiso(usuario_id, p):
                return True
        return False
    
    def tiene_todos(self, usuario_id: int, permisos: list) -> bool:
        """Verifica si el usuario tiene todos los permisos"""
        for p in permisos:
            if not self.tiene_permiso(usuario_id, p):
                return False
        return True
    
    def requiere_permiso(self, usuario_id: int, permiso_codigo: str) -> None:
        """Lanza excepción si no tiene el permiso. Para usar en validaciones."""
        if not self.tiene_permiso(usuario_id, permiso_codigo):
            logger.warning(f"Acceso denegado - Usuario {usuario_id} requiere permiso {permiso_codigo}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene permiso para: {permiso_codigo}"
            )
    
    def limpiar_cache_usuario(self, usuario_id: int) -> None:
        """Limpia el caché de permisos cuando se actualizan roles"""
        if usuario_id in self._cache_permisos:
            del self._cache_permisos[usuario_id]
            logger.info(f"Caché de permisos limpiado para usuario {usuario_id}")


class RolService:
    """Servicio para gestionar roles del sistema"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def obtener_rol_por_nombre(self, nombre: str):
        """Obtiene un rol por nombre"""
        from ..models_enterprise import Rol
        return self.db.query(Rol).filter(Rol.nombre == nombre).first()
    
    def crear_rol_predefinido(self, nombre: str, permisos_codigos: list) -> Optional[object]:
        """Crea un rol predefinido del sistema"""
        try:
            from ..models_enterprise import Rol, Permiso
            
            # Verificar si ya existe
            rol_existente = self.obtener_rol_por_nombre(nombre)
            if rol_existente:
                logger.info(f"Rol '{nombre}' ya existe")
                return rol_existente
            
            # Obtener permisos
            permisos = self.db.query(Permiso).filter(
                Permiso.codigo.in_(permisos_codigos)
            ).all()
            
            # Crear rol. El administrador es el super admin (nivel maximo);
            # el resto recibe un nivel segun su alcance.
            niveles = {"administrador": 100, "gerente": 80, "cajero": 40,
                       "mesero": 30, "cocinero": 30, "bartender": 30}
            rol = Rol(
                nombre=nombre,
                descripcion=f"Rol predefinido del sistema: {nombre}",
                es_predefinido=True,
                nivel_acceso=niveles.get(nombre, 30),
                permisos=permisos
            )
            
            self.db.add(rol)
            self.db.commit()
            logger.info(f"Rol '{nombre}' creado exitosamente")
            return rol
            
        except Exception as e:
            logger.error(f"Error creando rol '{nombre}': {e}")
            self.db.rollback()
            return None
    
    def crear_permisos_del_sistema(self) -> None:
        """Crea todos los permisos predefinidos del sistema"""
        from ..models_enterprise import Permiso
        
        permisos_predefinidos = [
            # Ventas
            ('ventas.crear', 'Crear venta', 'Crear nuevas ventas'),
            ('ventas.editar', 'Editar venta', 'Modificar ventas existentes'),
            ('ventas.eliminar', 'Eliminar venta', 'Eliminar ventas'),
            ('ventas.ver', 'Ver ventas', 'Visualizar listado de ventas'),
            ('ventas.cobrar', 'Cobrar venta', 'Procesar pagos'),
            ('ventas.precio_libre', 'Modificar precio', 'Vender a un precio distinto al del catalogo'),
            
            # Caja
            ('caja.abrir', 'Abrir caja', 'Apertura de caja'),
            ('caja.cerrar', 'Cerrar caja', 'Cierre de caja'),
            ('caja.arqueo', 'Hacer arqueo', 'Arqueo de caja'),
            ('caja.ver', 'Ver caja', 'Visualizar movimientos de caja'),
            
            # Mesas
            ('mesas.gestionar', 'Gestionar mesas', 'Crear, editar, eliminar mesas'),
            ('mesas.cambiar_estado', 'Cambiar estado de mesa', 'Cambiar estado de mesas'),
            
            # Usuarios
            ('usuarios.crear', 'Crear usuario', 'Crear nuevos usuarios'),
            ('usuarios.editar', 'Editar usuario', 'Modificar usuarios existentes'),
            ('usuarios.eliminar', 'Eliminar usuario', 'Eliminar usuarios'),
            ('usuarios.gestionar_roles', 'Gestionar roles', 'Asignar y revocar roles'),
            
            # Reportes
            ('reportes.ver', 'Ver reportes', 'Acceso a reportes'),
            ('reportes.exportar', 'Exportar reportes', 'Exportar datos de reportes'),
            
            # Configuración
            ('configuracion.editar', 'Editar configuración', 'Modificar configuración del sistema'),
            ('configuracion.ver', 'Ver configuración', 'Visualizar configuración'),
            
            # Administración
            ('admin.*', 'Acceso administrativo total', 'Control total del sistema'),
        ]

        # Permisos POR MODULO (acceso si/no a cada seccion). Complementan los
        # permisos por accion de arriba. Son los que gobiernan el acceso a las
        # vistas del sistema (Paso 17).
        modulos = [
            ("dashboard", "Dashboard"), ("mesas", "Mesas"),
            ("caja", "Caja / POS"), ("cocina", "Cocina"),
            ("domicilios", "Domicilios"), ("productos", "Productos"),
            ("inventario", "Inventario"), ("produccion", "Produccion"),
            ("compras", "Compras"), ("gastos", "Gastos"),
            ("clientes", "Clientes"), ("empleados", "Empleados / Asistencia"),
            ("nomina", "Nomina"), ("informes", "Informes"),
            ("usuarios", "Usuarios y Roles"), ("configuracion", "Configuracion"),
            ("auditoria", "Auditoria"),
            ("backups", "Copias de seguridad"),
        ]
        for cod, nom in modulos:
            permisos_predefinidos.append(
                (f"modulo.{cod}", f"Acceso a {nom}", f"Acceso al modulo {nom}"))
        
        try:
            for codigo, nombre, descripcion in permisos_predefinidos:
                # Verificar si ya existe
                permiso_existente = self.db.query(Permiso).filter(
                    Permiso.codigo == codigo
                ).first()
                
                if not permiso_existente:
                    categoria = codigo.split('.')[0]
                    permiso = Permiso(
                        codigo=codigo,
                        nombre=nombre,
                        descripcion=descripcion,
                        categoria=categoria
                    )
                    self.db.add(permiso)
            
            self.db.commit()
            logger.info("Permisos del sistema inicializados")
            
        except Exception as e:
            logger.error(f"Error creando permisos del sistema: {e}")
            self.db.rollback()
    
    def crear_roles_predefinidos(self) -> None:
        """Crea los roles predefinidos del sistema"""
        self.crear_permisos_del_sistema()
        
        roles_predefinidos = {
            'administrador': [
                'admin.*',
            ],
            'gerente': [
                'ventas.ver', 'ventas.editar', 'ventas.precio_libre',
                'caja.ver', 'caja.arqueo', 'usuarios.ver',
                'reportes.ver', 'reportes.exportar',
                'modulo.dashboard', 'modulo.mesas', 'modulo.caja',
                'modulo.cocina', 'modulo.domicilios', 'modulo.productos',
                'modulo.inventario', 'modulo.produccion', 'modulo.compras',
                'modulo.gastos', 'modulo.clientes', 'modulo.empleados',
                'modulo.informes',
            ],
            'cajero': [
                'caja.*', 'ventas.cobrar', 'ventas.ver', 'usuarios.ver',
                'modulo.dashboard', 'modulo.mesas', 'modulo.caja',
                'modulo.clientes', 'modulo.domicilios',
            ],
            'mesero': [
                'ventas.crear', 'ventas.editar', 'ventas.cobrar',
                'mesas.ver', 'mesas.cambiar_estado',
                'modulo.dashboard', 'modulo.mesas', 'modulo.caja',
            ],
            'cocinero': [
                'mesas.ver', 'modulo.dashboard', 'modulo.cocina', 'modulo.mesas',
            ],
            'bartender': [
                'mesas.ver', 'modulo.dashboard', 'modulo.cocina', 'modulo.mesas',
            ],
        }
        
        for nombre_rol, permisos in roles_predefinidos.items():
            self.crear_rol_predefinido(nombre_rol, permisos)

    # ------------------------------------------------------------------
    # Resolucion por MODULO (Paso 17): gobierna el acceso a las secciones.
    # ------------------------------------------------------------------
    def rol_por_nombre_flexible(self, nombre: str):
        """Busca un rol por nombre sin distinguir mayusculas."""
        from ..models_enterprise import Rol
        if not nombre:
            return None
        rol = self.db.query(Rol).filter(Rol.nombre == nombre).first()
        if rol:
            return rol
        for r in self.db.query(Rol).all():
            if r.nombre.lower() == nombre.lower():
                return r
        return None

    def es_super_admin(self, nombre_rol: str) -> bool:
        rol = self.rol_por_nombre_flexible(nombre_rol)
        return bool(rol and (rol.nivel_acceso or 0) >= 100)

    def puede_modulo(self, nombre_rol: str, modulo: str) -> bool:
        """True si el rol tiene acceso al modulo. El super admin siempre puede.

        El acceso se resuelve contra los permisos 'modulo.<codigo>' asignados al
        rol en la base de datos. No hay roles ni permisos codificados.
        """
        rol = self.rol_por_nombre_flexible(nombre_rol)
        if not rol or not rol.activo:
            return False
        if (rol.nivel_acceso or 0) >= 100:
            return True
        codigo = f"modulo.{modulo}"
        return any(p.codigo == codigo or p.codigo == "admin.*"
                   for p in rol.permisos)

    def permisos_modulo_de(self, nombre_rol: str) -> set:
        rol = self.rol_por_nombre_flexible(nombre_rol)
        if not rol:
            return set()
        if (rol.nivel_acceso or 0) >= 100:
            return {p.codigo.split(".", 1)[1] for p in self.db.query(
                __import__("app.models_enterprise", fromlist=["Permiso"]).Permiso
            ).all() if p.codigo.startswith("modulo.")}
        return {p.codigo.split(".", 1)[1] for p in rol.permisos
                if p.codigo.startswith("modulo.")}

    # ------------------------------------------------------------------
    # Gestion desde la UI (Paso 23): crear/editar/eliminar roles.
    # ------------------------------------------------------------------
    def listar_roles(self) -> list:
        from ..models_enterprise import Rol
        return self.db.query(Rol).order_by(Rol.nivel_acceso.desc()).all()

    def modulos_disponibles(self) -> list:
        """Lista de (codigo_modulo, nombre) que un rol puede tener asignados."""
        from ..models_enterprise import Permiso
        mods = []
        for p in self.db.query(Permiso).filter(
                Permiso.codigo.like("modulo.%")).order_by(Permiso.nombre).all():
            mods.append((p.codigo.split(".", 1)[1], p.nombre))
        return mods

    def crear_rol(self, nombre: str, *, nivel_acceso: int = 30,
                  modulos: Optional[list] = None):
        """Crea un rol nuevo con permisos por modulo. Nadie crea super admins."""
        from ..models_enterprise import Rol
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre del rol es obligatorio")
        if self.rol_por_nombre_flexible(nombre):
            raise ValueError(f"Ya existe un rol '{nombre}'")
        # Nadie crea un rol por encima o igual al super admin desde la UI.
        nivel = min(int(nivel_acceso), 99)
        rol = Rol(nombre=nombre, descripcion=f"Rol {nombre}",
                  nivel_acceso=nivel, activo=True, es_predefinido=False)
        self.db.add(rol)
        self.db.flush()
        self._asignar_modulos(rol, modulos or [])
        self.db.flush()
        return rol

    def actualizar_permisos_modulo(self, rol_id: int, modulos: list):
        """Reemplaza los permisos de modulo de un rol. El super admin no se toca."""
        from ..models_enterprise import Rol, Permiso
        rol = self.db.get(Rol, rol_id)
        if not rol:
            raise ValueError("Rol no encontrado")
        if (rol.nivel_acceso or 0) >= 100:
            raise ValueError(
                "El super administrador tiene acceso total y no se edita")
        # Quitar los permisos de modulo actuales, conservar los demas (admin.*, etc.)
        rol.permisos = [p for p in rol.permisos
                        if not p.codigo.startswith("modulo.")]
        self._asignar_modulos(rol, modulos)
        self.db.flush()
        return rol

    def eliminar_rol(self, rol_id: int):
        from ..models_enterprise import Rol
        from ..models import Usuario
        rol = self.db.get(Rol, rol_id)
        if not rol:
            raise ValueError("Rol no encontrado")
        if (rol.nivel_acceso or 0) >= 100:
            raise ValueError("El super administrador no se puede eliminar")
        if rol.es_predefinido:
            raise ValueError("Los roles predefinidos del sistema no se eliminan")
        # No eliminar si hay usuarios con ese rol.
        en_uso = self.db.query(Usuario).filter(
            Usuario.rol == rol.nombre).first()
        if en_uso:
            raise ValueError(
                f"No se puede eliminar: hay usuarios con el rol '{rol.nombre}'")
        self.db.delete(rol)
        self.db.flush()

    def _asignar_modulos(self, rol, modulos: list) -> None:
        from ..models_enterprise import Permiso
        for cod in modulos:
            permiso = self.db.query(Permiso).filter(
                Permiso.codigo == f"modulo.{cod}").first()
            if permiso and permiso not in rol.permisos:
                rol.permisos.append(permiso)


def inicializar_rbac(db: Session) -> None:
    """
    Inicializa el sistema RBAC con roles y permisos predefinidos.
    Llamar en el lifespan del servidor.
    """
    try:
        rol_service = RolService(db)
        rol_service.crear_roles_predefinidos()
        logger.info("✓ RBAC inicializado exitosamente")
    except Exception as e:
        logger.error(f"Error inicializando RBAC: {e}")
