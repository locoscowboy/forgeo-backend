from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from datetime import datetime

from app.models.audit import Audit, AuditResult, AuditDetailItem
from app.schemas.audit import AuditCreate, AuditUpdate

def create_audit(db: Session, *, obj_in: AuditCreate, user_id: int) -> Audit:
    """Crée un nouvel audit."""
    obj_in_data = jsonable_encoder(obj_in)
    db_obj = Audit(**obj_in_data, user_id=user_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_audit(db: Session, id: int) -> Optional[Audit]:
    """Récupère un audit par son ID."""
    return db.query(Audit).filter(Audit.id == id).first()

def get_audits(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Audit]:
    """Récupère tous les audits d'un utilisateur."""
    return db.query(Audit).filter(Audit.user_id == user_id).offset(skip).limit(limit).all()

def update_audit(db: Session, *, db_obj: Audit, obj_in: AuditUpdate) -> Audit:
    """Met à jour un audit."""
    obj_data = jsonable_encoder(db_obj)
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.dict(exclude_unset=True)

    for field in obj_data:
        if field in update_data:
            setattr(db_obj, field, update_data[field])

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_audit(db: Session, *, id: int) -> Audit:
    """Supprime un audit."""
    obj = db.query(Audit).get(id)
    db.delete(obj)
    db.commit()
    return obj

def get_audit_results(db: Session, audit_id: int) -> List[AuditResult]:
    """Récupère tous les résultats d'un audit."""
    return db.query(AuditResult).filter(AuditResult.audit_id == audit_id).all()

def get_audit_details(
    db: Session,
    audit_id: int,
    category: Optional[str] = None,
    criterion: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[AuditDetailItem]:
    """Récupère les détails d'un audit avec filtrage optionnel."""
    query = db.query(AuditDetailItem).filter(AuditDetailItem.audit_id == audit_id)

    if category:
        query = query.filter(AuditDetailItem.category == category)

    if criterion:
        query = query.filter(AuditDetailItem.criterion == criterion)

    return query.offset(skip).limit(limit).all()
