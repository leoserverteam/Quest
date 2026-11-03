import re
import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.session import get_current_user, require_user
from app.db.session import get_db
from app.models.user import User
from app.models.pools import QuestionPool, QuestionPoolItem, ProfileQuestionPool
from app.models.profile import Profile
from app.services.questions import (
    CHOICE_TYPES,
    QuestionValidationError,
    normalize_options,
    normalize_question_type,
)
from app.services.profile_questions import make_snapshot, snapshot_items, snapshot_name
from app.api.deps import get_profile_by_edit_token

router = APIRouter()

ITEM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class PoolSelection(BaseModel):
    pool_ids: List[str] = []


def _parse_uuid(value: Any, name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {name}")


def _owned_pool(pool_id: str, user: User, db: Session) -> QuestionPool:
    pool = (
        db.query(QuestionPool)
        .filter(QuestionPool.id == _parse_uuid(pool_id, "pool_id"), QuestionPool.user_id == user.id)
        .first()
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    return pool


def _ensure_profile_owner(profile: Profile, user: User, db: Session) -> None:
    """Allow the holder of the edit token to bind an unowned profile to their account."""
    if profile.user_id is None:
        profile.user_id = user.id
        profile.owner_bound_at = datetime.utcnow()
        profile.last_edited_via = "edit_token"
        db.flush()
        return
    if profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


def _serialize_item(item: QuestionPoolItem) -> dict:
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


def _serialize_link(link: ProfileQuestionPool) -> dict:
    items = snapshot_items(link.snapshot)
    return {
        "id": str(link.id),
        "link_id": str(link.id),
        "pool_id": str(link.pool_id) if link.pool_id else None,
        "name": snapshot_name(link.snapshot) or (link.pool.name if link.pool else "Мои вопросы"),
        "count": len(items),
        "position": link.position or 0,
        "attached_at": link.attached_at.isoformat() if link.attached_at else None,
    }


def _clean_item_id(raw_id: Any, pool: QuestionPool, db: Session, current_id: Optional[str] = None) -> str:
    if raw_id is None or str(raw_id).strip() == "":
        item_id = uuid.uuid4().hex[:12]
    else:
        item_id = str(raw_id).strip()
    if not ITEM_ID_RE.match(item_id):
        raise HTTPException(status_code=400, detail="Invalid item_id")
    query = db.query(QuestionPoolItem).filter(
        QuestionPoolItem.pool_id == pool.id, QuestionPoolItem.item_id == item_id
    )
    if current_id is not None:
        query = query.filter(QuestionPoolItem.id != _parse_uuid(current_id, "item_id"))
    if query.first():
        raise HTTPException(status_code=409, detail="Duplicate item_id")
    return item_id


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)


def _validate_item_fields(data: dict, *, current: Optional[QuestionPoolItem] = None) -> dict:
    title = data.get("title", current.title if current else None)
    if not isinstance(title, str) or not title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if len(title.strip()) > 255:
        raise HTTPException(status_code=400, detail="Title is too long")

    raw_type = data.get("type", current.type if current else None)
    try:
        qtype = normalize_question_type(raw_type)
    except QuestionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    options = data.get("options", current.options if current else None)
    if qtype in CHOICE_TYPES:
        try:
            options = normalize_options(options)
        except QuestionValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        options = None

    description = data.get("description", current.description if current else None)
    if description is not None and not isinstance(description, str):
        raise HTTPException(status_code=400, detail="Description must be a string")

    required = data.get("required", current.required if current else False)
    return {
        "title": title.strip(),
        "type": qtype,
        "options": options,
        "description": description,
        "required": _coerce_bool(required),
    }


def _attach_pool(profile: Profile, pool: QuestionPool, db: Session) -> ProfileQuestionPool:
    existing = (
        db.query(ProfileQuestionPool)
        .filter(
            ProfileQuestionPool.profile_id == profile.id,
            ProfileQuestionPool.pool_id == pool.id,
        )
        .first()
    )
    if existing:
        # Re-attaching an already attached pool must not duplicate questions.
        return existing

    max_pos = (
        db.query(func.max(ProfileQuestionPool.position))
        .filter(ProfileQuestionPool.profile_id == profile.id)
        .scalar()
    )
    try:
        snapshot = make_snapshot(pool)
    except QuestionValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Pool contains an invalid question: {exc}")

    link = ProfileQuestionPool(
        profile_id=profile.id,
        pool_id=pool.id,
        position=(max_pos + 1) if max_pos is not None else 0,
        snapshot=snapshot,
    )
    db.add(link)
    return link


def _selection_summary(profile: Profile, db: Session) -> list:
    links = (
        db.query(ProfileQuestionPool)
        .filter(ProfileQuestionPool.profile_id == profile.id)
        .order_by(ProfileQuestionPool.position, ProfileQuestionPool.attached_at)
        .all()
    )
    return [_serialize_link(link) for link in links]


@router.get("/pools")
def list_pools(user: User = Depends(require_user), db: Session = Depends(get_db)):
    pools = (
        db.query(QuestionPool)
        .filter(QuestionPool.user_id == user.id)
        .order_by(QuestionPool.created_at.desc())
        .all()
    )
    res = []
    for p in pools:
        res.append(
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "count": len(p.items),
                "is_public": bool(p.is_public),
            }
        )
    return res


