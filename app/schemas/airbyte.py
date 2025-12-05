"""Schémas Pydantic pour Airbyte"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AirbyteConnectionBase(BaseModel):
    """Base pour AirbyteConnection"""
    workspace_id: str
    source_id: str
    destination_id: str
    connection_id: str
    schema_name: str
    status: str = "active"


class AirbyteConnectionCreate(AirbyteConnectionBase):
    """Création d'une connexion Airbyte"""
    user_id: int


class AirbyteConnectionResponse(AirbyteConnectionBase):
    """Réponse API pour AirbyteConnection"""
    id: int
    user_id: int
    created_at: datetime
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    
    class Config:
        from_attributes = True


class SyncTriggerResponse(BaseModel):
    """Réponse après déclenchement d'un sync"""
    status: str
    job_id: str
    message: str


class SyncStatusResponse(BaseModel):
    """Statut d'une synchronisation"""
    job_id: str
    status: str  # pending, running, succeeded, failed, cancelled
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_synced: Optional[int] = None
    bytes_synced: Optional[int] = None
