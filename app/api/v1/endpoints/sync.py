"""
Endpoints pour la gestion de la synchronisation Airbyte
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.airbyte_service import AirbyteService
from app.schemas.airbyte_sync import (
    SyncJobResponse,
    SyncJobStatus,
    SyncHistoryResponse,
    ConnectionInfo
)

router = APIRouter()


@router.post("/trigger", response_model=SyncJobResponse)
async def trigger_manual_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Déclenche une synchronisation manuelle HubSpot → PostgreSQL
    
    **Action :** Lance immédiatement un job de sync Airbyte pour l'utilisateur
    """
    airbyte_service = AirbyteService(db=db, user_id=current_user.id)
    result = await airbyte_service.trigger_manual_sync()
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to trigger synchronization. Check Airbyte connection."
        )
    
    return SyncJobResponse(**result)


@router.get("/status/{job_id}", response_model=SyncJobStatus)
async def get_sync_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère le statut détaillé d'un job de synchronisation
    
    **Paramètres :**
    - `job_id` : ID du job Airbyte
    
    **Retour :**
    - Statut (pending, running, succeeded, failed)
    - Nombre de lignes synchronisées
    - Durée du job
    - Message d'erreur si échec
    """
    airbyte_service = AirbyteService(db=db, user_id=current_user.id)
    result = await airbyte_service.get_job_status(job_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or inaccessible"
        )
    
    return SyncJobStatus(**result)


@router.get("/history", response_model=SyncHistoryResponse)
async def get_sync_history(
    limit: int = Query(10, ge=1, le=50, description="Number of jobs to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère l'historique des synchronisations de l'utilisateur
    
    **Paramètres :**
    - `limit` : Nombre de jobs à récupérer (max 50)
    
    **Retour :**
    - Liste des jobs (récents en premier)
    - Date de la dernière sync réussie
    - Statistiques globales
    """
    airbyte_service = AirbyteService(db=db, user_id=current_user.id)
    result = await airbyte_service.get_sync_history(limit=limit)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No synchronization history found. Connect HubSpot first."
        )
    
    return SyncHistoryResponse(**result)


@router.get("/connection-info", response_model=ConnectionInfo)
async def get_connection_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère les informations de la connexion Airbyte
    
    **Retour :**
    - IDs de la source, destination, connexion
    - Statut de la connexion
    - Nom de la connexion
    """
    airbyte_service = AirbyteService(db=db, user_id=current_user.id)
    result = await airbyte_service.get_connection_info()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No Airbyte connection found. Connect HubSpot first."
        )
    
    return ConnectionInfo(**result)
