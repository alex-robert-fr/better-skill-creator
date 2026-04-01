---
name: workflow-config
description: Configuration du workflow AI-Driven Development pour ce projet. Contrat entre le plugin et le projet — lu par tous les skills du workflow. Rempli par /setup.
user-invocable: false
---

## Plateforme

- **Git hosting** : GitHub
- **Issue tracker** : GitHub Issues
- **Branche par defaut** : main

## Commandes

- **Lint** : ruff check .
- **Format** : ruff format .
- **Test** : pytest
- **Build** : N/A (plugin, pas de build)
- **Typecheck** : N/A

## Notifications

- **Canal** : aucun
- **MCP** : aucun

## Conventions

- **Branches** : type/numero-titre
- **Commits** : emoji type(scope): description
- **PR titre** : [Type] Titre de l'issue (#numero)
