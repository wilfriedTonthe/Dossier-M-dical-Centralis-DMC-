from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime, time
from typing import List, Optional, Union
from enum import Enum

# Énumérations
class TypeSexe(str, Enum):
    M = "M"
    F = "F"
    AUTRE = "Autre"

class TypePieceIdentite(str, Enum):
    CIN = "CIN"
    PASSPORT = "Passeport"
    PERMIS = "Permis de conduire"
    AUTRE = "Autre"

class StatutRendezVous(str, Enum):
    PLANIFIE = "planifie"
    CONFIRME = "confirme"
    ANNULE = "annule"
    TERMINE = "termine"

# Schémas de base
class UtilisateurBase(BaseModel):
    email: EmailStr
    nom: str = Field(..., max_length=255)
    prenom: str = Field(..., max_length=255)
    telephone: Optional[str] = Field(None, max_length=50)

class UtilisateurCreation(UtilisateurBase):
    mot_de_passe: str = Field(..., min_length=8, max_length=100)

class ConnexionUtilisateur(BaseModel):
    email: EmailStr
    mot_de_passe: str

class MiseAJourUtilisateur(BaseModel):
    email: Optional[EmailStr] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    mot_de_passe: Optional[str] = None

# Schémas des patients
class PatientBase(UtilisateurBase):
    sexe: Optional[TypeSexe] = None
    date_naissance: Optional[date] = None
    code_carte: Optional[str] = Field(None, max_length=50)
    adresse: Optional[str] = Field(None, max_length=255)
    nationalite: Optional[str] = Field(None, max_length=100)
    situation_familiale: Optional[str] = Field(None, max_length=50)
    profession: Optional[str] = Field(None, max_length=100)
    groupe_sanguin: Optional[str] = Field(None, max_length=5)
    nom_prenom_contact_urgence: Optional[str] = Field(None, max_length=255)
    tel_contact_urgence: Optional[str] = Field(None, max_length=50)
    adresse_contact_urgence: Optional[str] = Field(None, max_length=255)
    compagnie_assurance: Optional[str] = Field(None, max_length=100)
    numero_assurance: Optional[str] = Field(None, max_length=100)
    expiration_assurance: Optional[date] = None
    type_piece_identite: Optional[TypePieceIdentite] = None
    numero_piece_identite: Optional[str] = Field(None, max_length=100)
    expiration_piece_identite: Optional[date] = None

class PatientCreation(PatientBase, UtilisateurCreation):
    pass

class MiseAJourPatient(MiseAJourUtilisateur):
    sexe: Optional[TypeSexe] = None
    date_naissance: Optional[date] = None
    code_carte: Optional[str] = None
    adresse: Optional[str] = None
    nationalite: Optional[str] = None
    situation_familiale: Optional[str] = None
    profession: Optional[str] = None
    groupe_sanguin: Optional[str] = None
    nom_prenom_contact_urgence: Optional[str] = None
    tel_contact_urgence: Optional[str] = None
    adresse_contact_urgence: Optional[str] = None
    compagnie_assurance: Optional[str] = None
    numero_assurance: Optional[str] = None
    expiration_assurance: Optional[date] = None
    type_piece_identite: Optional[TypePieceIdentite] = None
    numero_piece_identite: Optional[str] = None
    expiration_piece_identite: Optional[date] = None

class Patient(PatientBase):
    id: int
    verifie: bool
    date_creation: datetime
    chemin_qr_code: Optional[str] = None
    chemin_photo: Optional[str] = None

    class Config:
        orm_mode = True

# Schémas des médecins
class MedecinBase(UtilisateurBase):
    specialite: Optional[str] = Field(None, max_length=255)

class MedecinCreation(MedecinBase, UtilisateurCreation):
    pass

class MiseAJourMedecin(MiseAJourUtilisateur):
    specialite: Optional[str] = None

class Medecin(MedecinBase):
    id: int
    date_creation: datetime

    class Config:
        orm_mode = True

# Schémas des hôpitaux
class HopitalBase(BaseModel):
    nom: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    adresse: Optional[str] = Field(None, max_length=255)
    service: Optional[str] = Field(None, max_length=255)
    telephone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    site_web: Optional[str] = Field(None, max_length=255)

class HopitalCreation(HopitalBase):
    pass

