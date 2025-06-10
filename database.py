from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de la base de données
URL_BASE_DE_DONNEES = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://root:password@localhost/dmc_db?charset=utf8mb4"
)

# Créer le moteur SQLAlchemy
moteur = create_engine(
    URL_BASE_DE_DONNEES,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=False  # Définir sur True pour la journalisation des requêtes SQL
)

# Usine de sessions
SessionLocale = sessionmaker(autocommit=False, autoflush=False, bind=moteur)

# Classe de base pour les modèles
Base = declarative_base()

def obtenir_session() -> Session:
    """Obtenir une session de base de données."""
    session = SessionLocale()
    try:
        yield session
    finally:
        session.close()

@contextmanager
def obtenir_session_base_de_donnees():
    """Gestionnaire de contexte pour les sessions de base de données."""
    session = SessionLocale()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        db.close()

def init_db():
    """Initialize the database by creating all tables."""
    from . import models  # Import models to register them with SQLAlchemy
    Base.metadata.create_all(bind=engine)

def drop_db():
    """Drop all tables in the database."""
    from . import models  # Import models to register them with SQLAlchemy
    Base.metadata.drop_all(bind=engine)

def recreate_db():
    """Drop and recreate all tables."""
    drop_db()
    init_db()

# Dependency to get DB session
def get_db_dependency():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
