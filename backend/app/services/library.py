"""Helpers for the public question-pool library.

The library exposes pools that their owners published (``public``) or shared
by link (``unlisted``).  Everything else stays private to the owner.

This module keeps the shared validation/serialization logic in one place so
the API layer stays thin and copies are created consistently.
"""
import copy
import hashlib
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.pools import PoolAdd, PoolView, QuestionPool, QuestionPoolItem
from app.models.profile import Profile
from app.models.user import User
from app.services.questions import (
    CHOICE_TYPES,
    QuestionValidationError,
    normalize_options,
    normalize_question_type,
)

VISIBILITY_PRIVATE = "private"
VISIBILITY_UNLISTED = "unlisted"
VISIBILITY_PUBLIC = "public"
VISIBILITIES = (VISIBILITY_PRIVATE, VISIBILITY_UNLISTED, VISIBILITY_PUBLIC)

MAX_TAGS = 10
MAX_TAG_LENGTH = 24
MAX_CATEGORY_LENGTH = 32

LIBRARY_CATEGORIES: List[Dict[str, str]] = [
    {"id": "personal", "label": "О себе"},
    {"id": "dating", "label": "Знакомства"},
    {"id": "friendship", "label": "Дружба и общение"},
    {"id": "gaming", "label": "Игры"},
    {"id": "music", "label": "Музыка"},
    {"id": "movies", "label": "Кино и сериалы"},
    {"id": "books", "label": "Книги"},
    {"id": "tech", "label": "Технологии"},
    {"id": "work", "label": "Работа"},
    {"id": "travel", "label": "Путешествия"},
    {"id": "food", "label": "Еда"},
    {"id": "humor", "label": "Юмор"},
    {"id": "other", "label": "Другое"},
]

CATEGORY_IDS = {category["id"] for category in LIBRARY_CATEGORIES}
CATEGORY_LABELS = {category["id"]: category["label"] for category in LIBRARY_CATEGORIES}


def visibility_of(pool: QuestionPool) -> str:
    """Return the effective visibility, tolerating legacy rows."""
    value = (pool.visibility or "").strip().lower()
    if value in VISIBILITIES:
        return value
    # Rows created before the library existed have no visibility column value.
    return VISIBILITY_PUBLIC if pool.is_public else VISIBILITY_PRIVATE


