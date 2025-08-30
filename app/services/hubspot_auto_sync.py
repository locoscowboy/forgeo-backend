import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db_init import SessionLocal
from app.crud.hubspot import get_active_token
from app.services.hubspot_sync import HubspotSyncService
from app.models.user import User

logger = logging.getLogger(__name__)

class HubspotAutoSyncService:
    """Service pour gérer la synchronisation automatique HubSpot"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
    
    async def start_scheduler(self) -> None:
        """Démarre le scheduler de synchronisation automatique"""
        if not settings.HUBSPOT_AUTO_SYNC_ENABLED:
            logger.info("HubSpot auto-sync is disabled")
            return
        
        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            self.scheduler = AsyncIOScheduler()
            
            # Ajouter la tâche de synchronisation
            self.scheduler.add_job(
                func=self.sync_all_users,
                trigger=IntervalTrigger(hours=settings.HUBSPOT_SYNC_INTERVAL_HOURS),
                id="hubspot_auto_sync",
                name="HubSpot Auto Sync",
                replace_existing=True,
                next_run_time=datetime.now() + timedelta(minutes=settings.HUBSPOT_SYNC_STARTUP_DELAY_MINUTES)
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"HubSpot auto-sync started - every {settings.HUBSPOT_SYNC_INTERVAL_HOURS} hours")
            logger.info(f"First sync scheduled in {settings.HUBSPOT_SYNC_STARTUP_DELAY_MINUTES} minutes")
            
        except Exception as e:
            logger.error(f"Failed to start HubSpot auto-sync scheduler: {e}")
            self.is_running = False
    
    async def stop_scheduler(self) -> None:
        """Arrête le scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("HubSpot auto-sync scheduler stopped")
    
    async def sync_all_users(self) -> None:
        """Synchronise tous les utilisateurs ayant des tokens HubSpot actifs"""
        logger.info("Starting automatic HubSpot sync for all users")
        
        db: Session = SessionLocal()
        try:
            # Récupérer tous les utilisateurs avec tokens HubSpot actifs
            users_with_tokens = db.query(User).join(
                User.hubspot_tokens
            ).filter(
                User.hubspot_tokens.any(is_active=True)
            ).all()
            
            if not users_with_tokens:
                logger.info("No users with active HubSpot tokens found")
                return
            
            sync_results = []
            for user in users_with_tokens:
                try:
                    # Vérifier que le token est encore valide
                    token = get_active_token(db, user.id)
                    if not token:
                        logger.warning(f"No active token for user {user.id}")
                        continue
                    
                    # Lancer la synchronisation
                    sync_service = HubspotSyncService(db, user.id)
                    sync_result = await sync_service.run_sync()
                    
                    if sync_result:
                        sync_results.append({
                            "user_id": user.id,
                            "sync_id": sync_result.id,
                            "status": sync_result.status,
                            "contacts": sync_result.total_contacts,
                            "companies": sync_result.total_companies,
                            "deals": sync_result.total_deals
                        })
                        logger.info(f"Sync completed for user {user.id}: {sync_result.total_contacts} contacts, {sync_result.total_companies} companies, {sync_result.total_deals} deals")
                    else:
                        logger.error(f"Sync failed for user {user.id}")
                        sync_results.append({
                            "user_id": user.id,
                            "status": "failed"
                        })
                
                except Exception as e:
                    logger.error(f"Error syncing user {user.id}: {e}")
                    sync_results.append({
                        "user_id": user.id,
                        "status": "error",
                        "error": str(e)
                    })
            
            logger.info(f"Auto-sync completed for {len(sync_results)} users")
            
        except Exception as e:
            logger.error(f"Error in auto-sync process: {e}")
        finally:
            db.close()
    
    def get_status(self) -> dict:
        """Retourne le statut du scheduler"""
        if not self.scheduler:
            return {
                "enabled": settings.HUBSPOT_AUTO_SYNC_ENABLED,
                "running": False,
                "next_run": None
            }
        
        job = self.scheduler.get_job("hubspot_auto_sync")
        return {
            "enabled": settings.HUBSPOT_AUTO_SYNC_ENABLED,
            "running": self.is_running and self.scheduler.running,
            "interval_hours": settings.HUBSPOT_SYNC_INTERVAL_HOURS,
            "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None
        }

# Instance globale
auto_sync_service = HubspotAutoSyncService()
