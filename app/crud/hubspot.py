from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.hubspot import HubspotToken
from app.schemas.hubspot import HubspotTokenCreate, HubspotTokenUpdate

def get_active_token(db: Session, user_id: int) -> Optional[HubspotToken]:
    return db.query(HubspotToken).filter(
        HubspotToken.user_id == user_id,
        HubspotToken.is_active == True
    ).first()

def create_token(db: Session, obj_in: HubspotTokenCreate, user_id: int) -> HubspotToken:
    # Désactiver les tokens précédents
    db.query(HubspotToken).filter(
        HubspotToken.user_id == user_id,
        HubspotToken.is_active == True
    ).update({"is_active": False})
    
    # Créer un nouveau token
    db_obj = HubspotToken(
        **obj_in.dict(),
        user_id=user_id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_token(db: Session, db_obj: HubspotToken, obj_in: HubspotTokenUpdate) -> HubspotToken:
    update_data = obj_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def deactivate_token(db: Session, user_id: int) -> None:
    db.query(HubspotToken).filter(
        HubspotToken.user_id == user_id,
        HubspotToken.is_active == True
    ).update({"is_active": False})
    db.commit()

def is_token_valid(token: HubspotToken) -> bool:
    if not token or not token.is_active:
        return False
    now = datetime.now(timezone.utc)
    return token.expires_at > now
