import os
import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, PostgresDsn, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    # durée de validité du token en minutes (60 * 24 * 8 = 8 jours)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # BACKEND_CORS_ORIGINS est une chaîne JSON de répertoires
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "Forgeo API"

    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "forgeo")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "forgeo")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "forgeo")
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v

        # Construction manuelle de l'URL PostgreSQL
        user = info.data.get("POSTGRES_USER", "")
        password = info.data.get("POSTGRES_PASSWORD", "")
        host = info.data.get("POSTGRES_SERVER", "")
        db = info.data.get("POSTGRES_DB", "")

        # Syntaxe compatible Pydantic v2
        return f"postgresql://{user}:{password}@{host}/{db}"

    # ✅ AJOUT : Propriété pour récupérer DATABASE_URL
    @property
    def DATABASE_URL(self) -> str:
        """Retourne l'URL de la base de données"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    # HubSpot settings
    HUBSPOT_CLIENT_ID: Optional[str] = os.getenv("HUBSPOT_CLIENT_ID")
    HUBSPOT_CLIENT_SECRET: Optional[str] = os.getenv("HUBSPOT_CLIENT_SECRET")
    HUBSPOT_REDIRECT_URI: Optional[str] = os.getenv("HUBSPOT_REDIRECT_URI")

    # HubSpot Auto-Sync Settings
    HUBSPOT_AUTO_SYNC_ENABLED: bool = os.getenv("HUBSPOT_AUTO_SYNC_ENABLED", "true").lower() == "true"
    HUBSPOT_SYNC_INTERVAL_HOURS: int = int(os.getenv("HUBSPOT_SYNC_INTERVAL_HOURS", "6"))
    HUBSPOT_SYNC_STARTUP_DELAY_MINUTES: int = int(os.getenv("HUBSPOT_SYNC_STARTUP_DELAY_MINUTES", "2"))

    # Google OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

settings = Settings()
