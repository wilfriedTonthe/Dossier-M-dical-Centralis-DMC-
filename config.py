"""
Configuration de l'application Hopi Medical
Ce module charge les variables d'environnement et fournit des paramètres de configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Set, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

# Charger les variables d'environnement depuis le fichier .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

class DatabaseConfig(BaseModel):
    """Configuration de la base de données"""
    engine: str = Field(default=os.getenv('DB_ENGINE', 'mysql+mysqlconnector'))
    user: str = Field(default=os.getenv('DB_USER', 'root'))
    password: str = Field(default=os.getenv('DB_PASSWORD', ''))
    host: str = Field(default=os.getenv('DB_HOST', 'localhost'))
    port: str = Field(default=os.getenv('DB_PORT', '3306'))
    name: str = Field(default=os.getenv('DB_NAME', 'hopi_medical'))
    charset: str = Field(default=os.getenv('DB_CHARSET', 'utf8mb4'))
    
    @property
    def url(self) -> str:
        """Construit l'URL de connexion à la base de données"""
        return f"{self.engine}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}?charset={self.charset}"

class JWTConfig(BaseModel):
    """Configuration JWT pour l'authentification"""
    secret_key: str = Field(default=os.getenv('JWT_SECRET_KEY', 'clé-jwt-secrète-par-défaut'))
    algorithm: str = Field(default=os.getenv('JWT_ALGORITHM', 'HS256'))
    access_token_expire_minutes: int = Field(
        default=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '10080'))
    )

class EmailConfig(BaseModel):
    """Configuration des emails"""
    smtp_server: str = Field(default=os.getenv('SMTP_SERVER', 'smtp.gmail.com'))
    smtp_port: int = Field(default=int(os.getenv('SMTP_PORT', '587')))
    smtp_use_tls: bool = Field(default=os.getenv('SMTP_USE_TLS', 'True') == 'True')
    smtp_username: str = Field(default=os.getenv('SMTP_USERNAME', ''))
    smtp_password: str = Field(default=os.getenv('SMTP_PASSWORD', ''))
    email_from: str = Field(default=os.getenv('EMAIL_FROM', 'noreply@example.com'))
    email_from_name: str = Field(default=os.getenv('EMAIL_FROM_NAME', 'Hopi Medical'))

class OpenAIConfig(BaseModel):
    """Configuration pour OpenAI"""
    api_key: str = Field(default=os.getenv('OPENAI_API_KEY', ''))
    model: str = Field(default=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'))
    temperature: float = Field(default=float(os.getenv('OPENAI_TEMPERATURE', '0.7')))
    max_tokens: int = Field(default=int(os.getenv('OPENAI_MAX_TOKENS', '1000')))

class Settings(BaseSettings):
    """Configuration principale de l'application"""
    # Paramètres de base
    debug: bool = Field(default=os.getenv('DEBUG', 'False') == 'True')
    environment: str = Field(default=os.getenv('ENVIRONMENT', 'development'))
    
    # Configuration des dossiers
    base_dir: Path = Path(__file__).resolve().parent
    upload_folder: Path = base_dir / os.getenv('UPLOAD_DIR', 'uploads')
    qr_code_folder: Path = base_dir / 'qrcodes'
    
    # Sous-configurations
    database: DatabaseConfig = DatabaseConfig()
    jwt: JWTConfig = JWTConfig()
    email: EmailConfig = EmailConfig()
    openai: OpenAIConfig = OpenAIConfig()
    
    # Configuration CORS
    cors_origins: List[str] = Field(
        default=os.getenv('CORS_ORIGINS', '*').split(',')
    )
    cors_allow_credentials: bool = Field(
        default=os.getenv('CORS_ALLOW_CREDENTIALS', 'True') == 'True'
    )
    cors_allow_methods: List[str] = Field(
        default=os.getenv('CORS_ALLOW_METHODS', 'GET,POST,PUT,DELETE,OPTIONS').split(',')
    )
    cors_allow_headers: str = Field(
        default=os.getenv('CORS_ALLOW_HEADERS', '*')
    )
    
    # Configuration de l'application
    app_name: str = Field(default=os.getenv('APP_NAME', 'Hopi Medical'))
    app_description: str = Field(
        default=os.getenv('APP_DESCRIPTION', 'Application de gestion médicale')
    )
    app_version: str = Field(default=os.getenv('APP_VERSION', '1.0.0'))
    contact_email: str = Field(
        default=os.getenv('CONTACT_EMAIL', 'contact@example.com')
    )
    support_email: str = Field(
        default=os.getenv('SUPPORT_EMAIL', 'support@example.com')
    )
    
    # Paramètres divers
    notification_check_interval: int = Field(
        default=int(os.getenv('NOTIFICATION_CHECK_INTERVAL', '300'))
    )
    
    class Config:
        env_file = env_path
        case_sensitive = True

# Créer et exporter l'instance de configuration
settings = Settings()

# Créer les dossiers nécessaires
os.makedirs(settings.upload_folder, exist_ok=True)
os.makedirs(settings.qr_code_folder, exist_ok=True)
