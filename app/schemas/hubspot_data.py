"""
Schemas Pydantic pour les données HubSpot synchronisées via Airbyte
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field

# TypeVar pour la pagination générique
T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════
# 1. MODÈLES DE BASE POUR LES OBJETS HUBSPOT
# ═══════════════════════════════════════════════════════════════

class HubspotContactBase(BaseModel):
    """Colonnes essentielles d'un contact HubSpot"""
    id: str
    email: Optional[str] = None
    firstname: Optional[str] = Field(None, alias="properties_firstname")
    lastname: Optional[str] = Field(None, alias="properties_lastname")
    phone: Optional[str] = Field(None, alias="properties_phone")
    company: Optional[str] = Field(None, alias="properties_company")
    jobtitle: Optional[str] = Field(None, alias="properties_jobtitle")
    hs_linkedin_url: Optional[str] = Field(None, alias="properties_hs_linkedin_url")
    lifecyclestage: Optional[str] = Field(None, alias="properties_lifecyclestage")
    country: Optional[str] = Field(None, alias="properties_country")
    city: Optional[str] = Field(None, alias="properties_city")
    createdate: Optional[datetime] = Field(None, alias="properties_createdate")
    hubspot_owner_id: Optional[str] = Field(None, alias="properties_hubspot_owner_id")
    _airbyte_extracted_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class HubspotContactDetail(HubspotContactBase):
    """Contact avec toutes les données (JSON properties inclus)"""
    properties: Optional[Dict[str, Any]] = None  # JSON complet
    archived: Optional[bool] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class HubspotCompanyBase(BaseModel):
    """Colonnes essentielles d'une company HubSpot"""
    id: str
    name: Optional[str] = Field(None, alias="properties_name")
    domain: Optional[str] = Field(None, alias="properties_domain")
    industry: Optional[str] = Field(None, alias="properties_industry")
    numberofemployees: Optional[int] = Field(None, alias="properties_numberofemployees")
    annualrevenue: Optional[float] = Field(None, alias="properties_annualrevenue")
    country: Optional[str] = Field(None, alias="properties_country")
    city: Optional[str] = Field(None, alias="properties_city")
    phone: Optional[str] = Field(None, alias="properties_phone")
    website: Optional[str] = Field(None, alias="properties_website")
    linkedin_company_page: Optional[str] = Field(None, alias="properties_linkedin_company_page")
    createdate: Optional[datetime] = Field(None, alias="properties_createdate")
    hubspot_owner_id: Optional[str] = Field(None, alias="properties_hubspot_owner_id")
    _airbyte_extracted_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class HubspotCompanyDetail(HubspotCompanyBase):
    """Company avec toutes les données"""
    properties: Optional[Dict[str, Any]] = None
    archived: Optional[bool] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class HubspotDealBase(BaseModel):
    """Colonnes essentielles d'un deal HubSpot"""
    id: str
    dealname: Optional[str] = Field(None, alias="properties_dealname")
    amount: Optional[float] = Field(None, alias="properties_amount")
    dealstage: Optional[str] = Field(None, alias="properties_dealstage")
    pipeline: Optional[str] = Field(None, alias="properties_pipeline")
    closedate: Optional[datetime] = Field(None, alias="properties_closedate")
    createdate: Optional[datetime] = Field(None, alias="properties_createdate")
    hubspot_owner_id: Optional[str] = Field(None, alias="properties_hubspot_owner_id")
    hs_is_closed_won: Optional[bool] = Field(None, alias="properties_hs_is_closed_won")
    hs_is_closed_lost: Optional[bool] = Field(None, alias="properties_hs_is_closed_lost")
    hs_forecast_amount: Optional[float] = Field(None, alias="properties_hs_forecast_amount")
    _airbyte_extracted_at: datetime

    class Config:
        populate_by_name = True
        from_attributes = True


class HubspotDealDetail(HubspotDealBase):
    """Deal avec toutes les données"""
    properties: Optional[Dict[str, Any]] = None
    archived: Optional[bool] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    contacts: Optional[List[str]] = None  # IDs des contacts associés
    companies: Optional[List[str]] = None  # IDs des companies associées


