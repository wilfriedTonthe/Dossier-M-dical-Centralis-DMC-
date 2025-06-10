from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from . import models, schemas
from .database import obtenir_session

# Charger les variables d'environnement
load_dotenv()

# Configuration de sécurité
CLE_SECRETE = os.getenv("CLE_SECRETE", "votre-cle-secrete-ici")
ALGORITHME = "HS256"
DUREE_EXPIRATION_JETON_MINUTES = 60 * 24 * 7  # 7 jours

# Hachage des mots de passe
contexte_mot_de_passe = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Schéma OAuth2
schema_oauth2 = OAuth2PasswordBearer(tokenUrl="token")

def verifier_mot_de_passe(mot_de_passe_texte: str, mot_de_passe_hache: str) -> bool:
    """Vérifie un mot de passe contre un hachage."""
    return contexte_mot_de_passe.verify(mot_de_passe_texte, mot_de_passe_hache)

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Génère un hachage de mot de passe."""
    return contexte_mot_de_passe.hash(mot_de_passe)

def creer_jeton_acces(donnees: Dict[str, Any], duree_expiration: Optional[timedelta] = None) -> str:
    """Crée un jeton d'accès JWT."""
    a_encoder = donnees.copy()
    if duree_expiration:
        expiration = datetime.utcnow() + duree_expiration
    else:
        expiration = datetime.utcnow() + timedelta(minutes=15)
    a_encoder.update({"exp": expiration})
    jeton_encode = jwt.encode(a_encoder, CLE_SECRETE, algorithm=ALGORITHME)
    return jeton_encode

async def obtenir_utilisateur_courant(
    jeton: str = Depends(schema_oauth2),
    session: Session = Depends(obtenir_session)
) -> Union[models.Patient, models.Medecin]:
    """Obtient l'utilisateur actuel à partir du jeton JWT."""
    exception_authentification = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        charge_utile = jwt.decode(jeton, CLE_SECRETE, algorithms=[ALGORITHME])
        email: str = charge_utile.get("sub")
        type_utilisateur: str = charge_utile.get("type_utilisateur")
        
        if email is None or type_utilisateur is None:
            raise exception_authentification
            
        donnees_jeton = schemas.DonneesJeton(email=email, type_utilisateur=type_utilisateur)
    except JWTError:
        raise exception_authentification
    
    # Obtenir l'utilisateur de la table appropriée en fonction du type d'utilisateur
    if type_utilisateur == "patient":
        utilisateur = session.query(models.Patient).filter(models.Patient.email == donnees_jeton.email).first()
    elif type_utilisateur == "medecin":
        utilisateur = session.query(models.Medecin).filter(models.Medecin.email == donnees_jeton.email).first()
    else:
        raise exception_authentification
    
    if utilisateur is None:
        raise exception_authentification
    return utilisateur

async def obtenir_utilisateur_actif(
    utilisateur_courant: Union[models.Patient, models.Medecin] = Depends(obtenir_utilisateur_courant)
) -> Union[models.Patient, models.Medecin]:
    """Obtient l'utilisateur actif."""
    # Ajouter des vérifications supplémentaires ici (par exemple, si l'utilisateur est actif)
    return utilisateur_courant

def authentifier_utilisateur(
    email: str, mot_de_passe: str, type_utilisateur: str, session: Session
) -> Union[models.Patient, models.Medecin, bool]:
    """Authentifie un utilisateur avec un email et un mot de passe."""
    if type_utilisateur == "patient":
        utilisateur = session.query(models.Patient).filter(models.Patient.email == email).first()
    elif type_utilisateur == "medecin":
        utilisateur = session.query(models.Medecin).filter(models.Medecin.email == email).first()
    else:
        return False
    
    if not utilisateur:
        return False
    if not verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe):
        return False
    
    return utilisateur

def create_user_token(user: Union[models.Patient, models.Medecin]) -> schemas.Token:
    """Crée un jeton d'accès pour un utilisateur."""
    user_type = "patient" if isinstance(user, models.Patient) else "medecin"
    access_token_expires = timedelta(minutes=15)
    access_token = creer_jeton_acces(
        data={"sub": user.email, "type_utilisateur": user_type},
        duree_expiration=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")

def get_user_type(user: Union[models.Patient, models.Medecin]) -> str:
    """Get the type of user (patient or medecin)."""
    return "patient" if isinstance(user, models.Patient) else "medecin"

def check_user_permissions(
    current_user: Union[models.Patient, models.Medecin], 
    required_roles: list[str] = None
) -> bool:
    """Check if the current user has the required permissions."""
    if required_roles is None:
        required_roles = ["patient", "medecin"]
    
    user_type = get_user_type(current_user)
    return user_type in required_roles

# Role-based dependencies
def require_patient(current_user: models.Patient = Depends(get_current_active_user)):
    """Dependency to require the current user to be a patient."""
    if not isinstance(current_user, models.Patient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient access required"
        )
    return current_user

def require_medecin(current_user: models.Medecin = Depends(get_current_active_user)):
    """Dependency to require the current user to be a medecin."""
    if not isinstance(current_user, models.Medecin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Medecin access required"
        )
    return current_user

def require_admin(current_user: models.Medecin = Depends(get_current_active_user)):
    """Dependency to require the current user to be an admin."""
    # Add admin check logic here if needed
    if not isinstance(current_user, models.Medecin):  # or not current_user.is_admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
