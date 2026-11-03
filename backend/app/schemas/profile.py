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

    # Extended design settings (kept in sync with the DesignSettings model).
    bg_type: Optional[str] = None
    bg_gradient: Optional[str] = None
    bg_position: Optional[str] = None
    bg_size: Optional[str] = None
    bg_overlay_opacity: Optional[str] = None
    bg_overlay_color: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[str] = None
    heading_size: Optional[str] = None
    line_height: Optional[str] = None
    card_opacity: Optional[str] = None
    card_blur: Optional[str] = None
    card_border_width: Optional[str] = None
    card_border_color: Optional[str] = None
    card_shadow: Optional[str] = None
    button_color: Optional[str] = None
    link_color: Optional[str] = None
    icon_color: Optional[str] = None
    avatar_style: Optional[str] = None
    avatar_size: Optional[str] = None
    profile_align: Optional[str] = None
    content_width: Optional[str] = None
    gap: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


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
    preset: Optional[str] = "dark"
    bg_color: Optional[str] = "#0f1026"
    text_color: Optional[str] = "#f4f4f9"
    heading_color: Optional[str] = "#ffffff"
    accent_color: Optional[str] = "#7c3aed"
    card_color: Optional[str] = "#1f2237"
    radius: Optional[str] = "12px"
    bg_image_url: Optional[str] = None

    bg_type: Optional[str] = "color"
    bg_gradient: Optional[str] = None
    bg_position: Optional[str] = "center"
    bg_size: Optional[str] = "cover"
    bg_overlay_opacity: Optional[str] = "0"
    bg_overlay_color: Optional[str] = "#000000"
    font_family: Optional[str] = "Inter, system-ui, sans-serif"
    font_size: Optional[str] = "16px"
    heading_size: Optional[str] = "28px"
    line_height: Optional[str] = "1.6"
    card_opacity: Optional[str] = "1"
    card_blur: Optional[str] = "0px"
    card_border_width: Optional[str] = "0px"
    card_border_color: Optional[str] = "#ffffff"
    card_shadow: Optional[str] = None
    button_color: Optional[str] = None
    link_color: Optional[str] = None
    icon_color: Optional[str] = None
    avatar_style: Optional[str] = "circle"
    avatar_size: Optional[str] = "80px"
    profile_align: Optional[str] = "left"
    content_width: Optional[str] = "760px"
    gap: Optional[str] = "16px"
    extra: Optional[Dict[str, Any]] = None

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
