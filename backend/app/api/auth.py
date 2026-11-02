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


def _gen():
    v = secrets.token_urlsafe(32)
    c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip('=')
    return v, c


@router.get("/auth/vk/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def vk_login(request: Request, response: Response):
    st = secrets.token_urlsafe(24)
    cv, cc = _gen()
    response.set_cookie("vk_state", st, httponly=True, samesite="lax", secure=settings.APP_ENV=="production", max_age=600, path="/")
    response.set_cookie("vk_verifier", cv, httponly=True, samesite="lax", secure=settings.APP_ENV=="production", max_age=600, path="/")
    p = {"client_id": settings.VK_CLIENT_ID, "redirect_uri": settings.VK_REDIRECT_URI, "response_type": "code", "state": st, "code_challenge": cc, "code_challenge_method": "S256"}
    return {"url": "https://id.vk.com/authorize?" + urlencode(p)}


@router.get("/auth/vk/callback")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def vk_callback(request: Request, response: Response, code: str = None, state: str = None, device_id: str = None, db: Session = Depends(get_db)):
    if not code or not state or request.cookies.get("vk_state") != state:
        raise HTTPException(400)
    cv = request.cookies.get("vk_verifier")
    if not cv:
        raise HTTPException(400)
    response.delete_cookie("vk_state", path="/")
    response.delete_cookie("vk_verifier", path="/")

    base_data = {
        "grant_type": "authorization_code",
        "client_id": settings.VK_CLIENT_ID,
        "code": code,
        "code_verifier": cv,
        "redirect_uri": settings.VK_REDIRECT_URI,
    }
    if device_id:
        base_data["device_id"] = device_id

    td = None
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as cl:
        for payload in [
            base_data,
            {**base_data, "client_secret": settings.VK_CLIENT_SECRET} if getattr(settings, "VK_CLIENT_SECRET", None) else None,
        ]:
            if not payload:
                continue
            for url in ["https://id.vk.com/oauth2/token", "https://oauth.vk.com/access_token"]:
                try:
                    r = await cl.post(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
                    text = r.text
                    if text.strip().startswith("<"):
                        continue
                    try:
                        j = r.json()
                        if isinstance(j, dict) and (j.get("access_token") or j.get("user_id")):
                            td = j
                            break
                    except Exception:
                        continue
                except Exception:
                    continue
            if td:
                break

    if not isinstance(td, dict) or not td.get("access_token"):
        raise HTTPException(status_code=502, detail="vk_token_failed")
    access_token = td["access_token"]
    vk_id = td.get("user_id")
    if vk_id is not None:
        vk_id = str(vk_id)
    info = {}
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as cl:
            rr = await cl.post(
                "https://id.vk.com/oauth2/user_info",
                data={"client_id": settings.VK_CLIENT_ID, "access_token": access_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            try:
                info = rr.json()
            except Exception:
                info = {"raw": rr.text[:500]}
    except Exception:
        info = {}
    if not vk_id and isinstance(info, dict):
        u = info.get("user") or info
        if isinstance(u, dict):
            if u.get("id") is not None:
                vk_id = str(u["id"])
            elif u.get("user_id") is not None:
                vk_id = str(u["user_id"])
    if not vk_id:
        raise HTTPException(status_code=400, detail="no_user")
    ident = db.query(AuthIdentity).filter_by(provider="vk", provider_user_id=vk_id).first()
    user = ident.user if ident else db.query(User).filter_by(vk_id=vk_id).first()
    if not user:
        dname="User"; ava=None
        if isinstance(info,dict):
            u=info.get("user") or info
            if isinstance(u,dict):
                dname = f"{u.get('first_name','')} {u.get('last_name','')}".strip() or "User"
                ava=u.get("avatar")
        user = User(vk_id=vk_id, display_name=dname[:128], avatar_url=ava)
        db.add(user); db.flush()
        db.add(AuthIdentity(user_id=user.id, provider="vk", provider_user_id=vk_id))
    user.last_login_at = datetime.utcnow(); db.commit(); db.refresh(user)
    st = create_session(db,user.id,request)
    response.set_cookie(settings.SESSION_COOKIE_NAME, st, httponly=True, samesite="lax", secure=settings.APP_ENV=="production", max_age=settings.SESSION_TTL_HOURS*3600, path="/")
    return Response(status_code=302, headers={"Location": "/cabinet"})


@router.get("/auth/me")
def auth_me(user: Optional[User]=Depends(get_current_user)):
    if not user: return {"user":None}
    return {"user":{"id":str(user.id),"display_name":user.display_name,"avatar_url":user.avatar_url,"vk_id":user.vk_id}}


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response, db: Session=Depends(get_db)):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        from app.core.session import hash_session_token
        from app.models.user import UserSession
        th = hash_session_token(token)
        s = db.query(UserSession).filter_by(session_token_hash=th).first()
        if s and not s.revoked_at:
            s.revoked_at = datetime.utcnow(); db.commit()
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return {"ok":True}
