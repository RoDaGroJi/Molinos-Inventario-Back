from typing import List, Optional
from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, schemas, auth, database
from .database import engine, get_db
from jose import jwt, JWTError
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from datetime import datetime
from fastapi.responses import StreamingResponse, Response
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
import tempfile
import os
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Inventario Oficina")
# --- CONFIGURACIÓN DE CORS ---
origins = [
    "http://localhost:5173", # Puerto por defecto de Vite
    "http://localhost:5174", # Puerto alternativo de Vite
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "https://molinos-inventario-front.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"], # Permite todos los headers (incluyendo Authorization)
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- LOGIN Y SEGURIDAD ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="No se pudo validar credenciales")
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
    except JWTError: raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None: raise credentials_exception
    return user

def get_current_admin_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operación no permitida para este nivel de usuario"
        )
    return current_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- INICIALIZACIÓN ADMIN ---

@app.on_event("startup")
def create_admin():
    db = database.SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        hashed_pw = auth.get_password_hash("admin123")
        new_admin = models.User(username="admin", password_hash=hashed_pw, full_name="Administrador", is_admin=True)
        db.add(new_admin)
        db.commit()
    db.close()

# --- ENDPOINTS EMPLEADOS ---

@app.post("/empleados/", response_model=schemas.EmpleadoOut)
def create_empleado(empleado: schemas.EmpleadoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_empleado = models.Empleado(**empleado.dict(), created_by_id=current_user.id)
    db.add(new_empleado)
    db.commit()
    db.refresh(new_empleado)
    return new_empleado

@app.get("/empleados/", response_model=List[schemas.EmpleadoOut])
def get_empleados(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user), search: str = None):
    query = db.query(models.Empleado)
    if not current_user.is_admin:
        query = query.filter(models.Empleado.is_active == True)
    if search:
        query = query.filter(models.Empleado.nombre.ilike(f"%{search}%"))
    return query.all()

