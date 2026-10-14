"""prompt versions, answer feedback, and LLM calls outside chat turns

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("prompt_version", sa.String(16)))
    op.add_column("chat_messages", sa.Column("feedback", sa.SmallInteger))
    op.add_column("chat_messages", sa.Column("feedback_comment", sa.Text))
    op.create_check_constraint("ck_chat_messages_feedback", "chat_messages", "feedback IN (-1, 1)")
    op.add_column("llm_calls", sa.Column("prompt", sa.String(60)))
    op.add_column(
        "llm_calls",
        sa.Column("scope", sa.String(20), nullable=False, server_default="chat"),
    )
    op.alter_column("llm_calls", "message_id", nullable=True)
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_created_at", "llm_calls")
    op.execute("DELETE FROM llm_calls WHERE message_id IS NULL")
    op.alter_column("llm_calls", "message_id", nullable=False)
    op.drop_column("llm_calls", "scope")
    op.drop_column("llm_calls", "prompt")
    op.drop_constraint("ck_chat_messages_feedback", "chat_messages")
    op.drop_column("chat_messages", "feedback_comment")
    op.drop_column("chat_messages", "feedback")
    op.drop_column("chat_messages", "prompt_version")
