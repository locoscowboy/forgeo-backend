from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db_init import Base

class HubspotDataSync(Base):
    """Suivi des synchronisations HubSpot"""
    __tablename__ = "hubspot_data_sync"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="in_progress")  # in_progress, completed, failed 

    # Statistiques de synchronisation
    total_contacts = Column(Integer, default=0)
    total_companies = Column(Integer, default=0)
    total_deals = Column(Integer, default=0)

    # Relations
    contacts = relationship("HubspotContact", back_populates="sync", cascade="all, delete-orphan")
    companies = relationship("HubspotCompany", back_populates="sync", cascade="all, delete-orphan")
    deals = relationship("HubspotDeal", back_populates="sync", cascade="all, delete-orphan")

    # Audit basé sur cette synchronisation
    audits = relationship("Audit", back_populates="data_sync")

class HubspotContact(Base):
    """Données de contact HubSpot"""
    __tablename__ = "hubspot_contact"

    id = Column(Integer, primary_key=True, index=True)
    sync_id = Column(Integer, ForeignKey("hubspot_data_sync.id"), index=True)        
    hubspot_id = Column(String, index=True)
    properties = Column(JSON)  # Toutes les propriétés du contact

    # Propriétés fréquemment utilisées (pour recherche et index)
    email = Column(String, index=True, nullable=True)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, nullable=True)

    # Relations
    sync = relationship("HubspotDataSync", back_populates="contacts")

class HubspotCompany(Base):
    """Données d'entreprise HubSpot"""
    __tablename__ = "hubspot_company"

    id = Column(Integer, primary_key=True, index=True)
    sync_id = Column(Integer, ForeignKey("hubspot_data_sync.id"), index=True)        
    hubspot_id = Column(String, index=True)
    properties = Column(JSON)  # Toutes les propriétés de l'entreprise

    # Propriétés fréquemment utilisées
    name = Column(String, nullable=True)
    domain = Column(String, nullable=True, index=True)

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, nullable=True)

    # Relations
    sync = relationship("HubspotDataSync", back_populates="companies")

class HubspotDeal(Base):
    """Données d'affaire HubSpot"""
    __tablename__ = "hubspot_deal"

    id = Column(Integer, primary_key=True, index=True)
    sync_id = Column(Integer, ForeignKey("hubspot_data_sync.id"), index=True)        
    hubspot_id = Column(String, index=True)
    properties = Column(JSON)  # Toutes les propriétés de l'affaire

    # Propriétés fréquemment utilisées
    deal_name = Column(String, nullable=True)
    amount = Column(String, nullable=True)
    pipeline = Column(String, nullable=True)

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, nullable=True)

    # Relations
    sync = relationship("HubspotDataSync", back_populates="deals")
