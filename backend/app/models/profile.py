import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    slug = Column(String(64), unique=True, index=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    avatar_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)

    edit_token_hash = Column(String(64), unique=True, index=True, nullable=False)
    owner_bound_at = Column(DateTime, nullable=True)
    last_edited_via = Column(String(16), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profiles")
    answers = relationship("Answer", back_populates="profile", cascade="all, delete-orphan")
    design = relationship("DesignSettings", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    profile_pools = relationship("ProfileQuestionPool", back_populates="profile", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(64), index=True, nullable=False)
    value = Column(JSON, nullable=True)  # store any serializable value
    hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="answers")

    __table_args__ = (
        UniqueConstraint("profile_id", "question_id", name="uq_profile_question"),
    )


class DesignSettings(Base):
    __tablename__ = "design_settings"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False)

    preset = Column(String(32), default="dark")
    bg_color = Column(String(16), default="#0f1026")
    text_color = Column(String(16), default="#f4f4f9")
    heading_color = Column(String(16), default="#ffffff")
    accent_color = Column(String(16), default="#7c3aed")
    card_color = Column(String(16), default="#1f2237")
    radius = Column(String(8), default="12px")
    bg_image_url = Column(Text, nullable=True)

    # Расширенные настройки
    bg_type = Column(String(16), default="color")  # color/gradient/image
    bg_gradient = Column(Text, nullable=True)
    bg_position = Column(String(32), default="center")
    bg_size = Column(String(16), default="cover")
    bg_overlay_opacity = Column(String(8), default="0")
    bg_overlay_color = Column(String(16), default="#000000")

    font_family = Column(String(64), default="Inter, system-ui, sans-serif")
    font_size = Column(String(8), default="16px")
    heading_size = Column(String(8), default="28px")
    line_height = Column(String(8), default="1.6")

    card_opacity = Column(String(8), default="1")
    card_blur = Column(String(8), default="0px")
    card_border_width = Column(String(8), default="0px")
    card_border_color = Column(String(16), default="#ffffff")
    card_shadow = Column(Text, nullable=True)

    button_color = Column(String(16), nullable=True)
    link_color = Column(String(16), nullable=True)
    icon_color = Column(String(16), nullable=True)

    avatar_style = Column(String(16), default="circle")
    avatar_size = Column(String(8), default="80px")
    profile_align = Column(String(16), default="left")
    content_width = Column(String(12), default="760px")
    gap = Column(String(8), default="16px")

    extra = Column(JSON, nullable=True)

    profile = relationship("Profile", back_populates="design")
