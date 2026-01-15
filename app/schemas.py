from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# Esquemas de Usuario
class UserBase(BaseModel):
    username: str
    full_name: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_admin: bool
    is_active: bool
    class Config:
        from_attributes = True

# Esquemas Genéricos para Tablas Independientes
class CatalogBase(BaseModel):
    nombre: str

class CatalogOut(CatalogBase):
    id: int
    is_active: bool
    class Config:
        from_attributes = True

# Esquema de Inventario
class InventoryCreate(BaseModel):
    empleado_nombre: str
    cargo_id: int
    area_id: int
    empresa_id: int
    equipo_id: int
    ciudad_id: int
    quien_entrega: str
    cantidad: int
    marca: str
    caracteristicas: str
    observacion: Optional[str] = None

class InventoryOut(BaseModel):
    id: int
    fecha: datetime
    empleado_nombre: str
    marca: Optional[str] = ""
    quien_entrega: Optional[str] = None
    cantidad: Optional[int] = 1
    caracteristicas: Optional[str] = None
    observacion: Optional[str] = None    
    # IMPORTANTE: Todos deben ser Optional y = None
    cargo: Optional[CatalogOut] = None
    area: Optional[CatalogOut] = None
    empresa: Optional[CatalogOut] = None
    equipo: Optional[CatalogOut] = None
    ciudad: Optional[CatalogOut] = None
    creator: Optional[UserOut] = None
    is_active: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str