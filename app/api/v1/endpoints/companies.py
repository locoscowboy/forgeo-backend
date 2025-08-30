from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from app.api import deps
from app.models.hubspot_data import HubspotCompany, HubspotDataSync  
from app.models.user import User

router = APIRouter()

@router.get("")
async def get_companies(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),      
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query("name"),
    sort_order: Optional[str] = Query("asc")
):
    """Récupère les companies avec pagination, recherche et tri"""    

    # Récupérer la dernière synchronisation de l'utilisateur
    latest_sync = db.query(HubspotDataSync).filter(
        HubspotDataSync.user_id == current_user.id,
        HubspotDataSync.status == "completed"
    ).order_by(desc(HubspotDataSync.completed_at)).first()

    if not latest_sync:
        return {
            "companies": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

    # Construire la requête
    query = db.query(HubspotCompany).filter(
        HubspotCompany.sync_id == latest_sync.id
    )

    # Appliquer la recherche
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                HubspotCompany.name.ilike(search_term),
                HubspotCompany.domain.ilike(search_term)
            )
        )

    # Appliquer le tri
    if sort_field and hasattr(HubspotCompany, sort_field):
        field = getattr(HubspotCompany, sort_field)
        if sort_order == "desc":
            query = query.order_by(desc(field))
        else:
            query = query.order_by(asc(field))

    # Compter le total
    total = query.count()

    # Appliquer la pagination
    offset = (page - 1) * limit
    companies = query.offset(offset).limit(limit).all()

    # Formater les données pour le frontend
    formatted_companies = []
    for company in companies:
        properties = company.properties or {}
        formatted_companies.append({
            "id": company.hubspot_id,
            "name": company.name or properties.get("name", ""),
            "domain": company.domain or properties.get("domain", ""),
            "website": properties.get("website", ""),
            "industry": properties.get("industry", ""),
            "phone": properties.get("phone", ""),
            "address": properties.get("address", ""),
            "city": properties.get("city", ""),
            "state": properties.get("state", ""),
            "zip": properties.get("zip", ""),
            "country": properties.get("country", ""),
            "description": properties.get("description", ""),
            "founded_year": properties.get("founded_year", ""),
            "numberofemployees": properties.get("numberofemployees", ""),
            "lastmodifieddate": properties.get("lastmodifieddate", ""),
            "properties": properties
        })

    total_pages = (total + limit - 1) // limit

    return {
        "companies": formatted_companies,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }
