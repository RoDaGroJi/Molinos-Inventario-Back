from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# Esquemas de Usuario
class UserBase(BaseModel):
    username: str
    full_name: str

class UserCreate(UserBase):
    password: str
    is_admin: Optional[bool] = False

class UserOut(UserBase):
    id: int
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Esquemas Genéricos para Tablas Independientes
class CatalogBase(BaseModel):
    nombre: str

class CatalogCreate(CatalogBase):
    pass

class CatalogOut(CatalogBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Esquemas de Empleado
class EmpleadoBase(BaseModel):
    nombre: str
    cargo_id: int
    area_id: int
    empresa_id: int
    ciudad_id: int

class EmpleadoCreate(EmpleadoBase):
    pass

class EmpleadoOut(EmpleadoBase):
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

# Esquemas de Producto
class ProductoBase(BaseModel):
    marca: str
    referencia: Optional[str] = None
    memoria_ram: Optional[str] = None
    disco_duro: Optional[str] = None
    serial: Optional[str] = None
    observaciones: Optional[str] = None
    tipo_id: int

class ProductoCreate(ProductoBase):
    pass

class ProductoOut(ProductoBase):
    id: int
    tipo: Optional[CatalogOut] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Esquema de Inventario
class InventoryCreate(BaseModel):
    empleado_id: int
    producto_id: int
    sede_id: Optional[int] = None
    quien_entrega: Optional[str] = None
    observacion: Optional[str] = None

class InventoryOut(BaseModel):
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

# Esquema de Historial
class HistorialOut(BaseModel):
    id: int
    inventory_id: int
    empleado_id: int
    producto_id: int
    accion: str
    fecha_accion: datetime
    observacion: Optional[str] = None
    empleado: Optional[EmpleadoOut] = None
    producto: Optional[ProductoOut] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str