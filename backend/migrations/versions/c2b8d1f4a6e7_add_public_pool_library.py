"""Add public question-pool library

Adds publication settings, statistics and copy-origin metadata to question
pools.  Existing pools stay private by default.

Revision ID: c2b8d1f4a6e7
Revises: b7c1e4a9d2f3
Create Date: 2026-11-04 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2b8d1f4a6e7"
down_revision: Union[str, None] = "b7c1e4a9d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "question_pools",
        sa.Column("visibility", sa.String(length=16), nullable=False, server_default="private"),
    )
    op.add_column("question_pools", sa.Column("category", sa.String(length=32), nullable=True))
    op.add_column("question_pools", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("question_pools", sa.Column("tags_text", sa.String(length=512), nullable=True))
    op.add_column("question_pools", sa.Column("cover_url", sa.Text(), nullable=True))
    op.add_column("question_pools", sa.Column("share_slug", sa.String(length=32), nullable=True))
    op.add_column("question_pools", sa.Column("published_at", sa.DateTime(), nullable=True))
    op.add_column(
        "question_pools",
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "question_pools",
        sa.Column("adds_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("question_pools", sa.Column("source_pool_id", sa.UUID(), nullable=True))
    op.add_column("question_pools", sa.Column("source_author_id", sa.UUID(), nullable=True))
    op.add_column("question_pools", sa.Column("source_pool_name", sa.String(length=128), nullable=True))
    op.add_column("question_pools", sa.Column("source_author_name", sa.String(length=128), nullable=True))
    op.add_column("question_pools", sa.Column("copied_at", sa.DateTime(), nullable=True))

    op.create_index(op.f("ix_question_pools_visibility"), "question_pools", ["visibility"])
    op.create_index(op.f("ix_question_pools_category"), "question_pools", ["category"])
    op.create_index(op.f("ix_question_pools_share_slug"), "question_pools", ["share_slug"], unique=True)
    op.create_index(op.f("ix_question_pools_source_pool_id"), "question_pools", ["source_pool_id"])
    op.create_index(op.f("ix_question_pools_source_author_id"), "question_pools", ["source_author_id"])
    op.create_index(
        "uq_pool_user_source",
        "question_pools",
        ["user_id", "source_pool_id"],
        unique=True,
        postgresql_where=sa.text("source_pool_id IS NOT NULL"),
    )

    op.create_table(
        "pool_views",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pool_id", sa.UUID(), nullable=False),
        sa.Column("viewer_key", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["pool_id"], ["question_pools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "viewer_key", name="uq_pool_view"),
    )
    op.create_index(op.f("ix_pool_views_pool_id"), "pool_views", ["pool_id"])

    op.create_table(
        "pool_adds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pool_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["pool_id"], ["question_pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "user_id", name="uq_pool_add"),
    )
    op.create_index(op.f("ix_pool_adds_pool_id"), "pool_adds", ["pool_id"])
    op.create_index(op.f("ix_pool_adds_user_id"), "pool_adds", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_pool_adds_user_id"), table_name="pool_adds")
    op.drop_index(op.f("ix_pool_adds_pool_id"), table_name="pool_adds")
    op.drop_table("pool_adds")
    op.drop_index(op.f("ix_pool_views_pool_id"), table_name="pool_views")
    op.drop_table("pool_views")

    op.drop_index("uq_pool_user_source", table_name="question_pools")
    op.drop_index(op.f("ix_question_pools_source_author_id"), table_name="question_pools")
    op.drop_index(op.f("ix_question_pools_source_pool_id"), table_name="question_pools")
    op.drop_index(op.f("ix_question_pools_share_slug"), table_name="question_pools")
    op.drop_index(op.f("ix_question_pools_category"), table_name="question_pools")
    op.drop_index(op.f("ix_question_pools_visibility"), table_name="question_pools")

    op.drop_column("question_pools", "copied_at")
    op.drop_column("question_pools", "source_author_name")
    op.drop_column("question_pools", "source_pool_name")
    op.drop_column("question_pools", "source_author_id")
    op.drop_column("question_pools", "source_pool_id")
    op.drop_column("question_pools", "adds_count")
    op.drop_column("question_pools", "views_count")
    op.drop_column("question_pools", "published_at")
    op.drop_column("question_pools", "share_slug")
    op.drop_column("question_pools", "cover_url")
    op.drop_column("question_pools", "tags_text")
    op.drop_column("question_pools", "tags")
    op.drop_column("question_pools", "category")
    op.drop_column("question_pools", "visibility")
