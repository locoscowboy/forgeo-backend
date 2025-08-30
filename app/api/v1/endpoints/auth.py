from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.google_oauth import google_oauth_service
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from google.auth.transport import requests

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.user import authenticate, create, get_by_email
from app.schemas.token import Token
from app.schemas.user import UserCreate, User as UserSchema

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
def login_access_token(
   request: Request, db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/signup", response_model=Token)
@limiter.limit("3/hour")
def create_user_signup(
    request: Request,
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Create new user account and return access token
    """
    # Check if user already exists
    user = get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system"
        )
    
    # Create new user
    user = create(db, obj_in=user_in)
    
    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.get("/google/login")
async def google_login():
    """Initiate Google OAuth login"""
    authorization_url = google_oauth_service.get_authorization_url()
    return {"authorization_url": authorization_url}

@router.get("/google/callback")
async def google_callback(
    code: str,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    try:
        # Exchange code for tokens
        token_data = await google_oauth_service.exchange_code_for_token(code)
        if not token_data:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Get user info from Google
        user_info = await google_oauth_service.get_user_info(token_data["access_token"])
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user information")
        
        # Check if user exists
        user = get_by_email(db, email=user_info["email"])
        
        if not user:
            # Create new user
            user_create = UserCreate(
                email=user_info["email"],
                full_name=user_info.get("name", ""),
                password="google_oauth_user"
            )
            user = create(db, obj_in=user_create)
        
        # Generate JWT token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            user.id, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        frontend_url = f"https://app.forgeo.io/auth/success?token={access_token}"
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.post("/google/token")
async def google_token_auth(
    token: str,
    db: Session = Depends(get_db)
):
    """Authenticate user with Google ID token"""
    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        # Get user info from token
        email = idinfo['email']
        name = idinfo.get('name', '')
        
        # Check if user exists
        user = get_by_email(db, email=email)
        
        if not user:
            # Create new user
            user_create = UserCreate(
                email=email,
                full_name=name,
                password="google_oauth_user"
            )
            user = create(db, obj_in=user_create)
        
        # Generate JWT token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            user.id, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")
