from typing import Any, List
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.models.user import User
from app.services.hubspot_audit import HubspotAuditService
from datetime import datetime
router = APIRouter()

@router.get("/", response_model=List[schemas.Audit])
def read_audits(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Récupérer tous les audits.
    """
    return crud.get_audits(db, user_id=current_user.id, skip=skip, limit=limit)

@router.post("/", response_model=schemas.Audit)
def create_audit(
    *,
    db: Session = Depends(deps.get_db),
    audit_in: schemas.AuditCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Créer un nouvel audit.
    """
    audit = crud.create_audit(db, obj_in=audit_in, user_id=current_user.id)
    return audit

@router.get("/{id}", response_model=schemas.Audit)
def read_audit(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Récupérer un audit par ID.
    """
    audit = crud.get_audit(db, id=id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return audit

@router.delete("/{id}", response_model=schemas.Audit)
def delete_audit(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Supprimer un audit.
    """
    audit = crud.get_audit(db, id=id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    audit = crud.delete_audit(db, id=id)
    return audit


@router.post("/{id}/run", response_model=schemas.Audit)
async def run_audit(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Exécute manuellement un audit HubSpot existant.
    """
    audit = crud.get_audit(db, id=id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Vérifier que l'utilisateur a un token HubSpot actif
    token = crud.crud_hubspot.get_active_token(db, current_user.id)
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No active HubSpot integration found."
        )
    
    try:
        # Réinitialiser le statut de l'audit si nécessaire
        if audit.status not in ["in_progress", "pending"]:
            crud.update_audit(db, db_obj=audit, obj_in={"status": "in_progress"})
        
        # Lancer l'audit directement (pas en tâche background)
        audit_service = HubspotAuditService(db, current_user.id)
        
        # Cette approche est sûre car FastAPI gère déjà les requêtes asynchrones
        # L'audit sera exécuté et les exceptions seront correctement gérées
        try:
            await audit_service.run_audit(audit.id)
            return audit
        except Exception as e:
            # Mettre à jour le statut en cas d'erreur
            audit.status = "failed"
            audit.updated_at = datetime.utcnow()
            db.add(audit)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")
    except Exception as e:
        crud.update_audit(db, db_obj=audit, obj_in={"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
@router.get("/{id}/results", response_model=List[schemas.AuditResult])
def read_audit_results(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Récupérer les résultats d'un audit par ID.
    """
    audit = crud.get_audit(db, id=id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.get_audit_results(db, audit_id=id)
