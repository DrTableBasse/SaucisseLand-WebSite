from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Base URL (IP, nom de domaine ou localhost)
    # Exemples: http://192.168.1.100:8000, http://example.com, http://localhost:8000
    BASE_URL: str
    
    # Discord OAuth
    DISCORD_CLIENT_ID: str
    DISCORD_CLIENT_SECRET: str
    DISCORD_REDIRECT_URI: str = ""  # Sera construit à partir de BASE_URL si vide
    DISCORD_GUILD_ID: str
    DISCORD_BOT_TOKEN: str
    
    @field_validator('DISCORD_CLIENT_ID')
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DISCORD_CLIENT_ID ne peut pas être vide. Veuillez le définir dans le fichier .env")
        if not v.isdigit():
            raise ValueError("DISCORD_CLIENT_ID doit être un nombre (snowflake Discord)")
        return v
    
    @field_validator('DISCORD_CLIENT_SECRET')
    @classmethod
    def validate_client_secret(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DISCORD_CLIENT_SECRET ne peut pas être vide. Veuillez le définir dans le fichier .env")
        return v
    
    @field_validator('DISCORD_BOT_TOKEN')
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DISCORD_BOT_TOKEN ne peut pas être vide. Veuillez le définir dans le fichier .env")
        return v
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or v.strip() == "" or v == "change-me-generate-a-secret-key-here":
            raise ValueError("SECRET_KEY ne peut pas être vide ou utiliser la valeur par défaut. Veuillez générer une clé secrète et la définir dans le fichier .env")
        return v
    
    @field_validator('BASE_URL')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("BASE_URL ne peut pas être vide. Veuillez le définir dans le fichier .env (ex: http://localhost:8000 ou http://192.168.1.100:8000)")
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("BASE_URL doit commencer par http:// ou https://")
        return v.rstrip('/')
    
    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DATABASE_URL ne peut pas être vide. Veuillez le définir dans le fichier .env")
        return v
    
    @field_validator('DISCORD_GUILD_ID')
    @classmethod
    def validate_guild_id(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DISCORD_GUILD_ID ne peut pas être vide. Veuillez le définir dans le fichier .env")
        return v
    
    # Allowed roles for article creation (comma-separated string from env)
    ALLOWED_ROLE_IDS_STR: str = ""
    
    # Session
    SECRET_KEY: str
    SESSION_COOKIE_NAME: str = "session"
    
    # CORS
    CORS_ORIGINS_STR: str = ""  # Sera construit à partir de BASE_URL si vide
    
    # Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    @property
    def DISCORD_REDIRECT_URI_FINAL(self) -> str:
        """Retourne l'URL de redirection Discord (construite ou configurée)"""
        if self.DISCORD_REDIRECT_URI:
            return self.DISCORD_REDIRECT_URI
        # Construire à partir de BASE_URL
        base = self.BASE_URL.rstrip('/')
        return f"{base}/api/auth/callback/social/discord"
    
    @property
    def ALLOWED_ROLE_IDS(self) -> List[str]:
        """Parse ALLOWED_ROLE_IDS from comma-separated string"""
        if not self.ALLOWED_ROLE_IDS_STR:
            return []
        return [role_id.strip() for role_id in self.ALLOWED_ROLE_IDS_STR.split(",") if role_id.strip()]
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string"""
        if self.CORS_ORIGINS_STR:
            return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",") if origin.strip()]
        # Par défaut, utiliser BASE_URL
        return [self.BASE_URL.rstrip('/')]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

