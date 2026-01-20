from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cambia la configuración para usar PostgreSQL
# Ejemplo: usuario=postgres, contraseña=postgres, base de datos=inventory, host=localhost, puerto=5432
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_NqOnXBEs1rH9@ep-muddy-rain-ahou8reu-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()