"""CRUD pour gérer les connexions Airbyte"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.models.airbyte import AirbyteConnection
from app.schemas.airbyte import AirbyteConnectionCreate


def get_connection_by_user_id(db: Session, user_id: int) -> Optional[AirbyteConnection]:
    """Récupérer la connexion Airbyte d'un utilisateur"""
    return db.query(AirbyteConnection).filter(
        AirbyteConnection.user_id == user_id
    ).first()


def get_connection_by_connection_id(db: Session, connection_id: str) -> Optional[AirbyteConnection]:
    """Récupérer une connexion Airbyte par son connection_id"""
    return db.query(AirbyteConnection).filter(
        AirbyteConnection.connection_id == connection_id
    ).first()


def create_connection(db: Session, connection: AirbyteConnectionCreate) -> AirbyteConnection:
    """Créer une nouvelle connexion Airbyte"""
    db_connection = AirbyteConnection(**connection.dict())
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    return db_connection


def update_last_sync(
    db: Session,
    connection_id: str,
    status: str,
    sync_time: Optional[datetime] = None
) -> Optional[AirbyteConnection]:
    """Mettre à jour le statut du dernier sync"""
    db_connection = get_connection_by_connection_id(db, connection_id)
    if db_connection:
        db_connection.last_sync_at = sync_time or datetime.utcnow()
        db_connection.last_sync_status = status
        db.commit()
        db.refresh(db_connection)
    return db_connection


def update_status(
    db: Session,
    user_id: int,
    status: str
) -> Optional[AirbyteConnection]:
    """Mettre à jour le statut d'une connexion"""
    db_connection = get_connection_by_user_id(db, user_id)
    if db_connection:
        db_connection.status = status
        db.commit()
        db.refresh(db_connection)
    return db_connection


def delete_connection(db: Session, user_id: int) -> bool:
    """Supprimer une connexion Airbyte"""
    db_connection = get_connection_by_user_id(db, user_id)
    if db_connection:
        db.delete(db_connection)
        db.commit()
        return True
    return False


def update_sync_status(
    db: Session,
    user_id: int,
    status: str,
    job_id: Optional[str] = None
) -> Optional[AirbyteConnection]:
    """Met à jour le statut de synchronisation"""
    connection = get_connection_by_user_id(db, user_id)
    if connection:
        connection.last_sync_status = status
        connection.last_sync_at = datetime.utcnow()
        db.commit()
        db.refresh(connection)
    return connection


def delete_connection(db: Session, user_id: int) -> bool:
    """Supprime une connexion Airbyte"""
    connection = get_connection_by_user_id(db, user_id)
    if connection:
        db.delete(connection)
        db.commit()
        return True
    return False
