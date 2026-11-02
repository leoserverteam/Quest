import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.session import require_user
from app.db.session import get_db
from app.models.user import User
from app.models.pools import QuestionPool, QuestionPoolItem, ProfileQuestionPool
from app.models.profile import Profile
from app.core.utils import sanitize_slug

router = APIRouter()


@router.get("/pools")
def list_pools(user: User = Depends(require_user), db: Session = Depends(get_db)):
    pools = db.query(QuestionPool).filter(QuestionPool.user_id == user.id).all()
    res = []
    for p in pools:
        res.append({"id": str(p.id), "name": p.name, "description": p.description, "count": len(p.items), "is_public": p.is_public})
    return res


@router.post("/pools")
def create_pool(data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    name = data.get("name") or "Новый пул"
    pool = QuestionPool(user_id=user.id, name=name[:128], description=data.get("description"))
    db.add(pool)
    db.commit()
    db.refresh(pool)
    return {"id": str(pool.id), "name": pool.name}


@router.get("/pools/{pool_id}")
def get_pool(pool_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = db.query(QuestionPool).filter(QuestionPool.id == pool_id, QuestionPool.user_id == user.id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Not found")
    items = []
    for it in sorted(pool.items, key=lambda x: x.position):
        items.append({"id": str(it.id), "item_id": it.item_id, "title": it.title, "description": it.description, "type": it.type, "required": it.required, "options": it.options, "position": it.position})
    return {"id": str(pool.id), "name": pool.name, "description": pool.description, "items": items}


@router.put("/pools/{pool_id}")
def update_pool(pool_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = db.query(QuestionPool).filter(QuestionPool.id == pool_id, QuestionPool.user_id == user.id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Not found")
    if data.get("name") is not None:
        pool.name = data["name"][:128]
    if data.get("description") is not None:
        pool.description = data["description"]
    pool.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/pools/{pool_id}")
def delete_pool(pool_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = db.query(QuestionPool).filter(QuestionPool.id == pool_id, QuestionPool.user_id == user.id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(pool)
    db.commit()
    return {"ok": True}


@router.post("/pools/{pool_id}/items")
def add_item(pool_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = db.query(QuestionPool).filter(QuestionPool.id == pool_id, QuestionPool.user_id == user.id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Not found")
    allowed = {"text", "textarea", "boolean", "select", "multiselect", "number", "date", "url"}
    qtype = data.get("type") or "text"
    if qtype not in allowed:
        raise HTTPException(status_code=400, detail="Invalid type")
    if qtype in ("select", "multiselect") and not data.get("options"):
        raise HTTPException(status_code=400, detail="Options required")
    item_id = data.get("item_id") or uuid.uuid4().hex[:12]
    max_pos = db.query(QuestionPoolItem).filter(QuestionPoolItem.pool_id == pool.id).count()
    item = QuestionPoolItem(pool_id=pool.id, item_id=item_id, title=data.get("title") or "Вопрос", description=data.get("description"), type=qtype, required=bool(data.get("required")), options=data.get("options"), position=max_pos)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "item_id": item.item_id}


@router.put("/pools/{pool_id}/items/{item_id}")
def update_item(pool_id: str, item_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = db.query(QuestionPool).filter(QuestionPool.id == pool_id, QuestionPool.user_id == user.id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Not found")
    item = db.query(QuestionPoolItem).filter(QuestionPoolItem.id == item_id, QuestionPoolItem.pool_id == pool.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    for k in ["title", "description", "type", "required", "options", "position"]:
        if k in data:
            setattr(item, k, data[k])
    item.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/pools/{pool_id}/items/{item_id}")
def delete_item(pool_id: str, item_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    pool = db.query(QuestionPool).filter(QuestionPool.id == pool_id, QuestionPool.user_id == user.id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Not found")
    item = db.query(QuestionPoolItem).filter(QuestionPoolItem.id == item_id, QuestionPoolItem.pool_id == pool.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/profiles/{profile_id}/pools")
def attach_pool(profile_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    pool_id = data.get("pool_id")
    pool = db.query(QuestionPool).filter(QuestionPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if pool.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # snapshot
    snapshot = []
    for it in sorted(pool.items, key=lambda x: x.position):
        snapshot.append({"item_id": it.item_id, "title": it.title, "description": it.description, "type": it.type, "required": it.required, "options": it.options, "position": it.position})
    max_pos = db.query(ProfileQuestionPool).filter(ProfileQuestionPool.profile_id == profile.id).count()
    link = ProfileQuestionPool(profile_id=profile.id, pool_id=pool.id, position=max_pos, snapshot=snapshot)
    try:
        db.add(link)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Already attached")
    return {"ok": True}


@router.delete("/profiles/{profile_id}/pools/{link_id}")
def detach_pool(profile_id: str, link_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    link = db.query(ProfileQuestionPool).filter(ProfileQuestionPool.id == link_id, ProfileQuestionPool.profile_id == profile.id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(link)
    db.commit()
    return {"ok": True}
