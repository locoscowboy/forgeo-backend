from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from app.api import deps
from app.models.hubspot_data import HubspotContact, HubspotDataSync
from app.models.user import User

router = APIRouter()

@router.get("")
async def get_contacts(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query("firstname"),
    sort_order: Optional[str] = Query("asc")
):
    """Récupère les contacts avec pagination, recherche et tri"""
    
    # Récupérer la dernière synchronisation de l'utilisateur
    latest_sync = db.query(HubspotDataSync).filter(
        HubspotDataSync.user_id == current_user.id,
        HubspotDataSync.status == "completed"
    ).order_by(desc(HubspotDataSync.completed_at)).first()
    
    if not latest_sync:
        return {
            "contacts": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }
    
    # Construire la requête
    query = db.query(HubspotContact).filter(
        HubspotContact.sync_id == latest_sync.id
    )
    
    # Appliquer la recherche
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                HubspotContact.firstname.ilike(search_term),
                HubspotContact.lastname.ilike(search_term),
                HubspotContact.email.ilike(search_term)
            )
        )
    
    # Appliquer le tri
    if sort_field and hasattr(HubspotContact, sort_field):
        field = getattr(HubspotContact, sort_field)
        if sort_order == "desc":
            query = query.order_by(desc(field))
        else:
            query = query.order_by(asc(field))
    
    # Compter le total
    total = query.count()
    
    # Appliquer la pagination
    offset = (page - 1) * limit
    contacts = query.offset(offset).limit(limit).all()
    
    # Formater les données pour le frontend
    formatted_contacts = []
    for contact in contacts:
        properties = contact.properties or {}
        formatted_contacts.append({
            "id": contact.hubspot_id,
            "firstname": contact.firstname or properties.get("firstname", ""),
            "lastname": contact.lastname or properties.get("lastname", ""),
            "email": contact.email or properties.get("email", ""),
            "phone": properties.get("phone", ""),
            "company": properties.get("company", ""),
            "website": properties.get("website", ""),
            "address": properties.get("address", ""),
            "city": properties.get("city", ""),
            "state": properties.get("state", ""),
            "zip": properties.get("zip", ""),
            "country": properties.get("country", ""),
            "jobtitle": properties.get("jobtitle", ""),
            "lifecyclestage": properties.get("lifecyclestage", ""),
            "hs_lead_status": properties.get("hs_lead_status", ""),
            "lastmodifieddate": properties.get("lastmodifieddate", ""),
            "properties": properties
        })
    
    total_pages = (total + limit - 1) // limit
    
    return {
        "contacts": formatted_contacts,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }
