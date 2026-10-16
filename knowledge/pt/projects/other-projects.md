---
id: project-other-projects
title: Outros projetos e estudos no GitHub
lang: pt
kind: project
url: https://github.com/Tiagokochem
tags: [github, portfólio, agentes de ia, langchain, langgraph, mcp, laravel, integrações, desafios técnicos, estudos]
---

## Visão geral

Além dos projetos principais, mantenho no GitHub (https://github.com/Tiagokochem) projetos menores, desafios técnicos e estudos. Abaixo estão os mais relevantes, agrupados por tema, com o que cada um realmente faz. Projetos públicos com LangChain / LangGraph nesta lista: medical-appointment-langgraph e autonomous-langchain-mcp-filesystem (LangChain.js). O Tiago AI (este assistente) também usa LangGraph e está documentado à parte.

## Agentes e aplicações com IA

- **Assistente de agendamento médico com LangGraph** (https://github.com/Tiagokochem/medical-appointment-langgraph): API em Node.js com Fastify e TypeScript que marca e cancela consultas por conversa. O núcleo é um fluxo LangGraph com nós de detecção de intenção, execução da ação e geração da resposta; o estado do grafo é validado com Zod, os modelos são acessados pelo OpenRouter e as consultas ficam em SQLite.
- **Agente autônomo com LangChain.js e MCP** (https://github.com/Tiagokochem/autonomous-langchain-mcp-filesystem): pipeline LangGraph (interpretação de intenção e agente) que usa ferramentas via Model Context Protocol: o servidor MCP oficial de filesystem para ler e gravar arquivos e um servidor MCP de MongoDB, além de uma ferramenta local de conversão de CSV para JSON. Exposto por uma API Fastify, com tracing opcional no LangSmith.
- **AI Code Reviewer** (https://github.com/Tiagokochem/ai-code-reviewer): aplicação full stack com frontend React, backend em Go e workflows n8n. Analisa código colado na interface com a API da OpenAI (com modo simulado sem chave), dá uma nota de qualidade e sugestões, considera as convenções de 11 linguagens e envia o resultado ao n8n para armazenamento e automação. Roda com Docker.
- **Recomendação de produtos com TensorFlow.js** (https://github.com/Tiagokochem/ecommerce-recommendations-tensorflow): loja de demonstração no navegador que treina um modelo com TensorFlow.js em um Web Worker a partir do histórico de compras, com atributos normalizados (categoria, cor, preço e idade do comprador) e visualização do treino.
- **Demo de IA multimodal no navegador** (https://github.com/Tiagokochem/web-ai-translate): perguntas com imagem ou áudio anexado respondidas pela Web AI API do próprio navegador, sem backend, com ajuste de temperatura e top K e testes automatizados.
- **Chat com a API da OpenAI** (https://github.com/Tiagokochem/chat-gpt): desafio técnico com backend NestJS, TypeORM e MySQL e frontend React com TypeScript e Tailwind, guardando usuários, mensagens e histórico. Roda com Docker.
- **Gerador de posts com IA** (https://github.com/Tiagokochem/ia-post-creator): API em Laravel 12 e frontend React (Vite) que geram textos para redes sociais com a API da OpenAI.

## Laravel, integrações e desafios técnicos

- **FansAPI** (https://github.com/Tiagokochem/fansapi): serviço em Laravel 13 com Redis e Horizon que atualiza perfis vindos de uma API externa. Resolve um incidente realista: quando o formato da resposta muda, o serviço preserva o último dado válido em vez de gravar zero, isola uma conta limitada por rate limit para ela não travar as outras e documenta timeouts de fila, reprocessamento, observabilidade e um plano de escala.
- **Integração com a Shopify** (https://github.com/Tiagokochem/shopifyintegration): sincronização de produtos com Laravel 11, GraphQL (Laravel Lighthouse) e Nuxt 3, com princípios SOLID, arquitetura limpa, testes PHPUnit e testes de ponta a ponta com Playwright, tudo em Docker.
- **Starian** (https://github.com/Tiagokochem/Starian): teste técnico de refatoração de uma aplicação de tarefas propositalmente mal estruturada, com Angular e Laravel; melhorei estrutura, separação de responsabilidades e confiabilidade sem complicar um CRUD simples, e documentei o uso de IA (Cursor) na entrega.
- **Catálogo de e-commerce** (https://github.com/Tiagokochem/ecommerceLaravelReact): API REST em Laravel com PHP 8.4 (Services, Repositories, API Resources e Sanctum), frontend React com MUI e MySQL, orquestrados com Docker Compose.
- **Busca de produtos** (https://github.com/Tiagokochem/product-search): Laravel 11 com Livewire 3 e PostgreSQL, com filtros combinados, seleção múltipla, filtros persistidos na URL, ordenação, paginação, busca com debounce e testes PHPUnit.
- **Entrega Express** (https://github.com/Tiagokochem/entregaexpress): sistema de entregas em Laravel 12 com Jetstream (Inertia), Vue 3, MySQL e Redis, em que empresas cadastram entregas e entregadores aceitam ou recusam pelo painel.
- **Integrações de pagamento:** app Flutter com painel Laravel integrado ao Pagar.me (https://github.com/Tiagokochem/EFoodPagarme) e projetos Laravel com Mercado Pago (https://github.com/Tiagokochem/LaravelMercadoPago).

## Outras plataformas

- **PagRent:** sistema de gestão de aluguéis com repositórios de backend em Laravel (https://github.com/Tiagokochem/back), frontend em Vue (https://github.com/Tiagokochem/front) e infraestrutura em Docker com Nginx e configuração de deploy blue-green (https://github.com/Tiagokochem/infra).
- **Pixeat** (https://github.com/Tiagokochem/pixeat): monorepo com API em Laravel e aplicativo mobile em Flutter.

## Estudos

O GitHub também tem estudos e projetos de curso desde 2022: Flutter (apps com GetX), Node.js com TypeScript e Express (projetos da Gama Academy), Vue.js, C# com ASP.NET Core MVC, Docker e vários CRUDs em Laravel.
