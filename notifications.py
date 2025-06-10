import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .config import settings
from . import models, schemas

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM_EMAIL

    def _send_email(self, to_email: str, subject: str, content: str) -> bool:
        """Envoyer un email de notification"""
        try:
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.smtp_from
            msg["To"] = to_email
            msg.attach(MIMEText(content, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:  # Pour le port 587, on utilise starttls
                    server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                logger.info(f"✅ Email envoyé avec succès à {to_email}")
                return True
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi de l'email à {to_email}: {str(e)}")
            return False

    def send_appointment_notification(
        self, 
        notification_type: str, 
        to_email: str, 
        doctor_name: str, 
        date: str, 
        time: str,
        patient_name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Envoyer une notification de rendez-vous
        
        Args:
            notification_type: Type de notification (creation, reminder_24h, reminder_1h, cancellation, modification)
            to_email: Email du destinataire
            doctor_name: Nom du médecin
            date: Date du rendez-vous (format: YYYY-MM-DD)
            time: Heure du rendez-vous (format: HH:MM)
            patient_name: Nom du patient (optionnel)
            reason: Raison de l'annulation/modification (optionnel)
        """
        templates = {
            "creation": {
                "subject": "Confirmation de votre rendez-vous",
                "content": f"""Bonjour {patient_name or ''},

Votre rendez-vous avec le Dr. {doctor_name} a été confirmé pour le {date} à {time}.

Merci de votre confiance.

Cordialement,
Votre équipe médicale"""
            },
            "reminder_24h": {
                "subject": "Rappel de rendez-vous - Demain",
                "content": f"""Bonjour {patient_name or ''},

Nous vous rappelons votre rendez-vous avec le Dr. {doctor_name} demain à {time}.

À bientôt !

Cordialement,
Votre équipe médicale"""
            },
            "reminder_1h": {
                "subject": "Rappel de rendez-vous - Bientôt",
                "content": f"""Bonjour {patient_name or ''},

Votre rendez-vous avec le Dr. {doctor_name} est dans 1 heure ({time}).

À très bientôt !

Cordialement,
Votre équipe médicale"""
            },
            "cancellation": {
                "subject": "Annulation de votre rendez-vous",
                "content": f"""Bonjour {patient_name or ''},

Votre rendez-vous avec le Dr. {doctor_name} prévu pour le {date} à {time} a été annulé.

Raison : {reason or 'Non spécifiée'}

Veuillez nous contacter pour le reprogrammer.

Cordialement,
Votre équipe médicale"""
            },
            "modification": {
                "subject": "Modification de votre rendez-vous",
                "content": f"""Bonjour {patient_name or ''},

Votre rendez-vous avec le Dr. {doctor_name} a été modifié.

Nouvelle date : {date} à {time}

Raison : {reason or 'Non spécifiée'}

Cordialement,
Votre équipe médicale"""
            }
        }


        if notification_type not in templates:
            logger.error(f"Type de notification inconnu: {notification_type}")
            return False

        template = templates[notification_type]
        return self._send_email(to_email, template["subject"], template["content"])

    def check_upcoming_appointments(self, db: Session) -> None:
        """
        Vérifie les rendez-vous à venir et envoie les notifications appropriées.
        
        Cette méthode doit être appelée périodiquement (par exemple, toutes les 5 minutes)
        par un planificateur de tâches comme Celery Beat ou APScheduler.
        """
        now = datetime.now()
        logger.info(f"Vérification des notifications de rendez-vous à {now}")
        
        try:
            # Récupérer les rendez-vous confirmés dans les prochaines 25 heures
            date_debut = now
            date_fin = now + timedelta(hours=25)
            
            # Récupérer les rendez-vous qui nécessitent des notifications
            rendez_vous = db.query(models.RendezVous).join(
                models.Patient,
                models.RendezVous.id_patient == models.Patient.id
            ).filter(
                models.RendezVous.statut == schemas.StatutRendezVous.CONFIRME,
                models.RendezVous.date >= date_debut.date(),
                models.RendezVous.date <= date_fin.date(),
                (
                    (models.RendezVous.notification_24h_envoyee == False) |
                    (models.RendezVous.notification_1h_envoyee == False)
                )
            ).all()
            
            for rdv in rendez_vous:
                heure_rdv = datetime.combine(rdv.date, rdv.heure)
                time_diff = heure_rdv - now
                
                # Vérifier si on est à 1h du rendez-vous
                if timedelta(hours=0) < time_diff <= timedelta(hours=1) and not rdv.notification_1h_envoyee:
                    if self.send_appointment_notification(
                        notification_type="reminder_1h",
                        to_email=rdv.patient.email,
                        doctor_name=f"{rdv.medecin.prenom} {rdv.medecin.nom}",
                        date=rdv.date.strftime("%d/%m/%Y"),
                        time=rdv.heure.strftime("%H:%M"),
                        patient_name=f"{rdv.patient.prenom} {rdv.patient.nom}"
                    ):
                        rdv.notification_1h_envoyee = True
                        db.commit()
                # Vérifier si on est à 24h du rendez-vous
                elif timedelta(hours=1) < time_diff <= timedelta(hours=24) and not rdv.notification_24h_envoyee:
                    if self.send_appointment_notification(
                        notification_type="reminder_24h",
                        to_email=rdv.patient.email,
                        doctor_name=f"{rdv.medecin.prenom} {rdv.medecin.nom}",
                        date=rdv.date.strftime("%d/%m/%Y"),
                        time=rdv.heure.strftime("%H:%M"),
                        patient_name=f"{rdv.patient.prenom} {rdv.patient.nom}"
                    ):
                        rdv.notification_24h_envoyee = True
                        db.commit()
                        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des rendez-vous: {str(e)}")
            db.rollback()
            raise

# Instance unique du service de notification
notification_service = NotificationService()
