import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserSession


def generate_session_token() -> Tuple[str, str]:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user_id, request: Request) -> str:
    token, token_hash = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.SESSION_TTL_HOURS)
    sess = UserSession(
        user_id=user_id,
        session_token_hash=token_hash,
        user_agent=request.headers.get("user-agent"),
        ip=request.headers.get("x-forwarded-for") or request.client.host if request.client else None,
        expires_at=expires_at,
    )
    db.add(sess)
    db.commit()
    return token


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    quest_session: Optional[str] = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
) -> Optional[User]:
    token = quest_session
    if not token:
        # also check header for flexibility
        token = request.headers.get("X-Session-Token")
    if not token:
        return None
    token_hash = hash_session_token(token)
    sess = db.query(UserSession).filter(UserSession.session_token_hash == token_hash, UserSession.revoked_at.is_(None)).first()
    if not sess:
        return None
    if sess.expires_at < datetime.utcnow():
        return None
    user = db.query(User).filter(User.id == sess.user_id).first()
    return user


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
