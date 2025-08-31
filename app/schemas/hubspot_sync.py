from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class HubspotSyncBase(BaseModel):
    status: str
    total_contacts: Optional[int] = None
    total_companies: Optional[int] = None
    total_deals: Optional[int] = None

class HubspotSyncCreate(HubspotSyncBase):
    pass

class HubspotSyncResponse(HubspotSyncBase):
    id: int
    user_id: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
       from_attributes = True

# === NOUVEAUX SCHÉMAS SMART SYNC ===
class SyncStatusResponse(BaseModel):
    """Réponse enrichie pour le statut de synchronisation"""
    needs_sync: bool
    reason: str
    last_sync: Optional[HubspotSyncResponse] = None
    data_freshness: str  # "fresh", "stale", "very_stale", "never"
    hours_since_sync: Optional[float] = None
    recommendation: str

class ShouldSyncResponse(BaseModel):
    """Réponse pour l'endpoint should-sync"""
    should_sync: bool
    reason: str
    last_sync_ago_hours: Optional[float] = None
    data_quality: str  # "fresh", "acceptable", "stale"
    auto_sync_recommended: bool
