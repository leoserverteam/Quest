"""Convert legacy boolean open_to_chat answers to single-choice values

Revision ID: b7c1e4a9d2f3
Revises: f0df48b9c0fa
Create Date: 2026-11-03 15:10:00.000000

The `open_to_chat` question used to be a boolean checkbox.  It is now a
single-choice question, so old `true`/`false` answers must be mapped to the
new option values without losing their meaning:
    true  -> "always"
    false -> "not_looking"

The statement is idempotent: after the first run the stored values are JSON
strings and no longer match the boolean conditions.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7c1e4a9d2f3"
down_revision: Union[str, None] = "f0df48b9c0fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "UPDATE answers SET value = '\"always\"'::json "
            "WHERE question_id = 'open_to_chat' "
            "AND CAST(value AS text) IN ('true', '1')"
        )
        op.execute(
            "UPDATE answers SET value = '\"not_looking\"'::json "
            "WHERE question_id = 'open_to_chat' "
            "AND CAST(value AS text) IN ('false', '0')"
        )
    else:
        # SQLite and other backends store JSON as text.
        op.execute(
            "UPDATE answers SET value = '\"always\"' "
            "WHERE question_id = 'open_to_chat' "
            "AND CAST(value AS text) IN ('true', '1')"
        )
        op.execute(
            "UPDATE answers SET value = '\"not_looking\"' "
            "WHERE question_id = 'open_to_chat' "
            "AND CAST(value AS text) IN ('false', '0')"
        )


def downgrade() -> None:
    # The conversion is intentionally lossy: several choice values collapse
    # back to the old boolean.  Restore the closest boolean representation.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "UPDATE answers SET value = 'true'::json "
            "WHERE question_id = 'open_to_chat' AND CAST(value AS text) = '\"always\"'"
        )
        op.execute(
            "UPDATE answers SET value = 'false'::json "
            "WHERE question_id = 'open_to_chat' "
            "AND CAST(value AS text) NOT IN ('\"always\"', 'true', 'false', 'null')"
        )
    else:
        op.execute(
            "UPDATE answers SET value = 'true' "
            "WHERE question_id = 'open_to_chat' AND CAST(value AS text) = '\"always\"'"
        )
        op.execute(
            "UPDATE answers SET value = 'false' "
            "WHERE question_id = 'open_to_chat' "
            "AND CAST(value AS text) NOT IN ('\"always\"', 'true', 'false', 'null')"
        )
