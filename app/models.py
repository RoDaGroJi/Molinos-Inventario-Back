"""
Modelos de base de datos para el sistema de inventario.
Utiliza SQLAlchemy ORM para la persistencia de datos.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# ===== TABLA DE ASOCIACIÓN =====

empleado_producto = Table(
    'empleado_producto',
    Base.metadata,
    Column('empleado_id', Integer, ForeignKey('empleados.id'), primary_key=True),
    Column('producto_id', Integer, ForeignKey('productos.id'), primary_key=True),
    Column('fecha_asignacion', DateTime, default=datetime.now),
    Column('created_by_id', Integer, ForeignKey('users.id'))
)


# ===== MODELOS =====

class User(Base):
    """
    Modelo de usuario del sistema.
    
    Atributos:
        id: Identificador único
        username: Nombre de usuario único
        password_hash: Hash de la contraseña
        full_name: Nombre completo
        is_admin: Indica si es administrador
        is_active: Indica si está activo
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"

    
class Area(Base):
    """Modelo de área o departamento de la empresa."""
    __tablename__ = "areas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Area(id={self.id}, nombre={self.nombre})>"

    
class Empresa(Base):
    """Modelo de empresa."""
    __tablename__ = "empresas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Empresa(id={self.id}, nombre={self.nombre})>"

    
class Cargo(Base):
    """Modelo de cargo o posición de un empleado."""
    __tablename__ = "cargos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Cargo(id={self.id}, nombre={self.nombre})>"

    
class EquipoTipo(Base):
    """
    Modelo de tipo de equipo.
    Ejemplos: Laptop, Monitor, Mouse, Teclado, etc.
    """
    __tablename__ = "equipo_tipos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<EquipoTipo(id={self.id}, nombre={self.nombre})>"

    
class Ciudad(Base):
    """Modelo de ciudad o sede."""
    __tablename__ = "ciudades"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Ciudad(id={self.id}, nombre={self.nombre})>"


class Empleado(Base):
    """
    Modelo de empleado.
    
    Atributos:
        id: Identificador único
        nombre: Nombre del empleado
        cargo_id: Referencia al cargo
        area_id: Referencia al área
        empresa_id: Referencia a la empresa
        ciudad_id: Referencia a la ciudad/sede
        is_active: Indica si está activo
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
        created_by_id: Usuario que creó el registro
    """
    __tablename__ = "empleados"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    cargo_id = Column(Integer, ForeignKey("cargos.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    ciudad_id = Column(Integer, ForeignKey("ciudades.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Relaciones
    cargo = relationship("Cargo")
    area = relationship("Area")
    empresa = relationship("Empresa")
    ciudad = relationship("Ciudad")
    productos = relationship("Producto", secondary=empleado_producto, back_populates="empleados")
    
    def __repr__(self):
        return f"<Empleado(id={self.id}, nombre={self.nombre})>"


class Producto(Base):
    """
    Modelo de producto/equipo del inventario.
    
    Atributos:
        id: Identificador único
        marca: Marca del producto
        referencia: Modelo o referencia del producto
        memoria_ram: Capacidad de RAM (si aplica)
        disco_duro: Capacidad de almacenamiento (si aplica)
        serial: Número de serie único
        observaciones: Notas adicionales
        tipo_id: Tipo de equipo (FK)
        is_active: Indica si está disponible
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
        created_by_id: Usuario que creó el registro
    """
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String, nullable=False)
    referencia = Column(String, nullable=True)
    memoria_ram = Column(String, nullable=True)
    disco_duro = Column(String, nullable=True)
    serial = Column(String, nullable=True, unique=True, index=True)
    observaciones = Column(Text, nullable=True)
    tipo_id = Column(Integer, ForeignKey("equipo_tipos.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Relaciones
    tipo = relationship("EquipoTipo")
    empleados = relationship("Empleado", secondary=empleado_producto, back_populates="productos")
    
    def __repr__(self):
        return f"<Producto(id={self.id}, marca={self.marca}, serial={self.serial})>"


class Inventory(Base):
    """
    Modelo de asignación de producto a empleado.
    Registra cuándo y a quién se asigna un producto.
    
    Atributos:
        id: Identificador único
        empleado_id: Referencia al empleado
        producto_id: Referencia al producto
        sede_id: Referencia a la sede/ciudad donde se encuentra
        fecha_asignacion: Fecha de asignación
        fecha_retiro: Fecha de retiro/devolución
        quien_entrega: Persona que realizó la entrega
        observacion: Notas sobre la asignación
        is_active: Indica si está activo
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
        created_by_id: Usuario que creó el registro
    """
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    sede_id = Column(Integer, ForeignKey("ciudades.id"), nullable=True)
    fecha_asignacion = Column(DateTime, default=datetime.now)
    fecha_retiro = Column(DateTime, nullable=True)
    quien_entrega = Column(String, nullable=True)
    observacion = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey("users.id"))

    # Relaciones
    empleado = relationship("Empleado")
    producto = relationship("Producto")
    sede = relationship("Ciudad")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<Inventory(id={self.id}, empleado_id={self.empleado_id}, producto_id={self.producto_id})>"


class HistorialInventario(Base):
    """
    Modelo de historial de inventario.
    Registra todas las acciones realizadas sobre asignaciones de productos.
    
    Atributos:
        id: Identificador único
        inventory_id: Referencia a la asignación
        empleado_id: Referencia al empleado
        producto_id: Referencia al producto
        accion: Tipo de acción (asignacion, retiro, cambio, actualizacion)
        fecha_accion: Fecha de la acción
        observacion: Detalles de la acción
        created_by_id: Usuario que registró la acción
    """
    __tablename__ = "historial_inventario"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    accion = Column(String, nullable=False, index=True)
    fecha_accion = Column(DateTime, default=datetime.now)
    observacion = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relaciones
    inventory = relationship("Inventory")
    empleado = relationship("Empleado")
    producto = relationship("Producto")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<HistorialInventario(id={self.id}, accion={self.accion}, fecha={self.fecha_accion})>"