import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class QuestionPool(Base):
    __tablename__ = "question_pools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="pools")
    items = relationship("QuestionPoolItem", back_populates="pool", cascade="all, delete-orphan", order_by="QuestionPoolItem.position")
    profile_links = relationship("ProfileQuestionPool", back_populates="pool")


class QuestionPoolItem(Base):
    __tablename__ = "question_pool_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("question_pools.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(32), nullable=False)
    required = Column(Boolean, default=False)
    options = Column(JSON, nullable=True)
    position = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pool = relationship("QuestionPool", back_populates="items")


class ProfileQuestionPool(Base):
    __tablename__ = "profile_question_pools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("question_pools.id", ondelete="SET NULL"), nullable=True, index=True)
    position = Column(Integer, default=0)
    snapshot = Column(JSON, nullable=False)
    attached_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="profile_pools")
    pool = relationship("QuestionPool", back_populates="profile_links")

    __table_args__ = (
        UniqueConstraint("profile_id", "pool_id", name="uq_profile_pool"),
    )


class SavedTheme(Base):
    __tablename__ = "saved_themes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    config = Column(JSON, nullable=False)
    is_preset_base = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="saved_themes")
