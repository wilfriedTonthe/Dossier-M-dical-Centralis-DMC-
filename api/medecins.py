import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from datetime import date, datetime, timedelta
import os
from pathlib import Path

from .. import models, schemas, auth
from ..database import get_db
from ..notifications import notification_service

routeur = APIRouter(
    prefix="/medecins",
    tags=["medecins"],
    dependencies=[Depends(auth.exiger_medecin)],
    responses={404: {"description": "Non trouvé"}},
)

# Points de terminaison des médecins
@routeur.get("/", response_model=List[schemas.Medecin])
def lister_medecins(
    debut: int = 0,
    limite: int = 100,
    specialite: Optional[str] = None,
    bd: Session = Depends(get_db),
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin)
):
    """Récupère tous les médecins avec un filtrage optionnel par spécialité."""
    requete = bd.query(models.Medecin)
    
    if specialite:
        requete = requete.filter(models.Medecin.specialite.ilike(f"%{specialite}%"))
    
    return requete.offset(debut).limit(limite).all()

@routeur.get("/moi", response_model=schemas.Medecin)
def lire_mon_profil(
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin)
):
    """Récupère le profil du médecin connecté."""
    return utilisateur_courant

@routeur.get("/{id_medecin}", response_model=schemas.Medecin)
def lire_medecin(
    id_medecin: int,
    bd: Session = Depends(get_db),
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin)
):
    """Récupère un médecin spécifique par son ID."""
    medecin = bd.query(models.Medecin).filter(models.Medecin.id == id_medecin).first()
    if medecin is None:
        raise HTTPException(status_code=404, detail="Médecin non trouvé")
    return medecin

@routeur.put("/moi", response_model=schemas.Medecin)
def mettre_a_jour_mon_profil(
    maj_medecin: schemas.MiseAJourMedecin,
    bd: Session = Depends(get_db),
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin)
):
    """Met à jour le profil du médecin connecté."""
    donnees_maj = maj_medecin.dict(exclude_unset=True)
    
    # Retirer le mot de passe des données de mise à jour s'il est présent
    donnees_maj.pop("mot_de_passe", None)
    
    for champ, valeur in donnees_maj.items():
        setattr(utilisateur_courant, champ, valeur)
    
    bd.commit()
    bd.refresh(utilisateur_courant)
    
    return utilisateur_courant

@routeur.get("/moi/patients", response_model=List[schemas.Patient])
def obtenir_mes_patients(
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin),
    debut: int = 0,
    limite: int = 100,
    recherche: Optional[str] = None,
    bd: Session = Depends(get_db)
):
    """Récupère les patients associés au médecin connecté."""
    # Récupère les patients distincts qui ont des rendez-vous avec ce médecin
    requete = bd.query(models.Patient)\
        .join(models.RendezVous, models.Patient.id == models.RendezVous.id_patient)\
        .filter(models.RendezVous.id_medecin == utilisateur_courant.id)
    
    if recherche:
        filtre_recherche = f"%{recherche}%"
        requete = requete.filter(
            (models.Patient.nom.ilike(filtre_recherche)) | 
            (models.Patient.prenom.ilike(filtre_recherche)) |
            (models.Patient.email.ilike(filtre_recherche))
        )
    
    return requete.distinct().offset(debut).limit(limite).all()

@routeur.get("/moi/rendez-vous", response_model=List[schemas.RendezVous])
def obtenir_mes_rendez_vous(
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin),
    statut: Optional[schemas.StatutRendezVous] = None,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    id_patient: Optional[int] = None,
    bd: Session = Depends(get_db)
):
    """Récupère les rendez-vous du médecin connecté avec des filtres optionnels."""
    requete = bd.query(models.RendezVous)\
        .filter(models.RendezVous.id_medecin == utilisateur_courant.id)
    
    if statut:
        requete = requete.filter(models.RendezVous.statut == statut)
    if date_debut:
        requete = requete.filter(models.RendezVous.date >= date_debut)
    if date_fin:
        requete = requete.filter(models.RendezVous.date <= date_fin)
    if id_patient:
        requete = requete.filter(models.RendezVous.id_patient == id_patient)
    
    return requete.order_by(
        models.RendezVous.date.asc(),
        models.RendezVous.heure.asc()
    ).all()

