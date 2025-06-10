import asyncio
import threading
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
import uvicorn
import os
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Importer la base de données et les modèles
from .database import moteur, Base, obtenir_session
from . import models

# Importer les routeurs API
from .api.auth import router as authentification_router
from .api.patients import router as patients_router
from .api.medecins import router as medecins_router
from .api.hospitals import router as hopitaux_router

# Importer le planificateur de notifications
from .tasks import NotificationScheduler

# Créer les tables de la base de données
Base.metadata.create_all(bind=moteur)

# Créer le répertoire des uploads si il n'existe pas
REPERTOIRE_UPLOAD = Path("uploads")
REPERTOIRE_UPLOAD.mkdir(exist_ok=True)

# Créer l'application FastAPI
application = FastAPI(
    title="HOPI - Système de gestion hospitalière API",
    description="API pour la gestion des opérations hospitalières, des patients, des médecins et des rendez-vous",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configuration du middleware CORS
origines_autorisees = ["*"]  # En production, remplacez par l'URL de votre application frontend
application.add_middleware(
    CORSMiddleware,
    allow_origins=origines_autorisees,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monter le répertoire des fichiers statiques
application.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Inclure les routeurs
application.include_router(authentification_router, prefix="/api/authentification", tags=["authentification"])
application.include_router(patients_router, prefix="/api/patients", tags=["patients"])
application.include_router(medecins_router, prefix="/api/medecins", tags=["medecins"])
application.include_router(hopitaux_router, prefix="/api/hopitaux", tags=["hopitaux"])

# Point de terminaison racine
@application.get("/api/", tags=["racine"])
async def racine():
    """Point de terminaison racine qui fournit des informations sur l'API."""
    return {
        "message": "Bienvenue sur l'API HOPI de gestion hospitalière",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "documentation_redoc": "/api/redoc"
    }

# Point de terminaison de vérification d'état
@application.get("/api/sante", tags=["sante"])
async def verifier_sante():
    """Point de terminaison de vérification d'état."""
    return {"statut": "en_ligne"}

# Gestionnaires d'exceptions personnalisés
@application.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

def demarrer_planificateur():
    """Démarre le planificateur de notifications dans un thread séparé."""
    scheduler = NotificationScheduler()
    scheduler.run()

def demarrer_application():
    """Démarre l'application FastAPI avec le planificateur de notifications."""
    # Démarrer le planificateur dans un thread séparé
    thread_planificateur = threading.Thread(target=demarrer_planificateur, daemon=True)
    thread_planificateur.start()
    logger.info("Planificateur de notifications démarré")
    
    # Démarrer le serveur FastAPI
    config = uvicorn.Config(
        "hopi.main:application",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        workers=1
    )
    serveur = uvicorn.Server(config)
    serveur.run()

if __name__ == "__main__":
    demarrer_application()
