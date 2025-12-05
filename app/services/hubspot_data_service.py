"""
Service pour lire les données HubSpot synchronisées via Airbyte
depuis les schémas PostgreSQL user_{id}_hubspot
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.schemas.hubspot_data import (
    HubspotContactBase,
    HubspotContactDetail,
    HubspotCompanyBase,
    HubspotCompanyDetail,
    HubspotDealBase,
    HubspotDealDetail,
    ColumnMetadata,
    AvailableColumns,
    ContactFilters,
    CompanyFilters,
    DealFilters,
    HubspotStats,
)

logger = logging.getLogger(__name__)


class HubspotDataService:
    """Service pour lire les données HubSpot depuis Airbyte"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.schema_name = f"user_{user_id}_hubspot"
    
    # ═══════════════════════════════════════════════════════════════
    # 1. VÉRIFICATION DU SCHÉMA
    # ═══════════════════════════════════════════════════════════════
    
    def schema_exists(self) -> bool:
        """Vérifie si le schéma existe"""
        query = text("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.schemata 
                WHERE schema_name = :schema_name
            )
        """)
        result = self.db.execute(query, {"schema_name": self.schema_name})
        return result.scalar()
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Récupère la liste des colonnes d'une table"""
        query = text("""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_schema = :schema_name 
            AND table_name = :table_name
            ORDER BY ordinal_position
        """)
        result = self.db.execute(
            query, 
            {"schema_name": self.schema_name, "table_name": table_name}
        )
        return [row[0] for row in result]
    
    # ═══════════════════════════════════════════════════════════════
    # 2. CONTACTS
    # ═══════════════════════════════════════════════════════════════
    
    def get_contacts(
        self, 
        page: int = 1, 
        limit: int = 50,
        filters: Optional[ContactFilters] = None,
        columns: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Récupère la liste des contacts avec pagination et filtres
        
        Returns:
            Tuple[List[Dict], int]: (données, total)
        """
        if not self.schema_exists():
            logger.warning(f"Schema {self.schema_name} does not exist")
            return [], 0
        
        # Colonnes par défaut
        default_columns = [
            "id", "properties_email", "properties_firstname", "properties_lastname",
            "properties_phone", "properties_company", "properties_jobtitle",
            "properties_hs_linkedin_url", "properties_lifecyclestage",
            "properties_country", "properties_city", "properties_createdate",
            "_airbyte_extracted_at"
        ]
        
        # Utiliser les colonnes demandées ou les colonnes par défaut
        select_columns = columns if columns else default_columns
        columns_str = ", ".join(select_columns)
        
        # Construction de la requête WHERE
        where_conditions = []
        params = {"limit": limit, "offset": (page - 1) * limit}
        
        if filters:
            if filters.search:
                where_conditions.append("""
                    (properties_email ILIKE :search 
                    OR properties_firstname ILIKE :search 
                    OR properties_lastname ILIKE :search)
                """)
                params["search"] = f"%{filters.search}%"
            
            if filters.lifecyclestage:
                where_conditions.append("properties_lifecyclestage = :lifecyclestage")
                params["lifecyclestage"] = filters.lifecyclestage
            
            if filters.country:
                where_conditions.append("properties_country = :country")
                params["country"] = filters.country
            
            if filters.city:
                where_conditions.append("properties_city = :city")
                params["city"] = filters.city
            
            if filters.hubspot_owner_id:
                where_conditions.append("properties_hubspot_owner_id = :owner_id")
                params["owner_id"] = filters.hubspot_owner_id
            
            if filters.created_after:
                where_conditions.append("properties_createdate >= :created_after")
                params["created_after"] = filters.created_after
            
            if filters.created_before:
                where_conditions.append("properties_createdate <= :created_before")
                params["created_before"] = filters.created_before
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Requête COUNT
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM {self.schema_name}.contacts 
            {where_clause}
        """)
        total = self.db.execute(count_query, params).scalar()
        
        # Requête SELECT
        select_query = text(f"""
            SELECT {columns_str}
            FROM {self.schema_name}.contacts 
            {where_clause}
            ORDER BY _airbyte_extracted_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = self.db.execute(select_query, params)
        rows = [dict(row._mapping) for row in result]
        
        return rows, total
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un contact par son ID avec toutes les données"""
        if not self.schema_exists():
            return None
        
        query = text(f"""
            SELECT *
            FROM {self.schema_name}.contacts 
            WHERE id = :contact_id
        """)
        
        result = self.db.execute(query, {"contact_id": contact_id})
        row = result.fetchone()
        
        return dict(row._mapping) if row else None
    
    # ═══════════════════════════════════════════════════════════════
    # 3. COMPANIES
    # ═══════════════════════════════════════════════════════════════
    
    def get_companies(
        self, 
        page: int = 1, 
        limit: int = 50,
        filters: Optional[CompanyFilters] = None,
        columns: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Récupère la liste des companies avec pagination et filtres"""
        if not self.schema_exists():
            return [], 0
        
        default_columns = [
            "id", "properties_name", "properties_domain", "properties_industry",
            "properties_numberofemployees", "properties_annualrevenue",
            "properties_country", "properties_city", "properties_phone",
            "properties_website", "properties_linkedin_company_page",
            "properties_hubspot_owner_id", "_airbyte_extracted_at"
        ]
        
        select_columns = columns if columns else default_columns
        columns_str = ", ".join(select_columns)
        
        where_conditions = []
        params = {"limit": limit, "offset": (page - 1) * limit}
        
        if filters:
            if filters.search:
                where_conditions.append("""
                    (properties_name ILIKE :search 
                    OR properties_domain ILIKE :search)
                """)
                params["search"] = f"%{filters.search}%"
            
            if filters.industry:
                where_conditions.append("properties_industry = :industry")
                params["industry"] = filters.industry
            
            if filters.country:
                where_conditions.append("properties_country = :country")
                params["country"] = filters.country
            
            if filters.city:
                where_conditions.append("properties_city = :city")
                params["city"] = filters.city
            
            if filters.hubspot_owner_id:
                where_conditions.append("properties_hubspot_owner_id = :owner_id")
                params["owner_id"] = filters.hubspot_owner_id
            
            if filters.min_employees is not None:
                where_conditions.append("properties_numberofemployees >= :min_employees")
                params["min_employees"] = filters.min_employees
            
            if filters.max_employees is not None:
                where_conditions.append("properties_numberofemployees <= :max_employees")
                params["max_employees"] = filters.max_employees
            
            if filters.created_after:
                where_conditions.append("properties_createdate >= :created_after")
                params["created_after"] = filters.created_after
            
            if filters.created_before:
                where_conditions.append("properties_createdate <= :created_before")
                params["created_before"] = filters.created_before
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM {self.schema_name}.companies 
            {where_clause}
        """)
        total = self.db.execute(count_query, params).scalar()
        
        select_query = text(f"""
            SELECT {columns_str}
            FROM {self.schema_name}.companies 
            {where_clause}
            ORDER BY _airbyte_extracted_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = self.db.execute(select_query, params)
        rows = [dict(row._mapping) for row in result]
        
        return rows, total
    
    def get_company_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une company par son ID avec toutes les données"""
        if not self.schema_exists():
            return None
        
        query = text(f"""
            SELECT *
            FROM {self.schema_name}.companies 
            WHERE id = :company_id
        """)
        
        result = self.db.execute(query, {"company_id": company_id})
        row = result.fetchone()
        
        return dict(row._mapping) if row else None
    
    # ═══════════════════════════════════════════════════════════════
    # 4. DEALS
    # ═══════════════════════════════════════════════════════════════
    
    def get_deals(
        self, 
        page: int = 1, 
        limit: int = 50,
        filters: Optional[DealFilters] = None,
        columns: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Récupère la liste des deals avec pagination et filtres"""
        if not self.schema_exists():
            return [], 0
        
        default_columns = [
            "id", "properties_dealname", "properties_amount", "properties_dealstage",
            "properties_pipeline", "properties_closedate", "properties_createdate",
            "properties_hs_is_closed_won", "properties_hs_is_closed_lost",
            "properties_hs_forecast_amount", "_airbyte_extracted_at"
        ]
        
        select_columns = columns if columns else default_columns
        columns_str = ", ".join(select_columns)
        
        where_conditions = []
        params = {"limit": limit, "offset": (page - 1) * limit}
        
        if filters:
            if filters.search:
                where_conditions.append("properties_dealname ILIKE :search")
                params["search"] = f"%{filters.search}%"
            
            if filters.dealstage:
                where_conditions.append("properties_dealstage = :dealstage")
                params["dealstage"] = filters.dealstage
            
            if filters.pipeline:
                where_conditions.append("properties_pipeline = :pipeline")
                params["pipeline"] = filters.pipeline
            
            if filters.hubspot_owner_id:
                where_conditions.append("properties_hubspot_owner_id = :owner_id")
                params["owner_id"] = filters.hubspot_owner_id
            
            if filters.min_amount is not None:
                where_conditions.append("properties_amount >= :min_amount")
                params["min_amount"] = filters.min_amount
            
            if filters.max_amount is not None:
                where_conditions.append("properties_amount <= :max_amount")
                params["max_amount"] = filters.max_amount
            
            if filters.is_closed is not None:
                where_conditions.append("properties_hs_is_closed = :is_closed")
                params["is_closed"] = filters.is_closed
            
            if filters.created_after:
                where_conditions.append("properties_createdate >= :created_after")
                params["created_after"] = filters.created_after
            
            if filters.created_before:
                where_conditions.append("properties_createdate <= :created_before")
                params["created_before"] = filters.created_before
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM {self.schema_name}.deals 
            {where_clause}
        """)
        total = self.db.execute(count_query, params).scalar()
        
        select_query = text(f"""
            SELECT {columns_str}
            FROM {self.schema_name}.deals 
            {where_clause}
            ORDER BY _airbyte_extracted_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = self.db.execute(select_query, params)
        rows = [dict(row._mapping) for row in result]
        
        return rows, total
    
    def get_deal_by_id(self, deal_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un deal par son ID avec toutes les données"""
        if not self.schema_exists():
            return None
        
        query = text(f"""
            SELECT *
            FROM {self.schema_name}.deals 
            WHERE id = :deal_id
        """)
        
        result = self.db.execute(query, {"deal_id": deal_id})
        row = result.fetchone()
        
        return dict(row._mapping) if row else None
    
    # ═══════════════════════════════════════════════════════════════
    # 5. MÉTADONNÉES DES COLONNES
    # ═══════════════════════════════════════════════════════════════
    
    def get_available_columns(self, object_type: str) -> AvailableColumns:
        """
        Récupère toutes les colonnes disponibles pour un type d'objet
        
        Args:
            object_type: 'contacts', 'companies', 'deals'
        """
        if not self.schema_exists():
            return AvailableColumns(
                object_type=object_type,
                default_columns=[],
                available_columns=[],
                total_columns=0
            )
        
        # Mapper les types SQL vers les types Pydantic
        type_mapping = {
            "character varying": "string",
            "text": "string",
            "integer": "number",
            "bigint": "number",
            "numeric": "number",
            "double precision": "number",
            "real": "number",
            "boolean": "boolean",
            "timestamp with time zone": "datetime",
            "timestamp without time zone": "datetime",
            "date": "date",
            "jsonb": "json",
            "json": "json",
        }
        
        # Récupérer les colonnes de la table
        query = text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = :schema_name 
            AND table_name = :table_name
            ORDER BY ordinal_position
        """)
        
        result = self.db.execute(
            query, 
            {"schema_name": self.schema_name, "table_name": object_type}
        )
        
        all_columns = []
        for row in result:
            col_name = row[0]
            col_type = row[1]
            
            # Ignorer les colonnes système Airbyte sauf _airbyte_extracted_at
            if col_name.startswith("_airbyte") and col_name != "_airbyte_extracted_at":
                continue
            
            # Déterminer le label (nom affiché)
            if col_name.startswith("properties_"):
                label = col_name.replace("properties_", "").replace("_", " ").title()
            else:
                label = col_name.replace("_", " ").title()
            
            # Déterminer la catégorie
            category = "system" if col_name.startswith("_") else "standard"
            
            # Mapper le type SQL vers le type Pydantic
            pydantic_type = type_mapping.get(col_type, "string")
            
            all_columns.append(ColumnMetadata(
                key=col_name,
                label=label,
                type=pydantic_type,
                category=category,
                is_searchable=pydantic_type in ["string", "number"],
                is_sortable=True
            ))
        
        # Séparer les colonnes par défaut et les autres
        default_keys = self._get_default_column_keys(object_type)
        default_columns = [col for col in all_columns if col.key in default_keys]
        available_columns = [col for col in all_columns if col.key not in default_keys]
        
        return AvailableColumns(
            object_type=object_type,
            default_columns=default_columns,
            available_columns=available_columns,
            custom_columns=[],  # TODO: Identifier les colonnes custom
            total_columns=len(all_columns)
        )
    
    def _get_default_column_keys(self, object_type: str) -> List[str]:
        """Retourne les clés des colonnes par défaut selon le type d'objet"""
        defaults = {
            "contacts": [
                "id", "properties_email", "properties_firstname", "properties_lastname",
                "properties_phone", "properties_company", "properties_jobtitle",
                "properties_hs_linkedin_url", "properties_lifecyclestage",
                "properties_country", "properties_createdate", "_airbyte_extracted_at"
            ],
            "companies": [
                "id", "properties_name", "properties_domain", "properties_industry",
                "properties_numberofemployees", "properties_annualrevenue",
                "properties_country", "properties_website", "properties_createdate",
                "_airbyte_extracted_at"
            ],
            "deals": [
                "id", "properties_dealname", "properties_amount", "properties_dealstage",
                "properties_pipeline", "properties_closedate", "properties_createdate",
                "_airbyte_extracted_at"
            ]
        }
        return defaults.get(object_type, [])
    
    # ═══════════════════════════════════════════════════════════════
    # 6. STATISTIQUES
    # ═══════════════════════════════════════════════════════════════
    
    def get_stats(self) -> HubspotStats:
        """Récupère les statistiques globales HubSpot"""
        if not self.schema_exists():
            return HubspotStats(
                total_contacts=0,
                total_companies=0,
                total_deals=0
            )
        
        # Counts
        contacts_count = self.db.execute(
            text(f"SELECT COUNT(*) FROM {self.schema_name}.contacts")
        ).scalar()
        
        companies_count = self.db.execute(
            text(f"SELECT COUNT(*) FROM {self.schema_name}.companies")
        ).scalar()
        
        deals_count = self.db.execute(
            text(f"SELECT COUNT(*) FROM {self.schema_name}.deals")
        ).scalar()
        
        # Dernière date de sync
        last_sync_query = text(f"""
            SELECT MAX(_airbyte_extracted_at) 
            FROM {self.schema_name}.contacts
        """)
        last_sync_at = self.db.execute(last_sync_query).scalar()
        
        # Stats par lifecyclestage
        lifecyclestage_query = text(f"""
            SELECT properties_lifecyclestage, COUNT(*) 
            FROM {self.schema_name}.contacts
            WHERE properties_lifecyclestage IS NOT NULL
            GROUP BY properties_lifecyclestage
        """)
        lifecyclestage_result = self.db.execute(lifecyclestage_query)
        contacts_by_lifecyclestage = {row[0]: row[1] for row in lifecyclestage_result}
        
        # Stats par industry
        industry_query = text(f"""
            SELECT properties_industry, COUNT(*) 
            FROM {self.schema_name}.companies
            WHERE properties_industry IS NOT NULL
            GROUP BY properties_industry
        """)
        industry_result = self.db.execute(industry_query)
        companies_by_industry = {row[0]: row[1] for row in industry_result}
        
        # Stats par dealstage
        dealstage_query = text(f"""
            SELECT properties_dealstage, COUNT(*) 
            FROM {self.schema_name}.deals
            WHERE properties_dealstage IS NOT NULL
            GROUP BY properties_dealstage
        """)
        dealstage_result = self.db.execute(dealstage_query)
        deals_by_stage = {row[0]: row[1] for row in dealstage_result}
        
        # Montants
        amounts_query = text(f"""
            SELECT 
                COALESCE(SUM(properties_amount), 0) as total_amount,
                COALESCE(SUM(CASE WHEN properties_hs_is_closed_won THEN properties_amount ELSE 0 END), 0) as won_amount,
                COALESCE(SUM(CASE WHEN NOT COALESCE(properties_hs_is_closed_won, false) AND NOT COALESCE(properties_hs_is_closed_lost, false) THEN properties_amount ELSE 0 END), 0) as pipeline_amount
            FROM {self.schema_name}.deals
        """)
        amounts_result = self.db.execute(amounts_query).fetchone()
        
        return HubspotStats(
            total_contacts=contacts_count,
            total_companies=companies_count,
            total_deals=deals_count,
            last_sync_at=last_sync_at,
            contacts_by_lifecyclestage=contacts_by_lifecyclestage,
            companies_by_industry=companies_by_industry,
            deals_by_stage=deals_by_stage,
            total_deal_amount=float(amounts_result[0]) if amounts_result else 0,
            won_deal_amount=float(amounts_result[1]) if amounts_result else 0,
            pipeline_value=float(amounts_result[2]) if amounts_result else 0
        )
