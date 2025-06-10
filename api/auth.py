from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Union

from .. import models, schemas, auth
from ..database import get_db

routeur = APIRouter(prefix="/authentification", tags=["authentification"])

@routeur.post("/jeton", response_model=schemas.Jeton)
async def connexion_pour_jeton_acces(
    donnees_formulaire: OAuth2PasswordRequestForm = Depends(),
    bd: Session = Depends(get_db)
):
    """Connexion compatible OAuth2, obtient un jeton d'accès pour les requêtes futures"""
    type_utilisateur = donnees_formulaire.scopes[0] if donnees_formulaire.scopes else "patient"
    utilisateur = auth.authentifier_utilisateur(
        donnees_formulaire.username, 
        donnees_formulaire.password, 
        type_utilisateur, 
        bd
    )
    
    if not utilisateur:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return auth.creer_jeton_utilisateur(utilisateur)

@routeur.post("/inscription/patient", response_model=schemas.Patient)
def inscrire_patient(
    patient: schemas.PatientCreation,
    bd: Session = Depends(get_db)
):
    """Inscrire un nouveau patient"""
    # Vérifier si l'email existe déjà
    patient_existant = bd.query(models.Patient).filter(
        models.Patient.email == patient.email
    ).first()
    if patient_existant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà enregistré"
        )
    
    # Hacher le mot de passe
    mot_de_passe_hache = auth.hacher_mot_de_passe(patient.mot_de_passe)
    
    # Créer le patient dans la base de données
    nouveau_patient = models.Patient(
        **patient.dict(exclude={"mot_de_passe"}),
        mot_de_passe=mot_de_passe_hache
    )
    
    bd.add(nouveau_patient)
    bd.commit()
    bd.refresh(nouveau_patient)
    
    return nouveau_patient

@routeur.post("/inscription/medecin", response_model=schemas.Medecin)
def inscrire_medecin(
    medecin: schemas.MedecinCreation,
    bd: Session = Depends(get_db),
    utilisateur_courant: models.Medecin = Depends(auth.exiger_admin)
):
    """Inscrire un nouveau médecin (administrateur uniquement)"""
    # Vérifier si l'email existe déjà
    medecin_existant = bd.query(models.Medecin).filter(
        models.Medecin.email == medecin.email
    ).first()
    if medecin_existant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà enregistré"
        )
    
    # Hacher le mot de passe
    mot_de_passe_hache = auth.hacher_mot_de_passe(medecin.mot_de_passe)
    
    # Créer le médecin dans la base de données
    nouveau_medecin = models.Medecin(
        **medecin.dict(exclude={"mot_de_passe"}),
        mot_de_passe=mot_de_passe_hache
    )
    
    bd.add(nouveau_medecin)
    bd.commit()
    bd.refresh(nouveau_medecin)
    
    return nouveau_medecin

@routeur.get("/moi", response_model=Union[schemas.Patient, schemas.Medecin])
async def lire_mes_informations(
    utilisateur_courant: Union[models.Patient, models.Medecin] = Depends(auth.obtenir_utilisateur_courant_actif)
):
    """Obtenir les informations de l'utilisateur connecté"""
    return utilisateur_courant

@routeur.put("/moi/motdepasse")
async def changer_mot_de_passe(
    mots_de_passe: schemas.ChangementMotDePasse,
    utilisateur_courant: Union[models.Patient, models.Medecin] = Depends(auth.obtenir_utilisateur_courant_actif),
    bd: Session = Depends(get_db)
):
    """Changer le mot de passe de l'utilisateur"""
    # Vérifier le mot de passe actuel
    if not auth.verifier_mot_de_passe(mots_de_passe.mot_de_passe_actuel, utilisateur_courant.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )
    
    # Mettre à jour le mot de passe
    utilisateur_courant.mot_de_passe = auth.hacher_mot_de_passe(mots_de_passe.nouveau_mot_de_passe)
    bd.commit()
    
    return {"message": "Mot de passe mis à jour avec succès"}

# Schéma pour le changement de mot de passe
class ChangementMotDePasse(schemas.BaseModel):
    mot_de_passe_actuel: str
    nouveau_mot_de_passe: str = Field(..., min_length=8, max_length=100)
