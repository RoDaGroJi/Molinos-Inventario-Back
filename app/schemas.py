"""
Esquemas Pydantic para validación y serialización de datos.
Define la estructura de request/response de todos los endpoints.
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List


# ===== ESQUEMAS DE USUARIO =====

class UserBase(BaseModel):
    """Base para esquemas de usuario."""
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    """Esquema para crear un nuevo usuario."""
    password: str = Field(..., min_length=6, max_length=100)
    is_admin: bool = False


class UserOut(UserBase):
    """Esquema de salida de usuario."""
    id: int
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Esquema de token JWT."""
    access_token: str
    token_type: str
    user: Optional[UserOut] = None


# ===== ESQUEMAS GENÉRICOS PARA CATÁLOGOS =====

class CatalogBase(BaseModel):
    """Base para esquemas de catálogos (Áreas, Empresas, Cargos, etc)."""
    nombre: str = Field(..., min_length=2, max_length=100)


class CatalogCreate(CatalogBase):
    """Esquema para crear un catálogo."""
    pass


class CatalogOut(CatalogBase):
    """Esquema de salida de catálogo."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== ESQUEMAS DE EMPLEADO =====

class EmpleadoBase(BaseModel):
    """Base para esquemas de empleado."""
    nombre: str = Field(..., min_length=2, max_length=100)
    cargo_id: int = Field(..., gt=0)
    area_id: int = Field(..., gt=0)
    empresa_id: int = Field(..., gt=0)
    ciudad_id: int = Field(..., gt=0)


class EmpleadoCreate(EmpleadoBase):
    """Esquema para crear un empleado."""
    pass


class EmpleadoUpdate(BaseModel):
    """Esquema para actualizar un empleado."""
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    cargo_id: Optional[int] = Field(None, gt=0)
    area_id: Optional[int] = Field(None, gt=0)
    empresa_id: Optional[int] = Field(None, gt=0)
    ciudad_id: Optional[int] = Field(None, gt=0)


class EmpleadoOut(EmpleadoBase):
    """Esquema de salida de empleado."""
    id: int
    cargo: Optional[CatalogOut] = None
    area: Optional[CatalogOut] = None
    empresa: Optional[CatalogOut] = None
    ciudad: Optional[CatalogOut] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== ESQUEMAS DE PRODUCTO =====

class ProductoBase(BaseModel):
    """Base para esquemas de producto."""
    marca: str = Field(..., min_length=1, max_length=100)
    referencia: Optional[str] = Field(None, max_length=100)
    memoria_ram: Optional[str] = Field(None, max_length=50)
    disco_duro: Optional[str] = Field(None, max_length=100)
    serial: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = Field(None, max_length=500)
    tipo_id: int = Field(..., gt=0)


class ProductoCreate(ProductoBase):
    """Esquema para crear un producto."""
    pass


class ProductoUpdate(BaseModel):
    """Esquema para actualizar un producto."""
    marca: Optional[str] = Field(None, min_length=1, max_length=100)
    referencia: Optional[str] = Field(None, max_length=100)
    memoria_ram: Optional[str] = Field(None, max_length=50)
    disco_duro: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = Field(None, max_length=500)
    tipo_id: Optional[int] = Field(None, gt=0)


class ProductoOut(ProductoBase):
    """Esquema de salida de producto."""
    id: int
    tipo: Optional[CatalogOut] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== ESQUEMAS DE INVENTARIO =====

class InventoryCreate(BaseModel):
    """Esquema para crear una asignación de inventario."""
    empleado_id: int = Field(..., gt=0)
    producto_id: int = Field(..., gt=0)
    sede_id: Optional[int] = Field(None, gt=0)
    quien_entrega: Optional[str] = Field(None, max_length=100)
    observacion: Optional[str] = Field(None, max_length=500)


class InventoryUpdate(BaseModel):
    """Esquema para actualizar una asignación de inventario."""
    sede_id: Optional[int] = Field(None, gt=0)
    quien_entrega: Optional[str] = Field(None, max_length=100)
    observacion: Optional[str] = Field(None, max_length=500)
    fecha_retiro: Optional[datetime] = None


class InventoryOut(BaseModel):
    """Esquema de salida de asignación de inventario."""
    id: int
    empleado_id: int
    producto_id: int
    sede_id: Optional[int] = None
    fecha_asignacion: datetime
    fecha_retiro: Optional[datetime] = None
    quien_entrega: Optional[str] = None
    observacion: Optional[str] = None
    empleado: Optional[EmpleadoOut] = None
    producto: Optional[ProductoOut] = None
    sede: Optional[CatalogOut] = None
    creator: Optional[UserOut] = None
    is_active: bool
    
    class Config:
        from_attributes = True


# ===== ESQUEMAS DE HISTORIAL =====

class HistorialCreate(BaseModel):
    """Esquema para crear un registro de historial."""
    inventory_id: Optional[int] = None
    empleado_id: int = Field(..., gt=0)
    producto_id: int = Field(..., gt=0)
    accion: str = Field(..., min_length=1, max_length=50)
    observacion: Optional[str] = Field(None, max_length=500)


class HistorialOut(BaseModel):
    """Esquema de salida de historial."""
    id: int
    inventory_id: Optional[int] = None
    empleado_id: int
    producto_id: int
    accion: str
    fecha_accion: datetime
    observacion: Optional[str] = None
    empleado: Optional[EmpleadoOut] = None
    producto: Optional[ProductoOut] = None
    creator: Optional[UserOut] = None
    
    class Config:
        from_attributes = True