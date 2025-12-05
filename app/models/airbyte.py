"""Modèle pour stocker les connexions Airbyte"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db_init import Base  # ✅ CORRECTION : Utiliser app.db_init au lieu de app.db.base_class


class AirbyteConnection(Base):
    """Mapping entre users et connexions Airbyte"""
    __tablename__ = "airbyte_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    
    # IDs Airbyte
    workspace_id = Column(String, nullable=False)
    source_id = Column(String, nullable=False, unique=True)
    destination_id = Column(String, nullable=False, unique=True)
    connection_id = Column(String, nullable=False, unique=True)
    
    # Configuration
    schema_name = Column(String, nullable=False)  # user_123_hubspot
    status = Column(String, default="active")  # active, paused, error
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String, nullable=True)  # succeeded, failed, running
    
    # Relations
    user = relationship("User", back_populates="airbyte_connection")
