from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Boolean, Time, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class TypeSexe(str, enum.Enum):
    M = "M"
    F = "F"
    AUTRE = "Autre"

class TypePieceIdentite(str, enum.Enum):
    CIN = "CIN"
    PASSPORT = "Passeport"
    PERMIS = "Permis de conduire"
    AUTRE = "Autre"

class Patient(Base):
    __tablename__ = 'patient'
    
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(255), nullable=False)
    prenom = Column(String(255), nullable=False)
    sexe = Column(Enum(TypeSexe), nullable=True)
    date_naissance = Column(Date, nullable=True)
    email = Column(String(191), unique=True, nullable=False, index=True)
    mot_de_passe = Column(String(255), nullable=False)
    code_carte = Column(String(50), unique=True, nullable=True)
    adresse = Column(String(255), nullable=True)
    telephone = Column(String(50), nullable=True)
    nationalite = Column(String(100), nullable=True)
    situation_familiale = Column(String(50), nullable=True)
    profession = Column(String(100), nullable=True)
    groupe_sanguin = Column(String(5), nullable=True)
    nom_prenom_contact_urgence = Column(String(255), nullable=True)
    tel_contact_urgence = Column(String(50), nullable=True)
    adresse_contact_urgence = Column(String(255), nullable=True)
    compagnie_assurance = Column(String(100), nullable=True)
    numero_assurance = Column(String(100), nullable=True)
    expiration_assurance = Column(Date, nullable=True)
    type_piece_identite = Column(Enum(TypePieceIdentite), nullable=True)
    numero_piece_identite = Column(String(100), nullable=True)
    expiration_piece_identite = Column(Date, nullable=True)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())
    chemin_qr_code = Column(String(255), nullable=True)
    verifie = Column(Boolean, default=False)
    chemin_photo = Column(String(255), nullable=True)
    
    # Relations
    dossiers_medicaux = relationship("DossierMedical", back_populates="patient")
    diagnostics = relationship("Diagnostic", back_populates="patient")
    antecedents = relationship("AntecedentMedical", back_populates="patient")
    rendez_vous = relationship("RendezVous", back_populates="patient")
    modifications = relationship("HistoriqueModification", back_populates="patient")
    rendez_vous = relationship("RendezVous", back_populates="patient")
    messages_envoyes = relationship("Message", 
                                  foreign_keys="[Message.id_expediteur]",
                                  back_populates="expediteur")
    messages_recus = relationship("Message",
                                foreign_keys="[Message.id_destinataire]",
                                back_populates="destinataire")
    modifications = relationship("HistoriqueModification", back_populates="patient")

class Hopital(Base):
    __tablename__ = 'hopital'
    
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    adresse = Column(String(255), nullable=True)
    service = Column(String(255), nullable=True)
    telephone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    site_web = Column(String(255), nullable=True)
    
    # Relations
    dossiers_medicaux = relationship("DossierMedical", back_populates="hopital")
    diagnostics = relationship("Diagnostic", back_populates="hopital")
    rendez_vous = relationship("RendezVous", back_populates="hopital")

class Medecin(Base):
    __tablename__ = 'medecin'
    
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(255), nullable=False)
    prenom = Column(String(255), nullable=False)
    email = Column(String(191), unique=True, nullable=False, index=True)
    mot_de_passe = Column(String(255), nullable=False)
    specialite = Column(String(255), nullable=True)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    dossiers_medicaux = relationship("DossierMedical", back_populates="medecin")
    diagnostics = relationship("Diagnostic", back_populates="medecin")
    rendez_vous = relationship("RendezVous", back_populates="medecin")
    messages_envoyes = relationship("Message", 
                                  foreign_keys="[Message.id_expediteur]",
                                  back_populates="expediteur")
    messages_recus = relationship("Message",
                                foreign_keys="[Message.id_destinataire]",
                                back_populates="destinataire")
    modifications = relationship("HistoriqueModification", back_populates="medecin")

class DossierMedical(Base):
    __tablename__ = 'dossier_medical'
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patient.id'), nullable=False)
    medecin_id = Column(Integer, ForeignKey('medecin.id'), nullable=False)
    hopital_id = Column(Integer, ForeignKey('hopital.id'), nullable=False)
    nom_hopital = Column(String(255), nullable=True)
    service_hopital = Column(String(255), nullable=True)
    code_hopital = Column(String(50), nullable=True)
    adresse_hopital = Column(String(255), nullable=True)
    observations_cliniques = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    traitements_en_cours = Column(Text, nullable=True)
    historique_hospitalisations = Column(Text, nullable=True)
    vaccinations = Column(Text, nullable=True)
    contacts_familiaux = Column(Text, nullable=True)
    documents_joints = Column(Text, nullable=True)
    contenu = Column(Text, nullable=False)
    date_modification = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    patient = relationship("Patient", back_populates="dossiers_medicaux")
    medecin = relationship("Medecin", back_populates="dossiers_medicaux")
    hopital = relationship("Hopital", back_populates="dossiers_medicaux")
    diagnostics = relationship("Diagnostic", back_populates="dossier_medical")
    antecedents = relationship("AntecedentMedical", back_populates="dossier_medical")
    modifications = relationship("HistoriqueModification", back_populates="dossier_medical")

