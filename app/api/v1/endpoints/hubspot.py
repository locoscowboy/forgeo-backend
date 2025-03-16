from typing import Any
import requests
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user
from app.crud import hubspot as crud_hubspot
from app.models.user import User
from app.core.config import settings
from app.schemas.hubspot import HubspotTokenCreate, HubspotToken, HubspotAuthResponse

router = APIRouter()

@router.get("/auth", response_model=HubspotAuthResponse)
def hubspot_auth(
    # current_user: User = Depends(get_current_active_user),
    user_id: int = 6,  # ID administrateur pour MVP
) -> Any:
    """
    Get HubSpot authentication URL
    """
    if not settings.HUBSPOT_CLIENT_ID or not settings.HUBSPOT_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="HubSpot integration not configured"
        )
    
    auth_url = (
        f"https://app.hubspot.com/oauth/authorize"
        f"?client_id={settings.HUBSPOT_CLIENT_ID}"
        f"&redirect_uri={settings.HUBSPOT_REDIRECT_URI}"
        f"&scope=crm.objects.contacts.read%20crm.objects.contacts.write%20crm.objects.companies.read%20crm.objects.companies.write%20crm.objects.deals.read%20crm.objects.deals.write%20crm.schemas.contacts.read%20crm.schemas.companies.read%20crm.schemas.deals.read%20crm.objects.owners.read%20oauth"
    )
    
    return {"auth_url": auth_url}

@router.get("/callback")
def hubspot_callback(
    code: str,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_active_user),
    user_id: int = 6,  # ID administrateur pour MVP
) -> Any:
    """
    HubSpot OAuth callback
    """
    if not settings.HUBSPOT_CLIENT_ID or not settings.HUBSPOT_CLIENT_SECRET or not settings.HUBSPOT_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="HubSpot integration not configured"
        )
    
    # Exchange code for token
    token_url = "https://api.hubapi.com/oauth/v1/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.HUBSPOT_CLIENT_ID,
        "client_secret": settings.HUBSPOT_CLIENT_SECRET,
        "redirect_uri": settings.HUBSPOT_REDIRECT_URI,
        "code": code
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get token: {response.text}"
        )
    
    token_data = response.json()
    expires_in = token_data.get("expires_in", 21600)  # Default 6 hours
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    token_obj = HubspotTokenCreate(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=expires_at,
        is_active=True
    )
    
    crud_hubspot.create_token(db, token_obj, user_id)
    
    return RedirectResponse(url="https://app.forgeo.io/audits?connected=true")

@router.get("/token", response_model=HubspotToken)
def get_hubspot_token(
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_active_user),
    user_id: int = 6,  # ID administrateur pour MVP
) -> Any:
    """
    Get current HubSpot token
    """
    token = crud_hubspot.get_active_token(db, user_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail="No active HubSpot integration found"
        )
    
    # Check if token is valid
    if not crud_hubspot.is_token_valid(token):
        # Try to refresh
        if not settings.HUBSPOT_CLIENT_ID or not settings.HUBSPOT_CLIENT_SECRET:
            raise HTTPException(
                status_code=500,
                detail="HubSpot integration not configured"
            )
        
        refresh_url = "https://api.hubapi.com/oauth/v1/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": settings.HUBSPOT_CLIENT_ID,
            "client_secret": settings.HUBSPOT_CLIENT_SECRET,
            "refresh_token": token.refresh_token
        }
        
        response = requests.post(refresh_url, data=data)
        if response.status_code != 200:
            # Deactivate token as it can't be refreshed
            crud_hubspot.deactivate_token(db, user_id)
            raise HTTPException(
                status_code=401,
                detail="HubSpot token expired and could not be refreshed"
            )
        
        token_data = response.json()
        expires_in = token_data.get("expires_in", 21600)  # Default 6 hours
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        token_update = HubspotTokenCreate(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
            is_active=True
        )
        
        token = crud_hubspot.create_token(db, token_update, user_id)
    
    return token

@router.delete("/disconnect")
def disconnect_hubspot(
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_active_user),
    user_id: int = 6,  # ID administrateur pour MVP
) -> Any:
    """
    Disconnect HubSpot integration
    """
    crud_hubspot.deactivate_token(db, user_id)
    return {"message": "HubSpot disconnected successfully"}
