from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.audit import Audit
from app.schemas.audit import AuditCreate, AuditUpdate

def get(db: Session, audit_id: int, user_id: Optional[int] = None):
    query = db.query(Audit).filter(Audit.id == audit_id, Audit.is_deleted == False)
    if user_id:
        query = query.filter(Audit.user_id == user_id)
    return query.first()

def get_multi(
    db: Session, 
    user_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None
):
    query = db.query(Audit).filter(Audit.is_deleted == False)
    
    if user_id:
        query = query.filter(Audit.user_id == user_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Audit.title.ilike(search_term),
                Audit.description.ilike(search_term),
                Audit.company_name.ilike(search_term)
            )
        )
    
    if status:
        query = query.filter(Audit.status == status)
    
    total = query.count()
    audits = query.order_by(Audit.created_at.desc()).offset(skip).limit(limit).all()
    
    return audits, total

def create(db: Session, obj_in: AuditCreate, user_id: int):
    db_obj = Audit(
        **obj_in.dict(),
        user_id=user_id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(db: Session, db_obj: Audit, obj_in: AuditUpdate):
    update_data = obj_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete(db: Session, db_obj: Audit):
    db_obj.is_deleted = True
    db.add(db_obj)
    db.commit()
    return db_obj
