from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.hubspot_data import HubspotDataSync
from app.schemas.hubspot_sync import HubspotSyncCreate, HubspotSyncResponse
from app.services.hubspot_sync import HubspotSyncService

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

@router.get("/latest", response_model=Optional[HubspotSyncResponse])
async def get_latest_sync(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Récupère la dernière synchronisation réussie.
    """
    sync_service = HubspotSyncService(db, current_user.id)
    latest_sync = await sync_service.get_latest_sync(db, current_user.id)
    
    return latest_sync

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
