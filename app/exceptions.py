"""
Excepciones personalizadas de la aplicación.
"""

from fastapi import HTTPException, status


class BaseAppException(HTTPException):
    """Excepción base de la aplicación."""
    
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class ResourceNotFoundException(BaseAppException):
    """Se lanza cuando un recurso no es encontrado."""
    
    def __init__(self, resource_name: str, resource_id: any = None):
        detail = f"{resource_name} no encontrado"
        if resource_id:
            detail += f" (ID: {resource_id})"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedException(BaseAppException):
    """Se lanza cuando el usuario no tiene permisos."""
    
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(BaseAppException):
    """Se lanza cuando el usuario no tiene permiso para la operación."""
    
    def __init__(self, detail: str = "Operación no permitida"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class InvalidCredentialsException(BaseAppException):
    """Se lanza cuando las credenciales son inválidas."""
    
    def __init__(self):
        super().__init__(
            detail="Usuario o contraseña incorrectos",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class DuplicateResourceException(BaseAppException):
    """Se lanza cuando se intenta crear un recurso duplicado."""
    
    def __init__(self, resource_name: str, field: str = None):
        detail = f"{resource_name} ya existe"
        if field:
            detail += f" con este {field}"
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class ValidationException(BaseAppException):
    """Se lanza cuando hay errores de validación."""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
