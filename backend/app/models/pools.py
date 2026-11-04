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

    # Public library
    visibility = Column(String(16), nullable=False, default="private", server_default="private", index=True)
    category = Column(String(32), nullable=True, index=True)
    tags = Column(JSON, nullable=True)
    # Lower-cased comma separated tags (",a,b,") used for portable filtering.
    tags_text = Column(String(512), nullable=True)
    cover_url = Column(Text, nullable=True)
    share_slug = Column(String(32), nullable=True, unique=True, index=True)
    published_at = Column(DateTime, nullable=True)
    views_count = Column(Integer, nullable=False, default=0, server_default="0")
    adds_count = Column(Integer, nullable=False, default=0, server_default="0")

    # Origin of a pool copied from the public library.  The original id is kept
    # even if the source pool is deleted, so copies stay self-contained.
    source_pool_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    source_author_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    source_pool_name = Column(String(128), nullable=True)
    source_author_name = Column(String(128), nullable=True)
    copied_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="pools")
    items = relationship("QuestionPoolItem", back_populates="pool", cascade="all, delete-orphan", order_by="QuestionPoolItem.position")
    profile_links = relationship("ProfileQuestionPool", back_populates="pool")
    views = relationship("PoolView", back_populates="pool", cascade="all, delete-orphan")
    adds = relationship("PoolAdd", back_populates="pool", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "source_pool_id", name="uq_pool_user_source"),
    )


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


class PoolView(Base):
    """A unique view of a public pool.

    ``viewer_key`` is a stable hash of the authenticated user id or of the
    anonymous visitor's IP + user agent, so repeated requests do not inflate
    the counter.
    """

    __tablename__ = "pool_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("question_pools.id", ondelete="CASCADE"), nullable=False, index=True)
    viewer_key = Column(String(80), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    pool = relationship("QuestionPool", back_populates="views")

    __table_args__ = (
        UniqueConstraint("pool_id", "viewer_key", name="uq_pool_view"),
    )


class PoolAdd(Base):
    """A unique (pool, user) pair for pools copied from the library."""

    __tablename__ = "pool_adds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("question_pools.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pool = relationship("QuestionPool", back_populates="adds")

    __table_args__ = (
        UniqueConstraint("pool_id", "user_id", name="uq_pool_add"),
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
