# Fallback: ensure new columns/tables exist for existing DBs
from sqlalchemy import text
from app.db.session import engine


def apply_fallback_migrations():
    with engine.begin() as conn:
        # profiles extensions
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS user_id UUID"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS owner_bound_at TIMESTAMP"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_edited_via VARCHAR(16)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_profiles_user_id ON profiles (user_id)"))

        # design_settings extensions
        for col, typ in [
            ("bg_type", "VARCHAR(16) DEFAULT 'color'"),
            ("bg_gradient", "TEXT"),
            ("bg_position", "VARCHAR(32) DEFAULT 'center'"),
            ("bg_size", "VARCHAR(16) DEFAULT 'cover'"),
            ("bg_overlay_opacity", "VARCHAR(8) DEFAULT '0'"),
            ("bg_overlay_color", "VARCHAR(16) DEFAULT '#000000'"),
            ("font_family", "VARCHAR(64) DEFAULT 'Inter, system-ui, sans-serif'"),
            ("font_size", "VARCHAR(8) DEFAULT '16px'"),
            ("heading_size", "VARCHAR(8) DEFAULT '28px'"),
            ("line_height", "VARCHAR(8) DEFAULT '1.6'"),
            ("card_opacity", "VARCHAR(8) DEFAULT '1'"),
            ("card_blur", "VARCHAR(8) DEFAULT '0px'"),
            ("card_border_width", "VARCHAR(8) DEFAULT '0px'"),
            ("card_border_color", "VARCHAR(16) DEFAULT '#ffffff'"),
            ("card_shadow", "TEXT"),
            ("button_color", "VARCHAR(16)"),
            ("link_color", "VARCHAR(16)"),
            ("icon_color", "VARCHAR(16)"),
            ("avatar_style", "VARCHAR(16) DEFAULT 'circle'"),
            ("avatar_size", "VARCHAR(8) DEFAULT '80px'"),
            ("profile_align", "VARCHAR(16) DEFAULT 'left'"),
            ("content_width", "VARCHAR(12) DEFAULT '760px'"),
            ("gap", "VARCHAR(8) DEFAULT '16px'"),
            ("extra", "JSON"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE design_settings ADD COLUMN IF NOT EXISTS {col} {typ}"))
            except Exception:
                pass
