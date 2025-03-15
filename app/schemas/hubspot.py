from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class HubspotTokenBase(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime
    is_active: bool = True

class HubspotTokenCreate(HubspotTokenBase):
    pass

class HubspotTokenUpdate(HubspotTokenBase):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

class HubspotTokenInDBBase(HubspotTokenBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class HubspotToken(HubspotTokenInDBBase):
    pass

class HubspotAuthResponse(BaseModel):
    auth_url: str
