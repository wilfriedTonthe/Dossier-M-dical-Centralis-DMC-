from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
import os
import logging
from dotenv import load_dotenv
from config import Config
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Medecin, RendezVous, Patient, StatutRendezVous
from sqlalchemy import or_

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialiser la configuration
config = Config()

class ChatBot:
    def __init__(self, patient_manager):
        """Initialiser le chatbot"""
        self.patient_manager = patient_manager
        # Configuration du modèle OpenAI
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1000,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.output_parser = StrOutputParser()
        
        # Initialize chat state
        self.chat_state = {}
        self.chat_history: List[AIMessage | HumanMessage | SystemMessage] = [
            SystemMessage(content="Tu es un assistant médical de la clinique. Réponds toujours en français."),
            AIMessage(content="Bonjour ! Je suis votre assistant virtuel. Je peux vous aider à :\n"
                     "1. Prendre un rendez-vous\n"
                     "2. Consulter vos rendez-vous\n"
                     "3. Répondre à vos questions\n\n"
                     "Comment puis-je vous aider aujourd'hui ?")
        ]

        
    def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """Récupérer l'état de la conversation pour un utilisateur"""
        return self.chat_state.get(user_id, [])

    def update_user_state(self, user_id: str, state: Dict[str, Any]):
        """Mettre à jour l'état de la conversation pour un utilisateur"""
        self.chat_state[user_id] = state

    def clear_user_state(self, user_id: str):
        """Effacer l'état de la conversation pour un utilisateur"""
        if user_id in self.chat_state:
            del self.chat_state[user_id]

    def _handle_appointment_cancel(self, user_id: str) -> str:
        """Gérer l'annulation d'un rendez-vous"""
        self.clear_user_state(user_id)
        return "La création du rendez-vous a été annulée 🚫. Pour en créer un autre, dites 'Je veux un rendez-vous'."

    def _handle_new_appointment(self, user_id: str) -> str:
        """Gérer une nouvelle demande de rendez-vous"""
        # Récupérer la liste des médecins depuis la base de données
        from database import SessionLocale
        from models import Medecin
        
        session = SessionLocale()
        try:
            medecins = session.query(Medecin).all()
            doctors = [f"{medecin.prenom} {medecin.nom} ({medecin.specialite or 'Spécialité non spécifiée'})" for medecin in medecins]
            
            if not doctors:
                return "Désolé, aucun médecin n'est actuellement disponible. Veuillez réessayer plus tard."
                
            self.update_user_state(user_id, {
                "progress": "doctor",
                "data": {}
            })
            doctors_list = "\n".join([f"- {doc}" for doc in doctors])
            return "Voici les médecins disponibles :\n" + doctors_list
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des médecins: {str(e)}")
            return "Une erreur est survenue lors de la récupération des médecins. Veuillez réessayer plus tard."
        finally:
            session.close()

    def _handle_doctor_selection(self, user_id: str, message: str, data: Dict[str, Any]) -> str:
        """Gérer la sélection du médecin"""
        doctor = message  # À remplacer par une vraie vérification
        self.update_user_state(user_id, {
            "progress": "date",
            "data": {**data, "doctor": doctor}
        })
        return f"Pour quelle date souhaitez-vous un rendez-vous avec {doctor} ? (format: AAAA-MM-JJ)"

    def _handle_date_selection(self, user_id: str, message: str, data: Dict[str, Any]) -> str:
        """Gérer la sélection de la date"""
        try:
            datetime.strptime(message, "%Y-%m-%d")
            self.update_user_state(user_id, {
                "progress": "time",
                "data": {**data, "date": message}
            })
            return "À quelle heure ? (format: HH:MM)"
        except ValueError:
            return "Format de date invalide. Utilisez AAAA-MM-JJ."

    def _handle_time_selection(self, user_id: str, message: str, data: Dict[str, Any]) -> str:
        """Gérer la sélection de l'heure"""
        try:
            datetime.strptime(message, "%H:%M")
            self.update_user_state(user_id, {
                "progress": "confirmation",
                "data": {**data, "time": message}
            })
            return (
                "📅 Résumé :\n"
                f"👨‍⚕️ Médecin : {data['doctor']}\n"
                f"📅 Date : {data['date']}\n"
                f"⏰ Heure : {message}\n\n"
                "Confirmez-vous ce rendez-vous ? (oui/non)"
            )
        except ValueError:
            return "Format d'heure invalide. Utilisez HH:MM."

    def handle_appointment_creation(self, user_id: str, message: str) -> str:
        """Gérer le processus de création de rendez-vous"""
        state = self.get_user_state(user_id)
        progress = state.get("progress")
        data = state.get("data", {})

        # Annulation
        if message.lower() in ["annuler", "je veux annuler", "annuler le rendez-vous", "stop"]:
            return self._handle_appointment_cancel(user_id)

        # Nouvelle demande de rendez-vous
        if message.lower() in ["je veux un rendez-vous", "je veux prendre rendez-vous", "rendez-vous"]:
            return self._handle_new_appointment(user_id)

        if not progress:
            return self.get_ai_response(message)

        # Sélection du médecin
        if progress == "doctor":
            return self._handle_doctor_selection(user_id, message, data)

        # Sélection de la date
        if progress == "date":
            return self._handle_date_selection(user_id, message, data)

        # Sélection de l'heure
        if progress == "time":
            return self._handle_time_selection(user_id, message, data)

        # Confirmation
        if progress == "confirmation":
            return self._handle_confirmation(user_id, message, data)

        return "Je n'ai pas compris. Pouvez-vous reformuler ?"

    def _handle_confirmation(self, user_id: str, message: str, data: Dict[str, Any]) -> str:
        """Gérer la confirmation du rendez-vous"""
        if message.lower() in ["oui", "je confirme", "confirmer"]:
            return self._confirm_appointment(user_id, data)
        if message.lower() in ["non", "annuler"]:
            self.clear_user_state(user_id)
            return "Rendez-vous annulé. Je peux vous aider pour autre chose ?"
        return "Veuillez répondre par oui ou non."

    def _confirm_appointment(self, user_id: str, data: Dict[str, Any]) -> str:
        """Confirmer le rendez-vous dans la base de données"""
        db = SessionLocal()
        try:
            # Récupérer l'ID du patient depuis l'utilisateur connecté
            patient = db.query(Patient).filter(Patient.email == user_id).first()
            if not patient:
                return "❌ Patient non trouvé. Veuillez vous connecter."
            
            # Extraire le nom du médecin du format "Prénom Nom (Spécialité)"
            medecin_nom = data['doctor'].split(' (')[0]
            prenom_medecin, nom_medecin = medecin_nom.split(' ', 1) if ' ' in medecin_nom else (medecin_nom, '')
            
            # Trouver le médecin dans la base de données
            medecin = db.query(Medecin).filter(
                Medecin.prenom == prenom_medecin,
                Medecin.nom == nom_medecin
            ).first()
            
            if not medecin:
                return "❌ Médecin non trouvé. Veuillez réessayer."
            
            # Créer le rendez-vous
            date_rdv = datetime.strptime(f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M")
            
            # Vérifier les conflits de rendez-vous
            conflit = db.query(RendezVous).filter(
                RendezVous.medecin_id == medecin.id,
                RendezVous.date == date_rdv.date(),
                RendezVous.heure == date_rdv.time(),
                RendezVous.statut != StatutRendezVous.ANNULE
            ).first()
            
            if conflit:
                return "❌ Ce créneau n'est plus disponible. Veuillez en choisir un autre."
            
            # Créer le rendez-vous
            nouveau_rdv = RendezVous(
                patient_id=patient.id,
                medecin_id=medecin.id,
                hopital_id=1,  # À adapter selon votre logique
                nom_medecin=f"{medecin.prenom} {medecin.nom}",
                date=date_rdv.date(),
                heure=date_rdv.time(),
                statut=StatutRendezVous.PLANIFIE,
                motif=data.get('motif', 'Consultation')
            )
            
            db.add(nouveau_rdv)
            db.commit()
            
            self.clear_user_state(user_id)
            return (
                f"🎉 Rendez-vous confirmé avec {medecin.prenom} {medecin.nom} "
                f"le {date_rdv.strftime('%d/%m/%Y')} à {date_rdv.strftime('%H:%M')}.\n"
                "Vous recevrez un rappel avant votre rendez-vous."
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la création du rendez-vous: {str(e)}")
            return "❌ Une erreur est survenue lors de la création du rendez-vous. Veuillez réessayer."
        finally:
            db.close()

    def get_ai_response(self, message: str) -> str:
        """Obtenir une réponse de l'IA pour les messages généraux et les questions de santé"""
        try:
            # Vérifier d'abord si c'est une question de santé
            is_health_question = any(keyword in message.lower() for keyword in [
                "santé", "sante", "malade", "maladie", "symptôme", "symptome", 
                "mal de tête", "fièvre", "fievre", "douleur", "traitement", "médicament"
            ])
            
            # Créer le système de prompt en fonction du type de question
            if is_health_question:
                system_prompt = """
                Tu es un assistant médical professionnel. 
                Fournis des réponses claires et précises sur les questions de santé.
                Sois bienveillant et rassurant, mais toujours précis.
                
                Pour toute question médicale sérieuse ou en cas de symptômes graves,
                conseille immédiatement de consulter un professionnel de santé.
                
                Réponds en français, de manière structurée et facile à comprendre.
                """
            else:
                system_prompt = """
                Tu es l'assistant virtuel d'une clinique médicale. 
                Réponds aux questions de manière professionnelle et courtoise.
                
                Tu peux aider avec :
                - La prise de rendez-vous
                - Les informations sur la clinique
                - Les horaires d'ouverture
                - Les services proposés
                - Les questions générales sur la santé
                
                Réponds toujours en français.
                """
            
            # Préparer l'historique de la conversation
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Ajouter l'historique récent (limité à 4 derniers échanges)
            for msg in self.chat_history[-4:]:
                if isinstance(msg, HumanMessage):
                    messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    messages.append({"role": "assistant", "content": msg.content})
            
            # Ajouter le nouveau message de l'utilisateur
            messages.append({"role": "user", "content": message})
            
            # Obtenir la réponse du modèle
            response = self.llm.invoke(messages)
            
            # Extraire le contenu de la réponse
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Ajouter des avertissements pour les questions de santé
            if is_health_question:
                response_text += "\n\n⚠️ Important : Ces informations sont fournies à titre informatif uniquement " \
                              "et ne constituent pas un avis médical. En cas de problème de santé, " \
                              "veuillez consulter un professionnel de santé qualifié."
            
            return response_text
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse: {str(e)}")
            return "Désolé, je rencontre des difficultés techniques. Pouvez-vous reformuler votre demande ?"

    def get_upcoming_appointments(self, user_id: str) -> str:
        """Récupérer les rendez-vous à venir du patient"""
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.email == user_id).first()
            if not patient:
                return "❌ Patient non trouvé. Veuillez vous connecter."
                
            maintenant = datetime.now()
            rdvs = db.query(RendezVous).join(Medecin).filter(
                RendezVous.patient_id == patient.id,
                RendezVous.statut == StatutRendezVous.PLANIFIE,
                RendezVous.date >= maintenant.date()
            ).order_by(RendezVous.date, RendezVous.heure).all()
            
            if not rdvs:
                return "Vous n'avez aucun rendez-vous à venir."
                
            response = ["📅 Vos prochains rendez-vous :"]
            for rdv in rdvs:
                response.append(
                    f"- {rdv.date.strftime('%d/%m/%Y')} à {rdv.heure.strftime('%H:%M')} "
                    f"avec {rdv.nom_medecin} ({'Confirmé' if rdv.statut == StatutRendezVous.CONFIRME else 'Planifié'})"
                )
                
            return "\n".join(response)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des rendez-vous: {str(e)}")
            return "❌ Impossible de récupérer vos rendez-vous. Veuillez réessayer."
        finally:
            db.close()

    def cancel_appointment(self, user_id: str, rdv_id: int) -> str:
        """Annuler un rendez-vous"""
        db = SessionLocal()
        try:
            rdv = db.query(RendezVous).filter(
                RendezVous.id == rdv_id,
                RendezVous.patient.has(email=user_id),
                RendezVous.statut != StatutRendezVous.ANNULE
            ).first()
            
            if not rdv:
                return "❌ Rendez-vous non trouvé ou déjà annulé."
                
            rdv.statut = StatutRendezVous.ANNULE
            db.commit()
            return "✅ Le rendez-vous a bien été annulé."
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de l'annulation du rendez-vous: {str(e)}")
            return "❌ Une erreur est survenue lors de l'annulation. Veuillez réessayer."
        finally:
            db.close()

    def chat(self, user_id: str, message: str) -> str:
        """Point d'entrée principal du chatbot"""
        message_lower = message.lower()
        
        # Gestion des commandes spéciales
        if message_lower in ["mes rdv", "mes rendez-vous", "afficher mes rendez-vous"]:
            return self.get_upcoming_appointments(user_id)
            
        # Annulation de rendez-vous
        if any(cmd in message_lower for cmd in ["annuler rdv", "annuler le rdv", "annuler rendez-vous"]):
            # Ici, vous pourriez ajouter une logique pour identifier le RDV à annuler
            # Par exemple, en demandant confirmation ou en affichant la liste des RDV annulables
            return "Veuillez préciser l'ID du rendez-vous à annuler. Vous pouvez d'abord demander 'Mes rendez-vous' pour voir la liste."
        
        # Gestion des numéros de RDV pour annulation (ex: "annuler rdv 123")
        if message_lower.startswith("annuler rdv ") and message_lower[11:].strip().isdigit():
            rdv_id = int(message_lower[11:].strip())
            return self.cancel_appointment(user_id, rdv_id)
        
        # Traitement standard des messages
        if message_lower == "oui" and self.get_user_state(user_id).get("progress") is None:
            response = (
                "Comment puis-je vous aider ? Voici ce que je peux faire pour vous :\n"
                "• Prendre un rendez-vous\n"
                "• Voir mes rendez-vous\n"
                "• Poser une question sur la santé\n"
                "• Annuler un rendez-vous"
            )
        elif any(keyword in message_lower for keyword in ["rendez-vous", "rdv", "consultation"]):
            response = self.handle_appointment_creation(user_id, message)
        else:
            response = self.get_ai_response(message)
            
        # Mettre à jour l'historique du chat
        self.chat_history.append(HumanMessage(content=message))
        self.chat_history.append(AIMessage(content=response))
        return response
