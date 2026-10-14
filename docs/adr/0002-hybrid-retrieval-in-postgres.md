# ADR 0002: Hybrid retrieval inside Postgres

- Status: accepted
- Date: 2026-10-14

## Context

The knowledge base is small (tens of documents, around a hundred chunks) and
bilingual. Recruiter questions mix exact names ("Nuvartis", "Laravel") with
paraphrases ("have you shipped AI to production?").

## Decision

Store chunks in Postgres with both a pgvector embedding (HNSW, cosine) and a
weighted `tsvector` using the language's text search configuration. Run both
searches and fuse them with Reciprocal Rank Fusion. Filter by the
conversation language. No separate vector database.

## Consequences

- One database for knowledge, conversations, metrics and agent checkpoints;
  simpler operations and backups on a single VPS.
- Exact terms are found by full-text even when embeddings miss them, and the
  system degrades to full-text when the embedding API is unavailable.
- Full-text uses OR semantics over stemmed terms so natural questions still
  match; RRF keeps the ranking robust without score calibration.
- The lexical-only mode doubles as a free, deterministic retrieval eval in CI.
