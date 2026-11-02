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
    code_verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return code_verifier, code_challenge


@router.get("/auth/vk/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def vk_login(request: Request, response: Response):
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce_pair()
    response.set_cookie("vk_state", state, httponly=True, samesite="lax", secure=settings.APP_ENV == "production", max_age=600, path="/")
    response.set_cookie("vk_verifier", code_verifier, httponly=True, samesite="lax", secure=settings.APP_ENV == "production", max_age=600, path="/")
    params = {
        "client_id": settings.VK_CLIENT_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "response_type": "code",
        "scope": "email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return {"url": f"https://id.vk.com/authorize?{urlencode(params)}"}


@router.get("/auth/vk/callback")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def vk_callback(request: Request, response: Response, code: str = None, state: str = None, db: Session = Depends(get_db)):
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing")
    if request.cookies.get("vk_state") != state:
        raise HTTPException(status_code=400, detail="bad_state")
    cv = request.cookies.get("vk_verifier")
    if not cv:
        raise HTTPException(status_code=400, detail="bad_verifier")
    response.delete_cookie("vk_state", path="/")
    response.delete_cookie("vk_verifier", path="/")

    async with httpx.AsyncClient() as client:
        r = await client.post("https://id.vk.com/oauth2/token", data={
            "grant_type": "authorization_code",
            "client_id": settings.VK_CLIENT_ID,
            "code": code,
            "code_verifier": cv,
            "redirect_uri": settings.VK_REDIRECT_URI,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        td = r.json()

    if not td.get("access_token"):
        raise HTTPException(status_code=400, detail=td)

    vk_id = str(td.get("user_id")) if td.get("user_id") else None
    info = {}
    try:
        async with httpx.AsyncClient() as client:
            rr = await client.get(f"https://id.vk.com/oauth2/user_info?access_token={td['access_token']}&client_id={settings.VK_CLIENT_ID}")
            info = rr.json()
    except:
        pass

    if not vk_id and isinstance(info, dict):
        u = info.get("user") or info
        if isinstance(u, dict) and u.get("id"):
            vk_id = str(u["id"])

    if not vk_id:
        raise HTTPException(status_code=400, detail="no_user")

    ident = db.query(AuthIdentity).filter_by(provider="vk", provider_user_id=vk_id).first()
    user = ident.user if ident else db.query(User).filter_by(vk_id=vk_id).first()
    if not user:
        dname = "User"
        ava = None
        if isinstance(info, dict):
            u = info.get("user") or info
            if isinstance(u, dict):
                dname = f"{u.get('first_name','')} {u.get('last_name','')}".strip() or "User"
                ava = u.get("avatar")
        user = User(vk_id=vk_id, display_name=dname[:128], avatar_url=ava)
        db.add(user)
        db.flush()
        db.add(AuthIdentity(user_id=user.id, provider="vk", provider_user_id=vk_id))
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    st = create_session(db, user.id, request)
    response.set_cookie(settings.SESSION_COOKIE_NAME, st, httponly=True, samesite="lax", secure=settings.APP_ENV=="production", max_age=settings.SESSION_TTL_HOURS*3600, path="/")
    return Response(status_code=302, headers={"Location": "/cabinet"})


@router.get("/auth/me")
def auth_me(user: Optional[User] = Depends(get_current_user)):
    if not user: return {"user": None}
    return {"user": {"id": str(user.id), "display_name": user.display_name, "avatar_url": user.avatar_url, "vk_id": user.vk_id}}


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        from app.core.session import hash_session_token
        from app.models.user import UserSession
        th = hash_session_token(token)
        s = db.query(UserSession).filter_by(session_token_hash=th).first()
        if s and not s.revoked_at:
            s.revoked_at = datetime.utcnow()
            db.commit()
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}
