from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from app.api import deps
from app.models.hubspot_data import HubspotDeal, HubspotDataSync
from app.models.user import User

router = APIRouter()

@router.get("")
async def get_deals(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query("dealname"),
    sort_order: Optional[str] = Query("asc")
):
    """Récupère les deals avec pagination, recherche et tri"""

    # Récupérer la dernière synchronisation de l'utilisateur
    latest_sync = db.query(HubspotDataSync).filter(
        HubspotDataSync.user_id == current_user.id,
        HubspotDataSync.status == "completed"
    ).order_by(desc(HubspotDataSync.completed_at)).first()

    if not latest_sync:
        return {
            "deals": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

    # Construire la requête
    query = db.query(HubspotDeal).filter(
        HubspotDeal.sync_id == latest_sync.id
    )

    # Appliquer la recherche
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                HubspotDeal.deal_name.ilike(search_term),
                HubspotDeal.pipeline.ilike(search_term)
            )
        )

    # Appliquer le tri
    if sort_field and hasattr(HubspotDeal, sort_field):
        field = getattr(HubspotDeal, sort_field)
        if sort_order == "desc":
            query = query.order_by(desc(field))
        else:
            query = query.order_by(asc(field))

    # Compter le total
    total = query.count()

    # Appliquer la pagination
    offset = (page - 1) * limit
    deals = query.offset(offset).limit(limit).all()

    # Formater les données pour le frontend
    formatted_deals = []
    for deal in deals:
        properties = deal.properties or {}
        formatted_deals.append({
            "id": deal.hubspot_id,
            "dealname": deal.deal_name or properties.get("dealname", ""),
            "amount": deal.amount or properties.get("amount", ""),
            "pipeline": deal.pipeline or properties.get("pipeline", ""),
            "dealstage": properties.get("dealstage", ""),
            "closedate": properties.get("closedate", ""),
            "dealtype": properties.get("dealtype", ""),
            "description": properties.get("description", ""),
            "createdate": properties.get("createdate", ""),
            "lastmodifieddate": properties.get("lastmodifieddate", ""),
            "hs_lastmodifieddate": properties.get("hs_lastmodifieddate", "")
        })

    total_pages = (total + limit - 1) // limit

    return {
        "deals": formatted_deals,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }
