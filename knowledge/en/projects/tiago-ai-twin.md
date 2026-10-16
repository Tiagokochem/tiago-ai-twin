---
id: project-tiago-ai-twin
title: Tiago AI, this Digital Twin
lang: en
kind: project
url: https://github.com/Tiagokochem/tiago-ai-twin
tags: [python, fastapi, langgraph, langchain, rag, pgvector, nextjs, whatsapp, open source]
---


## Overview

Tiago AI is the assistant you're talking to: an open source Agentic AI project that lets recruiters interview me by chat, voice or WhatsApp when I'm offline. It only answers from real sources (résumé, projects, website) and cites them. When it doesn't know the answer, or when the topic is offers or salary, it brings me in. Orchestration uses LangGraph, a library in the LangChain ecosystem.

## Architecture

- Python backend with FastAPI and LangGraph (LangChain ecosystem), using a controlled flow of guarding, intent routing, retrieval, relevance grading and answering.
- Hybrid RAG on PostgreSQL with pgvector (vector search) plus full-text search, over documents in Portuguese and English.
- OpenAI as the primary provider and DeepSeek as the fallback.
- Next.js frontend, an embeddable widget on my website and a WhatsApp channel via Evolution API, all sharing the same agent.

## Engineering

Automated RAG evaluation (hit@k, MRR and answer faithfulness) in CI, observability of latency, tokens and cost per step, and security with rate limiting, prompt-injection protection and keys kept on the backend only.

## Links

Open source code: https://github.com/Tiagokochem/tiago-ai-twin
