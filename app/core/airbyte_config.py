"""Configuration Airbyte"""
from pydantic_settings import BaseSettings
from typing import Optional


# Constantes des connecteurs Airbyte (IDs fixes)
HUBSPOT_SOURCE_DEFINITION_ID = "36c891d9-4bd9-43ac-bad2-10e12756272c"
POSTGRES_DESTINATION_DEFINITION_ID = "25c5221d-dce2-4163-ade9-739ef790f503"


class AirbyteSettings(BaseSettings):
    """Configuration pour l'API Airbyte"""

    # URL de l'API Airbyte
    AIRBYTE_API_URL: str = "http://airbyte-abctl-control-plane:80/api/public/v1"

    # Authentification Airbyte (Basic Auth)
    AIRBYTE_EMAIL: str = "quentin.tristan.pro@gmail.com"
    AIRBYTE_PASSWORD: str = "bAKm8KseDVGNMOXNdXmjnReI2nwklz4w"

    # Workspace ID Airbyte
    AIRBYTE_WORKSPACE_ID: str = "042b8617-bfeb-482a-bfdc-0740075895ab"

    # HubSpot OAuth (votre app Forgeo)
    HUBSPOT_CLIENT_ID: str = "d8382c73-5106-4efd-b586-f8903ec48551"
    HUBSPOT_CLIENT_SECRET: Optional[str] = None  # Sera récupéré du .env

    # PostgreSQL (pour les destinations Airbyte)
    POSTGRES_HOST: str = "forgeo_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "forgeo"
    POSTGRES_USER: str = "forgeo"
    POSTGRES_PASSWORD: Optional[str] = None  # Sera récupéré du .env

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Instance globale
airbyte_settings = AirbyteSettings()
