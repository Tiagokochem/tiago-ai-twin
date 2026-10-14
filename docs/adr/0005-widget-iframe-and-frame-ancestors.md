# ADR 0005: Widget as a Shadow DOM launcher plus an iframe

- Status: accepted
- Date: 2026-10-14

## Context

The chat must replace the WhatsApp button on an existing Vercel site without
style conflicts, offer a choice between chatting in place and WhatsApp, and
never expose API keys. A "public widget key" sent from the browser is not a
secret and can be copied by any site.

## Decision

`widget.js` is a dependency-free script that renders a launcher and a choice
menu inside a Shadow DOM. "Chat here" opens an iframe pointing to
`/[lang]/embed`, which reuses the full React interview UI with
`channel=widget`. Caddy sends `Content-Security-Policy: frame-ancestors 'self'
<EMBED_ORIGINS>` on the embed route only (and `'self'` elsewhere). The script
probes `/api/health` and degrades to a plain WhatsApp button when the API is
unreachable.

## Consequences

- Complete CSS and JS isolation; one UI codebase for the site, the widget and
  the full page.
- Embedding is restricted by the browser, using a header the embedding site
  cannot forge, instead of a copyable key.
- API calls from the iframe are same-origin, so CORS stays closed by default.
- Abuse is still bounded by per-IP rate limits and per-session budgets.
