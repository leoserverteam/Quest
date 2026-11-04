"""Public question-pool library.

Endpoints under ``/library`` are readable without authentication (except the
"copy" action).  Private pools are never exposed here.
"""
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.session import get_current_user, require_user
from app.db.session import get_db
from app.models.pools import QuestionPool
from app.models.user import User
from app.services.library import (
    LIBRARY_CATEGORIES,
    VISIBILITY_PUBLIC,
    copy_pool_to_user,
    get_public_pool,
    record_view,
    serialize_pool,
    viewer_key_for,
)

router = APIRouter()

SORT_POPULAR = "popular"
SORT_RECENT = "recent"
MAX_PAGE_SIZE = 48


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _facets(db: Session):
    pools = (
        db.query(QuestionPool)
        .filter(QuestionPool.visibility == VISIBILITY_PUBLIC)
        .all()
    )
    category_counts = Counter(pool.category for pool in pools if pool.category)
    tag_counts = Counter(tag for pool in pools for tag in (pool.tags or []))
    categories = [
        {
            "id": category["id"],
            "label": category["label"],
            "count": category_counts.get(category["id"], 0),
        }
        for category in LIBRARY_CATEGORIES
        if category_counts.get(category["id"])
    ]
    tags = [
        {"tag": tag, "count": count}
        for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ]
    return categories, tags


def _copied_source_ids(db: Session, viewer: Optional[User]) -> set:
    if viewer is None:
        return set()
    rows = (
        db.query(QuestionPool.source_pool_id)
        .filter(
            QuestionPool.user_id == viewer.id,
            QuestionPool.source_pool_id.isnot(None),
        )
        .all()
    )
    return {row[0] for row in rows}


@router.get("/library/meta")
def library_meta(db: Session = Depends(get_db)):
    categories, tags = _facets(db)
    return {
        "categories": LIBRARY_CATEGORIES,
        "categories_with_counts": categories,
        "tags": tags,
        "sorts": [
            {"id": SORT_POPULAR, "label": "По популярности"},
            {"id": SORT_RECENT, "label": "По дате публикации"},
        ],
    }


@router.get("/library/pools")
def library_pools(
    request: Request,
    q: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = SORT_POPULAR,
    page: int = 1,
    limit: int = 12,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if page < 1:
        page = 1
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    sort = sort if sort in (SORT_POPULAR, SORT_RECENT) else SORT_POPULAR

    query = (
        db.query(QuestionPool)
        .options(selectinload(QuestionPool.items))
        .filter(QuestionPool.visibility == VISIBILITY_PUBLIC)
    )

    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        query = query.filter(
            or_(
                QuestionPool.name.ilike(pattern, escape="\\"),
                QuestionPool.description.ilike(pattern, escape="\\"),
            )
        )
    if category and category.strip():
        query = query.filter(QuestionPool.category == category.strip().lower())
    if tag and tag.strip():
        # tags_text is stored as ",tag1,tag2," so the match is exact.
        query = query.filter(
            QuestionPool.tags_text.contains(f",{tag.strip().lower()},", autoescape=True)
        )

    total = query.count()

    if sort == SORT_RECENT:
        query = query.order_by(desc(QuestionPool.published_at), desc(QuestionPool.created_at))
    else:
        query = query.order_by(
            desc(QuestionPool.adds_count),
            desc(QuestionPool.views_count),
            desc(QuestionPool.published_at),
        )

    pools = query.offset((page - 1) * limit).limit(limit).all()
    copied = _copied_source_ids(db, user)
    categories, tags = _facets(db)

    return {
        "items": [
            serialize_pool(db, pool, viewer=user, copied_source_ids=copied)
            for pool in pools
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
        "sort": sort,
        "categories": categories,
        "tags": tags,
    }


@router.get("/library/pools/{share_slug}")
def library_pool_detail(
    share_slug: str,
    request: Request,
    preview: bool = False,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pool = get_public_pool(db, share_slug)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # The owner browsing their own pool must not inflate the counter.  Preview
    # requests from the catalogue are not counted as views either.
    if not preview and (not user or pool.user_id != user.id):
        record_view(db, pool, viewer_key_for(user, request))

    return serialize_pool(db, pool, viewer=user, include_items=True)


@router.post("/library/pools/{share_slug}/copy")
@limiter.limit(settings.RATE_LIMIT_COPY)
def copy_library_pool(
    request: Request,
    share_slug: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    pool = get_public_pool(db, share_slug)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if pool.user_id == user.id:
        raise HTTPException(status_code=400, detail="Это ваш собственный пул")

    copied, created = copy_pool_to_user(db, pool, user)
    message = (
        "Пул добавлен в ваши пулы"
        if created
        else "Этот пул уже есть в ваших пулах"
    )
    return {
        "ok": True,
        "created": created,
        "message": message,
        "pool": serialize_pool(db, copied, viewer=user),
    }
