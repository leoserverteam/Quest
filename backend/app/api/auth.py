import base64
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

    response.set_cookie("vk_state", state, httponly=True, samesite="lax", max_age=600)
    response.set_cookie("vk_verifier", code_verifier, httponly=True, samesite="lax", max_age=600)

    params = {
        "client_id": settings.VK_CLIENT_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "response_type": "code",
        "scope": "vkid.personal_info",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
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

    code_verifier = request.cookies.get("vk_verifier")
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Missing code_verifier")

    response.delete_cookie("vk_state")
    response.delete_cookie("vk_verifier")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.VK_CLIENT_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    if settings.VK_CLIENT_SECRET:
        data["client_secret"] = settings.VK_CLIENT_SECRET

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(settings.VK_TOKEN_URL, data=data, headers=headers)
            token_data = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"VK token exchange failed: {e}")

    if resp.status_code >= 400 or "access_token" not in token_data:
        err = token_data.get("error_description") or token_data.get("error") or str(token_data)
        raise HTTPException(status_code=400, detail=err)

    access_token = token_data["access_token"]
    user_id_vk = token_data.get("user_id") or token_data.get("id")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(settings.VK_USERINFO_URL, params={"access_token": access_token})
            info = r.json()
    except Exception:
        info = {}

    vk_id = str(user_id_vk) if user_id_vk else None
    if not vk_id and isinstance(info, dict):
        if info.get("user", {}).get("id"):
            vk_id = str(info["user"]["id"])
        elif info.get("id"):
            vk_id = str(info["id"])

    if not vk_id:
        raise HTTPException(status_code=400, detail="Cannot get VK user")

    identity = db.query(AuthIdentity).filter(AuthIdentity.provider == "vk", AuthIdentity.provider_user_id == vk_id).first()
    user = identity.user if identity else db.query(User).filter(User.vk_id == vk_id).first()

    if not user:
        display_name = "User"
        avatar_url = None
        if isinstance(info, dict) and isinstance(info.get("user"), dict):
            u = info["user"]
            first = u.get("first_name") or ""
            last = u.get("last_name") or ""
            display_name = (first + " " + last).strip() or display_name
            avatar_url = u.get("avatar") or u.get("photo_200")
        elif isinstance(info, dict):
            first = info.get("first_name") or ""
            last = info.get("last_name") or ""
            display_name = (first + " " + last).strip() or display_name
            avatar_url = info.get("avatar") or info.get("photo_200")

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
    )
    return Response(status_code=302, headers={"Location": "/cabinet"})
