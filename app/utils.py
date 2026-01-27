"""
Utilidades y funciones auxiliares de la aplicación.
"""

import logging
from typing import TypeVar, Generic, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CRUDRepository(Generic[T]):
    """
    Clase genérica para operaciones CRUD en la base de datos.
    Reduce código duplicado en las operaciones básicas.
    """
    
    def __init__(self, model_class: type[T]):
        self.model_class = model_class
    
    def create(self, db: Session, obj_in: dict) -> T:
        """Crea un nuevo objeto en la base de datos."""
        db_obj = self.model_class(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_by_id(self, db: Session, obj_id: int) -> Optional[T]:
        """Obtiene un objeto por su ID."""
        return db.query(self.model_class).filter(
            self.model_class.id == obj_id
        ).first()
    
    def get_all(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        order_by_field: str = "id",
        order_desc: bool = True
    ) -> List[T]:
        """
        Obtiene todos los objetos con paginación y ordenamiento.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar
            order_by_field: Campo por el cual ordenar
            order_desc: Si True, ordena descendente
            
        Returns:
            Lista de objetos
        """
        query = db.query(self.model_class)
        
        # Ordenamiento
        if hasattr(self.model_class, order_by_field):
            order_column = getattr(self.model_class, order_by_field)
            if order_desc:
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(order_column)
        
        return query.offset(skip).limit(limit).all()
    
    def update(self, db: Session, obj_id: int, obj_in: dict) -> Optional[T]:
        """Actualiza un objeto existente."""
        db_obj = self.get_by_id(db, obj_id)
        if db_obj:
            for key, value in obj_in.items():
                setattr(db_obj, key, value)
            db.commit()
            db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, obj_id: int) -> bool:
        """Elimina un objeto (soft delete si tiene is_active)."""
        db_obj = self.get_by_id(db, obj_id)
        if db_obj:
            if hasattr(db_obj, 'is_active'):
                db_obj.is_active = False
            else:
                db.delete(db_obj)
            db.commit()
            return True
        return False
