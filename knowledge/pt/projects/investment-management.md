---
id: project-investment-management
title: Gestão de investimentos com Laravel 13 e Vue
lang: pt
kind: project
tags: [laravel, php, vue, inertia, postgresql, idempotência, desafio técnico]
---

<!-- TODO(Tiago): adicionar url do repositório. -->

## Problema

Calcular rendimento composto, imposto regressivo e resgates sem erro, e garantir que a mesma retirada não seja processada duas vezes quando a requisição se repete.

## Solução

API em Laravel 13 com camada de serviço e de domínio, interface em Inertia/Vue, prévia do imposto antes do resgate, resgate idempotente (Idempotency-Key e lock de linha no banco), notificação em fila, documentação da API e testes rodando em CI.

## Meu papel

Desenvolvimento completo num desafio técnico: back-end, front-end, Docker, testes e pipeline de CI.

## Stack

Laravel 13, PHP 8.4, Vue 3, Inertia.js, PostgreSQL, PHPUnit e GitHub Actions.
