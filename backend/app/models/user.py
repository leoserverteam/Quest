import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vk_id = Column(String(64), unique=True, index=True, nullable=True)
    email = Column(String(255), nullable=True)
    display_name = Column(String(128), nullable=False)
    avatar_url = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    profiles = relationship("Profile", back_populates="user")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    identities = relationship("AuthIdentity", back_populates="user", cascade="all, delete-orphan")
    pools = relationship("QuestionPool", back_populates="user", cascade="all, delete-orphan")
    saved_themes = relationship("SavedTheme", back_populates="user", cascade="all, delete-orphan")


class AuthIdentity(Base):
    __tablename__ = "auth_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(32), nullable=False)
    provider_user_id = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_agent = Column(Text, nullable=True)
    ip = Column(String(64), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")
