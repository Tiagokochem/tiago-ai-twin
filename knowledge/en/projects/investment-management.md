---
id: project-investment-management
title: Investment management with Laravel 13 and Vue
lang: en
kind: project
tags: [laravel, php, vue, inertia, postgresql, idempotency, technical challenge]
---

<!-- TODO(Tiago): add repository URL. -->

## Problem

Calculate compound returns, regressive income tax and withdrawals correctly, and make sure the same withdrawal is never processed twice when a request is retried.

## Solution

A Laravel 13 API with service and domain layers, an Inertia/Vue interface, a tax preview before each withdrawal, idempotent withdrawals (Idempotency-Key header plus database row locking), queued notifications, API documentation and tests running in CI.

## My role

End-to-end development for a technical challenge: back-end, front-end, Docker, tests and CI pipeline.

## Stack

Laravel 13, PHP 8.4, Vue 3, Inertia.js, PostgreSQL, PHPUnit and GitHub Actions.
