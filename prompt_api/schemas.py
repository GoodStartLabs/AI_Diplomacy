from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class PromptType(str, Enum):
    ORDER = "Order"
    SYSTEM = "System"
    NEGOTIATION = "Negotiation"


# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Game schemas
class GameBase(BaseModel):
    name: str


class GameCreate(GameBase):
    pass


class GameResponse(GameBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Prompt schemas
class PromptBase(BaseModel):
    prompt_type: PromptType
    content: str


class PromptCreate(PromptBase):
    game_id: int


class PromptResponse(PromptBase):
    id: int
    game_id: int
    user_id: Optional[int] = None
    version: int
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str
