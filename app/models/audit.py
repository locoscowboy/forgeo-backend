from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.sql import func

from app.db_init import Base

class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_name = Column(String(255), nullable=True)
    company_address = Column(String(255), nullable=True)
    hubspot_company_id = Column(String(255), nullable=True)
    data = Column(JSON, nullable=True)
    status = Column(String(50), default="in_progress")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # Colonnes pour les statistiques d'audit
    contacts_total = Column(Integer, default=0)
    companies_total = Column(Integer, default=0)
    deals_total = Column(Integer, default=0)

    # Relations
    user = relationship("User", back_populates="audits")
    results = relationship("AuditResult", back_populates="audit", cascade="all, delete-orphan")
    detail_items = relationship("AuditDetailItem", back_populates="audit", cascade="all, delete-orphan")

    # Relation avec la synchronisation HubSpot

class AuditResult(Base):
    __tablename__ = "audit_results"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id"))
    category = Column(String)  # contact, company, deal
    criterion = Column(String)  # missing_firstname, no_website, etc.
    field_name = Column(String)  # Le nom exact du champ API HubSpot
    empty_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)

    # Relations
    audit = relationship("Audit", back_populates="results")
    detail_items = relationship("AuditDetailItem", back_populates="result", cascade="all, delete-orphan")

class AuditDetailItem(Base):
    __tablename__ = "audit_detail_items"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id"))
    result_id = Column(Integer, ForeignKey("audit_results.id"))
    category = Column(String)  # contact, company, deal
    criterion = Column(String)  # Pour faciliter le filtrage
    hubspot_id = Column(String)  # ID de l'objet dans HubSpot
    object_data = Column(JSON)  # Données pertinentes de l'objet pour affichage

    # Relations
    audit = relationship("Audit", back_populates="detail_items")
    result = relationship("AuditResult", back_populates="detail_items")
