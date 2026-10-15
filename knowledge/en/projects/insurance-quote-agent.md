---
id: project-insurance-quote-agent
title: Insurance quote agent
lang: en
kind: project
url: https://github.com/Tiagokochem/namastex-fde-challenge
tags: [python, fastapi, ai agents, llm, openrouter, handoff, resilience, technical challenge]
---

## Problem

A fictional insurer (AutoSeguro) handles car insurance leads over WhatsApp. The sales team needed an agent that qualifies the lead, quotes a plan through an unreliable legacy API and knows when to call a salesperson, without inventing a price when the API fails.

## Solution

A Python/FastAPI agent with a simple web chat that simulates the WhatsApp conversation. A custom orchestrator collects the minimum data (age, vehicle year and plan; postal code and start date are optional), calls the quote API and decides whether to resolve the case or hand it to a human.

- **Never invents a price:** it only shows amounts that came from an HTTP 200 response.
- **Resilience:** 12 s timeout, up to 3 attempts on 5xx, timeout or network errors, with 0.5 s, 1 s and 2 s backoff. A refusal (HTTP 422) is not retried.
- **Explicit handoff criteria:** quote refused, API unavailable after retries, lead asking for a person, out-of-scope topics (claims, cancellation), competitor pressure, no progress and media it cannot process.
- **LLM with fallback:** a model through OpenRouter handles tone and data extraction; without a key it runs on heuristic extraction and template replies.
- **Traceability:** every turn writes JSONL events (message in, quote attempts, outcome, handoff, message out), with tax id, e-mail and phone numbers masked.
- I used the challenge's ~2,500 synthetic conversations to calibrate tone and objection patterns, without fine-tuning.

## My role

Technical challenge for an FDE / AI Engineer role at Namastex: agent design, handoff rules, failure resilience, execution logs and bilingual documentation.

## Stack

Python, FastAPI, OpenRouter (LLM), uv and Docker.

## Links

Code: https://github.com/Tiagokochem/namastex-fde-challenge
