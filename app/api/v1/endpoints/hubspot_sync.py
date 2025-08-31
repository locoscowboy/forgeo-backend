from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.hubspot_data import HubspotDataSync
from app.schemas.hubspot_sync import HubspotSyncCreate, HubspotSyncResponse
from app.services.hubspot_sync import HubspotSyncService, sync_to_dict

router = APIRouter()

@router.post("", response_model=HubspotSyncResponse)
async def start_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Démarre une nouvelle synchronisation des données HubSpot.
    """
    sync_service = HubspotSyncService(db, current_user.id)
    
    # Créer une tâche en arrière-plan pour exécuter la synchronisation
    sync = await sync_service.run_sync()
    
    if not sync:
        raise HTTPException(status_code=500, detail="Failed to start synchronization")
    
    return sync

@router.get("", response_model=List[HubspotSyncResponse])
async def get_syncs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Récupère l'historique des synchronisations.
    """
    syncs = db.query(HubspotDataSync).filter(
        HubspotDataSync.user_id == current_user.id
    ).order_by(HubspotDataSync.created_at.desc()).offset(skip).limit(limit).all()
    
    return syncs

@router.get("/latest", response_model=dict)
async def get_latest_sync(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Récupère la dernière synchronisation avec informations de fraîcheur (Smart Sync).
    """
    latest_sync = await HubspotSyncService.get_latest_sync(db, current_user.id)
    
    if not latest_sync:
        return {
            "sync": None,
            "has_data": False,
            "needs_sync": True,
            "reason": "no_previous_sync",
            "data_freshness": "never",
            "recommendation": "Première synchronisation requise"
        }
    
    # Obtenir le statut enrichi
    status = await HubspotSyncService.get_sync_status(db, current_user.id)
    
    return {
        "sync": sync_to_dict(latest_sync),
        "has_data": True,
        "needs_sync": status["needs_sync"],
        "reason": status["reason"], 
        "data_freshness": status["data_freshness"],
        "hours_since_sync": status["hours_since_sync"],
        "recommendation": status["recommendation"]
    }

@router.get("/auto-status")
async def get_auto_sync_status(
    current_user: User = Depends(deps.get_current_user)
):
    """
    Récupère le statut de la synchronisation automatique.
    """
    from app.services.hubspot_auto_sync import auto_sync_service
    return auto_sync_service.get_status()

@router.post("/auto-trigger")
async def trigger_manual_auto_sync(
    current_user: User = Depends(deps.get_current_user)
):
    """
    Déclenche manuellement la synchronisation de tous les utilisateurs.
    """
    from app.services.hubspot_auto_sync import auto_sync_service
    
    # Vérifier que l'utilisateur est admin (optionnel)
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Déclencher la sync en arrière-plan
    import asyncio
    asyncio.create_task(auto_sync_service.sync_all_users())
    
    return {"message": "Auto-sync triggered successfully"}

# === NOUVEAUX ENDPOINTS SMART SYNC ===

@router.get("/should-sync", response_model=dict)
async def should_sync(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Détermine si l'utilisateur devrait synchroniser ses données HubSpot.
    Utilise la stratégie Smart Sync (6h threshold).
    """
    should_sync, reason, hours_since = await HubspotSyncService.should_sync_data(db, current_user.id)

    # Déterminer la qualité des données
    if hours_since is None:
        data_quality = "none"
        auto_sync_recommended = True
    elif hours_since >= 24:
        data_quality = "stale"
        auto_sync_recommended = True
    elif hours_since >= 6:
        data_quality = "acceptable"
        auto_sync_recommended = True
    else:
        data_quality = "fresh"
        auto_sync_recommended = False

    return {
        "should_sync": should_sync,
        "reason": reason,
        "last_sync_ago_hours": hours_since,
        "data_quality": data_quality,
        "auto_sync_recommended": auto_sync_recommended
    }

@router.get("/status", response_model=dict)
async def get_sync_status(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Retourne un statut enrichi de synchronisation avec recommandations.
    """
    return await HubspotSyncService.get_sync_status(db, current_user.id)

@router.get("/login-check")
async def login_sync_check(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Endpoint pour vérifier si une sync est nécessaire au login.
    Utilisé par le frontend après authentification.
    """
    should_sync_login = await HubspotSyncService.should_sync_on_login(db, current_user.id)
    latest_sync = await HubspotSyncService.get_latest_sync(db, current_user.id)

    return {
        "should_sync_on_login": should_sync_login,
        "has_data": latest_sync is not None,
        "last_sync": sync_to_dict(latest_sync)
    }

@router.get("/{sync_id}", response_model=HubspotSyncResponse)
async def get_sync(
    sync_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Récupère une synchronisation spécifique.
    """
    sync = db.query(HubspotDataSync).filter(
        HubspotDataSync.id == sync_id,
        HubspotDataSync.user_id == current_user.id
    ).first()

    if not sync:
        raise HTTPException(status_code=404, detail="Synchronization not found")

    return sync
