---
id: project-other-projects
title: Other projects and studies on GitHub
lang: en
kind: project
url: https://github.com/Tiagokochem
tags: [github, portfolio, ai agents, langchain, langgraph, mcp, laravel, integrations, technical challenges, studies]
---

## Overview

Besides my main projects, I keep smaller projects, technical challenges and studies on GitHub (https://github.com/Tiagokochem). These are the most relevant ones, grouped by theme, with what each one actually does. Public LangChain / LangGraph projects in this list: medical-appointment-langgraph and autonomous-langchain-mcp-filesystem (LangChain.js). Tiago AI (this assistant) also uses LangGraph and is documented separately.

## Agents and AI applications

- **Medical appointment assistant with LangGraph** (https://github.com/Tiagokochem/medical-appointment-langgraph): a Node.js API with Fastify and TypeScript that books and cancels appointments through conversation. Its core is a LangGraph workflow with intent detection, action execution and reply generation nodes; graph state is validated with Zod, models are reached through OpenRouter and appointments are stored in SQLite.
- **Autonomous agent with LangChain.js and MCP** (https://github.com/Tiagokochem/autonomous-langchain-mcp-filesystem): a LangGraph pipeline (intent parser and agent) that uses tools over the Model Context Protocol: the official filesystem MCP server to read and write files and a MongoDB MCP server, plus a local CSV-to-JSON tool. Exposed through a Fastify API, with optional LangSmith tracing.
- **AI Code Reviewer** (https://github.com/Tiagokochem/ai-code-reviewer): a full-stack app with a React frontend, a Go backend and n8n workflows. It reviews pasted code with the OpenAI API (with a mock mode when there is no key), returns a quality score and suggestions, applies the conventions of 11 languages and sends results to n8n for storage and automation. Runs on Docker.
- **Product recommendations with TensorFlow.js** (https://github.com/Tiagokochem/ecommerce-recommendations-tensorflow): an in-browser demo store that trains a TensorFlow.js model in a Web Worker from purchase history, with normalized features (category, color, price and buyer age) and training visualization.
- **Multimodal AI demo in the browser** (https://github.com/Tiagokochem/web-ai-translate): questions with an attached image or audio answered by the browser's built-in Web AI API, with no backend, adjustable temperature and top K, and automated tests.
- **Chat with the OpenAI API** (https://github.com/Tiagokochem/chat-gpt): a technical challenge with a NestJS, TypeORM and MySQL backend and a React, TypeScript and Tailwind frontend, storing users, messages and history. Runs on Docker.
- **AI post generator** (https://github.com/Tiagokochem/ia-post-creator): a Laravel 12 API and a React (Vite) frontend that write social media posts with the OpenAI API.

## Laravel, integrations and technical challenges

- **FansAPI** (https://github.com/Tiagokochem/fansapi): a Laravel 13 service with Redis and Horizon that refreshes profiles from an external API. It solves a realistic incident: when the upstream response changes shape, the service keeps the last valid data instead of storing zero, isolates a rate-limited account so it cannot starve the others, and documents queue timeouts, replays, observability and a scaling plan.
- **Shopify integration** (https://github.com/Tiagokochem/shopifyintegration): product synchronization with Laravel 11, GraphQL (Laravel Lighthouse) and Nuxt 3, following SOLID and clean architecture, with PHPUnit tests and Playwright end-to-end tests, all on Docker.
- **Starian** (https://github.com/Tiagokochem/Starian): a refactoring challenge on a deliberately badly structured task app with Angular and Laravel; I improved structure, separation of concerns and reliability without overengineering a simple CRUD, and documented how I used AI (Cursor) in the delivery.
- **E-commerce catalog** (https://github.com/Tiagokochem/ecommerceLaravelReact): a Laravel REST API on PHP 8.4 (Services, Repositories, API Resources and Sanctum), a React frontend with MUI and MySQL, orchestrated with Docker Compose.
- **Product search** (https://github.com/Tiagokochem/product-search): Laravel 11 with Livewire 3 and PostgreSQL, with combined filters, multi-select, filters persisted in the URL, sorting, pagination, debounced search and PHPUnit tests.
- **Entrega Express** (https://github.com/Tiagokochem/entregaexpress): a delivery system in Laravel 12 with Jetstream (Inertia), Vue 3, MySQL and Redis, where companies post deliveries and couriers accept or decline them from a dashboard.
- **Payment integrations:** a Flutter app with a Laravel panel integrated with Pagar.me (https://github.com/Tiagokochem/EFoodPagarme) and Laravel projects with Mercado Pago (https://github.com/Tiagokochem/LaravelMercadoPago).

## Other platforms

- **PagRent:** a rental management system with repositories for the Laravel backend (https://github.com/Tiagokochem/back), the Vue frontend (https://github.com/Tiagokochem/front) and the Docker infrastructure with Nginx and a blue-green deploy setup (https://github.com/Tiagokochem/infra).
- **Pixeat** (https://github.com/Tiagokochem/pixeat): a monorepo with a Laravel API and a Flutter mobile app.

## Studies

My GitHub also has studies and course projects since 2022: Flutter (apps with GetX), Node.js with TypeScript and Express (Gama Academy projects), Vue.js, C# with ASP.NET Core MVC, Docker and several Laravel CRUDs.
