import hashlib
import secrets
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.session import create_session, get_current_user
from app.db.session import get_db
from app.models.user import User, AuthIdentity

router = APIRouter()


@router.get("/auth/vk/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def vk_login(request: Request, response: Response):
    state = secrets.token_urlsafe(32)
    # store state in cookie for validation
    response.set_cookie("vk_state", state, httponly=True, samesite="lax", max_age=600)
    params = {
        "client_id": settings.VK_CLIENT_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "response_type": "code",
        "scope": "vkid.personal_info",
        "state": state,
    }
    url = f"{settings.VK_AUTH_URL}?{urlencode(params)}"
    return {"url": url}


@router.get("/auth/vk/callback")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def vk_callback(request: Request, response: Response, code: str = None, state: str = None, db: Session = Depends(get_db)):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")
    cookie_state = request.cookies.get("vk_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")
    response.delete_cookie("vk_state")

    # Exchange code for token
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.VK_CLIENT_ID,
        "client_secret": settings.VK_CLIENT_SECRET,
        "redirect_uri": settings.VK_REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(settings.VK_TOKEN_URL, data=data)
            token_data = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail="VK token exchange failed")
    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail="VK auth failed")

    access_token = token_data["access_token"]
    user_id_vk = token_data.get("user_id") or token_data.get("id")

    # Get user info
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(settings.VK_USERINFO_URL, params={"access_token": access_token})
            info = r.json()
    except Exception:
        info = {}

    vk_id = str(user_id_vk) if user_id_vk else None
    if not vk_id and info.get("user"):
        vk_id = str(info["user"].get("id"))
    if not vk_id:
        raise HTTPException(status_code=400, detail="Cannot get VK user")

    # Find or create user
    identity = db.query(AuthIdentity).filter(AuthIdentity.provider == "vk", AuthIdentity.provider_user_id == vk_id).first()
    user = None
    if identity:
        user = identity.user
    else:
        # try by vk_id
        user = db.query(User).filter(User.vk_id == vk_id).first()

    if not user:
        display_name = "User"
        avatar_url = None
        if info.get("user"):
            u = info["user"]
            display_name = u.get("first_name") or display_name
            if u.get("last_name"):
                display_name = f"{display_name} {u['last_name']}"
            avatar_url = u.get("avatar")
        user = User(vk_id=vk_id, display_name=display_name[:128], avatar_url=avatar_url)
        db.add(user)
        db.flush()
        identity = AuthIdentity(user_id=user.id, provider="vk", provider_user_id=vk_id)
        db.add(identity)

    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    session_token = create_session(db, user.id, request)
    response.set_cookie(settings.SESSION_COOKIE_NAME, session_token, httponly=True, samesite="lax", secure=settings.APP_ENV == "production", max_age=settings.SESSION_TTL_HOURS * 3600)
    # redirect to cabinet
    return {"ok": True, "redirect": "/cabinet"}


@router.get("/auth/me")
def auth_me(user: Optional[User] = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return {"user": None}
    return {"user": {"id": str(user.id), "display_name": user.display_name, "avatar_url": user.avatar_url, "vk_id": user.vk_id}}


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME) or request.headers.get("X-Session-Token")
    if token:
        from app.core.session import hash_session_token
        from app.models.user import UserSession

        th = hash_session_token(token)
        sess = db.query(UserSession).filter(UserSession.session_token_hash == th).first()
        if sess and not sess.revoked_at:
            sess.revoked_at = datetime.utcnow()
            db.commit()
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"ok": True}
