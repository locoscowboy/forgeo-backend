from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

# Schémas pour les métriques globales
class EntityStats(BaseModel):
    total_count: int = Field(..., description="Nombre total d'enregistrements")
    issues_count: int = Field(..., description="Nombre d'enregistrements avec anomalies")
    score: float = Field(..., description="Score de qualité (0-100)")

class AuditMetricsResponse(BaseModel):
    id: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    overall_score: float = Field(..., description="Score global de qualité")
    
    entities_stats: Dict[str, EntityStats] = Field(
        ..., 
        description="Statistiques par entité (contacts, companies, deals)"
    )
    
    class Config:
        from_attributes = True

# Schémas pour les métriques par entité
class IssueTypeMetric(BaseModel):
    count: int = Field(..., description="Nombre d'occurrences")
    severity: str = Field(..., description="Gravité (high, medium, low)")
    description: str = Field(..., description="Description du problème")
    fixable: bool = Field(..., description="Peut être corrigé automatiquement")

class EntityMetricsResponse(BaseModel):
    entity_type: str = Field(..., description="Type d'entité (contacts, companies, deals)")
    issue_types: Dict[str, IssueTypeMetric] = Field(
        ..., 
        description="Métriques par type d'anomalie"
    )
    
    class Config:
        from_attributes = True

# Schémas pour les détails des anomalies
class IssueRecord(BaseModel):
    id: str
    name: str
    properties: Dict[str, Any]
    issue_details: str
    fixable: bool
    fix_method: Optional[str] = None

class IssueDetailsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    records: List[IssueRecord]
    
    class Config:
        from_attributes = True
