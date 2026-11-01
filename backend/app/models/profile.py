import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(64), unique=True, index=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    avatar_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)

    edit_token_hash = Column(String(64), unique=True, index=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    answers = relationship("Answer", back_populates="profile", cascade="all, delete-orphan")
    design = relationship("DesignSettings", back_populates="profile", uselist=False, cascade="all, delete-orphan")


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

    profile = relationship("Profile", back_populates="design")
