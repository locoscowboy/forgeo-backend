from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import httpx
from sqlalchemy.orm import Session

from app.crud import crud_hubspot
from app.models.audit import Audit, AuditResult, AuditDetailItem
from app.core.config import settings

logger = logging.getLogger(__name__)

class HubspotAuditService:
    """Service pour auditer les données HubSpot d'un utilisateur."""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.token = crud_hubspot.get_active_token(db, user_id)
        if not self.token:
            raise ValueError("Aucun token HubSpot actif trouvé pour cet utilisateur")
        
        self.headers = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Content-Type": "application/json"
        }
        
        # Critères d'audit pour chaque type d'objet
        self.contact_criteria = {
            "missing_firstname": {"field": "firstname", "description": "Contacts sans prénom"},
            "missing_lastname": {"field": "lastname", "description": "Contacts sans nom"},
            "missing_phone": {"field": "phone", "description": "Contacts sans numéro de tel"},
            "missing_email": {"field": "email", "description": "Contacts sans email"},
            "missing_owner": {"field": "hubspot_owner_id", "description": "Contacts sans propriétaires"},
            "missing_jobtitle": {"field": "jobtitle", "description": "Contacts sans intitulés de poste"},
            "inactive_12months": {"field": "last_activity_date", "description": "Contacts avec date de la dernière activité > 12 mois"},
            "missing_lifecycle": {"field": "lifecyclestage", "description": "Contacts sans cycle de vie"},
            "missing_lead_status": {"field": "hs_lead_status", "description": "Contact sans statut de lead"},
            "missing_linkedin": {"field": "hs_linkedin_url", "description": "Contacts sans LinkedIn"}
        }
        
        self.company_criteria = {
            "missing_website": {"field": "website", "description": "Entreprises sans site web"},
            "missing_lifecycle": {"field": "lifecyclestage", "description": "Entreprises sans cycle de vie"},
            "missing_owner": {"field": "hubspot_owner_id", "description": "Entreprises sans propriétaires"},
            "missing_size": {"field": "numberofemployees", "description": "Entreprises sans taille d'entreprise"},
            "missing_industry": {"field": "industry", "description": "Entreprises sans secteur"}
        }
        
        self.deal_criteria = {
            "missing_next_step": {"field": "hs_next_step", "description": "Transactions sans actions prévues"},
            "missing_amount": {"field": "amount", "description": "Transaction sans valeur monétaire"},
            "inactive_15days": {"field": "notes_last_updated", "description": "Transaction (en cours) sans activité depuis 15j"},
            "inactive_30days": {"field": "notes_last_updated", "description": "Transaction (en cours) sans activité depuis 30j"},
            "inactive_90days": {"field": "notes_last_updated", "description": "Transaction (en cours) sans activité depuis 90j"},
            "missing_source": {"field": "hs_object_source_label", "description": "Transactions sans sources d'origine"}
        }
    
    async def run_audit(self, audit_id: int) -> Audit:
        """Exécute un audit complet des données HubSpot."""
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise ValueError(f"Audit avec ID {audit_id} non trouvé")
        
        try:
            # Audit des contacts
            contacts_total, contact_results = await self._audit_contacts()
            audit.contacts_total = contacts_total
            
            # Audit des entreprises
            companies_total, company_results = await self._audit_companies()
            audit.companies_total = companies_total
            
            # Audit des deals
            deals_total, deal_results = await self._audit_deals()
            audit.deals_total = deals_total
            
            # Enregistrement des résultats
            all_results = contact_results + company_results + deal_results
            for result_data in all_results:
                result = AuditResult(
                    audit_id=audit.id,
                    category=result_data["category"],
                    criterion=result_data["criterion"],
                    field_name=result_data["field_name"],
                    empty_count=result_data["empty_count"],
                    total_count=result_data["total_count"],
                    percentage=result_data["percentage"]
                )
                self.db.add(result)
                self.db.flush()  # Pour obtenir l'ID du résultat
                
                # Ajout des détails
                for item in result_data["items"]:
                    detail = AuditDetailItem(
                        audit_id=audit.id,
                        result_id=result.id,
                        category=result_data["category"],
                        criterion=result_data["criterion"],
                        hubspot_id=item["id"],
                        object_data=item["properties"]
                    )
                    self.db.add(detail)
            
            # Finalisation de l'audit
            audit.status = "completed"
            audit.updated_at = datetime.utcnow()
            self.db.commit()
            
            return audit
            
        except Exception as e:
            logger.error(f"Erreur lors de l'audit: {str(e)}")
            audit.status = "failed"
            self.db.commit()
            raise
    
    async def _fetch_all_objects(self, object_type: str, properties: List[str]) -> List[Dict[str, Any]]:
        """Récupère tous les objets d'un type donné avec pagination."""
        url = f"https://api.hubapi.com/crm/v3/objects/{object_type}"
        params = {
            "limit": 100,
            "properties": properties,
            "archived": False
        }
        
        all_objects = []
        has_more = True
        after = None
        
        while has_more:
            if after:
                params["after"] = after
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Erreur lors de la récupération des {object_type}: {response.text}")
                    raise Exception(f"Erreur API HubSpot: {response.status_code}")
                
                data = response.json()
                all_objects.extend(data["results"])
                
                if "paging" in data and "next" in data["paging"]:
                    after = data["paging"]["next"]["after"]
                else:
                    has_more = False
        
        return all_objects
    
    async def _audit_contacts(self) -> Tuple[int, List[Dict[str, Any]]]:
        """Audite les contacts selon les critères définis."""
        # Propriétés à récupérer
        properties = list(set([criteria["field"] for criteria in self.contact_criteria.values()]))
        properties.extend(["firstname", "lastname", "email"])  # Ajout de propriétés pour l'affichage
        
        # Récupération de tous les contacts
        contacts = await self._fetch_all_objects("contacts", properties)
        total_contacts = len(contacts)
        
        results = []
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        
        # Analyse selon chaque critère
        for criterion, config in self.contact_criteria.items():
            field = config["field"]
            empty_contacts = []
            
            for contact in contacts:
                props = contact.get("properties", {})
                
                # Cas spécial pour la dernière activité > 12 mois
                if criterion == "inactive_12months":
                    last_activity = props.get(field)
                    if last_activity:
                        try:
                            last_activity_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                            if last_activity_date > one_year_ago:
                                continue
                        except (ValueError, TypeError):
                            # Si la date n'est pas valide, on considère le contact comme inactif
                            pass
                    
                    empty_contacts.append(contact)
                    continue
                
                # Cas général - champ vide
                if field not in props or not props[field]:
                    empty_contacts.append(contact)
            
            # Création du résultat pour ce critère
            percentage = (len(empty_contacts) / total_contacts * 100) if total_contacts > 0 else 0
            results.append({
                "category": "contact",
                "criterion": criterion,
                "field_name": field,
                "empty_count": len(empty_contacts),
                "total_count": total_contacts,
                "percentage": percentage,
                "items": empty_contacts
            })
        
        return total_contacts, results
    
    async def _audit_companies(self) -> Tuple[int, List[Dict[str, Any]]]:
        """Audite les entreprises selon les critères définis."""
        # Propriétés à récupérer
        properties = list(set([criteria["field"] for criteria in self.company_criteria.values()]))
        properties.extend(["name", "domain"])  # Ajout de propriétés pour l'affichage
        
        # Récupération de toutes les entreprises
        companies = await self._fetch_all_objects("companies", properties)
        total_companies = len(companies)
        
        results = []
        
        # Analyse selon chaque critère
        for criterion, config in self.company_criteria.items():
            field = config["field"]
            empty_companies = []
            
            for company in companies:
                props = company.get("properties", {})
                
                if field not in props or not props[field]:
                    empty_companies.append(company)
            
            # Création du résultat pour ce critère
            percentage = (len(empty_companies) / total_companies * 100) if total_companies > 0 else 0
            results.append({
                "category": "company",
                "criterion": criterion,
                "field_name": field,
                "empty_count": len(empty_companies),
                "total_count": total_companies,
                "percentage": percentage,
                "items": empty_companies
            })
        
        return total_companies, results
    
    async def _audit_deals(self) -> Tuple[int, List[Dict[str, Any]]]:
        """Audite les deals selon les critères définis."""
        # Propriétés à récupérer
        properties = list(set([criteria["field"] for criteria in self.deal_criteria.values()]))
        properties.extend(["dealname", "pipeline", "dealstage"])  # Ajout de propriétés pour l'affichage
        
        # Récupération de tous les deals
        deals = await self._fetch_all_objects("deals", properties)
        total_deals = len(deals)
        
        results = []
        now = datetime.utcnow()
        
        # Analyse selon chaque critère
        for criterion, config in self.deal_criteria.items():
            field = config["field"]
            empty_deals = []
            
            for deal in deals:
                props = deal.get("properties", {})
                dealstage = props.get("dealstage", "")
                
                # Critères spécifiques aux deals en cours
                if criterion in ["inactive_15days", "inactive_30days", "inactive_90days"]:
                    # Vérifier si le deal est "en cours"
                    if not dealstage or not dealstage.startswith("in_progress"):
                        continue
                    
                    last_updated = props.get(field)
                    if not last_updated:
                        empty_deals.append(deal)
                        continue
                    
                    try:
                        last_updated_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        days_diff = (now - last_updated_date).days
                        
                        if criterion == "inactive_15days" and days_diff > 15:
                            empty_deals.append(deal)
                        elif criterion == "inactive_30days" and days_diff > 30:
                            empty_deals.append(deal)
                        elif criterion == "inactive_90days" and days_diff > 90:
                            empty_deals.append(deal)
                    except (ValueError, TypeError):
                        # Si la date n'est pas valide, on considère le deal comme inactif
                        empty_deals.append(deal)
                else:
                    # Critères généraux - champ vide
                    if field not in props or not props[field]:
                        empty_deals.append(deal)
            
            # Création du résultat pour ce critère
            percentage = (len(empty_deals) / total_deals * 100) if total_deals > 0 else 0
            results.append({
                "category": "deal",
                "criterion": criterion,
                "field_name": field,
                "empty_count": len(empty_deals),
                "total_count": total_deals,
                "percentage": percentage,
                "items": empty_deals
            })
        
        return total_deals, results
