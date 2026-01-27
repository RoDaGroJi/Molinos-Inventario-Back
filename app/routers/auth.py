"""
Rutas de autenticación y gestión de usuarios.
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from . import models, schemas, auth
from .database import get_db
from .exceptions import InvalidCredentialsException, ForbiddenException, DuplicateResourceException
from .auth import verify_password, get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint de login.
    
    Verifica las credenciales del usuario y retorna un token JWT.
    
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
        db: Sesión de base de datos
        
    Returns:
        Token JWT con información del usuario
        
    Raises:
        InvalidCredentialsException: Si las credenciales son incorrectas
    """
    user = db.query(models.User).filter(
        models.User.username == username
    ).first()
    
    if not user or not verify_password(password, user.password_hash):
        logger.warning(f"Intento de login fallido para usuario: {username}")
        raise InvalidCredentialsException()
    
    if not user.is_active:
        logger.warning(f"Usuario inactivo intentó acceder: {username}")
        raise InvalidCredentialsException()
    
    access_token = auth.create_access_token(data={"sub": user.username})
    logger.info(f"Usuario {username} inició sesión exitosamente")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserOut.from_orm(user)
    }


@router.get("/me", response_model=schemas.UserOut)
def get_current_user_info(
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Obtiene la información del usuario autenticado.
    
    Args:
        current_user: Usuario autenticado (inyectado)
        
    Returns:
        Información del usuario actual
    """
    return current_user


@router.post("/users/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Crea un nuevo usuario (solo administrador).
    
    Args:
        user_data: Datos del nuevo usuario
        db: Sesión de base de datos
        current_user: Usuario administrador autenticado
        
    Returns:
        Información del nuevo usuario creado
        
    Raises:
        DuplicateResourceException: Si el username ya existe
    """
    existing_user = db.query(models.User).filter(
        models.User.username == user_data.username
    ).first()
    
    if existing_user:
        raise DuplicateResourceException("Usuario", "username")
    
    new_user = models.User(
        username=user_data.username,
        full_name=user_data.full_name,
        password_hash=get_password_hash(user_data.password),
        is_admin=user_data.is_admin
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Nuevo usuario creado: {user_data.username} por {current_user.username}")
    
    return new_user
