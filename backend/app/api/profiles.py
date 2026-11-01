import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.models.profile import Profile, Answer, DesignSettings
from app.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    AnswersUpdate,
    DesignUpdate,
    ProfileOut,
    EditInitResponse,
    PublicProfileResponse,
    EditProfileResponse,
    DesignOut,
)
from app.core.security import generate_edit_token, hash_edit_token
from app.core.utils import sanitize_slug, safe_filename, ensure_dir
from app.core.config import settings
from app.services.questions import questions_service
from app.core.rate_limit import limiter
from app.api.deps import get_profile_by_edit_token

import magic
from PIL import Image

router = APIRouter()


def _get_public_base(request: Request) -> str:
    # try forwarded/proto
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}"


@router.post("/profiles", response_model=EditInitResponse)
@limiter.limit(settings.RATE_LIMIT_CREATE_PROFILE)
def create_profile(profile_in: ProfileCreate, request: Request, db: Session = Depends(get_db)):
    slug = sanitize_slug(profile_in.slug)
    if not slug:
        raise HTTPException(status_code=400, detail="Invalid slug")
    # check uniqueness
    if db.query(Profile).filter(Profile.slug == slug).first():
        raise HTTPException(status_code=409, detail="Slug already taken")

    token, token_hash = generate_edit_token()
    profile = Profile(
        slug=slug,
        display_name=profile_in.display_name,
        bio=profile_in.bio,
        edit_token_hash=token_hash,
    )
    db.add(profile)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slug already taken")

    design = DesignSettings(profile_id=profile.id)
    db.add(design)
    db.commit()
    db.refresh(profile)
    db.refresh(design)

    base = _get_public_base(request)
    edit_url = f"{base}/edit/{token}"
    return EditInitResponse(profile=profile, edit_token=token, edit_url=edit_url)


@router.get("/profiles/{slug}/public", response_model=PublicProfileResponse)
def get_public_profile(slug: str, db: Session = Depends(get_db)):
    slug_s = sanitize_slug(slug)
    profile = db.query(Profile).filter(Profile.slug == slug_s).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    design = profile.design or DesignSettings()
    answers_qs = db.query(Answer).filter(Answer.profile_id == profile.id).all()
    answers_dict = {}
    for a in answers_qs:
        if a.hidden:
            continue
        answers_dict[a.question_id] = a.value

    categories = questions_service.get_categories()
    # filter out questions user didn't answer? keep structure but only show answered in public view? per spec: "Не отображать вопросы, на которые пользователь не ответил, если это не требуется настройкой." - we'll filter answered
    # build filtered categories
    filtered = []
    for cat in categories:
        fcat = {"id": cat["id"], "title": cat["title"], "questions": []}
        for q in cat.get("questions", []):
            if q["id"] in answers_dict:
                fcat["questions"].append(q)
        if fcat["questions"]:
            filtered.append(fcat)

    return PublicProfileResponse(profile=profile, design=design, answers=answers_dict, categories=filtered)


@router.get("/edit/me", response_model=EditProfileResponse)
def get_edit_profile(profile: Profile = Depends(get_profile_by_edit_token), db: Session = Depends(get_db)):
    design = profile.design or DesignSettings()
    answers_qs = db.query(Answer).filter(Answer.profile_id == profile.id).all()
    answers_dict = {a.question_id: {"value": a.value, "hidden": a.hidden} for a in answers_qs}
    categories = questions_service.get_categories()
    return EditProfileResponse(profile=profile, design=design, categories=categories, answers=answers_dict)


@router.put("/edit/me")
def update_profile(profile_in: ProfileUpdate, profile: Profile = Depends(get_profile_by_edit_token), db: Session = Depends(get_db)):
    if profile_in.display_name is not None:
        profile.display_name = profile_in.display_name
    if profile_in.bio is not None:
        profile.bio = profile_in.bio
    if profile_in.slug is not None:
        new_slug = sanitize_slug(profile_in.slug)
        if not new_slug:
            raise HTTPException(status_code=400, detail="Invalid slug")
        if db.query(Profile).filter(Profile.slug == new_slug, Profile.id != profile.id).first():
            raise HTTPException(status_code=409, detail="Slug already taken")
        profile.slug = new_slug
    db.commit()
    db.refresh(profile)
    return {"ok": True, "profile": profile}


