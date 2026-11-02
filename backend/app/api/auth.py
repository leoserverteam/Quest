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


def _gen_pkce():
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


@router.get("/auth/vk/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def vk_login(request: Request, response: Response):
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _gen_pkce()
    response.set_cookie("vk_state", state, httponly=True, samesite="lax", secure=settings.APP_ENV == "production", max_age=600, path="/")
    response.set_cookie("vk_verifier", code_verifier, httponly=True, samesite="lax", secure=settings.APP_ENV == "production", max_age=600, path="/")
    params = {
        "client_id": settings.VK_CLIENT_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return {"url": "https://id.vk.com/authorize?" + urlencode(params)}


@router.get("/auth/vk/callback")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def vk_callback(request: Request, response: Response, code: str = None, state: str = None, device_id: str = None, db: Session = Depends(get_db)):
    if not code or not state or request.cookies.get("vk_state") != state:
        raise HTTPException(status_code=400, detail="invalid_state")
    code_verifier = request.cookies.get("vk_verifier")
    if not code_verifier:
        raise HTTPException(status_code=400, detail="missing_verifier")
    response.delete_cookie("vk_state", path="/")
    response.delete_cookie("vk_verifier", path="/")

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.VK_CLIENT_ID,
        "code_verifier": code_verifier,
        "redirect_uri": settings.VK_REDIRECT_URI,
    }
    if device_id:
        payload["device_id"] = device_id

    token_data = None
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                "https://id.vk.com/oauth2/token",
                data=payload,
            )
            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype and not resp.text.strip().startswith("<"):
                try:
                    token_data = resp.json()
                except Exception:
                    pass
            elif resp.status_code == 200 and resp.text.strip().startswith("{"):
                try:
                    token_data = resp.json()
                except Exception:
                    pass
        except Exception:
            pass

    if not isinstance(token_data, dict) or not token_data.get("access_token"):
        raise HTTPException(status_code=502, detail={"error": "token_failed"})

    access_token = token_data["access_token"]
    vk_id = token_data.get("user_id")
    if vk_id is not None:
        vk_id = str(vk_id)

    info = {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://id.vk.com/oauth2/user_info",
                data={"client_id": settings.VK_CLIENT_ID, "access_token": access_token},
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            )
            try:
                info = resp.json()
            except Exception:
                pass
    except Exception:
        pass

    if not vk_id and isinstance(info, dict):
        user_info = info.get("user") or info
        if isinstance(user_info, dict):
            if user_info.get("user_id") is not None:
                vk_id = str(user_info["user_id"])
            elif user_info.get("id") is not None:
                vk_id = str(user_info["id"])

    if not vk_id:
        raise HTTPException(status_code=400, detail="vk_user_not_found")

    identity = db.query(AuthIdentity).filter(AuthIdentity.provider == "vk", AuthIdentity.provider_user_id == vk_id).first()
    user = identity.user if identity else db.query(User).filter(User.vk_id == vk_id).first()

    if not user:
        display_name = "User"
        avatar_url = None
        if isinstance(info, dict):
            user_info = info.get("user") or info
            if isinstance(user_info, dict):
                first = user_info.get("first_name") or ""
                last = user_info.get("last_name") or ""
                full = (first + " " + last).strip()
                if full:
                    display_name = full
                avatar_url = user_info.get("avatar") or user_info.get("photo_200") or user_info.get("picture")
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
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
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
