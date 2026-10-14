---
id: project-insurance-quote-agent
title: Agente de cotação de seguros
lang: pt
kind: project
tags: [python, agentes de ia, llm, whatsapp, handoff, resiliência, desafio técnico]
---

<!-- TODO(Tiago): adicionar url do repositório e frameworks usados (LangGraph?). -->

## Problema

Um time de vendas atende leads de seguro pelo WhatsApp e precisa qualificar, cotar e saber a hora de chamar um vendedor, sem inventar preço quando a API de cotação falha.

## Solução

Um agente que conversa com o lead, coleta os dados do veículo, consulta a API de cotação e decide entre resolver sozinho ou passar para um humano. Ele trata falhas de infraestrutura e registra um log de execução.

## Meu papel

Desafio técnico para uma vaga de AI Engineer: desenho do agente, regras de handoff e resiliência a falhas.

## Stack

Python, agentes de IA, LLM, Docker e WhatsApp.
