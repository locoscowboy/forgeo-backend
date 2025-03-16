from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db_init import Base

class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_completed = Column(DateTime, nullable=True)
    status = Column(String, default="in_progress")  # in_progress, completed, failed

    # Statistiques globales
    contacts_total = Column(Integer, default=0)
    companies_total = Column(Integer, default=0)
    deals_total = Column(Integer, default=0)

    # Relations
    user = relationship("User", back_populates="audits")
    results = relationship("AuditResult", back_populates="audit", cascade="all, delete-orphan")
    detail_items = relationship("AuditDetailItem", back_populates="audit", cascade="all, delete-orphan")

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
