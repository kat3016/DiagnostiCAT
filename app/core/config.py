"""
Configuración de la aplicación
"""

from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Básico
    APP_NAME: str = "DiagnostiCAT"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]

    # Base de datos (por defecto SQLite para facilidad de arranque)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./diagnosticat.db")

    # OpenAI / LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # CrewAI (opcional)
    CREW_ENABLE: bool = os.getenv("CREW_ENABLE", "True").lower() == "true"

    # Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


