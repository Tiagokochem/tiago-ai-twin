---
id: project-nuvartis
title: Nuvartis, plataforma de e-commerce multicanal
lang: pt
kind: project
url: https://nuvartis.com
tags: [e-commerce, saas, multi-tenant, laravel, vue, nuxt, postgresql, marketplaces, frete, pagamentos, produto próprio]
---

## Visão geral

Nuvartis é um produto próprio, desenvolvido e mantido por mim, publicado em nuvartis.com. É uma plataforma SaaS de e-commerce multi-tenant para vender em vários canais a partir de um único painel: cada loja ganha o seu próprio subdomínio ({loja}.nuvartis.com).

## Estágio atual

O produto está em desenvolvimento ativo, organizado em sprints, e já está sendo testado com uma loja real. Ainda não tem clientes pagantes.

## Funcionalidades

- Integração com os marketplaces Mercado Livre, Magalu e Shopee.
- Cálculo de frete em tempo real com Correios, Melhor Envio e transportadoras.
- Checkout otimizado e meios de pagamento integrados.

## Stack e arquitetura

- **API:** Laravel 13 com PHP 8.4, organizada em Actions, Services e Contracts.
- **Painel administrativo:** Vue 3.
- **Vitrine das lojas:** Nuxt 4 com renderização no servidor (SSR).
- **Banco:** PostgreSQL 16.
- **Infra:** Docker (PHP 8.4 na API e Node 22 no painel e na vitrine), com domínios separados para site, painel, API e lojas.
- **Processo:** sprints documentados com PRD, arquitetura, modelo de dados, UX, catálogo de planos, histórias e checklist de QA.

## O que o projeto demonstra

Integração com várias APIs externas (marketplaces, frete e pagamentos) e arquitetura SaaS multi-tenant num produto real, unindo minha experiência de negócio em e-commerce com engenharia de software.
