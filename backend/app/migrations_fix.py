# Fallback: ensure new columns/tables exist for existing DBs
from sqlalchemy import text
from app.db.session import engine


def apply_fallback_migrations():
    # These statements use PostgreSQL-specific DDL.  Other databases (used by
    # the test suite) are created from SQLAlchemy metadata instead.
    if engine.dialect.name != "postgresql":
        return
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

        # Public question library: publication fields on pools.
        for col, typ in [
            ("visibility", "VARCHAR(16) NOT NULL DEFAULT 'private'"),
            ("category", "VARCHAR(32)"),
            ("tags", "JSON"),
            ("tags_text", "VARCHAR(512)"),
            ("cover_url", "TEXT"),
            ("share_slug", "VARCHAR(32)"),
            ("published_at", "TIMESTAMP"),
            ("views_count", "INTEGER NOT NULL DEFAULT 0"),
            ("adds_count", "INTEGER NOT NULL DEFAULT 0"),
            ("source_pool_id", "UUID"),
            ("source_author_id", "UUID"),
            ("source_pool_name", "VARCHAR(128)"),
            ("source_author_name", "VARCHAR(128)"),
            ("copied_at", "TIMESTAMP"),
        ]:
            conn.execute(
                text(f"ALTER TABLE question_pools ADD COLUMN IF NOT EXISTS {col} {typ}")
            )

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_question_pools_share_slug "
                "ON question_pools (share_slug)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_pool_user_source "
                "ON question_pools (user_id, source_pool_id) "
                "WHERE source_pool_id IS NOT NULL"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_question_pools_visibility "
                "ON question_pools (visibility)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_question_pools_category "
                "ON question_pools (category)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_question_pools_source_pool_id "
                "ON question_pools (source_pool_id)"
            )
        )

        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS pool_views ("
                "id UUID PRIMARY KEY, "
                "pool_id UUID NOT NULL REFERENCES question_pools(id) ON DELETE CASCADE, "
                "viewer_key VARCHAR(80) NOT NULL, "
                "created_at TIMESTAMP, "
                "CONSTRAINT uq_pool_view UNIQUE (pool_id, viewer_key))"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_pool_views_pool_id ON pool_views (pool_id)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS pool_adds ("
                "id UUID PRIMARY KEY, "
                "pool_id UUID NOT NULL REFERENCES question_pools(id) ON DELETE CASCADE, "
                "user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "created_at TIMESTAMP, "
                "CONSTRAINT uq_pool_add UNIQUE (pool_id, user_id))"
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_pool_adds_pool_id ON pool_adds (pool_id)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_pool_adds_user_id ON pool_adds (user_id)")
        )

        # `open_to_chat` used to be a boolean question.  Adapt old answers to
        # the new single-choice values without losing their meaning.
        try:
            conn.execute(
                text(
                    "UPDATE answers SET value = '\"always\"'::json "
                    "WHERE question_id = 'open_to_chat' AND CAST(value AS text) = 'true'"
                )
            )
            conn.execute(
                text(
                    "UPDATE answers SET value = '\"not_looking\"'::json "
                    "WHERE question_id = 'open_to_chat' AND CAST(value AS text) = 'false'"
                )
            )
        except Exception:
            pass
