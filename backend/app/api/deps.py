from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.profile import Profile
from app.core.security import hash_edit_token


def get_profile_by_edit_token(x_edit_token: str = Header(...), db: Session = Depends(get_db)) -> Profile:
    token_hash = hash_edit_token(x_edit_token)
    profile = db.query(Profile).filter(Profile.edit_token_hash == token_hash).first()
    if not profile:
        raise HTTPException(status_code=401, detail="Invalid edit token")
    return profile