@router.put("/edit/me/answers")
def update_answers(answers_in: AnswersUpdate, profile: Profile = Depends(get_profile_by_edit_token), db: Session = Depends(get_db)):
    qids = questions_service.get_question_ids()
    for item in answers_in.answers:
        if item.question_id not in qids:
            # still allow saving? spec says don't lose answers if question removed - but better to allow storing unknown? but better validate against current config; to not lose, we should allow if exists? easier to just upsert by id
            pass
        ans = db.query(Answer).filter(Answer.profile_id == profile.id, Answer.question_id == item.question_id).first()
        if ans:
            ans.value = item.value
            if item.hidden is not None:
                ans.hidden = item.hidden
        else:
            ans = Answer(profile_id=profile.id, question_id=item.question_id, value=item.value, hidden=bool(item.hidden))
            db.add(ans)
    db.commit()
    return {"ok": True}


@router.put("/edit/me/design")
def update_design(design_in: DesignUpdate, profile: Profile = Depends(get_profile_by_edit_token), db: Session = Depends(get_db)):
    design = profile.design
    if not design:
        design = DesignSettings(profile_id=profile.id)
        db.add(design)
    for k, v in design_in.model_dump(exclude_unset=True).items():
        setattr(design, k, v)
    db.commit()
    db.refresh(design)
    return {"ok": True, "design": design}


@router.post("/edit/me/avatar")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
def upload_avatar(request: Request, file: UploadFile = File(...), profile: Profile = Depends(get_profile_by_edit_token), db: Session = Depends(get_db)):
    ensure_dir(settings.UPLOAD_DIR)
    content = file.file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    # check mime
    mime = magic.from_buffer(content, mime=True)
    if mime not in settings.allowed_mimes_list:
        raise HTTPException(status_code=400, detail="Invalid file type")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raise HTTPException(status_code=400, detail="Invalid extension")

    # verify with PIL
    try:
        from io import BytesIO

        Image.open(BytesIO(content)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")

    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(content)

    profile.avatar_url = f"/uploads/{fname}"
    db.commit()
    return {"ok": True, "avatar_url": profile.avatar_url}


@router.post("/edit/me/bg")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
def upload_bg(request: Request, file: UploadFile = File(...), profile: Profile = Depends(get_profile_by_edit_token), db: Session = Depends(get_db)):
    ensure_dir(settings.UPLOAD_DIR)
    content = file.file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    mime = magic.from_buffer(content, mime=True)
    if mime not in settings.allowed_mimes_list:
        raise HTTPException(status_code=400, detail="Invalid file type")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raise HTTPException(status_code=400, detail="Invalid extension")

    try:
        from io import BytesIO

        Image.open(BytesIO(content)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")

    fname = f"bg_{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(content)

    design = profile.design
    if not design:
        design = DesignSettings(profile_id=profile.id)
        db.add(design)
    design.bg_image_url = f"/uploads/{fname}"
    db.commit()
    return {"ok": True, "bg_image_url": design.bg_image_url}


@router.get("/profiles/{slug}/json")
def export_json(slug: str, db: Session = Depends(get_db)):
    slug_s = sanitize_slug(slug)
    profile = db.query(Profile).filter(Profile.slug == slug_s).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    design = profile.design
    answers_qs = db.query(Answer).filter(Answer.profile_id == profile.id).all()
    answers = [{"question_id": a.question_id, "value": a.value, "hidden": a.hidden} for a in answers_qs]
    return {
        "profile": {"slug": profile.slug, "display_name": profile.display_name, "bio": profile.bio, "avatar_url": profile.avatar_url},
        "design": design.__dict__ if design else None,
        "answers": answers,
        "categories": questions_service.get_categories(),
    }


@router.delete("/edit/me")
@limiter.limit(settings.RATE_LIMIT_EDIT)
def delete_profile(request: Request, profile: Profile = Depends(get_profile_by_edit_token), db: Session = Depends(get_db)):
    db.delete(profile)
    db.commit()
    return {"ok": True}


@router.get("/questions")
def get_questions():
    return questions_service.get_config()
