"""
Configuración de la aplicación.
Maneja todas las variables de entorno y constantes globales.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación."""
    
    # Base de datos
    database_url: str = "postgresql://neondb_owner:npg_NqOnXBEs1rH9@ep-muddy-rain-ahou8reu-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    
    # Seguridad
    secret_key: str = "MI_CLAVE_SECRETA_SUPER_SEGURA"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 horas
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://molinos-inventario-front.onrender.com"
    ]
    
    # Credenciales por defecto
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"
    default_admin_full_name: str = "Administrador"
    
    # Entorno
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración de forma singleton.
    Se cachea después del primer acceso.
    """
    return Settings()
