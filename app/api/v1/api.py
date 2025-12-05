from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users
from app.api.v1.endpoints import hubspot
from app.api.v1.endpoints import airbyte  # ✅ AJOUT Phase 3

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(hubspot.router, prefix="/hubspot", tags=["hubspot"])
api_router.include_router(airbyte.router, prefix="/airbyte", tags=["airbyte"])  # ✅ AJOUT Phase 3

# Import des endpoints HubSpot Data
from app.api.v1.endpoints import hubspot_data

# Inclusion du router
api_router.include_router(
    hubspot_data.router,
    prefix="/hubspot-data",
    tags=["HubSpot Data"]
)

# Import des endpoints Sync
from app.api.v1.endpoints import sync

# Inclusion du router Sync
api_router.include_router(
    sync.router,
    prefix="/sync",
    tags=["Synchronization"]
)
