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
