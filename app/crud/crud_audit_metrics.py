from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import math
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.models.audit import Audit, AuditResult, AuditDetailItem

# Constantes pour la sévérité des anomalies
SEVERITY_MAPPING = {
    # Contacts
    "missing_firstname": "medium",
    "missing_lastname": "medium",
    "missing_email": "high",
    "invalid_email": "high",
    "duplicate_email": "high",
    "missing_phone": "low",
    "invalid_phone": "medium",
    "missing_company": "medium",
    "missing_lifecycle_stage": "low",
    "inactive_30days": "low",
    
    # Companies
    "missing_name": "high",
    "missing_website": "medium",
    "missing_industry": "low",
    "missing_phone": "low",
    "inactive_60days": "medium",
    
    # Deals
    "missing_amount": "high",
    "missing_close_date": "high",
    "missing_next_step": "medium",
    "stale_deal": "medium",
    "missing_contact": "high",
    "inactive_15days": "high"
}

# Description des anomalies
ISSUE_DESCRIPTIONS = {
    # Contacts
    "missing_firstname": "Le prénom est manquant",
    "missing_lastname": "Le nom de famille est manquant",
    "missing_email": "L'email est manquant",
    "invalid_email": "Le format de l'email est invalide",
    "duplicate_email": "L'email est en doublon",
    "missing_phone": "Le téléphone est manquant",
    "invalid_phone": "Le format du téléphone est invalide",
    "missing_company": "L'entreprise est manquante",
    "missing_lifecycle_stage": "L'étape du cycle de vie est manquante",
    "inactive_30days": "Aucune activité depuis 30 jours",
    
    # Companies
    "missing_name": "Le nom de l'entreprise est manquant",
    "missing_website": "Le site web est manquant",
    "missing_industry": "Le secteur d'activité est manquant",
    "missing_phone": "Le téléphone est manquant",
    "inactive_60days": "Aucune activité depuis 60 jours",
    
    # Deals
    "missing_amount": "Le montant est manquant",
    "missing_close_date": "La date de clôture est manquante",
    "missing_next_step": "La prochaine étape est manquante",
    "stale_deal": "L'affaire est inactive",
    "missing_contact": "Le contact est manquant",
    "inactive_15days": "Aucune activité depuis 15 jours"
}

# Fonction pour récupérer les métriques globales d'un audit
def get_audit_metrics(db: Session, audit_id: str):
    # Récupérer l'audit
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        return None
    
    # Récupérer les résultats agrégés par catégorie
    results = db.query(AuditResult).filter(AuditResult.audit_id == audit_id).all()
    
    # Calculer les statistiques par entité
    entity_stats = {
        "contacts": {"total_count": 0, "issues_count": 0, "score": 0},
        "companies": {"total_count": 0, "issues_count": 0, "score": 0},
        "deals": {"total_count": 0, "issues_count": 0, "score": 0}
    }
    
    for result in results:
        if result.category.lower() in entity_stats:
            entity = result.category.lower()
            entity_stats[entity]["total_count"] = max(entity_stats[entity]["total_count"], result.total_count)
            entity_stats[entity]["issues_count"] += result.empty_count
            
    # Calculer les scores par entité
    for entity in entity_stats:
        if entity_stats[entity]["total_count"] > 0:
            entity_stats[entity]["score"] = round(100 - (entity_stats[entity]["issues_count"] / entity_stats[entity]["total_count"] * 100), 2)
        else:
            entity_stats[entity]["score"] = 100
    
    # Calculer le score global
    total_records = sum(stats["total_count"] for stats in entity_stats.values())
    total_issues = sum(stats["issues_count"] for stats in entity_stats.values())
    overall_score = 100
    if total_records > 0:
        overall_score = round(100 - (total_issues / total_records * 100), 2)
    
    return {
        "id": str(audit.id),
        "created_at": audit.created_at,
        "completed_at": audit.updated_at if audit.status == "completed" else None,
        "status": audit.status,
        "overall_score": overall_score,
        "entities_stats": entity_stats
    }

