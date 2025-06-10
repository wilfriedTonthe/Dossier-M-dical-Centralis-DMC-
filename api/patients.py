from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Union
import os
from pathlib import Path
from datetime import date, datetime
import uuid
import qrcode
from io import BytesIO
from fastapi.responses import FileResponse, JSONResponse
import logging

from .. import models, schemas, auth
from ..database import get_db
from ..services.carte_assurance import CarteAssuranceGenerator

# Configuration du logger
logger = logging.getLogger(__name__)

routeur = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(auth.exiger_patient)],
    responses={404: {"description": "Non trouvé"}},
)

# Configuration des dossiers
DOSSIER_UPLOAD = Path("uploads/patients")
DOSSIER_UPLOAD.mkdir(parents=True, exist_ok=True)
DOSSIER_QR_CODE = Path("uploads/codes_qr")
DOSSIER_QR_CODE.mkdir(parents=True, exist_ok=True)

# Fonctions utilitaires
generer_code_qr = lambda id_patient, nom_patient: (
    lambda qr=qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4): 
    (qr.add_data(f"ID Patient: {id_patient}\nNom: {nom_patient}"), 
     qr.make(fit=True), 
     qr.make_image(fill_color="black", back_color="white").save(
         chemin_fichier := str(DOSSIER_QR_CODE / f"patient_{id_patient}.png")
     ), 
     chemin_fichier)[-1]
)()

# Points de terminaison des patients
@routeur.get("/", response_model=List[schemas.Patient])
def lister_patients(
    debut: int = 0,
    limite: int = 100,
    bd: Session = Depends(get_db),
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin)
):
    """Récupère tous les patients (uniquement pour les médecins)."""
    return bd.query(models.Patient).offset(debut).limit(limite).all()

@routeur.get("/moi", response_model=schemas.Patient)
def lire_mon_profil(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient)
):
    """Récupère le profil du patient connecté."""
    return utilisateur_courant

@routeur.get("/{id_patient}", response_model=schemas.Patient)
def lire_patient(
    id_patient: int,
    bd: Session = Depends(get_db),
    utilisateur_courant: Union[models.Patient, models.Medecin] = Depends(auth.obtenir_utilisateur_courant_actif)
):
    """Récupère un patient spécifique par son ID.
    
    Les patients ne peuvent voir que leur propre profil.
    Les médecins peuvent voir le profil de n'importe quel patient.
    """
    # Si l'utilisateur est un patient, il ne peut voir que son propre profil
    if isinstance(utilisateur_courant, models.Patient) and utilisateur_courant.id != id_patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non autorisé à voir le profil de ce patient"
        )
    
    patient = bd.query(models.Patient).filter(models.Patient.id == id_patient).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    return patient

@routeur.put("/moi", response_model=schemas.Patient)
def mettre_a_jour_mon_profil(
    maj_patient: schemas.MiseAJourPatient,
    bd: Session = Depends(get_db),
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient)
):
    """Met à jour le profil du patient connecté."""
    donnees_maj = maj_patient.dict(exclude_unset=True)
    
    # Retirer le mot de passe des données de mise à jour s'il est présent
    donnees_maj.pop("mot_de_passe", None)
    
    for champ, valeur in donnees_maj.items():
        setattr(utilisateur_courant, champ, valeur)
    
    bd.commit()
    bd.refresh(utilisateur_courant)
    
    return utilisateur_courant

@routeur.post("/moi/photo")
async def televerser_photo_profil(
    fichier: UploadFile = File(..., description="Fichier image à téléverser"),
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    bd: Session = Depends(get_db)
):
    """Téléverse une photo de profil pour le patient connecté.
    
    Args:
        fichier: Fichier image à téléverser (requis)
        utilisateur_courant: Patient connecté (injecté automatiquement)
        bd: Session de base de données (injectée automatiquement)
        
    Returns:
        dict: Message de confirmation avec le chemin du fichier
        
    Raises:
        HTTPException: Si le fichier n'est pas fourni ou s'il y a une erreur lors du traitement
    """
    # Le paramètre fichier est déjà correctement typé avec File(...) de FastAPI
    # FastAPI gère automatiquement la validation du fichier requis
    
    # Générer un nom de fichier unique
    extension = os.path.splitext(fichier.filename)[1]
    nom_fichier = f"{utilisateur_courant.id}_{uuid.uuid4()}{extension}"
    chemin_fichier = DOSSIER_UPLOAD / nom_fichier
    
    # Sauvegarder le fichier
    with open(chemin_fichier, "wb") as tampon:
        contenu = await fichier.read()
        tampon.write(contenu)
    
    # Mettre à jour le chemin de la photo dans la base de données
    utilisateur_courant.chemin_photo = str(chemin_fichier)
    bd.commit()
    
    return {"nom_fichier": nom_fichier, "chemin": str(chemin_fichier)}

@routeur.get("/moi/photo")
def obtenir_photo_profil(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient)
):
    """Récupère la photo de profil du patient connecté."""
    if not utilisateur_courant.chemin_photo or not os.path.exists(utilisateur_courant.chemin_photo):
        raise HTTPException(status_code=404, detail="Photo non trouvée")
    
    return FileResponse(utilisateur_courant.chemin_photo)

