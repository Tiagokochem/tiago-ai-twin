# ADR 0007: Versioned prompt templates tied to every answer and eval

- Status: accepted
- Date: 2026-10-14

## Context

Prompts were Python string constants formatted with `str.format`. A change
to a prompt was invisible in production data: when answer quality or cost
moved, there was no way to tell which prompt produced a given answer, and
eval reports could not be compared across prompt changes. A missing format
variable failed only at runtime, and shared rules (grounding, citations) were
duplicated between prompts.

## Decision

- Prompts are Jinja2 templates in `agent/prompts/templates/`, loaded by a
  `PromptRegistry` with `StrictUndefined`. Shared rules live in partials
  (`_grounding.j2`) included by the templates that need them.
- Each template is versioned by a short hash of its source plus the shared
  partials; the registry version is a hash over all templates. Versions are
  derived from content, so nobody has to remember to bump them.
- `render(name, **vars)` returns a `Prompt` with the text and a
  `name@version` ref. The ref is passed to the LLM gateway and stored on
  every `llm_calls` row; the registry version is stored on every assistant
  message, sent in the `done` event (shown as `prompts@…` in the UI trace)
  and written to every eval report and to `evals/reports/history.jsonl`.
- Untrusted content (sources, job descriptions) is never interpolated into
  the system prompt; it is sent as a separate message wrapped in tags the
  prompt declares as data.

## Consequences

- A quality, latency or cost regression can be grouped by prompt version in
  SQL and matched to the commit in the eval history.
- Any whitespace change creates a new version; this is intended, since the
  model sees whitespace too.
- Prompts are not editable at runtime; changing one is a code change that
  goes through review and CI (tests render every template with
  `StrictUndefined`). A prompt-management service (e.g. Langfuse prompts)
  could later replace the file loader behind the same registry interface.
