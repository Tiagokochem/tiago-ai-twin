---
id: project-nuvartis
title: Nuvartis, multichannel e-commerce platform
lang: en
kind: project
url: https://nuvartis.com
tags: [e-commerce, saas, multi-tenant, laravel, vue, nuxt, postgresql, marketplaces, shipping, payments, own product]
---

## Overview

Nuvartis is my own product, built and maintained by me, published at nuvartis.com. It's a multi-tenant e-commerce SaaS to sell across multiple channels from a single dashboard: each store gets its own subdomain ({store}.nuvartis.com).

## Current stage

The product is in active development, organized in sprints, and is already being tested with a real store. It has no paying customers yet.

## Features

- Integration with the Mercado Livre, Magalu and Shopee marketplaces.
- Real-time shipping quotes with Correios, Melhor Envio and carriers.
- Optimized checkout and integrated payment methods.

## Stack and architecture

- **API:** Laravel 13 on PHP 8.4, organized into Actions, Services and Contracts.
- **Admin panel:** Vue 3.
- **Storefronts:** Nuxt 4 with server-side rendering (SSR).
- **Database:** PostgreSQL 16.
- **Infra:** Docker (PHP 8.4 for the API, Node 22 for admin and storefront), with separate domains for the website, admin, API and stores.
- **Process:** sprints documented with PRD, architecture, data model, UX, plan catalog, user stories and a QA checklist.

## What it shows

Integrating multiple external APIs (marketplaces, shipping and payments) and a multi-tenant SaaS architecture in a real product, combining my e-commerce business background with software engineering.
