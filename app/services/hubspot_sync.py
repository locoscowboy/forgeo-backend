import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from httpx import AsyncClient

from app.crud.hubspot import get_active_token
from app.models.hubspot import HubspotToken
from app.models.hubspot_data import HubspotDataSync, HubspotContact, HubspotCompany, HubspotDeal
from app.services.hubspot_audit import HubspotAuditService  # Pour réutiliser _fetch_all_objects

logger = logging.getLogger(__name__)

class HubspotSyncService:
    """Service pour synchroniser les données HubSpot avec la base de données locale"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        # Réutiliser les méthodes de récupération de HubspotAuditService
        self.audit_service = HubspotAuditService(db, user_id)
    
    async def run_sync(self) -> Optional[HubspotDataSync]:
        """Exécute une synchronisation complète des données HubSpot"""
        # Créer un nouvel enregistrement de synchronisation
        sync = HubspotDataSync(
            user_id=self.user_id,
            status="in_progress",
            created_at=datetime.utcnow()
        )
        self.db.add(sync)
        self.db.commit()
        self.db.refresh(sync)
        
        try:
            # Récupérer et stocker les contacts
            await self._sync_contacts(sync.id)
            
            # Récupérer et stocker les entreprises
            await self._sync_companies(sync.id)
            
            # Récupérer et stocker les affaires
            await self._sync_deals(sync.id)
            
            # Mettre à jour les statistiques et le statut
            sync.status = "completed"
            sync.completed_at = datetime.utcnow()
            sync.total_contacts = self.db.query(HubspotContact).filter(HubspotContact.sync_id == sync.id).count()
            sync.total_companies = self.db.query(HubspotCompany).filter(HubspotCompany.sync_id == sync.id).count()
            sync.total_deals = self.db.query(HubspotDeal).filter(HubspotDeal.sync_id == sync.id).count()
            
            self.db.commit()
            self.db.refresh(sync)
            
            logger.info(f"Synchronization {sync.id} completed successfully")
            return sync
            
        except Exception as e:
            logger.error(f"Error during synchronization: {e}")
            sync.status = "failed"
            self.db.commit()
            return None
    
    async def _sync_contacts(self, sync_id: int) -> None:
        """Récupère et stocke tous les contacts"""
        logger.info("Syncing contacts...")
        # Demander toutes les propriétés possibles pour les contacts
        # PROPRIÉTÉS ÉTENDUES - 38 propriétés (15 originales + 23 nouvelles)
        properties = [
            # Propriétés originales (15)
            "firstname", "lastname", "email", "phone", "company", "website",
            "address", "city", "state", "zip", "country", "jobtitle",
            "lifecyclestage", "hs_lead_status", "lastmodifieddate",
    
            # Nouvelles propriétés critiques (23)
            "createdate",                                   # Date de création
            "hs_latest_meeting_activity",                   # Dernière activité meeting
            "notes_last_contacted",                         # Dernière prise de contact
            "engagements_last_meeting_booked",              # Dernier meeting programmé
            "hs_linkedin_url",                              # URL LinkedIn du contact
            "hs_analytics_source",                          # Source d'acquisition originale
            "hs_analytics_source_data_1",                   # Données détaillées source
            "hs_latest_source",                             # Dernière source de contact
            "hs_latest_source_data_1",                      # Dernière source - détails
            "hs_lead_score",                                # Score de lead HubSpot
            "hubspot_owner_id",                             # Propriétaire assigné
            "hs_persona",                                   # Persona du contact
            "hs_email_optout",                              # Opt-out email
            "hs_email_bounce",                              # Bounces email
            "num_contacted_notes",                          # Nombre de fois contacté
            "num_notes",                                    # Nombre de notes
            "hs_lifecyclestage_lead_date",                  # Date passage en lead
            "hs_lifecyclestage_marketingqualifiedlead_date", # Date MQL
            "hs_lifecyclestage_salesqualifiedlead_date",    # Date SQL
            "hs_lifecyclestage_customer_date",              # Date client
            "mobilephone",                                  # Téléphone mobile
            "fax",                                          # Fax
            "hs_time_zone"                                  # Fuseau horaire
        ]
        
        contacts = await self.audit_service._fetch_all_objects("contacts", properties)
        
        for contact in contacts:
            properties = contact.get("properties", {})
            
            # Extraire les propriétés communes pour indexation
            email = properties.get("email")
            firstname = properties.get("firstname")
            lastname = properties.get("lastname")
            
            # Créer l'objet contact
            db_contact = HubspotContact(
                sync_id=sync_id,
                hubspot_id=contact.get("id"),
                properties=properties,
                email=email,
                firstname=firstname,
                lastname=lastname,
                last_modified=datetime.utcnow()
            )
            
            self.db.add(db_contact)
        
        # Commit par lot pour économiser des ressources
        self.db.commit()
        logger.info(f"Synced {len(contacts)} contacts")
    
    async def _sync_companies(self, sync_id: int) -> None:
        """Récupère et stocke toutes les entreprises"""
        logger.info("Syncing companies...")
        # Demander toutes les propriétés possibles pour les entreprises
        # PROPRIÉTÉS ÉTENDUES - 29 propriétés (14 originales + 15 nouvelles)
        properties = [
            # Propriétés originales (14)
            "name", "domain", "website", "industry", "phone",
            "address", "city", "state", "zip", "country",
            "description", "founded_year", "numberofemployees", "lastmodifieddate",
    
            # Nouvelles propriétés critiques (15)
            "createdate",                       # Date de création
            "notes_last_contacted",             # Dernière prise de contact
            "engagements_last_meeting_booked",  # Dernier meeting programmé
            "linkedin_company_page",            # URL LinkedIn de l'entreprise
            "linkedinbio",                      # Bio LinkedIn de l'entreprise
            "facebook_company_page",            # Page Facebook
            "twitterhandle",                    # Handle Twitter
            "annualrevenue",                    # Chiffre d'affaires annuel
            "total_money_raised",               # Fonds levés total
            "is_public",                        # Entreprise publique/privée
            "address_2",                        # Adresse supplémentaire
            "timezone",                         # Fuseau horaire
            "website_url",                      # URL du site web
            "web_technologies",                 # Technologies utilisées
            "hubspot_owner_id"                  # Propriétaire assigné
        ]
        
        companies = await self.audit_service._fetch_all_objects("companies", properties)
        
        for company in companies:
            properties = company.get("properties", {})
            
            # Extraire les propriétés communes
            name = properties.get("name")
            domain = properties.get("domain")
            
            # Créer l'objet entreprise
            db_company = HubspotCompany(
                sync_id=sync_id,
                hubspot_id=company.get("id"),
                properties=properties,
                name=name,
                domain=domain,
                last_modified=datetime.utcnow()
            )
            
            self.db.add(db_company)
        
        self.db.commit()
        logger.info(f"Synced {len(companies)} companies")
    
    async def _sync_deals(self, sync_id: int) -> None:
        """Récupère et stocke toutes les affaires"""
        logger.info("Syncing deals...")
        # Demander toutes les propriétés possibles pour les deals
        # PROPRIÉTÉS ÉTENDUES - 22 propriétés (10 originales + 12 nouvelles) 
        properties = [
            # Propriétés originales (10)
            "dealname", "amount", "pipeline", "dealstage",
            "closedate", "createdate", "lastmodifieddate",
            "hs_lastmodifieddate", "dealtype", "description",
    
            # Nouvelles propriétés critiques (12)
            "engagements_last_meeting_booked",              # Dernier meeting programmé
            "notes_last_contacted",                         # Dernière prise de contact
            "hubspot_owner_id",                             # Propriétaire du deal
            "hs_analytics_source",                          # Source d'acquisition
            "deal_currency_code",                           # Devise du deal
            "hs_projected_amount",                          # Montant projeté
            "hs_deal_stage_probability",                    # Probabilité de stage
            "days_to_close",                                # Jours pour clôturer
            "hs_closed_amount",                             # Montant fermé
            "num_contacted_notes",                          # Nombre de contacts
            "num_notes",                                    # Nombre de notes
            "hs_deal_amount_calculation_preference"         # Préférence calcul montant
        ]
        
        deals = await self.audit_service._fetch_all_objects("deals", properties)
        
        for deal in deals:
            properties = deal.get("properties", {})
            
            # Extraire les propriétés communes
            deal_name = properties.get("dealname")
            amount = properties.get("amount")
            pipeline = properties.get("pipeline")
            
            # Créer l'objet affaire
            db_deal = HubspotDeal(
                sync_id=sync_id,
                hubspot_id=deal.get("id"),
                properties=properties,
                deal_name=deal_name,
                amount=amount,
                pipeline=pipeline,
                last_modified=datetime.utcnow()
            )
            
            self.db.add(db_deal)
        
        self.db.commit()
        logger.info(f"Synced {len(deals)} deals")
    
    @staticmethod
    async def get_latest_sync(db: Session, user_id: int) -> Optional[HubspotDataSync]:
        """Récupère la dernière synchronisation réussie pour un utilisateur"""
        return db.query(HubspotDataSync) \
            .filter(HubspotDataSync.user_id == user_id, HubspotDataSync.status == "completed") \
            .order_by(HubspotDataSync.completed_at.desc()) \
            .first()