@routeur.get("/moi/qr-code", response_class=FileResponse)
async def obtenir_code_qr(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    bd: Session = Depends(get_db)
):
    """Récupère le code QR du patient connecté."""
    try:
        # Vérifier si le code QR existe déjà
        if not utilisateur_courant.chemin_qr_code or not os.path.exists(utilisateur_courant.chemin_qr_code):
            # Générer un nouveau code QR s'il n'existe pas
            qr_path = generer_code_qr(utilisateur_courant.id, f"{utilisateur_courant.prenom} {utilisateur_courant.nom}")
            
            # Mettre à jour le chemin du code QR dans la base de données
            utilisateur_courant.chemin_qr_code = qr_path
            bd.commit()
            bd.refresh(utilisateur_courant)
        
        return FileResponse(
            utilisateur_courant.chemin_qr_code,
            media_type="image/png",
            filename=f"qr_code_patient_{utilisateur_courant.id}.png"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la génération du code QR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération du code QR"
        )

@routeur.get("/moi/carte-assurance", response_class=FileResponse)
async def generer_carte_assurance(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    bd: Session = Depends(get_db)
):
    """
    Génère et retourne la carte d'assurance du patient au format PDF.
    
    La carte contient les informations personnelles du patient, sa photo,
    son code QR et ses informations d'assurance.
    """
    try:
        # Vérifier si le code QR existe, sinon le générer
        if not utilisateur_courant.chemin_qr_code or not os.path.exists(utilisateur_courant.chemin_qr_code):
            qr_path = generer_code_qr(utilisateur_courant.id, f"{utilisateur_courant.prenom} {utilisateur_courant.nom}")
            utilisateur_courant.chemin_qr_code = qr_path
            bd.commit()
            bd.refresh(utilisateur_courant)
        
        # Préparer les données pour la carte d'assurance
        patient_data = {
            'id': str(utilisateur_courant.id),
            'nom': utilisateur_courant.nom,
            'prenom': utilisateur_courant.prenom,
            'date_naissance': utilisateur_courant.date_naissance.strftime('%d/%m/%Y') if utilisateur_courant.date_naissance else 'Non renseignée',
            'numero_assurance': utilisateur_courant.numero_assurance or 'Non renseigné',
            'expiration_assurance': utilisateur_courant.expiration_assurance.strftime('%d/%m/%Y') if utilisateur_courant.expiration_assurance else 'Non renseignée',
            'photo_path': utilisateur_courant.chemin_photo if utilisateur_courant.chemin_photo and os.path.exists(utilisateur_courant.chemin_photo) else None,
            'qr_code_data': f"ID: {utilisateur_courant.id}\nNom: {utilisateur_courant.nom} {utilisateur_courant.prenom}\nDate de naissance: {utilisateur_courant.date_naissance}"
        }
        
        # Générer la carte d'assurance
        generator = CarteAssuranceGenerator()
        pdf_path = generator.generer_carte_assurance(patient_data)
        
        # Retourner le fichier PDF généré
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"carte_assurance_{utilisateur_courant.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la carte d'assurance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération de la carte d'assurance: {str(e)}"
        )

@routeur.get("/moi/historique-medical", response_model=List[schemas.DossierMedical])
def obtenir_historique_medical(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    bd: Session = Depends(get_db)
):
    """Récupère l'historique médical du patient connecté."""
    return bd.query(models.DossierMedical)\
        .filter(models.DossierMedical.id_patient == utilisateur_courant.id)\
        .order_by(models.DossierMedical.date_modification.desc())\
        .all()

@routeur.get("/moi/rendez-vous", response_model=List[schemas.RendezVous])
def obtenir_rendez_vous(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    statut: Optional[schemas.StatutRendezVous] = None,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    bd: Session = Depends(get_db)
):
    """Récupère les rendez-vous du patient connecté avec des filtres optionnels."""
    requete = bd.query(models.RendezVous)\
        .filter(models.RendezVous.id_patient == utilisateur_courant.id)
    
    if statut:
        requete = requete.filter(models.RendezVous.statut == statut)
    if date_debut:
        requete = requete.filter(models.RendezVous.date >= date_debut)
    if date_fin:
        requete = requete.filter(models.RendezVous.date <= date_fin)
    
    return requete.order_by(
        models.RendezVous.date.asc(),
        models.RendezVous.heure.asc()
    ).all()

@routeur.get("/moi/diagnostics", response_model=List[schemas.Diagnostic])
def obtenir_diagnostics(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    debut: int = 0,
    limite: int = 100,
    bd: Session = Depends(get_db)
):
    """Récupère les diagnostics du patient connecté."""
    return bd.query(models.Diagnostic)\
        .filter(models.Diagnostic.id_patient == utilisateur_courant.id)\
        .order_by(models.Diagnostic.date_diagnostic.desc())\
        .offset(debut)\
        .limit(limite)\
        .all()

@routeur.get("/moi/antecedents", response_model=List[schemas.AntecedentMedical])
def obtenir_antecedents(
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    debut: int = 0,
    limite: int = 100,
    bd: Session = Depends(get_db)
):
    """Récupère les antécédents médicaux du patient connecté."""
    return bd.query(models.AntecedentMedical)\
        .filter(models.AntecedentMedical.id_patient == utilisateur_courant.id)\
        .order_by(models.AntecedentMedical.date.desc())\
        .offset(debut)\
        .limit(limite)\
        .all()

@routeur.post("/moi/antecedents", response_model=schemas.AntecedentMedical, status_code=status.HTTP_201_CREATED)
def creer_antecedent(
    antecedent: schemas.AntecedentMedicalCreation,
    utilisateur_courant: models.Patient = Depends(auth.exiger_patient),
    bd: Session = Depends(get_db)
):
    """Ajoute un antécédent médical pour le patient connecté."""
    nouvel_antecedent = models.AntecedentMedical(
        **antecedent.dict(),
        id_patient=utilisateur_courant.id
    )
    
    bd.add(nouvel_antecedent)
    bd.commit()
    bd.refresh(nouvel_antecedent)
    
    return nouvel_antecedent
