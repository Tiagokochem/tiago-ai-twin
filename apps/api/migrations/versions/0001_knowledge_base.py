"""knowledge base: documents and chunks with pgvector + full-text

Revision ID: 0001
Revises:
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("key", sa.String(200), primary_key=True),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("lang", sa.String(5), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("url", sa.String(500)),
        sa.Column("tags", postgresql.ARRAY(sa.String(80)), nullable=False, server_default="{}"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_documents_lang", "documents", ["lang"])
    op.create_index("ix_documents_kind", "documents", ["kind"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "document_key",
            sa.String(200),
            sa.ForeignKey("documents.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ord", sa.Integer, nullable=False),
        sa.Column("heading", sa.String(300), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("tsv", postgresql.TSVECTOR, nullable=False),
    )
    op.create_index("ix_chunks_document_key", "chunks", ["document_key"])
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute("CREATE INDEX ix_chunks_tsv_gin ON chunks USING gin (tsv)")


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("documents")
