import base64
import hashlib
import json
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


def _generate_pkce_pair():
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


@router.get("/auth/vk/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def vk_login(request: Request, response: Response):
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce_pair()

    response.set_cookie("vk_state", state, httponly=True, samesite="lax", max_age=600, path="/")
    response.set_cookie("vk_verifier", code_verifier, httponly=True, samesite="lax", max_age=600, path="/")

    params = {
        "response_type": "code",
        "client_id": settings.VK_CLIENT_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    url = f"https://id.vk.com/authorize?{urlencode(params)}"
    return {"url": url}


@router.get("/auth/vk/callback")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def vk_callback(request: Request, response: Response, code: str = None, state: str = None, device_id: str = None, db: Session = Depends(get_db)):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")

    cookie_state = request.cookies.get("vk_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")

    code_verifier = request.cookies.get("vk_verifier")
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Missing code_verifier")

    response.delete_cookie("vk_state", path="/")
    response.delete_cookie("vk_verifier", path="/")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.VK_CLIENT_ID,
        "code_verifier": code_verifier,
        "redirect_uri": settings.VK_REDIRECT_URI,
    }
    if device_id:
        data["device_id"] = device_id

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post("https://id.vk.com/oauth2/token", data=data)
        try:
            token_data = resp.json()
        except Exception:
            raise HTTPException(status_code=502, detail=resp.text)

    if resp.status_code != 200 or not isinstance(token_data, dict) or not token_data.get("access_token"):
        raise HTTPException(status_code=502, detail=token_data)

    access_token = token_data["access_token"]
    vk_id = token_data.get("user_id")
    if vk_id is not None:
        vk_id = str(vk_id)

    info = {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("https://id.vk.com/oauth2/user_info", data={"client_id": settings.VK_CLIENT_ID, "access_token": access_token})
            info = r.json()
    except Exception:
        info = {}

    if not vk_id and isinstance(info, dict):
        u = info.get("user") or info
        if isinstance(u, dict) and u.get("id"):
            vk_id = str(u["id"])

    if not vk_id:
        raise HTTPException(status_code=400, detail="Cannot get VK user")

    identity = db.query(AuthIdentity).filter(AuthIdentity.provider == "vk", AuthIdentity.provider_user_id == vk_id).first()
    user = identity.user if identity else db.query(User).filter(User.vk_id == vk_id).first()

    if not user:
        display_name = "User"
        avatar_url = None
        if isinstance(info, dict):
            u = info.get("user") or info
            if isinstance(u, dict):
                first = u.get("first_name") or ""
                last = u.get("last_name") or ""
                display_name = (f"{first} {last}").strip() or display_name
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
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="lax",
        secure=settings.APP_ENV == "production",
        max_age=settings.SESSION_TTL_HOURS * 3600,
        path="/",
    )
    return Response(status_code=302, headers={"Location": "/cabinet"})


@router.get("/auth/me")
def auth_me(user: Optional[User] = Depends(get_current_user)):
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
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}
