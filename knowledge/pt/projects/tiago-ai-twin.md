---
id: project-tiago-ai-twin
title: Tiago AI, este Digital Twin
lang: pt
kind: project
url: https://github.com/Tiagokochem/tiago-ai-twin
tags: [python, fastapi, langgraph, langchain, rag, pgvector, nextjs, whatsapp, open source]
---


## Visão geral

Tiago AI é o assistente com quem você está conversando: um projeto open source de Agentic AI que permite a recrutadores me entrevistarem por chat, voz ou WhatsApp quando não estou online. Ele responde apenas com base em fontes reais (currículo, projetos, site) e cita essas fontes. Quando não sabe a resposta, ou quando o assunto é proposta e salário, ele me chama. A orquestração usa LangGraph, biblioteca do ecossistema LangChain.

## Arquitetura

- Backend em Python com FastAPI e LangGraph (ecossistema LangChain), com um fluxo controlado de guarda, roteamento de intenção, recuperação, avaliação de relevância e resposta.
- RAG híbrido no PostgreSQL com pgvector (busca vetorial) e full-text search, com documentos em português e inglês.
- OpenAI como provedor principal e DeepSeek como fallback.
- Frontend em Next.js, widget embutível no meu site e canal WhatsApp via Evolution API, todos usando o mesmo agente.

## Engenharia

Avaliação automatizada do RAG (hit@k, MRR e fidelidade das respostas) no CI, observabilidade de latência, tokens e custo por etapa, e segurança com rate limit, proteção contra prompt injection e chaves apenas no backend.

## Links

Código aberto: https://github.com/Tiagokochem/tiago-ai-twin
