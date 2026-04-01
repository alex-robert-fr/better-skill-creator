---
name: changelog-generator
description: Generate a structured CHANGELOG.md from git commits since the last tag. Use whenever the user wants to generate, update, or create a changelog, document what changed between releases, categorize commits by type (feat, fix, breaking change), or produce release notes from git history — even without the word "changelog".
---

# Changelog Generator

Analyse les commits git depuis le dernier tag et génère un `CHANGELOG.md` structuré, catégorisé et lisible.

---

## Workflow

### Étape 1 : Détecter le point de départ

Trouver le dernier tag git pour délimiter la plage de commits :

```bash
git describe --tags --abbrev=0 2>/dev/null || echo "NO_TAG"
```

- Si un tag existe : analyser les commits depuis ce tag jusqu'à HEAD
- Si aucun tag : analyser tous les commits du dépôt

```bash
# Avec tag
git log <dernier-tag>..HEAD --pretty=format:"%H|%s|%b|%an|%ad" --date=short

# Sans tag
git log --pretty=format:"%H|%s|%b|%an|%ad" --date=short
```

### Étape 2 : Catégoriser les commits

Analyser chaque message de commit selon les conventions Conventional Commits :

| Catégorie | Patterns détectés | Section CHANGELOG |
|-----------|------------------|-------------------|
| Breaking changes | `BREAKING CHANGE` dans le corps, `!` après le type (ex: `feat!:`) | `### Breaking Changes` |
| Nouvelles fonctionnalités | `feat:`, `feat(...):`  | `### Features` |
| Corrections de bugs | `fix:`, `fix(...):` | `### Bug Fixes` |
| Performance | `perf:`, `perf(...):` | `### Performance` |
| Refactoring | `refactor:`, `refactor(...):` | `### Refactoring` |
| Documentation | `docs:`, `docs(...):` | `### Documentation` |
| Maintenance | `chore:`, `ci:`, `build:`, `test:` | `### Chores` |
| Autres | tout le reste | `### Other Changes` |

Pour les commits avec scope `(auth):`, `(api):`, etc., conserver le scope dans l'entrée.

**Commits à ignorer** : merges automatiques (`Merge branch`, `Merge pull request`), commits de version bump.

### Étape 3 : Déterminer la version

Si un argument de version est fourni (`v1.2.0`), l'utiliser directement.

Sinon, proposer une version selon SemVer basée sur les commits analysés :
- Breaking changes détectés → bump majeur
- Features sans breaking → bump mineur
- Fixes uniquement → bump patch

Afficher la version proposée et la logique avant d'écrire.

### Étape 4 : Générer le CHANGELOG.md

#### Cas 1 — Pas de CHANGELOG.md existant

Créer le fichier avec l'en-tête standard et la première entrée.

#### Cas 2 — CHANGELOG.md existant

Insérer la nouvelle version **en haut**, après l'en-tête `# Changelog`, en conservant l'historique intact.

#### Format de sortie

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-04-01

### Breaking Changes

- `auth`: remove legacy token format support — migration required ([abc1234])

### Features

- `api`: add pagination to list endpoints ([def5678])
- support dark mode in dashboard ([ghi9012])

### Bug Fixes

- fix race condition in session refresh ([jkl3456])
- `ui`: correct button alignment on mobile ([mno7890])

### Chores

- update dependencies to latest versions ([pqr1234])

[1.2.0]: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
```

**Règles de formatage :**
- Chaque entrée : `- <description courte et lisible> ([<sha court>])`
- Supprimer les préfixes de type des messages (`feat:`, `fix:` → déjà dans la section)
- Conserver le scope entre backticks si présent
- Capitaliser la première lettre de chaque entrée
- Ajouter le lien de comparaison en bas si l'URL remote est disponible

Pour récupérer l'URL remote :
```bash
git remote get-url origin 2>/dev/null
```

---

## Inputs optionnels

| Argument | Description | Exemple |
|----------|-------------|---------|
| Version cible | Forcer une version spécifique | `v2.0.0` |
| Plage de commits | Remplacer la détection auto du tag | `v1.0.0..v1.1.0` |
| Fichier de sortie | Chemin alternatif | `RELEASES.md` |
| Depuis le début | Ignorer les tags, tout inclure | `--all` |

---

## Exemples de déclenchement

- "Génère le changelog depuis le dernier tag"
- "Mets à jour le CHANGELOG.md pour la release 2.1.0"
- "Quels changements depuis v1.5.0 ?"
- "Prépare les release notes pour cette version"
- "Documente les changements depuis la dernière release"

---

## Edge cases

**Dépôt sans tags** : générer un changelog complet depuis l'initial commit, proposer `v0.1.0` comme version initiale.

**Commits non-conventionnels** : les classer dans `### Other Changes` sans les ignorer — ils représentent du travail réel.

**Historique vide** (aucun commit depuis le dernier tag) : informer l'utilisateur, ne pas créer d'entrée vide.

**Plusieurs tags au même commit** : prendre le plus récent.

**Branches** : n'analyser que les commits de la branche courante.
