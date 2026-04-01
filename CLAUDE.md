# better-skill-creator

Plugin Claude pour créer et améliorer des skills de façon plus efficace (tokens + qualité) que le skill-creator officiel d'Anthropic.

## Stack

- **Langage** : Python 3.12+
- **Lint/Format** : ruff
- **Tests** : pytest
- **Structure** : Plugin Claude (SKILL.md + scripts/ + agents/ + references/ + assets/)

## Règles critiques

- Ce projet est un **plugin Claude** — la structure `.claude-plugin/plugin.json` + `skills/` est obligatoire
- Chaque skill a son propre répertoire avec `SKILL.md` comme point d'entrée
- Les scripts Python vont dans `skills/<nom>/scripts/`
- Les fichiers de référence vont dans `skills/<nom>/references/`
- Les agents subagents vont dans `skills/<nom>/agents/`
- Les templates/assets vont dans `skills/<nom>/assets/`
- Garder le SKILL.md principal sous 500 lignes — déléguer vers des fichiers de référence si nécessaire

## Git

### Branches

Format : `type/numero-titre-court`

| Préfixe | Usage |
|---------|-------|
| `feat/` | Nouvelle fonctionnalité |
| `fix/` | Correction de bug |
| `refactor/` | Refactoring |
| `perf/` | Optimisation performance |
| `docs/` | Documentation |
| `chore/` | Maintenance / config |

- Titre en **kebab-case**, en **anglais**, max 5 mots

### Commits

Format : `emoji type(scope): description en français`

| Emoji | Type | Usage |
|-------|------|-------|
| ✨ | feat | Nouvelle fonctionnalité |
| 🐛 | fix | Correction de bug |
| ♻️ | refactor | Refactoring |
| ⚡ | perf | Optimisation performance |
| 📝 | docs | Documentation |
| 🔧 | chore | Maintenance / config |

- **Jamais** de trailer `Co-Authored-By` dans les commits

### Pull Requests

Format titre : `[Type] Titre de l'issue (#numero)`
