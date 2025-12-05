"""Service pour gérer Airbyte via son API"""
import httpx
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.core.airbyte_config import (
    airbyte_settings,
    HUBSPOT_SOURCE_DEFINITION_ID,
    POSTGRES_DESTINATION_DEFINITION_ID
)
from app.models.airbyte import AirbyteConnection
from app.crud import airbyte as airbyte_crud
from app.schemas.airbyte import AirbyteConnectionCreate

logger = logging.getLogger(__name__)


class AirbyteService:
    """Service pour interagir avec l'API Airbyte"""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.base_url = airbyte_settings.AIRBYTE_API_URL
        self.auth = (airbyte_settings.AIRBYTE_EMAIL, airbyte_settings.AIRBYTE_PASSWORD)
        self.workspace_id = airbyte_settings.AIRBYTE_WORKSPACE_ID

    async def create_hubspot_source(self, refresh_token: str) -> Optional[str]:
        """Créer une source HubSpot dans Airbyte"""
        try:
            source_config = {
                "name": f"HubSpot - User {self.user_id}",
                "workspaceId": self.workspace_id,
                "definitionId": HUBSPOT_SOURCE_DEFINITION_ID,
                "configuration": {
                    "credentials": {
                        "credentials_title": "OAuth Credentials",
                        "client_id": airbyte_settings.HUBSPOT_CLIENT_ID,
                        "client_secret": airbyte_settings.HUBSPOT_CLIENT_SECRET,
                        "refresh_token": refresh_token
                    },
                    "start_date": "2020-01-01T00:00:00Z"
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/sources",
                    auth=self.auth,
                    json=source_config
                )

                if response.status_code != 200:
                    logger.error(f"Error creating HubSpot source: {response.status_code} - {response.text}")
                    return None

                source_id = response.json().get("sourceId")
                logger.info(f"Created HubSpot source: {source_id} for user {self.user_id}")
                return source_id

        except Exception as e:
            logger.error(f"Error creating HubSpot source: {e}")
            return None

    async def create_postgres_destination(self, schema_name: str) -> Optional[str]:
        """Créer une destination PostgreSQL dans Airbyte"""
        try:
            dest_config = {
                "name": f"PostgreSQL - User {self.user_id}",
                "workspaceId": self.workspace_id,
                "definitionId": POSTGRES_DESTINATION_DEFINITION_ID,
                "configuration": {
                    "host": airbyte_settings.POSTGRES_HOST,
                    "port": airbyte_settings.POSTGRES_PORT,
                    "database": airbyte_settings.POSTGRES_DB,
                    "username": airbyte_settings.POSTGRES_USER,
                    "password": airbyte_settings.POSTGRES_PASSWORD,
                    "schema": schema_name,
                    "ssl_mode": {"mode": "disable"},
                    "tunnel_method": {"tunnel_method": "NO_TUNNEL"}
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/destinations",
                    auth=self.auth,
                    json=dest_config
                )

                if response.status_code != 200:
                    logger.error(f"Error creating Postgres destination: {response.status_code} - {response.text}")
                    return None

                destination_id = response.json().get("destinationId")
                logger.info(f"Created Postgres destination: {destination_id} for user {self.user_id}")
                return destination_id

        except Exception as e:
            logger.error(f"Error creating Postgres destination: {e}")
            return None

    async def create_connection(self, source_id: str, destination_id: str, schema_name: str) -> Optional[str]:
        """Créer une connexion entre source et destination"""
        try:
            connection_config = {
                "name": f"HubSpot to PostgreSQL - User {self.user_id}",
                "sourceId": source_id,
                "destinationId": destination_id,
                "schedule": {
                    "scheduleType": "manual"
                },
                "namespaceDefinition": "custom_format",
                "namespaceFormat": schema_name,
                "nonBreakingSchemaUpdatesBehavior": "ignore"
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/connections",
                    auth=self.auth,
                    json=connection_config
                )

                if response.status_code != 200:
                    logger.error(f"Error creating connection: {response.status_code} - {response.text}")
                    return None

                connection_id = response.json().get("connectionId")
                logger.info(f"Created connection: {connection_id} for user {self.user_id}")
                return connection_id

        except Exception as e:
            logger.error(f"Error creating connection: {e}")
            return None

    async def trigger_sync(self, connection_id: str) -> Optional[str]:
        """Déclencher une synchronisation manuelle"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/jobs",
                    auth=self.auth,
                    json={
                        "connectionId": connection_id,
                        "jobType": "sync"
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Error triggering sync: {response.status_code} - {response.text}")
                    return None

                job_id = response.json().get("jobId")
                logger.info(f"Triggered sync job: {job_id} for connection {connection_id}")

                airbyte_crud.update_sync_status(self.db, self.user_id, "running", job_id)
                return job_id

        except Exception as e:
            logger.error(f"Error triggering sync: {e}")
            return None

    async def get_sync_status(self, job_id: str) -> Optional[Dict]:
        """Récupérer le statut d'une synchronisation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/jobs/{job_id}",
                    auth=self.auth
                )

                if response.status_code != 200:
                    logger.error(f"Error fetching sync status: {response.status_code}")
                    return None

                return response.json()

        except Exception as e:
            logger.error(f"Error fetching sync status: {e}")
            return None

    async def setup_user_connection(self, refresh_token: str) -> Optional[AirbyteConnection]:
        """Configuration complète Airbyte pour un nouvel utilisateur"""
        try:
            existing_connection = airbyte_crud.get_connection_by_user_id(self.db, self.user_id)
            if existing_connection:
                logger.info(f"User {self.user_id} already has an Airbyte connection")
                return existing_connection

            schema_name = f"user_{self.user_id}_hubspot"

            logger.info(f"Creating HubSpot source for user {self.user_id}...")
            source_id = await self.create_hubspot_source(refresh_token)
            if not source_id:
                raise ValueError("Failed to create HubSpot source")

            logger.info(f"Creating PostgreSQL destination for user {self.user_id}...")
            destination_id = await self.create_postgres_destination(schema_name)
            if not destination_id:
                raise ValueError("Failed to create PostgreSQL destination")

            logger.info(f"Creating connection for user {self.user_id}...")
            connection_id = await self.create_connection(source_id, destination_id, schema_name)
            if not connection_id:
                raise ValueError("Failed to create connection")

            connection_data = AirbyteConnectionCreate(
                user_id=self.user_id,
                workspace_id=self.workspace_id,
                source_id=source_id,
                destination_id=destination_id,
                connection_id=connection_id,
                schema_name=schema_name,
                status="active"
            )

            airbyte_conn = airbyte_crud.create_connection(self.db, connection_data)
            logger.info(f"Saved Airbyte connection to database for user {self.user_id}")

            logger.info(f"Triggering initial sync for user {self.user_id}...")
            job_id = await self.trigger_sync(connection_id)

            if job_id:
                logger.info(f"Initial sync started with job_id: {job_id}")

            return airbyte_conn

        except Exception as e:
            logger.error(f"Error setting up user connection: {e}")
            return None

    async def delete_user_connection(self) -> bool:
        """Supprimer toutes les ressources Airbyte d'un utilisateur"""
        try:
            connection = airbyte_crud.get_connection_by_user_id(self.db, self.user_id)
            if not connection:
                logger.warning(f"No Airbyte connection found for user {self.user_id}")
                return True

            async with httpx.AsyncClient(timeout=30.0) as client:
                if connection.connection_id:
                    await client.delete(f"{self.base_url}/connections/{connection.connection_id}", auth=self.auth)
                    logger.info(f"Deleted connection {connection.connection_id}")

                if connection.source_id:
                    await client.delete(f"{self.base_url}/sources/{connection.source_id}", auth=self.auth)
                    logger.info(f"Deleted source {connection.source_id}")

                if connection.destination_id:
                    await client.delete(f"{self.base_url}/destinations/{connection.destination_id}", auth=self.auth)
                    logger.info(f"Deleted destination {connection.destination_id}")

            airbyte_crud.delete_connection(self.db, self.user_id)
            logger.info(f"Deleted Airbyte connection from database for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user connection: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODES DE SYNCHRONISATION
    # ═══════════════════════════════════════════════════════════════

    async def trigger_manual_sync(self) -> Optional[dict]:
        """
        Déclenche une synchronisation manuelle pour la connexion de l'utilisateur
        
        Returns:
            dict avec job_id, status, etc. ou None si erreur
        """
        try:
            # Récupérer la connexion depuis la DB
            connection = airbyte_crud.get_connection_by_user_id(self.db, self.user_id)
            
            if not connection or not connection.connection_id:
                logger.error(f"No Airbyte connection found for user {self.user_id}")
                return None
            
            connection_id = connection.connection_id

            # Déclencher le job via l'API Airbyte
            url = f"{airbyte_settings.AIRBYTE_API_URL}/jobs"
            payload = {
                "connectionId": connection_id,
                "jobType": "sync"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, auth=self.auth, timeout=30.0)

                if response.status_code == 200:
                    job_data = response.json()
                    logger.info(f"Sync triggered for user {self.user_id}: job_id={job_data.get('jobId')}")
                    return {
                        "job_id": str(job_data.get("jobId")),
                        "connection_id": connection_id,
                        "status": job_data.get("status", "pending"),
                        "created_at": datetime.utcnow()
                    }
                else:
                    logger.error(f"Failed to trigger sync: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error triggering sync for user {self.user_id}: {str(e)}")
            return None

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Récupère le statut d'un job de synchronisation
        
        Args:
            job_id: ID du job Airbyte
            
        Returns:
            dict avec les détails du job ou None si erreur
        """
        try:
            url = f"{airbyte_settings.AIRBYTE_API_URL}/jobs/{job_id}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, auth=self.auth, timeout=30.0)

                if response.status_code == 200:
                    job_data = response.json()
                    return {
                        "job_id": str(job_data.get("jobId")),
                        "connection_id": job_data.get("connectionId"),
                        "status": job_data.get("status"),
                        "rows_synced": job_data.get("rowsSynced", 0),
                        "bytes_synced": job_data.get("bytesSynced", 0),
                        "duration": job_data.get("duration"),
                        "created_at": job_data.get("createdAt"),
                        "started_at": job_data.get("startedAt"),
                        "completed_at": job_data.get("updatedAt"),
                        "error_message": job_data.get("failureReason")
                    }
                else:
                    logger.error(f"Failed to get job status: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting job status {job_id}: {str(e)}")
            return None

    async def get_sync_history(self, limit: int = 10) -> Optional[dict]:
        """
        Récupère l'historique des synchronisations pour l'utilisateur
        
        Args:
            limit: Nombre de jobs à récupérer (par défaut 10)
            
        Returns:
            dict avec la liste des jobs et stats ou None si erreur
        """
        try:
            # Récupérer la connexion depuis la DB
            connection = airbyte_crud.get_connection_by_user_id(self.db, self.user_id)
            
            if not connection or not connection.connection_id:
                logger.error(f"No Airbyte connection found for user {self.user_id}")
                return None
            
            connection_id = connection.connection_id

            # Récupérer l'historique via l'API Airbyte
            url = f"{airbyte_settings.AIRBYTE_API_URL}/jobs"
            params = {
                "connectionId": connection_id,
                "limit": limit,
                "orderBy": "createdAt|DESC"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, auth=self.auth, params=params, timeout=30.0)

                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("data", [])

                    # Formater les jobs
                    formatted_jobs = []
                    last_successful_sync = None

                    for job in jobs:
                        job_item = {
                            "job_id": str(job.get("jobId")),
                            "status": job.get("status"),
                            "rows_synced": job.get("rowsSynced", 0),
                            "duration": job.get("duration"),
                            "started_at": job.get("startedAt"),
                            "completed_at": job.get("updatedAt")
                        }
                        formatted_jobs.append(job_item)

                        # Trouver le dernier sync réussi
                        if job.get("status") == "succeeded" and not last_successful_sync:
                            last_successful_sync = job.get("updatedAt")

                    return {
                        "connection_id": connection_id,
                        "total_jobs": len(formatted_jobs),
                        "jobs": formatted_jobs,
                        "last_successful_sync": last_successful_sync
                    }
                else:
                    logger.error(f"Failed to get sync history: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting sync history for user {self.user_id}: {str(e)}")
            return None

    async def get_connection_info(self) -> Optional[dict]:
        """
        Récupère les informations de la connexion Airbyte de l'utilisateur
        
        Returns:
            dict avec connection_id, source_id, destination_id, status
        """
        try:
            # Récupérer la connexion depuis la DB
            connection = airbyte_crud.get_connection_by_user_id(self.db, self.user_id)
            
            if not connection:
                return None
            
            connection_id = connection.connection_id
            source_id = connection.source_id
            destination_id = connection.destination_id

            # Récupérer le statut via l'API Airbyte
            url = f"{airbyte_settings.AIRBYTE_API_URL}/connections/{connection_id}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, auth=self.auth, timeout=30.0)

                if response.status_code == 200:
                    conn_data = response.json()
                    return {
                        "connection_id": connection_id,
                        "source_id": source_id,
                        "destination_id": destination_id,
                        "status": conn_data.get("status", "unknown"),
                        "name": conn_data.get("name", f"User {self.user_id} HubSpot Sync")
                    }
                else:
                    # Si l'API échoue, retourner les infos de base
                    return {
                        "connection_id": connection_id,
                        "source_id": source_id,
                        "destination_id": destination_id,
                        "status": "unknown",
                        "name": f"User {self.user_id} HubSpot Sync"
                    }

        except Exception as e:
            logger.error(f"Error getting connection info for user {self.user_id}: {str(e)}")
            return None
