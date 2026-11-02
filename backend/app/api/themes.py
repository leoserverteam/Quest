from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.session import require_user
from app.db.session import get_db
from app.models.user import User
from app.models.pools import SavedTheme
from app.models.profile import Profile, DesignSettings

router = APIRouter()

PRESETS = {
    "Minimal": {"preset": "minimal", "bg_type": "color", "bg_color": "#ffffff", "text_color": "#1a1a1a", "heading_color": "#000000", "accent_color": "#333333", "card_color": "#f7f7f7", "radius": "8px", "card_blur": "0px", "card_shadow": "none"},
    "Midnight": {"preset": "midnight", "bg_type": "color", "bg_color": "#000814", "text_color": "#e0e1dd", "heading_color": "#ffffff", "accent_color": "#00b4d8", "card_color": "#001d3d", "radius": "10px"},
    "Cyberpunk": {"preset": "cyberpunk", "bg_type": "color", "bg_color": "#0a0a0f", "text_color": "#00ff9f", "heading_color": "#ff00ff", "accent_color": "#ff3366", "card_color": "#11111b", "radius": "0px", "card_shadow": "0 0 20px rgba(255,0,255,0.3)"},
    "Vaporwave": {"preset": "vaporwave", "bg_type": "gradient", "bg_gradient": "linear-gradient(135deg, #ff71ce 0%, #01cdfe 50%, #b967ff 100%)", "text_color": "#2d1b69", "heading_color": "#ff71ce", "accent_color": "#01cdfe", "card_color": "rgba(255,255,255,0.6)", "radius": "16px", "card_blur": "8px"},
    "Y2K": {"preset": "y2k", "bg_type": "gradient", "bg_gradient": "linear-gradient(180deg, #a3d9ff 0%, #ffd1dc 100%)", "text_color": "#1f1f1f", "heading_color": "#ff6b9d", "accent_color": "#7c3aed", "card_color": "rgba(255,255,255,0.7)", "radius": "20px"},
    "Pastel": {"preset": "pastel", "bg_type": "color", "bg_color": "#fef7ff", "text_color": "#4a4a4a", "heading_color": "#333333", "accent_color": "#a78bfa", "card_color": "#ffffff", "radius": "16px"},
    "Glassmorphism": {"preset": "glass", "bg_type": "gradient", "bg_gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "text_color": "#ffffff", "heading_color": "#ffffff", "accent_color": "#ffffff", "card_color": "rgba(255,255,255,0.15)", "radius": "16px", "card_blur": "12px", "card_border_width": "1px", "card_border_color": "rgba(255,255,255,0.3)"},
    "Brutalism": {"preset": "brutal", "bg_type": "color", "bg_color": "#f5f5f5", "text_color": "#000000", "heading_color": "#000000", "accent_color": "#000000", "card_color": "#ffffff", "radius": "0px", "card_border_width": "2px", "card_border_color": "#000000"},
    "Nature": {"preset": "nature", "bg_type": "color", "bg_color": "#f1f8e9", "text_color": "#2e7d32", "heading_color": "#1b5e20", "accent_color": "#4caf50", "card_color": "#ffffff", "radius": "12px"},
    "Retro Web": {"preset": "retro", "bg_type": "color", "bg_color": "#c0c0c0", "text_color": "#000000", "heading_color": "#000080", "accent_color": "#0000ff", "card_color": "#ffffff", "radius": "0px", "font_family": "Courier New, monospace"},
}


@router.get("/themes/presets")
def get_presets():
    return PRESETS


@router.get("/themes")
def list_themes(user: User = Depends(require_user), db: Session = Depends(get_db)):
    themes = db.query(SavedTheme).filter(SavedTheme.user_id == user.id).all()
    return [{"id": str(t.id), "name": t.name, "config": t.config} for t in themes]


@router.post("/themes")
def save_theme(data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    name = data.get("name") or "Моя тема"
    config = data.get("config") or {}
    theme = SavedTheme(user_id=user.id, name=name[:128], config=config)
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return {"id": str(theme.id)}


@router.delete("/themes/{theme_id}")
def delete_theme(theme_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    theme = db.query(SavedTheme).filter(SavedTheme.id == theme_id, SavedTheme.user_id == user.id).first()
    if not theme:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(theme)
    db.commit()
    return {"ok": True}


@router.post("/profiles/{profile_id}/apply-theme")
def apply_theme(profile_id: str, data: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    config = data.get("config") or {}
    design = profile.design
    if not design:
        design = DesignSettings(profile_id=profile.id)
        db.add(design)
    for k, v in config.items():
        if hasattr(design, k):
            setattr(design, k, v)
    db.commit()
    return {"ok": True}
