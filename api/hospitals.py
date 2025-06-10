from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union
import os
from pathlib import Path
import shutil

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/hopitaux",
    tags=["hopitaux"],
    responses={404: {"description": "Non trouvé"}},
)

# Configuration
UPLOAD_DIR = Path("uploads/hospitals")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Fonction d'aide pour récupérer un hôpital par son ID
def lire_hopital(db: Session, id_hopital: int):
    """Récupère un hôpital spécifique par son ID."""
    hopital = db.query(models.Hopital).filter(models.Hopital.id == id_hopital).first()
    if hopital is None:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    return hopital

# Points de terminaison des hôpitaux
@router.get("/", response_model=List[schemas.Hopital])
def lister_hopitaux(
    debut: int = 0,
    limite: int = 100,
    recherche: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Récupère tous les hôpitaux avec un filtre de recherche optionnel."""
    requete = db.query(models.Hopital)
    
    if recherche:
        filtre_recherche = f"%{recherche}%"
        requete = requete.filter(
            (models.Hopital.nom.ilike(filtre_recherche)) |
            (models.Hopital.ville.ilike(filtre_recherche)) |
            (models.Hopital.pays.ilike(filtre_recherche))
        )
    
    return requete.offset(debut).limit(limite).all()

@router.post("/", response_model=schemas.Hopital, status_code=status.HTTP_201_CREATED)
def creer_hopital(
    hopital: schemas.HopitalCreate,
    db: Session = Depends(get_db),
    utilisateur_courant: models.Utilisateur = Depends(auth.require_admin)
):
    """Crée un nouvel hôpital (Administrateur uniquement)."""
    # Vérifier si un hôpital avec ce code existe déjà
    db_hopital = db.query(models.Hopital).filter(models.Hopital.code == hopital.code).first()
    
    if db_hopital:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hôpital avec ce code existe déjà"
        )
    
    # Créer l'hôpital
    db_hopital = models.Hopital(**hopital.dict())
    
    db.add(db_hopital)
    db.commit()
    db.refresh(db_hopital)
    
    return db_hopital

@router.get("/{id_hopital}", response_model=schemas.Hopital)
def lire_hopital(
    id_hopital: int,
    db: Session = Depends(get_db)
):
    """Récupère un hôpital spécifique par son ID."""
    return lire_hopital(db, id_hopital)

@router.put("/{id_hopital}", response_model=schemas.Hopital)
def mettre_a_jour_hopital(
    id_hopital: int,
    hopital_mise_a_jour: schemas.HopitalUpdate,
    db: Session = Depends(get_db),
    utilisateur_courant: models.Utilisateur = Depends(auth.require_admin)
):
    """Met à jour un hôpital (Administrateur uniquement)."""
    db_hopital = lire_hopital(db, id_hopital)
    
    # Vérifier si le nouveau code est déjà pris
    if hopital_mise_a_jour.code and hopital_mise_a_jour.code != db_hopital.code:
        hopital_existant = db.query(models.Hopital).filter(models.Hopital.code == hopital_mise_a_jour.code).first()
        
        if hopital_existant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hôpital avec ce code existe déjà"
            )
    
    # Mettre à jour les champs de l'hôpital
    donnees_mise_a_jour = hopital_mise_a_jour.dict(exclude_unset=True)
    for champ, valeur in donnees_mise_a_jour.items():
        setattr(db_hopital, champ, valeur)
    
    db.commit()
    db.refresh(db_hopital)
    
    return db_hopital

@router.delete("/{id_hopital}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_hopital(
    id_hopital: int,
    db: Session = Depends(get_db),
    utilisateur_courant: models.Utilisateur = Depends(auth.require_admin)
):
    """Supprime un hôpital (Administrateur uniquement)."""
    hopital = lire_hopital(db, id_hopital)
    
    # Vérifier si il y a des dossiers médicaux associés
    a_des_dossiers = db.query(models.DossierMedical).filter(models.DossierMedical.hopital_id == id_hopital).first() is not None
    
    a_des_diagnostiques = db.query(models.Diagnostic).filter(models.Diagnostic.hopital_id == id_hopital).first() is not None
    
    a_des_rendez_vous = db.query(models.RendezVous).filter(models.RendezVous.hopital_id == id_hopital).first() is not None
    
    if a_des_dossiers or a_des_diagnostiques or a_des_rendez_vous:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer l'hôpital avec des dossiers médicaux associés"
        )
    
    db.delete(hopital)
    db.commit()
    return None

@router.get("/{id_hopital}/medecins", response_model=List[schemas.Medecin])
def obtenir_medecins_hopital(
    id_hopital: int,
    specialite: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Récupère les médecins associés à un hôpital."""
    # Vérifier si l'hôpital existe
    lire_hopital(db, id_hopital)
    
    requete = db.query(models.Medecin).join(models.RendezVous, models.Medecin.id == models.RendezVous.medecin_id).filter(models.RendezVous.hopital_id == id_hopital)
    
    if specialite:
        requete = requete.filter(models.Medecin.specialite.ilike(f"%{specialite}%"))
    
    return requete.distinct().all()

@router.get("/{id_hopital}/rendez-vous", response_model=List[schemas.RendezVous])
def obtenir_rendez_vous_hopital(
    id_hopital: int,
    date: Optional[date] = None,
    statut: Optional[schemas.StatutRendezVous] = None,
    medecin_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Récupère les rendez-vous pour un hôpital avec des filtres optionnels."""
    # Vérifier si l'hôpital existe
    lire_hopital(db, id_hopital)
    
    requete = db.query(models.RendezVous).filter(models.RendezVous.hopital_id == id_hopital)
    
    if date:
        requete = requete.filter(models.RendezVous.date == date)
    
    if statut:
        requete = requete.filter(models.RendezVous.statut == statut)
    
    if medecin_id:
        requete = requete.filter(models.RendezVous.medecin_id == medecin_id)
    
    if patient_id:
        requete = requete.filter(models.RendezVous.patient_id == patient_id)
    
    return requete.order_by(
        models.RendezVous.date.asc(),
        models.RendezVous.heure.asc()
    ).all()

@router.get("/{id_hopital}/statistiques")
def obtenir_statistiques_hopital(
    id_hopital: int,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Récupère les statistiques pour un hôpital."""
    # Vérifier si l'hôpital existe
    hopital = lire_hopital(db, id_hopital)
    
    # Requête de base pour les rendez-vous
    requete = db.query(models.RendezVous).filter(models.RendezVous.hopital_id == id_hopital)
    
    # Appliquer les filtres de date
    if date_debut:
        requete = requete.filter(models.RendezVous.date >= date_debut)
    if date_fin:
        requete = requete.filter(models.RendezVous.date <= date_fin)
    
    # Récupérer tous les rendez-vous
    rendez_vous = requete.all()
    
    # Calculer les statistiques
    total_rendez_vous = len(rendez_vous)
    
    rendez_vous_par_statut = {}
    for statut in schemas.StatutRendezVous:
        count = sum(1 for rdv in rendez_vous if rdv.statut == statut)
        rendez_vous_par_statut[statut] = {
            "count": count,
            "pourcentage": (count / total_rendez_vous * 100) if total_rendez_vous > 0 else 0
        }
    
    # Compter les patients et médecins uniques
    patients_uniques = len({rdv.patient_id for rdv in rendez_vous})
    medecins_uniques = len({rdv.medecin_id for rdv in rendez_vous})
    
    # Récupérer les services (simplifié)
    services = db.query(models.Hopital.service).filter(models.Hopital.id == id_hopital).distinct().all()
    
    return {
        "id_hopital": id_hopital,
        "nom_hopital": hopital.nom,
        "total_rendez_vous": total_rendez_vous,
        "patients_uniques": patients_uniques,
        "medecins_uniques": medecins_uniques,
        "rendez_vous_par_statut": rendez_vous_par_statut,
        "services": [s[0] for s in services if s[0]],
        "periode": {
            "date_debut": date_debut.isoformat() if date_debut else None,
            "date_fin": date_fin.isoformat() if date_fin else None
        }
    }

@router.post("/{id_hopital}/upload-logo")
async def upload_logo_hopital(
    id_hopital: int,
    fichier: UploadFile = File(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Medecin = Depends(auth.require_admin)
):
    """Upload a logo for a hospital (admin only)."""
    hospital = get_hospital(db, hospital_id)
    
    # Generate a unique filename
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"hospital_{hospital_id}_logo{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    # Save the file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update hospital's logo path in the database
    # Note: You'll need to add a logo_path field to the Hopital model
    # hospital.logo_path = str(file_path)
    # db.commit()
    
    return {"filename": filename, "path": str(file_path)}
