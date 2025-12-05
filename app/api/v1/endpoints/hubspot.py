from typing import Any
import requests
import logging
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user
from app.crud import hubspot as crud_hubspot
from app.models.user import User
from app.core.config import settings
from app.schemas.hubspot import HubspotTokenCreate, HubspotToken, HubspotAuthResponse
from app.services.airbyte_service import AirbyteService  # ✅ AJOUT

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/auth", response_model=HubspotAuthResponse)
def hubspot_auth(
    current_user: User = Depends(get_current_active_user),
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
        f"&state={current_user.id}"
    )

    return {"auth_url": auth_url}

# ✅ AJOUT : Fonction pour configurer Airbyte en arrière-plan
async def setup_airbyte_connection(db: Session, user_id: int, refresh_token: str):
    """Configure Airbyte en arrière-plan après OAuth"""
    try:
        logger.info(f"Starting Airbyte setup for user {user_id}...")
        airbyte_service = AirbyteService(db, user_id)
        airbyte_conn = await airbyte_service.setup_user_connection(refresh_token)
        
        if airbyte_conn:
            logger.info(f"✅ Airbyte setup completed for user {user_id}")
        else:
            logger.error(f"❌ Airbyte setup failed for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error setting up Airbyte for user {user_id}: {e}")

@router.get("/callback")
async def hubspot_callback(
    code: str,
    state: str,
    background_tasks: BackgroundTasks,  # ✅ AJOUT
    db: Session = Depends(get_db),
) -> Any:
    """
    HubSpot OAuth callback
    """
    # Valider et récupérer l'user_id depuis le parameter state
    try:
        user_id = int(state)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter"
        )

    # Vérifier que l'utilisateur existe
    from app import crud
    user = crud.user.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

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
        access_token=token_data["refresh_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=expires_at,
        is_active=True
    )

    crud_hubspot.create_token(db, token_obj, user_id)

    # ✅ AJOUT : Configurer Airbyte en arrière-plan
    background_tasks.add_task(
        setup_airbyte_connection,
        db,
        user_id,
        token_data["refresh_token"]
    )
    logger.info(f"Airbyte setup scheduled for user {user_id}")

    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>HubSpot Connection Success</title>
</head>
<body>
    <script>
        try {
            window.opener.postMessage({
                type: 'hubspot-auth-success'
            }, window.location.origin);
            window.close();
        } catch (error) {
            console.error('Error sending message to parent:', error);
            window.location.href = 'https://app.forgeo.io/audits?connected=true';
        }
    </script>
    <p>Connexion réussie ! Configuration Airbyte en cours...</p>
</body>
</html>
""")

@router.get("/token", response_model=HubspotToken)
def get_hubspot_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current HubSpot token
    """
    token = crud_hubspot.get_active_token(db, current_user.id)
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
            crud_hubspot.deactivate_token(db, current_user.id)
            raise HTTPException(
                status_code=401,
                detail="HubSpot token expired and could not be refreshed"
            )

        token_data = response.json()
        expires_in = token_data.get("expires_in", 21600)  # Default 6 hours
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        token_update = HubspotTokenCreate(
            access_token=token_data["refresh_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
            is_active=True
        )

        token = crud_hubspot.create_token(db, token_update, current_user.id)

    return token

@router.delete("/disconnect")
def disconnect_hubspot(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Disconnect HubSpot integration
    """
    crud_hubspot.deactivate_token(db, current_user.id)
    return {"message": "HubSpot disconnected successfully"}
