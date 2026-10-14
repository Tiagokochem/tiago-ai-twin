---
id: project-insurance-quote-agent
title: Insurance quote agent
lang: en
kind: project
tags: [python, ai agents, llm, whatsapp, handoff, resilience, technical challenge]
---

<!-- TODO(Tiago): add repository URL and frameworks used (LangGraph?). -->

## Problem

A sales team handles insurance leads on WhatsApp and needs to qualify them, produce quotes and know when to bring in a salesperson, without making up prices when the quote API fails.

## Solution

An agent that talks to the lead, collects the vehicle data, calls the quote API and decides whether to handle the case itself or hand it over to a human. It handles infrastructure failures and keeps an execution log.

## My role

Technical challenge for an AI Engineer position: agent design, handoff rules and failure resilience.

## Stack

Python, AI agents, LLMs, Docker and WhatsApp.