# ═══════════════════════════════════════════════════════════════
# 2. MÉTADONNÉES DES COLONNES
# ═══════════════════════════════════════════════════════════════

class ColumnMetadata(BaseModel):
    """Métadonnées d'une colonne disponible"""
    key: str  # Nom de la colonne en DB (ex: "properties_email")
    label: str  # Nom affiché (ex: "Email")
    type: str  # Type de données (string, number, datetime, boolean)
    category: str = "standard"  # standard, custom, system
    description: Optional[str] = None
    is_searchable: bool = True
    is_sortable: bool = True


class AvailableColumns(BaseModel):
    """Liste de toutes les colonnes disponibles pour un objet"""
    object_type: str  # contacts, companies, deals
    default_columns: List[ColumnMetadata]  # Colonnes affichées par défaut
    available_columns: List[ColumnMetadata]  # Toutes les autres colonnes
    custom_columns: List[ColumnMetadata] = []  # Colonnes custom HubSpot
    total_columns: int


# ═══════════════════════════════════════════════════════════════
# 3. PRÉFÉRENCES UTILISATEUR POUR LES COLONNES
# ═══════════════════════════════════════════════════════════════

class ColumnPreferences(BaseModel):
    """Préférences de colonnes d'un utilisateur"""
    object_type: str  # contacts, companies, deals
    visible_columns: List[str]  # Liste des clés de colonnes visibles
    column_order: Optional[List[str]] = None  # Ordre des colonnes
    column_widths: Optional[Dict[str, int]] = None  # Largeurs personnalisées


class ColumnPreferencesResponse(ColumnPreferences):
    """Réponse avec les préférences sauvegardées"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# 4. RÉPONSES PAGINÉES
# ═══════════════════════════════════════════════════════════════

class PaginatedResponse(BaseModel, Generic[T]):
    """Réponse paginée générique"""
    total: int
    page: int
    limit: int
    pages: int
    items: List[T]


class ContactsListResponse(BaseModel):
    """Réponse de la liste des contacts"""
    total: int
    page: int
    limit: int
    pages: int
    items: List[HubspotContactBase]


class CompaniesListResponse(BaseModel):
    """Réponse de la liste des companies"""
    total: int
    page: int
    limit: int
    pages: int
    items: List[HubspotCompanyBase]


class DealsListResponse(BaseModel):
    """Réponse de la liste des deals"""
    total: int
    page: int
    limit: int
    pages: int
    items: List[HubspotDealBase]


# ═══════════════════════════════════════════════════════════════
# 5. FILTRES ET PARAMÈTRES DE RECHERCHE
# ═══════════════════════════════════════════════════════════════

class ContactFilters(BaseModel):
    """Filtres pour la recherche de contacts"""
    search: Optional[str] = None  # Recherche dans email, nom, prénom
    lifecyclestage: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    hubspot_owner_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class CompanyFilters(BaseModel):
    """Filtres pour la recherche de companies"""
    search: Optional[str] = None  # Recherche dans name, domain
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    hubspot_owner_id: Optional[str] = None
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class DealFilters(BaseModel):
    """Filtres pour la recherche de deals"""
    search: Optional[str] = None  # Recherche dans dealname
    dealstage: Optional[str] = None
    pipeline: Optional[str] = None
    hubspot_owner_id: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_closed: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════
# 6. STATISTIQUES
# ═══════════════════════════════════════════════════════════════

class HubspotStats(BaseModel):
    """Statistiques globales HubSpot"""
    total_contacts: int
    total_companies: int
    total_deals: int
    last_sync_at: Optional[datetime] = None
    
    # Stats par catégorie
    contacts_by_lifecyclestage: Dict[str, int] = {}
    companies_by_industry: Dict[str, int] = {}
    deals_by_stage: Dict[str, int] = {}
    
    # Montants
    total_deal_amount: float = 0
    won_deal_amount: float = 0
    pipeline_value: float = 0


# ═══════════════════════════════════════════════════════════════
# 7. RÉPONSES D'ERREUR ET SUCCESS
# ═══════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Réponse de succès générique"""
    success: bool = True
    message: str
    data: Optional[Any] = None
