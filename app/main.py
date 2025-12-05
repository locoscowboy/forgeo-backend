from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.api import api_router
from app.db_init import init_db
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        print("🚀 Démarrage de l'application...")
        print("✅ Application démarrée")
    except Exception as e:
        print(f"❌ Erreur dans lifespan startup: {e}")
        import traceback
        traceback.print_exc()

    yield

    # Shutdown
    try:
        print("🛑 Application arrêtée")
    except Exception as e:
        print(f"❌ Erreur dans lifespan shutdown: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
    lifespan=lifespan
)

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://app.forgeo.io", "https://forgeo-frontend.vercel.app"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    )

# Initialize database tables
init_db()

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    """
    Point d'entrée racine de l'API
    """
    return {
        "message": "Welcome to Forgeo API",
        "docs": "/docs",
        "redoc": "/redoc",
        "api": settings.API_V1_STR
    }