def normalize_visibility(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("visibility must be a string")
    normalized = value.strip().lower()
    if normalized not in VISIBILITIES:
        raise ValueError("Unsupported visibility")
    return normalized


def normalize_category(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("category must be a string")
    normalized = value.strip().lower()
    if not normalized:
        return None
    if len(normalized) > MAX_CATEGORY_LENGTH:
        raise ValueError("category is too long")
    if normalized not in CATEGORY_IDS:
        raise ValueError("Unknown category")
    return normalized


def normalize_tags(value: Any) -> Tuple[List[str], Optional[str]]:
    """Normalize tags and build the lowercase lookup string used for filters."""
    if value is None:
        return [], None
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ValueError("tags must be a list")

    tags: List[str] = []
    seen = set()
    for raw in raw_items:
        if not isinstance(raw, str):
            raise ValueError("Each tag must be a string")
        tag = " ".join(raw.split())
        if not tag:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise ValueError(f"Tag is too long (max {MAX_TAG_LENGTH})")
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tags.append(tag)
        if len(tags) > MAX_TAGS:
            raise ValueError(f"Too many tags (max {MAX_TAGS})")
    if not tags:
        return [], None
    return tags, "," + ",".join(tag.lower() for tag in tags) + ","


def generate_share_slug(db: Session) -> str:
    """Generate a unique, unguessable public link slug."""
    for _ in range(20):
        slug = secrets.token_urlsafe(9)
        exists = (
            db.query(QuestionPool.id)
            .filter(QuestionPool.share_slug == slug)
            .first()
        )
        if not exists:
            return slug
    # Extremely unlikely, but never return a duplicate.
    return secrets.token_urlsafe(16)


def serialize_item(item: QuestionPoolItem) -> Dict[str, Any]:
    qtype = item.type
    options = item.options
    try:
        qtype = normalize_question_type(item.type)
        if qtype in CHOICE_TYPES:
            options = normalize_options(item.options)
    except QuestionValidationError:
        # Keep legacy/invalid data visible so it can be fixed in the editor.
        pass
    return {
        "id": str(item.id),
        "item_id": item.item_id,
        "title": item.title,
        "description": item.description,
        "type": qtype,
        "required": bool(item.required),
        "options": options,
        "position": item.position or 0,
    }


def author_info(db: Session, user_id: Any) -> Optional[Dict[str, Any]]:
    """Public author card.  Never exposes internal ids, email or VK id."""
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .order_by(Profile.created_at.asc())
        .first()
    )
    return {
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "profile_slug": profile.slug if profile else None,
    }


def serialize_origin(db: Session, pool: QuestionPool) -> Optional[Dict[str, Any]]:
    """Describe where a copied pool came from.

    The copy keeps working even if the original was deleted or unpublished;
    in that case ``available`` is false and no link is returned.
    """
    if not pool.source_pool_id:
        return None

    source = (
        db.query(QuestionPool)
        .filter(QuestionPool.id == pool.source_pool_id)
        .first()
    )
    # Only public originals get a link: exposing an unlisted pool's secret
    # link through a public copy would defeat the point of "unlisted".
    available = bool(
        source
        and visibility_of(source) == VISIBILITY_PUBLIC
        and source.share_slug
    )

    author_name = pool.source_author_name
    author_profile_slug = None
    if source and source.user:
        author_name = author_name or source.user.display_name
        profile = (
            db.query(Profile)
            .filter(Profile.user_id == source.user_id)
            .order_by(Profile.created_at.asc())
            .first()
        )
        author_profile_slug = profile.slug if profile else None

    return {
        "pool_id": str(pool.source_pool_id),
        "title": pool.source_pool_name or (source.name if source else None),
        "author_name": author_name,
        "author_profile_slug": author_profile_slug,
        "copied_at": pool.copied_at.isoformat() if pool.copied_at else None,
        "available": available,
        "share_slug": source.share_slug if available else None,
    }


def serialize_pool(
    db: Session,
    pool: QuestionPool,
    *,
    viewer: Optional[User] = None,
    copied_source_ids: Optional[set] = None,
    include_items: bool = False,
    preview_limit: int = 5,
) -> Dict[str, Any]:
    items = sorted(pool.items, key=lambda item: (item.position or 0, str(item.id)))
    visibility = visibility_of(pool)

    if copied_source_ids is not None:
        is_added = pool.id in copied_source_ids
    elif viewer is not None:
        is_added = bool(
            db.query(QuestionPool.id)
            .filter(
                QuestionPool.user_id == viewer.id,
                QuestionPool.source_pool_id == pool.id,
            )
            .first()
        )
    else:
        is_added = False

    data: Dict[str, Any] = {
        "id": str(pool.id),
        "share_slug": pool.share_slug,
        "name": pool.name,
        "description": pool.description,
        "category": pool.category,
        "category_label": CATEGORY_LABELS.get(pool.category) if pool.category else None,
        "tags": list(pool.tags or []),
        "cover_url": pool.cover_url,
        "count": len(items),
        "author": author_info(db, pool.user_id),
        "views_count": int(pool.views_count or 0),
        "adds_count": int(pool.adds_count or 0),
        # One PoolAdd row per user, so this is also the number of unique users.
        "users_count": int(pool.adds_count or 0),
        "visibility": visibility,
        "published_at": pool.published_at.isoformat() if pool.published_at else None,
        "created_at": pool.created_at.isoformat() if pool.created_at else None,
        "is_owner": bool(viewer and pool.user_id == viewer.id),
        "is_added": is_added,
        "origin": serialize_origin(db, pool),
        "preview": [
            {
                "title": item.title,
                "type": item.type,
                "required": bool(item.required),
            }
            for item in items[:preview_limit]
        ],
    }
    if include_items:
        data["items"] = [serialize_item(item) for item in items]
    return data


def get_public_pool(db: Session, share_slug: str, *, allow_unlisted: bool = True) -> Optional[QuestionPool]:
    if not share_slug:
        return None
    pool = db.query(QuestionPool).filter(QuestionPool.share_slug == share_slug).first()
    if not pool:
        return None
    allowed = {VISIBILITY_PUBLIC}
    if allow_unlisted:
        allowed.add(VISIBILITY_UNLISTED)
    if visibility_of(pool) not in allowed:
        return None
    return pool


def copy_pool_to_user(
    db: Session, source: QuestionPool, user: User
) -> Tuple[QuestionPool, bool]:
    """Create an independent copy of ``source`` for ``user``.

    Returns ``(copy, created)``.  Adding the same pool twice returns the
    existing copy instead of creating a duplicate.
    """
    existing = (
        db.query(QuestionPool)
        .filter(
            QuestionPool.user_id == user.id,
            QuestionPool.source_pool_id == source.id,
        )
        .first()
    )
    if existing:
        return existing, False

    copied = QuestionPool(
        user_id=user.id,
        name=source.name,
        description=source.description,
        visibility=VISIBILITY_PRIVATE,
        is_public=False,
        source_pool_id=source.id,
        source_author_id=source.user_id,
        source_pool_name=source.name,
        source_author_name=source.user.display_name if source.user else None,
        copied_at=datetime.utcnow(),
    )
    db.add(copied)
    try:
        db.flush()
    except IntegrityError:
        # Another request created the copy concurrently.
        db.rollback()
        existing = (
            db.query(QuestionPool)
            .filter(
                QuestionPool.user_id == user.id,
                QuestionPool.source_pool_id == source.id,
            )
            .first()
        )
        if existing:
            return existing, False
        raise

    for item in sorted(source.items, key=lambda x: (x.position or 0, str(x.id))):
        db.add(
            QuestionPoolItem(
                pool_id=copied.id,
                item_id=item.item_id,
                title=item.title,
                description=item.description,
                type=item.type,
                required=bool(item.required),
                options=copy.deepcopy(item.options),
                position=item.position or 0,
            )
        )

    already_added = (
        db.query(PoolAdd)
        .filter(PoolAdd.pool_id == source.id, PoolAdd.user_id == user.id)
        .first()
    )
    if not already_added:
        db.add(PoolAdd(pool_id=source.id, user_id=user.id))
        source.adds_count = int(source.adds_count or 0) + 1

    db.commit()
    db.refresh(copied)
    return copied, True


def record_view(db: Session, pool: QuestionPool, viewer_key: str) -> bool:
    """Count a view once per viewer.  Returns True when the counter changed."""
    already = (
        db.query(PoolView.id)
        .filter(PoolView.pool_id == pool.id, PoolView.viewer_key == viewer_key)
        .first()
    )
    if already:
        return False
    db.add(PoolView(pool_id=pool.id, viewer_key=viewer_key))
    pool.views_count = int(pool.views_count or 0) + 1
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def viewer_key_for(user: Optional[User], request) -> str:
    if user is not None:
        return f"u:{user.id}"
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "unknown")
    user_agent = request.headers.get("user-agent") or ""
    digest = hashlib.sha256(f"{ip}|{user_agent}".encode("utf-8")).hexdigest()[:40]
    return f"a:{digest}"
