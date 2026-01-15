from typing import List
from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import models, schemas, auth, database
from .database import engine, get_db
from jose import jwt, JWTError
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from datetime import datetime
from fastapi.responses import StreamingResponse

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Inventario Oficina")
# --- CONFIGURACIÓN DE CORS ---
origins = [
    "http://localhost:5173", # Puerto por defecto de Vite
    "http://127.0.0.1:5173",
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

# --- ENDPOINTS INVENTARIO ---

@app.post("/inventory/", response_model=schemas.InventoryOut)
def create_item(item: schemas.InventoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_item = models.Inventory(**item.dict(), created_by_id=current_user.id)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/inventory/", response_model=List[schemas.InventoryOut])
def get_inventory(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.is_admin:
        return db.query(models.Inventory).all()
    return db.query(models.Inventory).filter(models.Inventory.is_active == True).all()

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
    new_user = models.User(username=user.username, full_name=user.full_name, password_hash=hashed_pw, is_admin=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/cargos/", response_model=schemas.CatalogOut)
def create_cargo(obj: schemas.CatalogBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    new_obj = models.Cargo(nombre=obj.nombre)
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
    new_obj = models.EquipoTipo(nombre=obj.nombre)
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return new_obj

@app.put("/inventory/{item_id}", response_model=schemas.InventoryOut)
def update_inventory(item_id: int, data: schemas.InventoryCreate, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin_user)
):
    # BUSCAR EL REGISTRO
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    # ACTUALIZAR CAMPOS
    for key, value in data.dict().items():
        setattr(item, key, value)
    
    db.commit()
    db.refresh(item)
    return item

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.patch("/inventory/{item_id}/retirar")
def retirar_equipo(
    item_id: int, 
    db: Session = Depends(get_db), 
    admin: models.User = Depends(get_current_admin_user)
):
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    item.is_active = False  # Cambiamos a estado Retirado
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

    # 1. Obtener datos de la DB (Ajusta según tu ORM)
    # Ejemplo: items = db.query(Inventory).all()
    items = db.query(models.Inventory).all()

    data = []
    for item in items:
        data.append({
            "Fecha": item.created_at.strftime('%d/%m/%Y'),
            "Responsable": item.empleado_nombre,
            "Cargo": item.cargo.nombre if item.cargo else "N/A",
            "Área": item.area.nombre if item.area else "N/A",
            "Quién Entrega": item.quien_entrega,
            "Empresa": item.empresa.nombre if item.empresa else "N/A",
            "Ciudad": item.ciudad.nombre if item.ciudad else "N/A",
            "Tipo Equipo": item.equipo.nombre if item.equipo else "N/A",
            "Cantidad": item.cantidad,
            "Marca": item.marca if item.marca else "",
            "Características": item.caracteristicas,
            "Observación": item.observacion,
            "Estado": "ACTIVO" if item.is_active else "RETIRADO"
        })

    # 2. Crear Excel en memoria usando Pandas
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
    # Leemos el Excel
    df = pd.read_excel(io.BytesIO(contents))

    registros_creados = 0
    
    for _, row in df.iterrows():
        try:
            # Si la celda está vacía en el Excel, podrías definir un default o saltarlo
            # Usamos dayfirst=True para formato dd/mm/yyyy
            fecha_excel = pd.to_datetime(row['Fecha'], dayfirst=True).to_pydatetime()
        except:
            # Si hay un error en el formato de fecha del Excel, usa la actual o reporta error
            fecha_excel = datetime.now()
        
        # Buscar o crear Cargo
        cargo = db.query(models.Cargo).filter(models.Cargo.nombre == row['Cargo']).first()
        if not cargo:
            cargo = models.Cargo(nombre=row['Cargo'], created_by_id=current_user.id)
            db.add(cargo)
            db.flush()
        
        # Buscar o crear Area
        area = db.query(models.Area).filter(models.Area.nombre == row['Área']).first()
        if not area:
            area = models.Area(nombre=row['Área'], created_by_id=current_user.id)
            db.add(area)
            db.flush()
        
        # Buscar o crear Empresa
        empresa = db.query(models.Empresa).filter(models.Empresa.nombre == row['Empresa']).first()
        if not empresa:
            empresa = models.Empresa(nombre=row['Empresa'], created_by_id=current_user.id)
            db.add(empresa)
            db.flush()
        
        # Buscar o crear EquipoTipo
        equipo = db.query(models.EquipoTipo).filter(models.EquipoTipo.nombre == row['Tipo Equipo']).first()
        if not equipo:
            equipo = models.EquipoTipo(nombre=row['Tipo Equipo'], created_by_id=current_user.id)
            db.add(equipo)
            db.flush()
        
        # Buscar o crear Ciudad
        ciudad = db.query(models.Ciudad).filter(models.Ciudad.nombre == row['Ciudad']).first()
        if not ciudad:
            ciudad = models.Ciudad(nombre=row['Ciudad'])
            db.add(ciudad)
            db.flush()
        
        new_item = models.Inventory(
            empleado_nombre=row['Responsable'],
            cantidad=row['Cantidad'],
            marca=row.get('Marca', '') if pd.notna(row.get('Marca')) else '',
            caracteristicas=row['Características'],
            is_active=True,
            created_at=fecha_excel,
            cargo_id=cargo.id,
            area_id=area.id,
            empresa_id=empresa.id,
            equipo_id=equipo.id,
            ciudad_id=ciudad.id,
            quien_entrega=row['Quién Entrega'],
            observacion=row['Observación'],
            created_by_id=current_user.id
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        registros_creados += 1

    return {"message": f"Carga exitosa: {registros_creados} nuevos registros con sus fechas originales."}