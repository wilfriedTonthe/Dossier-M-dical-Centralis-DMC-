import time
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .notifications import notification_service
from .database import Base, get_db

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self, db_url: str = None):
        """Initialise le planificateur de notifications."""
        self.db_url = db_url or settings.DATABASE_URL
        self.running = False
        self.check_interval = settings.NOTIFICATION_CHECK_INTERVAL
        
    def check_notifications(self):
        """Vérifie et envoie les notifications nécessaires."""
        logger.info(f"Vérification des notifications à {datetime.now()}")
        
        # Créer une nouvelle session pour cette vérification
        engine = create_engine(self.db_url)
        db = Session(engine)
        
        try:
            notification_service.check_upcoming_appointments(db)
            db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Erreur de base de données lors de la vérification des notifications: {e}")
            db.rollback()
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la vérification des notifications: {e}")
            db.rollback()
        finally:
            db.close()
    
    def run(self):
        """Démarre le planificateur de notifications."""
        self.running = True
        logger.info(f"Démarrage du planificateur de notifications (vérification toutes les {self.check_interval} secondes)")
        
        try:
            while self.running:
                start_time = time.time()
                self.check_notifications()
                
                # Attendre jusqu'à la prochaine vérification
                elapsed = time.time() - start_time
                sleep_time = max(0, self.check_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            logger.info("Arrêt du planificateur de notifications")
            self.running = False
        except Exception as e:
            logger.error(f"Erreur critique dans le planificateur de notifications: {e}")
            self.running = False

# Pour exécuter le planificateur directement
if __name__ == "__main__":
    scheduler = NotificationScheduler()
    scheduler.run()
