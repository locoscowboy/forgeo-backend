"""
Schemas Pydantic pour la synchronisation Airbyte
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class SyncStatus(str, Enum):
    """Statut d'un job de synchronisation"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncJobResponse(BaseModel):
    """Réponse après déclenchement d'une synchronisation"""
    job_id: str
    connection_id: str
    status: SyncStatus
    created_at: datetime
    message: str = "Synchronization triggered successfully"


class SyncJobStatus(BaseModel):
    """Statut détaillé d'un job de synchronisation"""
    job_id: str
    connection_id: str
    status: SyncStatus
    rows_synced: int = 0
    bytes_synced: int = 0
    duration: Optional[str] = None  # Format: "PT5M30S" (5min 30sec)
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SyncJobHistoryItem(BaseModel):
    """Élément de l'historique de synchronisation"""
    job_id: str
    status: SyncStatus
    rows_synced: int = 0
    duration: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SyncHistoryResponse(BaseModel):
    """Historique complet des synchronisations"""
    connection_id: str
    total_jobs: int
    jobs: List[SyncJobHistoryItem]
    last_successful_sync: Optional[datetime] = None


class SyncTriggerRequest(BaseModel):
    """Paramètres optionnels pour déclencher une sync"""
    full_refresh: bool = False  # Si True, réinitialise toutes les données


class ConnectionInfo(BaseModel):
    """Informations sur la connexion Airbyte"""
    connection_id: str
    source_id: str
    destination_id: str
    status: str
    name: str