@router.post("/pools")
def create_pool(data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="Pool name is required")
    pool = QuestionPool(
        user_id=user.id,
        name=name.strip()[:128],
        description=data.get("description"),
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)
    return {"id": str(pool.id), "name": pool.name}


@router.get("/pools/{pool_id}")
def get_pool(pool_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = _owned_pool(pool_id, user, db)
    items = [_serialize_item(it) for it in sorted(pool.items, key=lambda x: (x.position or 0, str(x.id)))]
    return {"id": str(pool.id), "name": pool.name, "description": pool.description, "items": items}


@router.put("/pools/{pool_id}")
def update_pool(pool_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = _owned_pool(pool_id, user, db)
    if data.get("name") is not None:
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="Pool name is required")
        pool.name = name.strip()[:128]
    if data.get("description") is not None:
        pool.description = data["description"]
    pool.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/pools/{pool_id}")
def delete_pool(pool_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = _owned_pool(pool_id, user, db)
    db.delete(pool)
    db.commit()
    return {"ok": True}


@router.post("/pools/{pool_id}/items")
def add_item(pool_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = _owned_pool(pool_id, user, db)
    fields = _validate_item_fields(data)
    item_id = _clean_item_id(data.get("item_id"), pool, db)
    max_pos = (
        db.query(func.max(QuestionPoolItem.position))
        .filter(QuestionPoolItem.pool_id == pool.id)
        .scalar()
    )
    item = QuestionPoolItem(
        pool_id=pool.id,
        item_id=item_id,
        position=(max_pos + 1) if max_pos is not None else 0,
        **fields,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_item(item)


@router.put("/pools/{pool_id}/items/{item_id}")
def update_item(pool_id: str, item_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = _owned_pool(pool_id, user, db)
    item = (
        db.query(QuestionPoolItem)
        .filter(
            QuestionPoolItem.id == _parse_uuid(item_id, "item_id"),
            QuestionPoolItem.pool_id == pool.id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    fields = _validate_item_fields(data, current=item)
    if "item_id" in data:
        item.item_id = _clean_item_id(data.get("item_id"), pool, db, current_id=item_id)
    for key, value in fields.items():
        setattr(item, key, value)
    if data.get("position") is not None:
        try:
            item.position = int(data["position"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid position")
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return _serialize_item(item)


@router.delete("/pools/{pool_id}/items/{item_id}")
def delete_item(pool_id: str, item_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = _owned_pool(pool_id, user, db)
    item = (
        db.query(QuestionPoolItem)
        .filter(
            QuestionPoolItem.id == _parse_uuid(item_id, "item_id"),
            QuestionPoolItem.pool_id == pool.id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/profiles/{profile_id}/pools")
def list_profile_pools(profile_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == _parse_uuid(profile_id, "profile_id")).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _selection_summary(profile, db)


@router.post("/profiles/{profile_id}/pools")
def attach_pool(profile_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == _parse_uuid(profile_id, "profile_id")).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    pool = _owned_pool(data.get("pool_id"), user, db)
    link = _attach_pool(profile, pool, db)
    db.commit()
    db.refresh(link)
    return {"ok": True, "link_id": str(link.id)}


@router.delete("/profiles/{profile_id}/pools/{link_id}")
def detach_pool(profile_id: str, link_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == _parse_uuid(profile_id, "profile_id")).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    link = (
        db.query(ProfileQuestionPool)
        .filter(
            ProfileQuestionPool.id == _parse_uuid(link_id, "link_id"),
            ProfileQuestionPool.profile_id == profile.id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Not found")
    # Answers are intentionally left in the answers table.  Detaching only
    # hides the pool from the questionnaire.
    db.delete(link)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Edit-token based pool management (used by the questionnaire editor)
# ---------------------------------------------------------------------------


@router.get("/edit/me/pools")
def get_edit_pools(
    profile: Profile = Depends(get_profile_by_edit_token),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attached = _selection_summary(profile, db)
    attached_pool_ids = {link["pool_id"] for link in attached if link["pool_id"]}

    pools = []
    if user:
        owned = (
            db.query(QuestionPool)
            .filter(QuestionPool.user_id == user.id)
            .order_by(QuestionPool.created_at.desc())
            .all()
        )
        for pool in owned:
            pools.append(
                {
                    "id": str(pool.id),
                    "name": pool.name,
                    "description": pool.description,
                    "count": len(pool.items),
                    "is_public": bool(pool.is_public),
                    "attached": str(pool.id) in attached_pool_ids,
                }
            )

    can_manage = bool(user and (profile.user_id is None or profile.user_id == user.id))
    return {
        "authenticated": bool(user),
        "can_manage": can_manage,
        "attached": attached,
        "pools": pools,
    }


@router.put("/edit/me/pools")
def set_edit_pools(
    selection: PoolSelection,
    profile: Profile = Depends(get_profile_by_edit_token),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    _ensure_profile_owner(profile, user, db)

    requested_ids = []
    for raw in selection.pool_ids:
        parsed = _parse_uuid(raw, "pool_id")
        if parsed not in requested_ids:
            requested_ids.append(parsed)

    pools = []
    if requested_ids:
        pools = (
            db.query(QuestionPool)
            .filter(QuestionPool.id.in_(requested_ids), QuestionPool.user_id == user.id)
            .all()
        )
        found = {pool.id for pool in pools}
        if found != set(requested_ids):
            # Do not reveal whether the pool exists or belongs to someone else.
            raise HTTPException(status_code=403, detail="Forbidden")

    existing_links = (
        db.query(ProfileQuestionPool)
        .filter(ProfileQuestionPool.profile_id == profile.id)
        .all()
    )
    by_pool_id = {link.pool_id: link for link in existing_links if link.pool_id is not None}

    for pool in pools:
        if pool.id not in by_pool_id:
            _attach_pool(profile, pool, db)

    requested_set = set(requested_ids)
    for link in existing_links:
        if link.pool_id is not None and link.pool_id not in requested_set:
            # Keep answers; only the pool attachment is removed.
            db.delete(link)

    db.commit()
    return {
        "ok": True,
        "attached": _selection_summary(profile, db),
        "categories": [],
    }


@router.post("/edit/me/pools")
def attach_edit_pool(
    data: dict,
    profile: Profile = Depends(get_profile_by_edit_token),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    _ensure_profile_owner(profile, user, db)
    pool_ids = data.get("pool_ids")
    if not isinstance(pool_ids, list):
        pool_ids = [data.get("pool_id")]
    pool_ids = [pid for pid in pool_ids if pid]

    parsed_ids = [_parse_uuid(pid, "pool_id") for pid in pool_ids]
    if parsed_ids:
        pools = (
            db.query(QuestionPool)
            .filter(QuestionPool.id.in_(parsed_ids), QuestionPool.user_id == user.id)
            .all()
        )
        found = {pool.id for pool in pools}
        if found != set(parsed_ids):
            raise HTTPException(status_code=403, detail="Forbidden")
        for pool in pools:
            _attach_pool(profile, pool, db)
    db.commit()
    return {"ok": True, "attached": _selection_summary(profile, db)}


@router.delete("/edit/me/pools/{link_id}")
def detach_edit_pool(
    link_id: str,
    profile: Profile = Depends(get_profile_by_edit_token),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    _ensure_profile_owner(profile, user, db)
    link = (
        db.query(ProfileQuestionPool)
        .filter(
            ProfileQuestionPool.id == _parse_uuid(link_id, "link_id"),
            ProfileQuestionPool.profile_id == profile.id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(link)
    db.commit()
    return {"ok": True}
