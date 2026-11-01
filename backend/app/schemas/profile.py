from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


class ProfileCreate(BaseModel):
    slug: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    bio: Optional[str] = None


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    bio: Optional[str] = None
    slug: Optional[str] = Field(default=None, min_length=3, max_length=64)


class AnswerItem(BaseModel):
    question_id: str
    value: Any
    hidden: Optional[bool] = False


class AnswersUpdate(BaseModel):
    answers: List[AnswerItem]


class DesignUpdate(BaseModel):
    preset: Optional[str] = None
    bg_color: Optional[str] = None
    text_color: Optional[str] = None
    heading_color: Optional[str] = None
    accent_color: Optional[str] = None
    card_color: Optional[str] = None
    radius: Optional[str] = None
    bg_image_url: Optional[str] = None


class ProfileOut(BaseModel):
    id: UUID
    slug: str
    display_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DesignOut(BaseModel):
    preset: str
    bg_color: str
    text_color: str
    heading_color: str
    accent_color: str
    card_color: str
    radius: str
    bg_image_url: Optional[str]

    class Config:
        from_attributes = True


class PublicProfileResponse(BaseModel):
    profile: ProfileOut
    design: DesignOut
    answers: Dict[str, Any]
    categories: List[Dict[str, Any]]


class EditInitResponse(BaseModel):
    profile: ProfileOut
    edit_token: str
    edit_url: str


class EditProfileResponse(BaseModel):
    profile: ProfileOut
    design: DesignOut
    categories: List[Dict[str, Any]]
    answers: Dict[str, Any]