# Fonction pour récupérer les métriques par type d'entité
def get_entity_metrics(db: Session, audit_id: str, entity_type: str):
    # Valider le type d'entité
    if entity_type.lower() not in ["contacts", "companies", "deals"]:
        return None
    
    # Récupérer les résultats pour cette entité
    results = db.query(AuditResult).filter(
        AuditResult.audit_id == audit_id,
        func.lower(AuditResult.category) == entity_type.lower()
    ).all()
    
    if not results:
        return None
    
    # Préparer les métriques par type d'anomalie
    issue_types = {}
    
    for result in results:
        issue_type = result.criterion.lower()
        
        # Déterminer la gravité et la possibilité de correction
        severity = SEVERITY_MAPPING.get(issue_type, "medium")
        description = ISSUE_DESCRIPTIONS.get(issue_type, f"Problème: {issue_type}")
        
        # Déterminer si le problème est corrigeable automatiquement
        fixable = issue_type in [
            "missing_lifecycle_stage", "missing_next_step", 
            "duplicate_email", "invalid_email", "invalid_phone"
        ]
        
        issue_types[issue_type] = {
            "count": result.empty_count,
            "severity": severity,
            "description": description,
            "fixable": fixable
        }
    
    return {
        "entity_type": entity_type.lower(),
        "issue_types": issue_types
    }

# Fonction pour récupérer les détails des anomalies par type
def get_issue_details(
    db: Session, 
    audit_id: str, 
    entity_type: str, 
    issue_type: str,
    page: int = 1,
    limit: int = 50
):
    # Valider le type d'entité
    if entity_type.lower() not in ["contacts", "companies", "deals"]:
        return None
    
    # Récupérer les détails pour cette anomalie
    details = db.query(AuditDetailItem).filter(
        AuditDetailItem.audit_id == audit_id,
        func.lower(AuditDetailItem.category) == entity_type.lower(),
        func.lower(AuditDetailItem.criterion) == issue_type.lower()
    ).all()
    
    if not details:
        return {
            "total": 0,
            "page": page,
            "page_size": limit,
            "total_pages": 0,
            "records": []
        }
    
    # Calculer la pagination
    total = len(details)
    total_pages = math.ceil(total / limit)
    start_idx = (page - 1) * limit
    end_idx = min(start_idx + limit, total)
    
    # Sélectionner les enregistrements pour cette page
    page_details = details[start_idx:end_idx]
    
    # Formater les enregistrements
    records = []
    for detail in page_details:
        # Déterminer si le problème est corrigeable
        issue_type_lower = issue_type.lower()
        fixable = issue_type_lower in [
            "missing_lifecycle_stage", "missing_next_step", 
            "duplicate_email", "invalid_email", "invalid_phone"
        ]
        
        # Déterminer la méthode de correction
        fix_method = None
        if fixable:
            if issue_type_lower == "missing_lifecycle_stage":
                fix_method = "set_default_lifecycle"
            elif issue_type_lower == "missing_next_step":
                fix_method = "set_default_next_step"
            elif issue_type_lower in ["duplicate_email", "invalid_email"]:
                fix_method = "fix_email"
            elif issue_type_lower == "invalid_phone":
                fix_method = "fix_phone"
        
        # Formater les propriétés
        properties = {}
        if detail.properties:
            try:
                # Si les propriétés sont stockées sous forme de chaîne JSON
                import json
                properties = json.loads(detail.properties)
            except (TypeError, json.JSONDecodeError):
                # Si les propriétés sont déjà un dictionnaire ou autre format
                properties = detail.properties if isinstance(detail.properties, dict) else {}
        
        records.append({
            "id": detail.record_id,
            "name": detail.record_name or "Sans nom",
            "properties": properties,
            "issue_details": detail.details or ISSUE_DESCRIPTIONS.get(issue_type_lower, f"Problème: {issue_type}"),
            "fixable": fixable,
            "fix_method": fix_method
        })
    
    return {
        "total": total,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages,
        "records": records
    }
