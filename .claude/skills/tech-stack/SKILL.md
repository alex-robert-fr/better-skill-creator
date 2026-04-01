---
name: tech-stack
description: Stack technique et conventions de code du projet. Utiliser lors de l'ecriture ou la revue de code pour respecter les standards et la stack du projet.
user-invocable: false
---

## Stack technique

### Scripts / Outillage
- **Langage** : Python 3.12+
- **Lint + Format** : ruff (remplace flake8 + isort + black en un seul outil)
- **Tests** : pytest

### Structure plugin Claude
- **Point d'entrée** : `SKILL.md` (frontmatter YAML + instructions Markdown)
- **Scripts** : `scripts/` — code Python déterministe et réutilisable
- **Agents** : `agents/` — instructions pour les subagents spécialisés
- **Références** : `references/` — docs chargées en contexte selon les besoins
- **Assets** : `assets/` — templates, HTML, fichiers statiques

## Git

- **Branche par defaut** : main

## Architecture

- **Pattern** : Plugin Claude (Progressive Disclosure — 3 niveaux de chargement)
  1. Metadata (name + description) — toujours en contexte
  2. SKILL.md body — chargé quand le skill est déclenché
  3. Bundled resources — chargés à la demande

## Conventions de nommage

| Contexte | Convention |
|----------|-----------|
| Fichiers | `kebab-case` |
| Code Python (variables, fonctions) | `snake_case` |
| Classes Python | `PascalCase` |

## Règles de qualité

- Pas de commentaires évidents — le code doit se lire seul
- Chaque fichier créé ou modifié doit être dans un état propre et committable
- Pas de `print()` de debug oublié
- Pas d'import inutilisé
- Typage Python explicite sur les fonctions publiques