@routeur.post("/moi/rendez-vous", response_model=schemas.RendezVous, status_code=status.HTTP_201_CREATED)
@routeur.post("/moi/rendez-vous/", response_model=schemas.RendezVous, include_in_schema=False)
def creer_rendez_vous(
    rendez_vous: schemas.RendezVousCreation,
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin),
    bd: Session = Depends(get_db)
):
    """Crée un nouveau rendez-vous."""
    # Vérifier si le patient existe
    patient = bd.query(models.Patient)\
        .filter(models.Patient.id == rendez_vous.id_patient)\
        .first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    # Vérifier si l'hôpital existe
    hopital = bd.query(models.Hopital)\
        .filter(models.Hopital.id == rendez_vous.id_hopital)\
        .first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    # Vérifier les conflits d'horaire
    rendez_vous_existant = bd.query(models.RendezVous)\
        .filter(
            models.RendezVous.id_medecin == utilisateur_courant.id,
            models.RendezVous.date == rendez_vous.date,
            models.RendezVous.heure == rendez_vous.heure,
            models.RendezVous.statut != schemas.StatutRendezVous.ANNULE
        )\
        .first()
    
    if rendez_vous_existant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Créneau horaire déjà réservé"
        )
    
    # Créer le rendez-vous
    nouveau_rendez_vous = models.RendezVous(
        **rendez_vous.dict(),
        id_medecin=utilisateur_courant.id,
        nom_medecin=f"Dr. {utilisateur_courant.prenom} {utilisateur_courant.nom}",
        statut=schemas.StatutRendezVous.PLANIFIE
    )
    
    bd.add(nouveau_rendez_vous)
    bd.commit()
    bd.refresh(nouveau_rendez_vous)
    
    # Envoyer une notification au patient en arrière-plan
    try:
        # Récupérer le patient pour avoir son email et son nom complet
        patient = bd.query(models.Patient).filter(models.Patient.id == nouveau_rendez_vous.id_patient).first()
        if patient and patient.email:
            # Formater la date et l'heure
            date_rdv = nouveau_rendez_vous.date.strftime("%d/%m/%Y")
            heure_rdv = nouveau_rendez_vous.heure.strftime("%H:%M")
            
            # Envoyer la notification de création de rendez-vous
            notification_service.send_appointment_notification(
                notification_type="creation",
                to_email=patient.email,
                doctor_name=f"Dr. {utilisateur_courant.prenom} {utilisateur_courant.nom}",
                date=date_rdv,
                time=heure_rdv,
                patient_name=f"{patient.prenom} {patient.nom}"
            )
    except Exception as e:
        # Ne pas échouer la création du rendez-vous si l'envoi de la notification échoue
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de l'envoi de la notification de création de rendez-vous: {str(e)}")
    
    return nouveau_rendez_vous

@routeur.put("/moi/rendez-vous/{id_rendez_vous}", response_model=schemas.RendezVous)
def mettre_a_jour_rendez_vous(
    id_rendez_vous: int,
    maj_rendez_vous: schemas.MiseAJourRendezVous,
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin),
    bd: Session = Depends(get_db)
):
    """Met à jour un rendez-vous existant."""
    # Récupérer le rendez-vous
    rendez_vous = bd.query(models.RendezVous)\
        .filter(
            models.RendezVous.id == id_rendez_vous,
            models.RendezVous.id_medecin == utilisateur_courant.id
        )\
        .first()
    
    if not rendez_vous:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    # Vérifier les conflits d'horaire si la date ou l'heure est mise à jour
    if maj_rendez_vous.date or maj_rendez_vous.heure:
        nouvelle_date = maj_rendez_vous.date if maj_rendez_vous.date else rendez_vous.date
        nouvelle_heure = maj_rendez_vous.heure if maj_rendez_vous.heure else rendez_vous.heure
        
        conflit = bd.query(models.RendezVous)\
            .filter(
                models.RendezVous.id_medecin == utilisateur_courant.id,
                models.RendezVous.id != id_rendez_vous,
                models.RendezVous.date == nouvelle_date,
                models.RendezVous.heure == nouvelle_heure,
                models.RendezVous.statut != schemas.StatutRendezVous.ANNULE
            )\
            .first()
        
        if conflit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Créneau horaire déjà réservé"
            )
    
    # Mettre à jour le rendez-vous
    for champ, valeur in maj_rendez_vous.dict(exclude_unset=True).items():
        setattr(rendez_vous, champ, valeur)
    
    bd.commit()
    bd.refresh(rendez_vous)
    
    # Envoyer une notification de mise à jour au patient
    try:
        # Récupérer le patient pour avoir son email et son nom complet
        patient = bd.query(models.Patient).filter(models.Patient.id == rendez_vous.id_patient).first()
        if patient and patient.email:
            # Formater la date et l'heure
            date_rdv = rendez_vous.date.strftime("%d/%m/%Y")
            heure_rdv = rendez_vous.heure.strftime("%H:%M")
            
            # Envoyer la notification de mise à jour de rendez-vous
            notification_service.send_appointment_notification(
                notification_type="modification",
                to_email=patient.email,
                doctor_name=rendez_vous.nom_medecin,
                date=date_rdv,
                time=heure_rdv,
                patient_name=f"{patient.prenom} {patient.nom}",
                motif=rendez_vous.motif or "Non spécifié"
            )
    except Exception as e:
        # Ne pas échouer la mise à jour du rendez-vous si l'envoi de la notification échoue
        logger.error(f"Erreur lors de l'envoi de la notification de mise à jour de rendez-vous: {str(e)}")
    
    return rendez_vous

