from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, hubspot, audits

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(hubspot.router, prefix="/hubspot", tags=["hubspot"])
api_router.include_router(audits.router, prefix="/audits", tags=["audits"])
