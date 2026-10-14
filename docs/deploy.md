# Deploying on a VPS

The whole stack (Postgres, API, web app, Caddy) runs with Docker Compose on
one small VPS (1 vCPU / 2 GB RAM is enough). No domain is required.

## 1. Prerequisites

- Docker Engine with the Compose plugin.
- Ports **80** and **443** open to the internet (Let's Encrypt validates on 80).
- An OpenAI API key; optionally a DeepSeek key for fallback.
- Optional: an [Evolution API](https://doc.evolution-api.com/) instance with a
  dedicated WhatsApp number for the bot.

## 2. Configure

```bash
git clone https://github.com/Tiagokochem/tiago-ai-twin.git
cd tiago-ai-twin
cp .env.example .env
```

Edit `.env`:

| Variable | Value |
|---|---|
| `PUBLIC_HOST` | VPS IP in sslip.io form: `203.0.113.10` → `203-0-113-10.sslip.io` |
| `PUBLIC_URL` | `https://203-0-113-10.sslip.io` (used in links sent to you) |
| `HTTP_PORT` / `HTTPS_PORT` | `80` / `443` |
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` |
| `ADMIN_TOKEN` | `openssl rand -hex 32` |
| `OPENAI_API_KEY` | your key |
| `DEEPSEEK_API_KEY` | optional fallback |
| `EMBED_ORIGINS` | sites allowed to embed the widget, e.g. `"https://tiagokochemsite.vercel.app"` |
| `CORS_ORIGINS` | same sites, comma separated (only needed for direct API calls) |

[sslip.io](https://sslip.io) is a public wildcard DNS: `203-0-113-10.sslip.io`
resolves to `203.0.113.10`, so Caddy can obtain a real certificate without
you owning a domain. If you later buy a domain, just change `PUBLIC_HOST`.

## 3. Start

```bash
docker compose up -d --build
docker compose logs -f caddy        # wait for "certificate obtained successfully"
docker compose exec api python -m twin.rag.ingest
curl https://203-0-113-10.sslip.io/api/health
```

Migrations run automatically when the API container starts. Re-run the
ingestion (or `POST /api/v1/admin/ingest` with the admin token) whenever you
change `knowledge/`; unchanged documents are skipped.

## 4. Embed on your site

Replace your current WhatsApp button with:

```html
<script src="https://203-0-113-10.sslip.io/widget.js" data-locale="pt"
        data-whatsapp="55XXXXXXXXXXX" defer></script>
```

On a Next.js site (e.g. Vercel), use `next/script` with
`strategy="afterInteractive"` in the root layout. If the API is unreachable,
the widget falls back to a plain WhatsApp button
(`data-fallback-whatsapp`, default `data-whatsapp`).

## 5. WhatsApp (Evolution API)

Use two numbers:

- **Bot number** (A): connected to the Evolution instance; recruiters talk to it.
- **Owner number** (B): your personal WhatsApp; it only *receives* handoffs and
  interview summaries sent by the bot. Never connect your personal number to
  Evolution.

`.env`:

```bash
WHATSAPP_BOT_NUMBER=55XXXXXXXXXXX        # A
WHATSAPP_OWNER_NUMBER=55YYYYYYYYYYY      # B
EVOLUTION_API_URL=http://host.docker.internal:8080   # Evolution on the same VPS
EVOLUTION_API_KEY=<global or instance api key>
EVOLUTION_INSTANCE=<instance name>
EVOLUTION_WEBHOOK_TOKEN=$(openssl rand -hex 24)
```

If Evolution runs in another Compose project on the same host, either use
`host.docker.internal` with its published port (as above) or attach both
stacks to a shared Docker network and use the container name.

Configure the webhook for the instance (event `MESSAGES_UPSERT`):

```bash
curl -X POST "$EVOLUTION_API_URL/webhook/set/$EVOLUTION_INSTANCE" \
  -H "apikey: $EVOLUTION_API_KEY" -H "Content-Type: application/json" \
  -d '{"webhook": {"enabled": true,
        "url": "https://203-0-113-10.sslip.io/api/v1/channels/whatsapp",
        "headers": {"X-Webhook-Token": "<EVOLUTION_WEBHOOK_TOKEN>"},
        "events": ["MESSAGES_UPSERT"], "byEvents": false, "base64": true}}'
```

If your Evolution version cannot send custom headers, append
`?token=<EVOLUTION_WEBHOOK_TOKEN>` to the URL instead. The API never writes
query strings to its access log. Events from any other instance are ignored.

`base64: true` lets voice notes arrive inline; otherwise the API downloads
them through Evolution. Restart the API after editing `.env`:

```bash
docker compose up -d api
```

Recruiter commands: `/humano` (or `/human`) notifies you; `/novo` (or `/new`)
starts a new conversation. Idle interviews are closed after
`SESSION_IDLE_MINUTES` and summarized to your number.

## 6. Operate

```bash
# metrics for the last 7 days
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://<host>/api/v1/admin/metrics?days=7

# update
git pull && docker compose up -d --build

# backup
docker compose exec postgres pg_dump -U twin twin | gzip > twin-$(date +%F).sql.gz
```

Optional tracing: set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and
`LANGFUSE_BASE_URL` (Langfuse Cloud free tier or self-hosted).
