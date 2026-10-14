# Tiago AI — web app

Next.js 16 (App Router, React 19, Tailwind v4, Motion) frontend for the
digital twin.

- `app/[lang]/page.tsx` — landing page (pt/en, locale from `proxy.ts`)
- `app/[lang]/interview` — chat, voice mode, job fit and the agent "glass box"
- `app/[lang]/embed` — compact interview used by the widget iframe
- `public/widget.js` — embeddable launcher (Shadow DOM, no dependencies)
- `lib/api.ts`, `lib/use-interview.ts`, `lib/use-voice.ts` — API client, SSE
  chat state and audio recording/playback

```bash
npm install
API_PROXY_URL=http://localhost:8000 npm run dev   # proxies /api to the FastAPI app
npm run lint && npm run build
```

In Docker the app runs as a standalone server behind Caddy, which routes
`/api/*` to the API. See the [root README](../../README.md).
