from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

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

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.now)
    empleado_nombre = Column(String)
    quien_entrega = Column(String)
    cantidad = Column(Integer, default=1)
    marca = Column(String, nullable=True)
    caracteristicas = Column(Text)
    observacion = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Llaves foráneas
    cargo_id = Column(Integer, ForeignKey("cargos.id"))
    area_id = Column(Integer, ForeignKey("areas.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    equipo_id = Column(Integer, ForeignKey("equipo_tipos.id"))
    created_by_id = Column(Integer, ForeignKey("users.id"))
    ciudad_id = Column(Integer, ForeignKey("ciudades.id"))

    # Relaciones para auditoría
    creator = relationship("User")
    area = relationship("Area")
    empresa = relationship("Empresa")
    cargo = relationship("Cargo")
    equipo = relationship("EquipoTipo")
    ciudad = relationship("Ciudad")