@routeur.post("/moi/diagnostics", response_model=schemas.Diagnostic)
@routeur.post("/moi/diagnostics/", response_model=schemas.Diagnostic, include_in_schema=False)
def creer_diagnostic(
    diagnostic: schemas.DiagnosticCreation,
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin),
    bd: Session = Depends(get_db)
):
    """Crée un nouveau diagnostic pour un patient."""
    # Vérifier si le patient existe
    patient = bd.query(models.Patient)\
        .filter(models.Patient.id == diagnostic.id_patient)\
        .first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    
    # Vérifier si l'hôpital existe
    hopital = bd.query(models.Hopital)\
        .filter(models.Hopital.id == diagnostic.id_hopital)\
        .first()
    if not hopital:
        raise HTTPException(status_code=404, detail="Hôpital non trouvé")
    
    # Créer le diagnostic
    nouveau_diagnostic = models.Diagnostic(
        **diagnostic.dict(),
        id_medecin=utilisateur_courant.id,
        date_diagnostic=datetime.utcnow()
    )
    
    bd.add(nouveau_diagnostic)
    bd.commit()
    bd.refresh(nouveau_diagnostic)
    
    return nouveau_diagnostic

@routeur.get("/moi/disponibilite")
@routeur.get("/moi/disponibilite/", include_in_schema=False)
def verifier_disponibilite(
    date_rdv: date,
    utilisateur_courant: models.Medecin = Depends(auth.exiger_medecin),
    bd: Session = Depends(get_db)
):
    """Vérifie les créneaux horaires disponibles pour le médecin à une date donnée."""
    # Heures de travail du médecin (à configurer dans le profil du médecin)
    HEURE_DEBUT = 9  # 9h00
    HEURE_FIN = 18    # 18h00
    DUREE_RDV = 30    # 30 minutes par rendez-vous
    
    # Récupérer les rendez-vous existants pour cette date
    rendez_vous = bd.query(models.RendezVous)\
        .filter(
            models.RendezVous.id_medecin == utilisateur_courant.id,
            models.RendezVous.date == date_rdv,
            models.RendezVous.statut != schemas.StatutRendezVous.ANNULE
        )\
        .all()
    
    # Créer une liste des créneaux occupés
    creneaux_occupes = set()
    for rdv in rendez_vous:
        heure_rdv = rdv.heure
        creneaux_occupes.add(heure_rdv.hour * 60 + heure_rdv.minute)  # Convertir en minutes
    
    # Générer les créneaux disponibles
    creneaux_disponibles = []
    for minutes in range(HEURE_DEBUT * 60, HEURE_FIN * 60, DUREE_RDV):
        if minutes not in creneaux_occupes:
            heure = datetime.combine(date_rdv, datetime.min.time()) + timedelta(minutes=minutes)
            creneaux_disponibles.append(heure)
    
    return creneaux_disponibles
    
