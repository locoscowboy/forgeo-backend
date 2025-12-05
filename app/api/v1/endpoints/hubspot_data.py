"""
Endpoints API pour accéder aux données HubSpot synchronisées via Airbyte
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.hubspot_data_service import HubspotDataService
from app.schemas.hubspot_data import (
    HubspotContactBase,
    HubspotContactDetail,
    HubspotCompanyBase,
    HubspotCompanyDetail,
    HubspotDealBase,
    HubspotDealDetail,
    AvailableColumns,
    ContactFilters,
    CompanyFilters,
    DealFilters,
    PaginatedResponse,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS CONTACTS
# ═══════════════════════════════════════════════════════════════

@router.get("/contacts", response_model=PaginatedResponse[HubspotContactBase])
def get_contacts(
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    limit: int = Query(50, ge=1, le=500, description="Items per page (max 500)"),
    email: Optional[str] = Query(None, description="Filter by email (exact match)"),
    firstname: Optional[str] = Query(None, description="Filter by first name (partial match)"),
    lastname: Optional[str] = Query(None, description="Filter by last name (partial match)"),
    company: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    country: Optional[str] = Query(None, description="Filter by country"),
    lifecyclestage: Optional[str] = Query(None, description="Filter by lifecycle stage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer la liste des contacts HubSpot synchronisés pour l'utilisateur connecté.
    
    **Colonnes retournées par défaut (essentielles):**
    - email, firstname, lastname, phone, company
    - jobtitle, hs_linkedin_url, lifecyclestage, country, createdate
    
    **Filtres disponibles:**
    - Par email (exact)
    - Par nom/prénom (partiel)
    - Par entreprise, pays, lifecycle stage
    
    **Pagination:**
    - Page 1 = premiers résultats
    - Limite par défaut : 50 contacts/page (max 500)
    """
    service = HubspotDataService(db, user_id=current_user.id)
    
    # Vérifier que le schéma existe
    if not service.schema_exists():
        raise HTTPException(
            status_code=404,
            detail=f"No HubSpot data found for user {current_user.id}. Please connect your HubSpot account first."
        )
    
    # Construire les filtres
    filters = ContactFilters(
        email=email,
        firstname=firstname,
        lastname=lastname,
        company=company,
        country=country,
        lifecyclestage=lifecyclestage,
    )
    
    # Récupérer les contacts
    contacts, total = service.get_contacts(
        page=page,
        limit=limit,
        filters=filters
    )
    
    return PaginatedResponse(
        items=contacts,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit  # Arrondi supérieur
    )


@router.get("/contacts/{contact_id}", response_model=HubspotContactDetail)
def get_contact_by_id(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer les détails complets d'un contact spécifique par son HubSpot ID.
    
    **Retourne:**
    - Toutes les colonnes essentielles
    - Le JSON `properties` complet avec TOUTES les données HubSpot
    - Les métadonnées Airbyte (_airbyte_extracted_at, etc.)
    """
    service = HubspotDataService(db, user_id=current_user.id)
    
    if not service.schema_exists():
        raise HTTPException(
            status_code=404,
            detail=f"No HubSpot data found for user {current_user.id}."
        )
    
    contact = service.get_contact_by_id(contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=404,
            detail=f"Contact {contact_id} not found."
        )
    
    return contact


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS COMPANIES
# ═══════════════════════════════════════════════════════════════

@router.get("/companies", response_model=PaginatedResponse[HubspotCompanyBase])
def get_companies(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    domain: Optional[str] = Query(None, description="Filter by domain (partial match)"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer la liste des entreprises HubSpot synchronisées.
    
    **Colonnes retournées par défaut:**
    - name, domain, industry, numberofemployees
    - annualrevenue, country, website, createdate
    """
    service = HubspotDataService(db, user_id=current_user.id)
    
    if not service.schema_exists():
        raise HTTPException(
            status_code=404,
            detail=f"No HubSpot data found for user {current_user.id}."
        )
    
    filters = CompanyFilters(
        name=name,
        domain=domain,
        industry=industry,
        country=country,
    )
    
    companies, total = service.get_companies(
        page=page,
        limit=limit,
        filters=filters
    )
    
    return PaginatedResponse(
        items=companies,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/companies/{company_id}", response_model=HubspotCompanyDetail)
def get_company_by_id(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer les détails complets d'une entreprise spécifique.
    """
    service = HubspotDataService(db, user_id=current_user.id)
    
    if not service.schema_exists():
        raise HTTPException(
            status_code=404,
            detail=f"No HubSpot data found for user {current_user.id}."
        )
    
    company = service.get_company_by_id(company_id)
    
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company {company_id} not found."
        )
    
    return company


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS DEALS
# ═══════════════════════════════════════════════════════════════

@router.get("/deals", response_model=PaginatedResponse[HubspotDealBase])
def get_deals(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    dealname: Optional[str] = Query(None, description="Filter by deal name (partial match)"),
    dealstage: Optional[str] = Query(None, description="Filter by deal stage"),
    pipeline: Optional[str] = Query(None, description="Filter by pipeline"),
    min_amount: Optional[float] = Query(None, description="Minimum deal amount"),
    max_amount: Optional[float] = Query(None, description="Maximum deal amount"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer la liste des deals HubSpot synchronisés.
    
    **Colonnes retournées par défaut:**
    - dealname, amount, dealstage, pipeline
    - closedate, createdate
    """
    service = HubspotDataService(db, user_id=current_user.id)
    
    if not service.schema_exists():
        raise HTTPException(
            status_code=404,
            detail=f"No HubSpot data found for user {current_user.id}."
        )
    
    filters = DealFilters(
        dealname=dealname,
        dealstage=dealstage,
        pipeline=pipeline,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    
    deals, total = service.get_deals(
        page=page,
        limit=limit,
        filters=filters
    )
    
    return PaginatedResponse(
        items=deals,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/deals/{deal_id}", response_model=HubspotDealDetail)
def get_deal_by_id(
    deal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer les détails complets d'un deal spécifique.
    """
    service = HubspotDataService(db, user_id=current_user.id)
    
    if not service.schema_exists():
        raise HTTPException(
            status_code=404,
            detail=f"No HubSpot data found for user {current_user.id}."
        )
    
    deal = service.get_deal_by_id(deal_id)
    
    if not deal:
        raise HTTPException(
            status_code=404,
            detail=f"Deal {deal_id} not found."
        )
    
    return deal


# ═══════════════════════════════════════════════════════════════
# ENDPOINT MÉTADONNÉES - COLONNES DISPONIBLES
# ═══════════════════════════════════════════════════════════════

@router.get("/available-columns/{object_type}", response_model=AvailableColumns)
def get_available_columns(
    object_type: str = Path(..., regex="^(contacts|companies|deals)$", description="Type d'objet HubSpot"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer la liste de TOUTES les colonnes disponibles pour un type d'objet.
    
    **Usage:**
    - Frontend : Permet d'afficher le bouton "Ajouter une colonne"
    - L'utilisateur peut sélectionner les colonnes additionnelles à afficher dans le tableau
    
    **Retourne:**
    - Liste des colonnes avec nom, label, type, description
    - Indique si la colonne est "essentielle" (affichée par défaut) ou non
    
    **Types d'objets acceptés:**
    - `contacts`
    - `companies`
    - `deals`
    """
    service = HubspotDataService(db, user_id=current_user.id)
    
    if not service.schema_exists():
        raise HTTPException(
            status_code=404,
            detail=f"No HubSpot data found for user {current_user.id}."
        )
    
    return service.get_available_columns(object_type)