@app.get("/empleados/{empleado_id}", response_model=schemas.EmpleadoOut)
def get_empleado(empleado_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado

@app.put("/empleados/{empleado_id}", response_model=schemas.EmpleadoOut)
def update_empleado(
    empleado_id: int,
    empleado: schemas.EmpleadoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not db_empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    for key, value in empleado.dict().items():
        setattr(db_empleado, key, value)
    
    db_empleado.updated_at = datetime.now()
    db.commit()
    db.refresh(db_empleado)
    return db_empleado

@app.delete("/empleados/{empleado_id}")
def delete_empleado(
    empleado_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    empleado.is_active = False
    empleado.updated_at = datetime.now()
    db.commit()
    return {"message": "Empleado desactivado exitosamente"}

# --- ENDPOINTS PRODUCTOS ---

@app.post("/productos/", response_model=schemas.ProductoOut)
def create_producto(
    producto: schemas.ProductoCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # Validar si ya existe un producto con el mismo serial
    existing_producto = db.query(models.Producto).filter(models.Producto.serial == producto.serial).first()
    if existing_producto:
        raise HTTPException(status_code=400, detail="Ya existe un producto con ese serial")
    new_producto = models.Producto(**producto.dict(), created_by_id=current_user.id)
    db.add(new_producto)
    db.commit()
    db.refresh(new_producto)
    return new_producto

@app.get("/productos/", response_model=List[schemas.ProductoOut])
def get_productos(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user), search: str = None):
    query = db.query(models.Producto)
    if not current_user.is_admin:
        query = query.filter(models.Producto.is_active == True)
    if search:
        query = query.filter(
            or_(
                models.Producto.marca.ilike(f"%{search}%"),
                models.Producto.referencia.ilike(f"%{search}%"),
                models.Producto.serial.ilike(f"%{search}%")
            )
        )
    return query.all()

@app.get("/productos/{producto_id}", response_model=schemas.ProductoOut)
def get_producto(producto_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@app.put("/productos/{producto_id}", response_model=schemas.ProductoOut)
def update_producto(
    producto_id: int,
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    for key, value in producto.dict().items():
        setattr(db_producto, key, value)
    
    db_producto.updated_at = datetime.now()
    db.commit()
    db.refresh(db_producto)
    return db_producto

@app.delete("/productos/{producto_id}")
def delete_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    producto.is_active = False
    producto.updated_at = datetime.now()
    db.commit()
    return {"message": "Producto desactivado exitosamente"}

@app.get("/empleados/{empleado_id}/productos", response_model=List[schemas.ProductoOut])
def get_productos_empleado(empleado_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado.productos

@app.post("/empleados/{empleado_id}/productos/{producto_id}")
def asociar_producto_empleado(
    empleado_id: int, 
    producto_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    
    if not empleado or not producto:
        raise HTTPException(status_code=404, detail="Empleado o producto no encontrado")
    
    if producto not in empleado.productos:
        empleado.productos.append(producto)
        db.commit()
    
    return {"message": "Producto asociado exitosamente al empleado"}

@app.delete("/empleados/{empleado_id}/productos/{producto_id}")
def retirar_producto_empleado(
    empleado_id: int,
    producto_id: int,
    observacion: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    
    if not empleado or not producto:
        raise HTTPException(status_code=404, detail="Empleado o producto no encontrado")
    
    if producto not in empleado.productos:
        raise HTTPException(status_code=400, detail="El producto no está asociado a este empleado")
    
    # Buscar registro de inventario activo
    inventario = db.query(models.Inventory).filter(
        models.Inventory.empleado_id == empleado_id,
        models.Inventory.producto_id == producto_id,
        models.Inventory.is_active == True
    ).first()
    
    if inventario:
        inventario.is_active = False
        inventario.fecha_retiro = datetime.now()
        
        # Crear registro en historial
        historial = models.HistorialInventario(
            inventory_id=inventario.id,
            empleado_id=empleado_id,
            producto_id=producto_id,
            accion='retiro',
            observacion=observacion or f"Producto retirado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            created_by_id=current_user.id
        )
        db.add(historial)
    
    # Remover producto del empleado
    empleado.productos.remove(producto)
    db.commit()
    
    return {"message": "Producto retirado exitosamente del empleado"}

# --- ENDPOINTS INVENTARIO ---

@app.post("/inventory/", response_model=schemas.InventoryOut)
def create_item(item: schemas.InventoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Verificar si ya existe un registro activo con el mismo empleado y producto
    existing = db.query(models.Inventory).filter(
        models.Inventory.empleado_id == item.empleado_id,
        models.Inventory.producto_id == item.producto_id,
        models.Inventory.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un registro activo para este empleado y producto (ID: {existing.id})"
        )
    
    # Obtener empleado para usar su sede si no se proporciona
    empleado = db.query(models.Empleado).filter(models.Empleado.id == item.empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    # Usar sede del empleado si no se proporciona
    sede_id = item.sede_id if item.sede_id else empleado.ciudad_id
    
    item_dict = item.dict()
    item_dict['sede_id'] = sede_id
    new_item = models.Inventory(**item_dict, created_by_id=current_user.id)
    db.add(new_item)
    
    # Crear registro en historial
    historial = models.HistorialInventario(
        inventory_id=None,  # Se actualizará después del commit
        empleado_id=item.empleado_id,
        producto_id=item.producto_id,
        accion='asignacion',
        observacion=item.observacion,
        created_by_id=current_user.id
    )
    db.add(historial)
    db.flush()
    
    # Asociar producto al empleado si no existe
    producto = db.query(models.Producto).filter(models.Producto.id == item.producto_id).first()
    if empleado and producto and producto not in empleado.productos:
        empleado.productos.append(producto)
    
    db.commit()
    db.refresh(new_item)
    
    # Actualizar historial con inventory_id
    historial.inventory_id = new_item.id
    db.commit()
    
    return new_item

@app.get("/inventory/", response_model=List[schemas.InventoryOut])
def get_inventory(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Inventory)
    if not current_user.is_admin:
        query = query.filter(models.Inventory.is_active == True)
    total = query.count()
    items = query.all()
    return items

@app.get("/inventory/count")
def get_inventory_count(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Inventory)
    if not current_user.is_admin:
        query = query.filter(models.Inventory.is_active == True)
    return {"total": query.count()}

# --- ENDPOINTS TABLAS INDEPENDIENTES ---

@app.post("/areas/", response_model=schemas.CatalogOut)
def create_area(area: schemas.CatalogBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    new_area = models.Area(nombre=area.nombre, created_by_id=current_user.id)
    db.add(new_area)
    db.commit()
    db.refresh(new_area)
    return new_area

@app.get("/areas/", response_model=List[schemas.CatalogOut])
def get_areas(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Area).filter(models.Area.is_active == True).all()

@app.get("/empresas/", response_model=List[schemas.CatalogOut])
def get_empresas(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Empresa).filter(models.Empresa.is_active == True).all()

@app.get("/cargos/", response_model=List[schemas.CatalogOut])
def get_cargos(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Cargo).filter(models.Cargo.is_active == True).all()

@app.get("/ciudades/", response_model=List[schemas.CatalogOut])
def get_ciudades(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Ciudad).filter(models.Ciudad.is_active == True).all()

@app.get("/equipo_tipos/", response_model=List[schemas.CatalogOut])
def get_equipo_tipos(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.EquipoTipo).filter(models.EquipoTipo.is_active == True).all()

@app.post("/empresas/", response_model=schemas.CatalogOut)
def create_empresa(emp: schemas.CatalogBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    new_obj = models.Empresa(nombre=emp.nombre, created_by_id=current_user.id)
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return new_obj

    # --- ENDPOINT PARA CREAR USUARIOS ---
@app.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    # Opcional: Verificar si el current_user es admin
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    hashed_pw = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, full_name=user.full_name, password_hash=hashed_pw, is_admin=user.is_admin if user.is_admin is not None else False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    return db.query(models.User).all()

@app.post("/cargos/", response_model=schemas.CatalogOut)
def create_cargo(obj: schemas.CatalogBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    new_obj = models.Cargo(nombre=obj.nombre, created_by_id=current_user.id)
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return new_obj

@app.post("/ciudades/", response_model=schemas.CatalogOut)
def create_ciudad(obj: schemas.CatalogBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    new_obj = models.Ciudad(nombre=obj.nombre)
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return new_obj

@app.post("/equipo_tipos/", response_model=schemas.CatalogOut)
def create_equipo_tipo(obj: schemas.CatalogBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    new_obj = models.EquipoTipo(nombre=obj.nombre, created_by_id=current_user.id)
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return new_obj

# --- ENDPOINT PUT ESPECÍFICO PARA INVENTORY (DEBE IR ANTES DE LOS GENÉRICOS) ---
@app.put("/inventory/{item_id}", response_model=schemas.InventoryOut)
def update_inventory(item_id: int, data: schemas.InventoryCreate, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin_user)):
    # BUSCAR EL REGISTRO
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    # Guardar valores anteriores para el historial
    old_empleado_id = item.empleado_id
    old_producto_id = item.producto_id
    
    # ACTUALIZAR CAMPOS
    data_dict = data.model_dump() if hasattr(data, 'model_dump') else data.dict()
    for key, value in data_dict.items():
        setattr(item, key, value)
    
    # Crear registro en historial si cambió empleado o producto
    if old_empleado_id != data.empleado_id or old_producto_id != data.producto_id:
        historial = models.HistorialInventario(
            inventory_id=item_id,
            empleado_id=data.empleado_id,
            producto_id=data.producto_id,
            accion='cambio' if old_empleado_id != data.empleado_id or old_producto_id != data.producto_id else 'actualizacion',
            observacion=data.observacion,
            created_by_id=admin.id
        )
        db.add(historial)
        
        # Actualizar relaciones empleado-producto
        empleado = db.query(models.Empleado).filter(models.Empleado.id == data.empleado_id).first()
        producto = db.query(models.Producto).filter(models.Producto.id == data.producto_id).first()
        if empleado and producto and producto not in empleado.productos:
            empleado.productos.append(producto)
    
    db.commit()
    db.refresh(item)
    return item

# --- ENDPOINTS PUT Y DELETE PARA CATÁLOGOS (GENÉRICOS - DEBEN IR DESPUÉS DE LOS ESPECÍFICOS) ---
CATALOG_MODELS = {
    "areas": models.Area,
    "empresas": models.Empresa,
    "cargos": models.Cargo,
    "ciudades": models.Ciudad,
    "equipo_tipos": models.EquipoTipo
}

@app.put("/{catalog_type}/{item_id}", response_model=schemas.CatalogOut)
def update_catalog_item(
    catalog_type: str,
    item_id: int,
    item: schemas.CatalogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    if catalog_type not in CATALOG_MODELS:
        raise HTTPException(status_code=404, detail="Catálogo no encontrado")
    
    Model = CATALOG_MODELS[catalog_type]
    db_item = db.query(Model).filter(Model.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    db_item.nombre = item.nombre
    db_item.updated_at = datetime.now()
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/{catalog_type}/{item_id}")
def delete_catalog_item(
    catalog_type: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    if catalog_type not in CATALOG_MODELS:
        raise HTTPException(status_code=404, detail="Catálogo no encontrado")
    
    Model = CATALOG_MODELS[catalog_type]
    db_item = db.query(Model).filter(Model.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    db_item.is_active = False
    db_item.updated_at = datetime.now()
    db.commit()
    return {"message": "Item eliminado exitosamente"}

@app.get("/inventory/{item_id}/historial", response_model=List[schemas.HistorialOut])
def get_historial_inventory(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    historial = db.query(models.HistorialInventario).filter(
        models.HistorialInventario.inventory_id == item_id
    ).order_by(models.HistorialInventario.fecha_accion.desc()).all()
    return historial

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.patch("/inventory/{item_id}/retirar")
def retirar_equipo(
    item_id: int, 
    db: Session = Depends(get_db), 
    admin: models.User = Depends(get_current_admin_user),
    fecha_retiro: Optional[str] = None
):
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    item.is_active = False
    
    # Parsear fecha si se proporciona
    if fecha_retiro:
        try:
            item.fecha_retiro = datetime.fromisoformat(fecha_retiro.replace('Z', '+00:00'))
        except:
            item.fecha_retiro = datetime.now()
    else:
        item.fecha_retiro = datetime.now()
    
    # Crear registro en historial
    historial = models.HistorialInventario(
        inventory_id=item_id,
        empleado_id=item.empleado_id,
        producto_id=item.producto_id,
        accion='retiro',
        observacion=f"Equipo retirado el {item.fecha_retiro.strftime('%Y-%m-%d %H:%M:%S')}",
        created_by_id=admin.id
    )
    db.add(historial)
    db.commit()
    return {"message": "Equipo retirado exitosamente"}

@app.patch("/inventory/{item_id}/activar")
def activar_equipo(
    item_id: int, 
    db: Session = Depends(get_db), 
    admin: models.User = Depends(get_current_admin_user)
):
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    item.is_active = True  # Cambiamos a estado Retirado
    db.commit()
    return {"message": "Equipo activado exitosamente"}

@app.get("/reporte/excel")
async def export_inventory_excel(current_user: models.User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No tiene permisos para generar reportes")

    items = db.query(models.Inventory).all()

    data = []
    for item in items:
        empleado = item.empleado
        producto = item.producto
        sede = item.sede or (empleado.ciudad if empleado else None)
        data.append({
            "Fecha Asignación": item.fecha_asignacion.strftime('%d/%m/%Y') if item.fecha_asignacion else "N/A",
            "Fecha Retiro": item.fecha_retiro.strftime('%d/%m/%Y') if item.fecha_retiro else "N/A",
            "Responsable": empleado.nombre if empleado else "N/A",
            "Cargo": empleado.cargo.nombre if empleado and empleado.cargo else "N/A",
            "Área": empleado.area.nombre if empleado and empleado.area else "N/A",
            "Empresa": empleado.empresa.nombre if empleado and empleado.empresa else "N/A",
            "Ciudad": empleado.ciudad.nombre if empleado and empleado.ciudad else "N/A",
            "Sede": sede.nombre if sede else (empleado.ciudad.nombre if empleado and empleado.ciudad else "N/A"),
            "Marca": producto.marca if producto and producto.marca else "N/A",
            "Referencia": producto.referencia if producto and producto.referencia else "",
            "Tipo Equipo": producto.tipo.nombre if producto and producto.tipo else "N/A",
            "Memoria RAM": producto.memoria_ram if producto and producto.memoria_ram else "",
            "Disco Duro": producto.disco_duro if producto and producto.disco_duro else "",
            "Serial": producto.serial if producto and producto.serial else "",
            "Observaciones Producto": producto.observaciones if producto and producto.observaciones else "",
            "Quién Entrega": item.quien_entrega if item.quien_entrega else "N/A",
            "Observación": item.observacion if item.observacion else "",
            "Estado": "ACTIVO" if item.is_active else "RETIRADO"
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventario')
        
    output.seek(0)
    
    filename = f"Reporte_Inventario_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/inventory/upload-masivo")
async def bulk_upload_inventory(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))

    empleados_creados = 0
    productos_creados = 0
    registros_creados = 0
    
    for _, row in df.iterrows():
        try:
            fecha_excel = pd.to_datetime(row.get('Fecha', datetime.now()), dayfirst=True).to_pydatetime() if pd.notna(row.get('Fecha')) else datetime.now()
        except:
            fecha_excel = datetime.now()
        
        # Buscar o crear Cargo
        cargo_nombre = row.get('Cargo', '')
        cargo = None
        if cargo_nombre and pd.notna(cargo_nombre):
            cargo = db.query(models.Cargo).filter(models.Cargo.nombre == cargo_nombre).first()
            if not cargo:
                cargo = models.Cargo(nombre=cargo_nombre, created_by_id=current_user.id)
                db.add(cargo)
                db.flush()
        
        # Buscar o crear Area
        area_nombre = row.get('Área', '')
        area = None
        if area_nombre and pd.notna(area_nombre):
            area = db.query(models.Area).filter(models.Area.nombre == area_nombre).first()
            if not area:
                area = models.Area(nombre=area_nombre, created_by_id=current_user.id)
                db.add(area)
                db.flush()
        
        # Buscar o crear Empresa
        empresa_nombre = row.get('Empresa', '')
        empresa = None
        if empresa_nombre and pd.notna(empresa_nombre):
            empresa = db.query(models.Empresa).filter(models.Empresa.nombre == empresa_nombre).first()
            if not empresa:
                empresa = models.Empresa(nombre=empresa_nombre, created_by_id=current_user.id)
                db.add(empresa)
                db.flush()
        
        # Buscar o crear EquipoTipo
        tipo_nombre = row.get('Tipo Equipo', '')
        tipo = None
        if tipo_nombre and pd.notna(tipo_nombre):
            tipo = db.query(models.EquipoTipo).filter(models.EquipoTipo.nombre == tipo_nombre).first()
            if not tipo:
                tipo = models.EquipoTipo(nombre=tipo_nombre, created_by_id=current_user.id)
                db.add(tipo)
                db.flush()
        
        # Buscar o crear Ciudad
        ciudad_nombre = row.get('Ciudad', '')
        ciudad = None
        if ciudad_nombre and pd.notna(ciudad_nombre):
            ciudad = db.query(models.Ciudad).filter(models.Ciudad.nombre == ciudad_nombre).first()
            if not ciudad:
                ciudad = models.Ciudad(nombre=ciudad_nombre)
                db.add(ciudad)
                db.flush()
        
        # Buscar o crear Empleado
        empleado_nombre = row.get('Responsable', '')
        if not empleado_nombre or pd.isna(empleado_nombre):
            continue  # Saltar filas sin responsable
            
        empleado = db.query(models.Empleado).filter(
            models.Empleado.nombre == empleado_nombre,
            models.Empleado.cargo_id == (cargo.id if cargo else None),
            models.Empleado.area_id == (area.id if area else None),
            models.Empleado.empresa_id == (empresa.id if empresa else None)
        ).first()
        
        if not empleado and cargo and area and empresa and ciudad:
            empleado = models.Empleado(
                nombre=empleado_nombre,
                cargo_id=cargo.id,
                area_id=area.id,
                empresa_id=empresa.id,
                ciudad_id=ciudad.id,
                created_by_id=current_user.id
            )
            db.add(empleado)
            db.flush()
            empleados_creados += 1
        
        # Buscar o crear Producto
        marca = row.get('Marca', '')
        if not marca or pd.isna(marca):
            continue  # La marca es requerida
        
        referencia = row.get('Referencia', '') if pd.notna(row.get('Referencia')) else None
        memoria_ram = row.get('Memoria RAM', '') if pd.notna(row.get('Memoria RAM')) else None
        disco_duro = row.get('Disco Duro', '') if pd.notna(row.get('Disco Duro')) else None
        serial = row.get('Serial', '') if pd.notna(row.get('Serial')) else None
        observaciones_prod = row.get('Observaciones Producto', '') if pd.notna(row.get('Observaciones Producto')) else None
        
        # Buscar producto por serial si existe, o por marca+referencia
        producto = None
        if serial:
            producto = db.query(models.Producto).filter(models.Producto.serial == serial).first()
        
        if not producto and referencia:
            producto = db.query(models.Producto).filter(
                models.Producto.marca == marca,
                models.Producto.referencia == referencia
            ).first()
        
        if not producto:
            if not tipo:
                continue  # Necesitamos tipo para crear producto
            producto = models.Producto(
                marca=marca,
                referencia=referencia,
                memoria_ram=memoria_ram,
                disco_duro=disco_duro,
                serial=serial,
                observaciones=observaciones_prod,
                tipo_id=tipo.id,
                created_by_id=current_user.id
            )
            db.add(producto)
            db.flush()
            productos_creados += 1
        
        # Si no se pudo crear empleado o producto, continuar
        if not empleado or not producto:
            continue
        
        # Asociar producto al empleado si no existe
        if producto not in empleado.productos:
            empleado.productos.append(producto)
            db.flush()
        
        # Obtener sede (del campo Sede o Ciudad)
        sede_nombre = row.get('Sede', '') or ciudad_nombre
        sede = None
        if sede_nombre and pd.notna(sede_nombre):
            sede = db.query(models.Ciudad).filter(models.Ciudad.nombre == sede_nombre).first()
            if not sede:
                sede = ciudad  # Usar ciudad si no se encuentra sede
        
        # Crear registro de inventario
        new_item = models.Inventory(
            empleado_id=empleado.id,
            producto_id=producto.id,
            sede_id=sede.id if sede else empleado.ciudad_id,
            fecha_asignacion=fecha_excel,
            quien_entrega=row.get('Quién Entrega', '') if pd.notna(row.get('Quién Entrega')) else None,
            observacion=row.get('Observación', '') if pd.notna(row.get('Observación')) else None,
            is_active=True,
            created_by_id=current_user.id
        )
        db.add(new_item)
        db.flush()
        
        # Crear registro en historial
        historial = models.HistorialInventario(
            inventory_id=None,  # Se actualizará después del commit
            empleado_id=empleado.id,
            producto_id=producto.id,
            accion='asignacion',
            observacion=f"Carga masiva - {row.get('Observación', '') if pd.notna(row.get('Observación')) else ''}",
            created_by_id=current_user.id
        )
        db.add(historial)
        db.flush()
        
        historial.inventory_id = new_item.id
        db.commit()
        db.refresh(new_item)
        registros_creados += 1

    return {
        "message": f"Carga exitosa: {empleados_creados} empleados, {productos_creados} productos, {registros_creados} registros de inventario creados."

def generate_pdf_content(inventory_item, tipo='asignacion'):
    """Genera contenido PDF para asignación o retiro de equipo utilizando plantilla PDF, colocando la información más abajo en la página."""
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=500, detail="ReportLab no está instalado. Instale con: pip install reportlab")

    plantilla_path = os.path.join(os.path.dirname(__file__), "plantilla", "HOJA_MEMBRETE_MOLINOS.pdf")

    # --- Crear PDF temporal para el contenido dinámico ---
    data_buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(data_buffer.name, pagesize=A4)

    # --- Definimos el margen superior más bajo para colocar la información más abajo ---
    # Puedes ajustar MARGIN_TOP según el diseño de la plantilla PDF (por ejemplo, rebajado unos 6-7cm)
    MARGIN_TOP = 7.7 * cm  # Más bajo para que todo baje
    LEFT_MARGIN = 2.1 * cm  # Leve ajuste lateral

    # Título (más abajo)
    title_text = "ACTA DE ASIGNACIÓN DE EQUIPO" if tipo == 'asignacion' else "ACTA DE RETIRO DE EQUIPO"
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor('#1e40af')
    c.drawCentredString(A4[0] / 2, A4[1] - MARGIN_TOP, title_text)
    c.setFillColor('black')
    y = A4[1] - MARGIN_TOP - 1.3 * cm

    # Información del empleado y equipo en líneas tipo "formulario"
    empleado = inventory_item.empleado
    producto = inventory_item.producto

    sede = None
    if hasattr(inventory_item, 'sede') and inventory_item.sede:
        sede = inventory_item.sede
    elif empleado and hasattr(empleado, 'ciudad') and empleado.ciudad:
        sede = empleado.ciudad

    # Fecha
    fecha_valor = inventory_item.fecha_asignacion.strftime('%d/%m/%Y %H:%M') if tipo == 'asignacion' and inventory_item.fecha_asignacion \
        else (inventory_item.fecha_retiro.strftime('%d/%m/%Y %H:%M') if inventory_item.fecha_retiro else datetime.now().strftime('%d/%m/%Y %H:%M'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT_MARGIN, y, "FECHA:")
    c.setFont("Helvetica", 10)
    c.drawString(LEFT_MARGIN + 2.7*cm, y, fecha_valor)
    y -= 0.7*cm

    if empleado:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, y, "EMPLEADO:")
        c.setFont("Helvetica", 10)
        c.drawString(LEFT_MARGIN + 2.7*cm, y, str(empleado.nombre or 'N/A'))
        y -= 0.6*cm

        if empleado.cargo:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(LEFT_MARGIN, y, "CARGO:")
            c.setFont("Helvetica", 10)
            c.drawString(LEFT_MARGIN + 2.7*cm, y, str(empleado.cargo.nombre))
            y -= 0.6*cm

        if empleado.area:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(LEFT_MARGIN, y, "ÁREA:")
            c.setFont("Helvetica", 10)
            c.drawString(LEFT_MARGIN + 2.7*cm, y, str(empleado.area.nombre))
            y -= 0.6*cm

        if empleado.empresa:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(LEFT_MARGIN, y, "EMPRESA:")
            c.setFont("Helvetica", 10)
            c.drawString(LEFT_MARGIN + 2.7*cm, y, str(empleado.empresa.nombre))
            y -= 0.6*cm

    if sede:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, y, "SEDE:")
        c.setFont("Helvetica", 10)
        c.drawString(LEFT_MARGIN + 2.7*cm, y, str(sede.nombre))
        y -= 0.6*cm

    if inventory_item.quien_entrega:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, y, "QUIÉN ENTREGA:")
        c.setFont("Helvetica", 10)
        c.drawString(LEFT_MARGIN + 2.7*cm, y, str(inventory_item.quien_entrega))
        y -= 0.7*cm

    # Espacio antes de especificaciones
    y -= 0.45*cm

    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(LEFT_MARGIN, y, "ESPECIFICACIONES DEL EQUIPO:")
    y -= 0.6*cm

    # Especificaciones del producto
    c.setFont("Helvetica", 10)
    if producto:
        if producto.marca:
            c.drawString(LEFT_MARGIN, y, f"Marca: {producto.marca}")
            y -= 0.45*cm
        if producto.referencia:
            c.drawString(LEFT_MARGIN, y, f"Referencia: {producto.referencia}")
            y -= 0.45*cm
        if producto.tipo:
            c.drawString(LEFT_MARGIN, y, f"Tipo de Equipo: {producto.tipo.nombre}")
            y -= 0.45*cm
        if producto.serial:
            c.drawString(LEFT_MARGIN, y, f"Serial: {producto.serial}")
            y -= 0.45*cm
        if producto.memoria_ram:
            c.drawString(LEFT_MARGIN, y, f"Memoria RAM: {producto.memoria_ram}")
            y -= 0.45*cm
        if producto.disco_duro:
            c.drawString(LEFT_MARGIN, y, f"Disco Duro: {producto.disco_duro}")
            y -= 0.45*cm
        if producto.observaciones:
            c.drawString(LEFT_MARGIN, y, f"Observaciones: {producto.observaciones}")
            y -= 0.45*cm

    if inventory_item.observacion:
        c.drawString(LEFT_MARGIN, y, f"Observación General: {inventory_item.observacion}")
        y -= 0.45*cm

    # Espaciado hacia la parte baja para las firmas
    y_firma_empleado = 4.5*cm
    y_firma_entrega = 3.2*cm

    c.setFont("Helvetica", 10)
    c.drawString(LEFT_MARGIN, y_firma_empleado, "Firma del Empleado: ___________________________")
    c.drawString(LEFT_MARGIN, y_firma_entrega, "Firma de Quien Entrega: ________________________")

    c.save()

    # --- Merge plantilla con PDF generado ---
    output_buffer = io.BytesIO()
    with open(plantilla_path, "rb") as plantilla_file:
        plantilla_reader = PdfReader(plantilla_file)
        plantilla_page = plantilla_reader.pages[0]

        contenido_reader = PdfReader(data_buffer.name)
        contenido_page = contenido_reader.pages[0]

        writer = PdfWriter()
        # Overlay (el contenido "cae encima" de la plantilla)
        plantilla_page.merge_page(contenido_page)
        writer.add_page(plantilla_page)
        writer.write(output_buffer)
        output_buffer.seek(0)

    # Limpiar archivo temporal
    data_buffer.close()
    try:
        os.unlink(data_buffer.name)
    except Exception:
        pass

    return output_buffer

@app.get("/inventory/{item_id}/pdf-asignacion")
def generar_pdf_asignacion(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Genera PDF de asignación de equipo"""
    from sqlalchemy.orm import joinedload
    inventory_item = db.query(models.Inventory)\
        .options(
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.cargo),
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.area),
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.empresa),
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.ciudad),
            joinedload(models.Inventory.producto).joinedload(models.Producto.tipo),
            joinedload(models.Inventory.sede)
        )\
        .filter(models.Inventory.id == item_id).first()
    if not inventory_item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    buffer = generate_pdf_content(inventory_item, tipo='asignacion')
    
    filename = f"Acta_Asignacion_{inventory_item.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/inventory/{item_id}/pdf-retiro")
def generar_pdf_retiro(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Genera PDF de retiro de equipo"""
    from sqlalchemy.orm import joinedload
    inventory_item = db.query(models.Inventory)\
        .options(
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.cargo),
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.area),
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.empresa),
            joinedload(models.Inventory.empleado).joinedload(models.Empleado.ciudad),
            joinedload(models.Inventory.producto).joinedload(models.Producto.tipo),
            joinedload(models.Inventory.sede)
        )\
        .filter(models.Inventory.id == item_id).first()
    if not inventory_item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    buffer = generate_pdf_content(inventory_item, tipo='retiro')
    
    filename = f"Acta_Retiro_{inventory_item.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )