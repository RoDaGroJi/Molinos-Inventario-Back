from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# Tabla de asociación many-to-many entre Empleado y Producto
empleado_producto = Table(
    'empleado_producto',
    Base.metadata,
    Column('empleado_id', Integer, ForeignKey('empleados.id'), primary_key=True),
    Column('producto_id', Integer, ForeignKey('productos.id'), primary_key=True),
    Column('fecha_asignacion', DateTime, default=datetime.now),
    Column('created_by_id', Integer, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
class Area(Base):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
class Cargo(Base):
    __tablename__ = "cargos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
class EquipoTipo(Base):
    __tablename__ = "equipo_tipos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True) # Ej: Laptop, Monitor, Mouse
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
class Ciudad(Base):
    __tablename__ = "ciudades"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Empleado(Base):
    __tablename__ = "empleados"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    cargo_id = Column(Integer, ForeignKey("cargos.id"))
    area_id = Column(Integer, ForeignKey("areas.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    ciudad_id = Column(Integer, ForeignKey("ciudades.id"))
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

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String)
    referencia = Column(String, nullable=True)
    memoria_ram = Column(String, nullable=True)  # Ej: "8GB", "16GB"
    disco_duro = Column(String, nullable=True)  # Ej: "256GB SSD", "500GB HDD"
    serial = Column(String, nullable=True, unique=True)
    observaciones = Column(Text, nullable=True)
    tipo_id = Column(Integer, ForeignKey("equipo_tipos.id"))  # Tipo de equipo
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Relaciones
    tipo = relationship("EquipoTipo")
    empleados = relationship("Empleado", secondary=empleado_producto, back_populates="productos")

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), index=True)
    sede_id = Column(Integer, ForeignKey("ciudades.id"), nullable=True)  # Sede/ciudad
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

class HistorialInventario(Base):
    __tablename__ = "historial_inventario"
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"))
    empleado_id = Column(Integer, ForeignKey("empleados.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    accion = Column(String)  # 'asignacion', 'retiro', 'cambio', 'actualizacion'
    fecha_accion = Column(DateTime, default=datetime.now)
    observacion = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Relaciones
    inventory = relationship("Inventory")
    empleado = relationship("Empleado")
    producto = relationship("Producto")
    creator = relationship("User")