# ADR 0006: WhatsApp with a dedicated bot number and owner notifications

- Status: accepted
- Date: 2026-10-14

## Context

Recruiters often prefer WhatsApp. The owner already runs Evolution API (an
unofficial WhatsApp client) on the VPS and has two numbers. Unofficial clients
carry a ban risk, and the owner's personal number must not be automated.

## Decision

- Number A (bot) is connected to Evolution and talks to recruiters through
  the same agent (`channel=whatsapp`, WhatsApp formatting, voice notes in and out).
- Number B (owner) is never connected; the bot only *sends* handoffs and
  interview summaries to it. Messages that come from number B are ignored.
- Handoff and welcome messages tell recruiters that the bot number is an
  assistant and give the owner's direct `wa.me` link.
- The webhook is authenticated with a token, returns immediately and
  processes asynchronously with deduplication, per-number debounce,
  serialization and rate limiting. `/humano` and `/novo` commands are supported.

## Consequences

- If the bot number is banned, the owner's personal number is unaffected.
- Deduplication and debounce state is in memory, so the API runs as a single
  replica; moving it to Redis would allow horizontal scaling.
- The official WhatsApp Cloud API could replace Evolution behind the same
  `WhatsAppSender` protocol.
