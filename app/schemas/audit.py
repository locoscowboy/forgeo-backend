from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Base schemas
class AuditBase(BaseModel):
    title: str
    description: Optional[str] = None

class AuditResultBase(BaseModel):
    category: str
    criterion: str
    field_name: str
    empty_count: int
    total_count: int
    percentage: float

class AuditDetailItemBase(BaseModel):
    category: str
    criterion: str
    hubspot_id: str
    object_data: dict

# Create schemas
class AuditCreate(AuditBase):
    pass

class AuditResultCreate(AuditResultBase):
    audit_id: int

class AuditDetailItemCreate(AuditDetailItemBase):
    audit_id: int
    result_id: int

# Update schemas
class AuditUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    contacts_total: Optional[int] = None
    companies_total: Optional[int] = None
    deals_total: Optional[int] = None

# Response schemas
class AuditDetailItem(AuditDetailItemBase):
    id: int
    audit_id: int
    result_id: int

    class Config:
        orm_mode = True

class AuditResult(AuditResultBase):
    id: int
    audit_id: int
    detail_items: List[AuditDetailItem] = []

    class Config:
        orm_mode = True

# Résumé des résultats d'audit (classe manquante)
class AuditResultSummary(BaseModel):
    category: str
    total_issues: int
    criteria: List[dict]

    class Config:
        orm_mode = True

class Audit(AuditBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    contacts_total: int = 0
    companies_total: int = 0
    deals_total: int = 0
    results: List[AuditResult] = []

    class Config:
        orm_mode = True
