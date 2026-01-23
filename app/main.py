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
import os

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.utils import ImageReader
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
    allow_methods=["*"],
    allow_headers=["*"],
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

# --- ENDPOINTS DE PRODUCTOS ---
@app.get("/productos/", response_model=List[schemas.Producto])
def listar_productos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    productos = db.query(models.Producto).offset(skip).limit(limit).all()
    return productos

@app.get("/productos/{producto_id}", response_model=schemas.Producto)
def obtener_producto(producto_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@app.post("/productos/", response_model=schemas.Producto)
def crear_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_producto = models.Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

@app.put("/productos/{producto_id}", response_model=schemas.Producto)
def actualizar_producto(producto_id: int, producto: schemas.ProductoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for k, v in producto.dict().items():
        setattr(db_producto, k, v)
    db.commit()
    db.refresh(db_producto)
    return db_producto

@app.delete("/productos/{producto_id}")
def eliminar_producto(producto_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(db_producto)
    db.commit()
    return {"msg": "Producto eliminado correctamente"}

# --- ENDPOINTS DE EMPLEADOS ---
@app.get("/empleados/", response_model=List[schemas.Empleado])
def listar_empleados(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    empleados = db.query(models.Empleado).offset(skip).limit(limit).all()
    return empleados

@app.get("/empleados/{empleado_id}", response_model=schemas.Empleado)
def obtener_empleado(empleado_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado

@app.post("/empleados/", response_model=schemas.Empleado)
def crear_empleado(empleado: schemas.EmpleadoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_empleado = models.Empleado(**empleado.dict())
    db.add(db_empleado)
    db.commit()
    db.refresh(db_empleado)
    return db_empleado

@app.put("/empleados/{empleado_id}", response_model=schemas.Empleado)
def actualizar_empleado(empleado_id: int, empleado: schemas.EmpleadoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not db_empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    for k, v in empleado.dict().items():
        setattr(db_empleado, k, v)
    db.commit()
    db.refresh(db_empleado)
    return db_empleado

@app.delete("/empleados/{empleado_id}")
def eliminar_empleado(empleado_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not db_empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    db.delete(db_empleado)
    db.commit()
    return {"msg": "Empleado eliminado correctamente"}

# --- ENDPOINTS DE INVENTARIO ---
@app.get("/inventory/", response_model=List[schemas.Inventory])
def listar_inventario(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    items = db.query(models.Inventory).offset(skip).limit(limit).all()
    return items

@app.get("/inventory/{item_id}", response_model=schemas.Inventory)
def obtener_inventario(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro de inventario no encontrado")
    return item

@app.post("/inventory/", response_model=schemas.Inventory)
def crear_inventario(inventory: schemas.InventoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_item = models.Inventory(**inventory.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/inventory/{item_id}", response_model=schemas.Inventory)
def actualizar_inventario(item_id: int, inventory: schemas.InventoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Registro de inventario no encontrado")
    for k, v in inventory.dict().items():
        setattr(db_item, k, v)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/inventory/{item_id}")
def eliminar_inventario(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    db_item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Registro de inventario no encontrado")
    db.delete(db_item)
    db.commit()
    return {"msg": "Registro de inventario eliminado correctamente"}


def generate_pdf_content_with_hoja_membrete(inventory_item, tipo='asignacion'):
    """Genera contenido PDF para asignación de equipo utilizando la plantilla HOJA_MEMBRETE_MOLINOS.pdf"""
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=500, detail="ReportLab no está instalado. Instale con: pip install reportlab")

    from reportlab.pdfgen import canvas
    from reportlab.platypus import Table, TableStyle, Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    plantilla_path = os.path.join(BASE_DIR, "plantilla", "HOJA_MEMBRETE_MOLINOS.pdf")
    if not os.path.exists(plantilla_path):
        raise HTTPException(status_code=500, detail="Plantilla HOJA_MEMBRETE_MOLINOS.pdf no encontrada en app/plantilla/")

    from PyPDF2 import PdfReader, PdfWriter

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )
    story = []
    styles = getSampleStyleSheet()

    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=1  # Centrado
    )
    title_text = "ACTA DE ASIGNACIÓN DE EQUIPO"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 0.5*cm))

    # Datos Generales
    empleado = inventory_item.empleado
    producto = inventory_item.producto
    sede = None
    if hasattr(inventory_item, 'sede') and inventory_item.sede:
        sede = inventory_item.sede
    elif empleado and hasattr(empleado, 'ciudad') and empleado.ciudad:
        sede = empleado.ciudad

    data = [
        ['<b>FECHA:</b>', inventory_item.fecha_asignacion.strftime('%d/%m/%Y %H:%M') if inventory_item.fecha_asignacion else datetime.now().strftime('%d/%m/%Y %H:%M')],
    ]
    if empleado:
        data.append(['<b>EMPLEADO:</b>', empleado.nombre or 'N/A'])
        if empleado.cargo:
            data.append(['<b>CARGO:</b>', empleado.cargo.nombre])
        if empleado.area:
            data.append(['<b>ÁREA:</b>', empleado.area.nombre])
        if empleado.empresa:
            data.append(['<b>EMPRESA:</b>', empleado.empresa.nombre])
    if sede:
        data.append(['<b>SEDE:</b>', sede.nombre])
    if inventory_item.quien_entrega:
        data.append(['<b>QUIÉN ENTREGA:</b>', inventory_item.quien_entrega])

    story.append(Spacer(1, 0.3*cm))
    table = Table(data, colWidths=[5*cm, 12*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5*cm))

    product_title = Paragraph("<b>ESPECIFICACIONES DEL EQUIPO:</b>", styles['Heading2'])
    story.append(product_title)
    story.append(Spacer(1, 0.3*cm))
    product_data = []
    if producto:
        if producto.marca:
            product_data.append(['<b>Marca:</b>', producto.marca])
        if producto.referencia:
            product_data.append(['<b>Referencia:</b>', producto.referencia])
        if producto.tipo:
            product_data.append(['<b>Tipo de Equipo:</b>', producto.tipo.nombre])
        if producto.serial:
            product_data.append(['<b>Serial:</b>', producto.serial])
        if producto.memoria_ram:
            product_data.append(['<b>Memoria RAM:</b>', producto.memoria_ram])
        if producto.disco_duro:
            product_data.append(['<b>Disco Duro:</b>', producto.disco_duro])
        if producto.observaciones:
            product_data.append(['<b>Observaciones:</b>', producto.observaciones])
    if inventory_item.observacion:
        product_data.append(['<b>Observación General:</b>', inventory_item.observacion])

    if product_data:
        product_table = Table(product_data, colWidths=[5*cm, 12*cm])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(product_table)

    story.append(Spacer(1, 1*cm))
    # Firmas
    signature_text = "Firma del Empleado: _________________________"
    story.append(Paragraph(signature_text, styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Firma de Quien Entrega: _________________________", styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    # Superponer contenido sobre el membrete
    temp_pdf_buf = buffer.getvalue()
    packet = io.BytesIO(temp_pdf_buf)

    plantilla_reader = PdfReader(plantilla_path)
    plantilla_page = plantilla_reader.pages[0]

    from PyPDF2 import PdfReader as PDFReader2, PdfWriter as PDFWriter2

    overlay_reader = PDFReader2(packet)
    overlay_page = overlay_reader.pages[0]

    plantilla_page.merge_page(overlay_page)
    output_writer = PDFWriter2()
    output_writer.add_page(plantilla_page)

    result_buffer = io.BytesIO()
    output_writer.write(result_buffer)
    result_buffer.seek(0)
    return result_buffer

@app.get("/inventory/{item_id}/pdf-asignacion")
def generar_pdf_asignacion(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Genera PDF de asignación de equipo usando HOJA_MEMBRETE_MOLINOS.pdf"""
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

    buffer = generate_pdf_content_with_hoja_membrete(inventory_item, tipo='asignacion')
    filename = f"Acta_Asignacion_{inventory_item.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
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

    # Para retiro, se sigue usando el PDF sin membrete.
    def generate_pdf_content(inventory_item, tipo='retiro'):
        if not REPORTLAB_AVAILABLE:
            raise HTTPException(status_code=500, detail="ReportLab no está instalado. Instale con: pip install reportlab")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        story = []
        styles = getSampleStyleSheet()

        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=1  # Center
        )
        title_text = "ACTA DE RETIRO DE EQUIPO"
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 0.5*cm))

        # Datos tabla
        empleado = inventory_item.empleado
        producto = inventory_item.producto
        sede = None
        if hasattr(inventory_item, 'sede') and inventory_item.sede:
            sede = inventory_item.sede
        elif empleado and hasattr(empleado, 'ciudad') and empleado.ciudad:
            sede = empleado.ciudad

        data = [
            ['<b>FECHA:</b>', inventory_item.fecha_retiro.strftime('%d/%m/%Y %H:%M') if inventory_item.fecha_retiro else datetime.now().strftime('%d/%m/%Y %H:%M')],
        ]
        if empleado:
            data.append(['<b>EMPLEADO:</b>', empleado.nombre or 'N/A'])
            if empleado.cargo:
                data.append(['<b>CARGO:</b>', empleado.cargo.nombre])
            if empleado.area:
                data.append(['<b>ÁREA:</b>', empleado.area.nombre])
            if empleado.empresa:
                data.append(['<b>EMPRESA:</b>', empleado.empresa.nombre])
        if sede:
            data.append(['<b>SEDE:</b>', sede.nombre])
        if inventory_item.quien_entrega:
            data.append(['<b>QUIÉN ENTREGA:</b>', inventory_item.quien_entrega])

        story.append(Spacer(1, 0.3*cm))
        table = Table(data, colWidths=[5*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

        product_title = Paragraph("<b>ESPECIFICACIONES DEL EQUIPO:</b>", styles['Heading2'])
        story.append(product_title)
        story.append(Spacer(1, 0.3*cm))
        product_data = []
        if producto:
            if producto.marca:
                product_data.append(['<b>Marca:</b>', producto.marca])
            if producto.referencia:
                product_data.append(['<b>Referencia:</b>', producto.referencia])
            if producto.tipo:
                product_data.append(['<b>Tipo de Equipo:</b>', producto.tipo.nombre])
            if producto.serial:
                product_data.append(['<b>Serial:</b>', producto.serial])
            if producto.memoria_ram:
                product_data.append(['<b>Memoria RAM:</b>', producto.memoria_ram])
            if producto.disco_duro:
                product_data.append(['<b>Disco Duro:</b>', producto.disco_duro])
            if producto.observaciones:
                product_data.append(['<b>Observaciones:</b>', producto.observaciones])
        if inventory_item.observacion:
            product_data.append(['<b>Observación General:</b>', inventory_item.observacion])

        if product_data:
            product_table = Table(product_data, colWidths=[5*cm, 12*cm])
            product_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(product_table)

        story.append(Spacer(1, 1*cm))
        # Firma
        signature_text = "Firma del Empleado: _________________________"
        story.append(Paragraph(signature_text, styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Firma de Quien Entrega: _________________________", styles['Normal']))

        doc.build(story)
        buffer.seek(0)
        return buffer

    buffer = generate_pdf_content(inventory_item, tipo='retiro')
    filename = f"Acta_Retiro_{inventory_item.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )