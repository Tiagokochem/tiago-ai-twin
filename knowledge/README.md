# knowledge/

Sources for the RAG pipeline. Every document exists in `pt/` and `en/` with the
same `id` (a test enforces it).

Front matter:

```yaml
id: profile            # unique per language, kebab-case
title: Perfil
lang: pt               # pt | en
kind: profile          # profile | experience | skills | education | project | faq
url: https://...       # optional, shown as a source link
tags: [laravel, ai]
draft: false           # drafts are not ingested
```

HTML comments (`<!-- ... -->`) are stripped before ingestion; use them for
TODOs and private notes. Only write facts you are comfortable showing to a
recruiter: everything here can be quoted by the twin.

After editing, run `uv run python -m twin.rag.ingest` (only changed files are
re-embedded).