class Diagnostic(Base):
    __tablename__ = 'diagnostic'
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patient.id'), nullable=False)
    medecin_id = Column(Integer, ForeignKey('medecin.id'), nullable=False)
    hopital_id = Column(Integer, ForeignKey('hopital.id'), nullable=False)
    dossier_medical_id = Column(Integer, ForeignKey('dossier_medical.id'), nullable=True)
    nom_hopital = Column(String(255), nullable=True)
    service_hopital = Column(String(255), nullable=True)
    code_hopital = Column(String(50), nullable=True)
    adresse_hopital = Column(String(255), nullable=True)
    resultat = Column(String(255), nullable=True)
    symptomes = Column(Text, nullable=True)
    observations_cliniques = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    traitements_en_cours = Column(Text, nullable=True)
    historique_hospitalisations = Column(Text, nullable=True)
    vaccinations = Column(Text, nullable=True)
    contacts_familiaux = Column(Text, nullable=True)
    documents_joints = Column(Text, nullable=True)
    date_diagnostic = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    patient = relationship("Patient", back_populates="diagnostics")
    medecin = relationship("Medecin", back_populates="diagnostics")
    hopital = relationship("Hopital", back_populates="diagnostics")
    dossier_medical = relationship("DossierMedical", back_populates="diagnostics")

class AntecedentMedical(Base):
    __tablename__ = 'antecedent_medical'
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patient.id'), nullable=False)
    dossier_medical_id = Column(Integer, ForeignKey('dossier_medical.id'), nullable=True)
    description = Column(Text, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    patient = relationship("Patient", back_populates="antecedents")
    dossier_medical = relationship("DossierMedical", back_populates="antecedents")

class StatutRendezVous(str, enum.Enum):
    PLANIFIE = "planifie"
    CONFIRME = "confirme"
    ANNULE = "annule"
    TERMINE = "termine"

class RendezVous(Base):
    __tablename__ = 'rendez_vous'
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patient.id'), nullable=False)
    medecin_id = Column(Integer, ForeignKey('medecin.id'), nullable=False)
    hopital_id = Column(Integer, ForeignKey('hopital.id'), nullable=False)
    nom_medecin = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    heure = Column(Time, nullable=False)
    statut = Column(Enum(StatutRendezVous), default=StatutRendezVous.PLANIFIE)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())
    notification_24h_envoyee = Column(Boolean, default=False)
    notification_1h_envoyee = Column(Boolean, default=False)
    motif = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relations
    patient = relationship("Patient", back_populates="rendez_vous")
    medecin = relationship("Medecin", back_populates="rendez_vous")
    hopital = relationship("Hopital", back_populates="rendez_vous")

class Message(Base):
    __tablename__ = 'message'
    
    id = Column(Integer, primary_key=True, index=True)
    id_expediteur = Column(Integer, nullable=False)
    id_destinataire = Column(Integer, nullable=False)
    contenu = Column(Text, nullable=False)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())
    lu = Column(Boolean, default=False)
    
    # Relations
    expediteur = relationship("Utilisateur", foreign_keys=[id_expediteur], back_populates="messages_envoyes")
    destinataire = relationship("Utilisateur", foreign_keys=[id_destinataire], back_populates="messages_recus")

class HistoriqueModification(Base):
    __tablename__ = 'historique_modification'
    
    id = Column(Integer, primary_key=True, index=True)
    dossier_id = Column(Integer, ForeignKey('dossier_medical.id'), nullable=False)
    patient_id = Column(Integer, ForeignKey('patient.id'), nullable=False)
    medecin_id = Column(Integer, ForeignKey('medecin.id'), nullable=False)
    modifie_par_id = Column(Integer, nullable=False)
    date_modification = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(String(255), nullable=True)
    ancien_contenu = Column(Text, nullable=True)
    
    # Relations
    dossier_medical = relationship("DossierMedical", back_populates="modifications")
    patient = relationship("Patient", back_populates="modifications")
    medecin = relationship("Medecin", back_populates="modifications")
