from typing import Optional
import re
from pydantic import BaseModel, EmailStr, validator

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_admin: bool = False
    full_name: Optional[str] = None

class UserCreate(UserBase):
    email: EmailStr
    password: str
    
    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        if not re.search(r'[a-z]', v):
            raise ValueError('Le mot de passe doit contenir au moins une minuscule')
        if not re.search(r'\d', v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Le mot de passe doit contenir au moins un caractère spécial')
        return v

class UserUpdate(UserBase):
    password: Optional[str] = None
    
    @validator('password')
    def validate_password_strength(cls, v):
        if v is not None:  # Only validate if password is being updated
            if len(v) < 8:
                raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
            if not re.search(r'[A-Z]', v):
                raise ValueError('Le mot de passe doit contenir au moins une majuscule')
            if not re.search(r'[a-z]', v):
                raise ValueError('Le mot de passe doit contenir au moins une minuscule')
            if not re.search(r'\d', v):
                raise ValueError('Le mot de passe doit contenir au moins un chiffre')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
                raise ValueError('Le mot de passe doit contenir au moins un caractère spécial')
        return v

class UserInDBBase(UserBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str
