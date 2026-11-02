import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.session import require_user
from app.db.session import get_db
from app.models.user import User
from app.models.profile import Profile, Answer, DesignSettings
from app.models.pools import QuestionPool, SavedTheme
from app.core.security import hash_edit_token

router = APIRouter()


@router.get("/cabinet")
def cabinet_overview(user: User = Depends(require_user), db: Session = Depends(get_db)):
    profiles = db.query(Profile).filter(Profile.user_id == user.id).all()
    pools = db.query(QuestionPool).filter(QuestionPool.user_id == user.id).all()
    themes = db.query(SavedTheme).filter(SavedTheme.user_id == user.id).all()
    return {
        "profiles": [{"id": str(p.id), "slug": p.slug, "display_name": p.display_name, "avatar_url": p.avatar_url} for p in profiles],
        "pools_count": len(pools),
        "themes_count": len(themes),
    }


@router.get("/cabinet/profiles")
def cabinet_profiles(user: User = Depends(require_user), db: Session = Depends(get_db)):
    profiles = db.query(Profile).filter(Profile.user_id == user.id).all()
    return [{"id": str(p.id), "slug": p.slug, "display_name": p.display_name, "avatar_url": p.avatar_url, "bio": p.bio} for p in profiles]


@router.post("/cabinet/attach")
def attach_profile(edit_token: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    token_hash = hash_edit_token(edit_token)
    profile = db.query(Profile).filter(Profile.edit_token_hash == token_hash).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id and profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Already attached to another user")
    profile.user_id = user.id
    from datetime import datetime

    profile.owner_bound_at = datetime.utcnow()
    profile.last_edited_via = "session"
    db.commit()
    return {"ok": True}
