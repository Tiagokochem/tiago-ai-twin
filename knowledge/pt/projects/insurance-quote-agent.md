---
id: project-insurance-quote-agent
title: Agente de cotação de seguros
lang: pt
kind: project
url: https://github.com/Tiagokochem/namastex-fde-challenge
tags: [python, fastapi, agentes de ia, llm, openrouter, handoff, resiliência, desafio técnico]
---

## Problema

Uma seguradora fictícia (AutoSeguro) atende leads de seguro de veículo pelo WhatsApp. O time de vendas precisava de um agente que qualificasse o lead, cotasse um plano numa API legada instável e soubesse a hora de chamar um vendedor, sem inventar preço quando a API falha.

## Solução

Um agente em Python/FastAPI com um chat web simples que simula a conversa de WhatsApp. Um orquestrador próprio coleta os dados mínimos (idade, ano do veículo e plano; CEP e data de início são opcionais), chama a API de cotação e decide entre resolver sozinho ou passar para um humano.

- **Nunca inventa preço:** só mostra valores que vieram de uma resposta HTTP 200 da API.
- **Resiliência:** timeout de 12 s, até 3 tentativas em erro 5xx, timeout ou falha de rede, com backoff de 0,5 s, 1 s e 2 s. Uma recusa (HTTP 422) não é repetida.
- **Critérios de handoff explícitos:** cotação recusada, API indisponível depois das tentativas, lead pedindo atendente, assunto fora do escopo (sinistro, cancelamento), pressão de concorrente, conversa sem progresso e mídia que não dá para processar.
- **LLM com fallback:** usa um modelo via OpenRouter para o tom e a extração de dados; sem chave, funciona com extração heurística e respostas prontas.
- **Rastreabilidade:** cada turno grava eventos em JSONL (mensagem recebida, tentativas de cotação, resultado, handoff, resposta), com CPF, e-mail e telefone mascarados.
- Usei o histórico de cerca de 2.500 conversas sintéticas do desafio para calibrar o tom e os padrões de objeção, sem fine-tuning.

## Meu papel

Desafio técnico para uma vaga de FDE / AI Engineer na Namastex: desenho do agente, regras de handoff, resiliência a falhas, logs de execução e documentação bilíngue.

## Stack

Python, FastAPI, OpenRouter (LLM), uv e Docker.

## Links

Código: https://github.com/Tiagokochem/namastex-fde-challenge