class MiseAJourHopital(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    adresse: Optional[str] = None
    service: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[EmailStr] = None
    site_web: Optional[str] = None

class Hopital(HopitalBase):
    id: int

    class Config:
        orm_mode = True

# Dossier Medical Schemas
class DossierMedicalBase(BaseModel):
    id_patient: int
    id_medecin: int
    id_hopital: int
    nom_hopital: Optional[str] = None
    service_hopital: Optional[str] = None
    code_hopital: Optional[str] = None
    adresse_hopital: Optional[str] = None
    observations_cliniques: Optional[str] = None
    allergies: Optional[str] = None
    traitements_en_cours: Optional[str] = None
    historique_hospitalisations: Optional[str] = None
    vaccinations: Optional[str] = None
    contacts_familiaux: Optional[str] = None
    documents_joints: Optional[str] = None
    contenu: str

class DossierMedicalCreation(DossierMedicalBase):
    pass

class MiseAJourDossierMedical(BaseModel):
    observations_cliniques: Optional[str] = None
    allergies: Optional[str] = None
    traitements_en_cours: Optional[str] = None
    historique_hospitalisations: Optional[str] = None
    vaccinations: Optional[str] = None
    contacts_familiaux: Optional[str] = None
    documents_joints: Optional[str] = None
    contenu: Optional[str] = None

class DossierMedical(DossierMedicalBase):
    id: int
    date_modification: datetime
    patient: Optional[Patient] = None
    medecin: Optional[Medecin] = None
    hopital: Optional[Hopital] = None

    class Config:
        orm_mode = True

# Diagnostic Schemas
class DiagnosticBase(BaseModel):
    id_patient: int
    id_medecin: int
    id_hopital: int
    id_dossier_medical: Optional[int] = None
    resultat: Optional[str] = None
    symptomes: Optional[str] = None
    observations_cliniques: Optional[str] = None
    allergies: Optional[str] = None
    traitements_en_cours: Optional[str] = None
    historique_hospitalisations: Optional[str] = None
    vaccinations: Optional[str] = None
    contacts_familiaux: Optional[str] = None
    documents_joints: Optional[str] = None

class DiagnosticCreation(DiagnosticBase):
    pass

class DiagnosticUpdate(BaseModel):
    resultat: Optional[str] = None
    symptomes: Optional[str] = None
    observations_cliniques: Optional[str] = None
    allergies: Optional[str] = None
    traitements_en_cours: Optional[str] = None
    historique_hospitalisations: Optional[str] = None
    vaccinations: Optional[str] = None
    contacts_familiaux: Optional[str] = None
    documents_joints: Optional[str] = None

class Diagnostic(DiagnosticBase):
    id: int
    date_diagnostic: datetime
    patient: Optional[Patient] = None
    medecin: Optional[Medecin] = None
    hopital: Optional[Hopital] = None
    dossier_medical: Optional[DossierMedical] = None

    class Config:
        orm_mode = True

# Antecedent Medical Schemas
class AntecedentMedicalBase(BaseModel):
    id_patient: int
    id_dossier_medical: Optional[int] = None
    description: str

class AntecedentMedicalCreation(AntecedentMedicalBase):
    pass

class MiseAJourAntecedentMedical(BaseModel):
    description: Optional[str] = None
    date: Optional[datetime] = None

class AntecedentMedical(AntecedentMedicalBase):
    id: int
    date: datetime
    patient: Optional[Patient] = None
    dossier_medical: Optional[DossierMedical] = None

    class Config:
        orm_mode = True

# Appointment Schemas
class RendezVousBase(BaseModel):
    id_patient: int
    id_medecin: int
    id_hopital: int
    nom_medecin: str = Field(..., max_length=255)
    date: date
    heure: time
    statut: StatutRendezVous = StatutRendezVous.PLANIFIE

class RendezVousCreation(RendezVousBase):
    pass

class MiseAJourRendezVous(BaseModel):
    date: Optional[date] = None
    heure: Optional[time] = None
    statut: Optional[StatutRendezVous] = None

class Appointment(AppointmentBase):
    id: int
    created_at: datetime
    patient: Optional[Patient] = None
    medecin: Optional[Medecin] = None
    hopital: Optional[Hopital] = None

    class Config:
        orm_mode = True

# Message Schemas
class MessageBase(BaseModel):
    id_expediteur: int
    id_destinataire: int
    contenu: str
    lu: bool = False

class MessageCreation(MessageBase):
    pass

class Message(MessageBase):
    id: int
    created_at: datetime
    expediteur: Optional[Union[Patient, Medecin]] = None
    destinataire: Optional[Union[Patient, Medecin]] = None

    class Config:
        orm_mode = True

# Historique Modification Schemas
class HistoriqueModificationBase(BaseModel):
    id_dossier: int
    id_patient: int
    id_medecin: int
    id_modificateur: int
    description: Optional[str] = None
    ancien_contenu: Optional[str] = None

class HistoriqueModificationCreation(HistoriqueModificationBase):
    pass

class HistoriqueModification(HistoriqueModificationBase):
    id: int
    date_modification: datetime
    dossier_medical: Optional[DossierMedical] = None
    patient: Optional[Patient] = None
    medecin: Optional[Medecin] = None

    class Config:
        orm_mode = True

# Token Schemas
class Jeton(BaseModel):
    jeton_acces: str
    type_jeton: str

class DonneesJeton(BaseModel):
    email: Optional[str] = None
    type_utilisateur: Optional[str] = None

# Schémas de recherche
class RequeteRecherche(BaseModel):
    requete: str

class ResultatsRecherche(BaseModel):
    patients: List[Patient] = []
    medecins: List[Medecin] = []
    hopitaux: List[Hopital] = []
    dossiers: List[DossierMedical] = []
    diagnostics: List[Diagnostic] = []
    rendez_vous: List[RendezVous] = []

# Schémas de réponse
class MessageReponse(BaseModel):
    message: str

class ReponseErreur(BaseModel):
    detail: str
