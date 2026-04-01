---
name: pipe-changelog
description: Générer ou mettre à jour le CHANGELOG.md depuis les commits git et les tags. Analyse automatiquement les commits depuis le dernier tag, les catégorise (feat, fix, breaking change, perf, docs, etc.) et produit un fichier CHANGELOG.md structuré au format Keep a Changelog avec versionnement SemVer. Utiliser après une série de commits ou avant de créer une PR/release, quand l'utilisateur demande "génère le changelog", "mets à jour le changelog", "crée le CHANGELOG depuis les commits", ou lance /pipe-changelog.
---

# pipe-changelog

Génère ou met à jour `CHANGELOG.md` depuis les commits git en respectant
[Keep a Changelog](https://keepachangelog.com) et [SemVer](https://semver.org).

Démarre directement sans poser de questions sauf si des informations critiques manquent.

---

## 1. Détecter le contexte

```bash
# Dernier tag existant
git describe --tags --abbrev=0 2>/dev/null || echo "aucun tag"

# Commits depuis le dernier tag (ou tous les commits si pas de tag)
git log $(git describe --tags --abbrev=0 2>/dev/null)..HEAD --oneline 2>/dev/null \
  || git log --oneline
```

Si un `CHANGELOG.md` existe déjà, le lire pour comprendre le format utilisé et la
dernière version enregistrée — ne pas écraser, ajouter une nouvelle section en tête.

---

## 2. Analyser et catégoriser les commits

Parser chaque ligne de `git log` pour identifier le **type** de changement.

### Mapping des types vers les sections Keep a Changelog

| Préfixe commit | Section CHANGELOG |
|----------------|-------------------|
| `feat`, `✨` | **Added** |
| `fix`, `🐛` | **Fixed** |
| `perf`, `⚡` | **Changed** (amélioration) |
| `refactor`, `♻️` | **Changed** |
| `docs`, `📝` | **Documentation** (omis si peu pertinent) |
| `chore`, `🔧` | Omettre sauf si impact utilisateur |
| `BREAKING CHANGE` (corps) ou `!` après le type | **Breaking Changes** |
| `deprecate` | **Deprecated** |
| `remove` | **Removed** |
| `security` | **Security** |

**Règle BREAKING CHANGE** : chercher `BREAKING CHANGE:` dans le corps du commit
**ou** un `!` juste avant les `:` (ex: `feat!: ...`). Ces commits vont TOUJOURS en tête
de la section, quelle que soit leur catégorie d'origine.

---

## 3. Déterminer la version

Si aucune version n'est fournie explicitement, inférer via SemVer depuis les commits analysés :

- Au moins un BREAKING CHANGE → **MAJOR** bump
- Au moins un `feat` sans breaking → **MINOR** bump
- Uniquement des `fix`, `perf`, `docs`, `chore` → **PATCH** bump

Exemples depuis `v1.2.3` :
- BREAKING → `v2.0.0`
- feat → `v1.3.0`
- fix only → `v1.2.4`

Si aucun tag précédent n'existe, démarrer à `v0.1.0`.

---

## 4. Rédiger les entrées

Chaque entrée doit être :
- **Orientée utilisateur** : décrire l'impact, pas l'implémentation technique
- **Concise** : une ligne par commit en général, deux lignes max si clarification nécessaire
- **Sans le hash** ni le préfixe de type (ils disparaissent dans le changelog)

Transformer :
```
✨ feat(auth): ajouter la connexion via Google OAuth
```
En :
```
- Ajout de la connexion via Google OAuth
```

Pour les BREAKING CHANGES, toujours inclure une note de migration si possible :
```
- **BREAKING** : La méthode `getUser()` renvoie désormais une Promise. Remplacer par `await getUser()`.
```

---

## 5. Format de sortie

```markdown
# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Versionnement Sémantique](https://semver.org/lang/fr/).

## [Unreleased]

## [X.Y.Z] - YYYY-MM-DD

### Breaking Changes
- ...

### Added
- ...

### Fixed
- ...

### Changed
- ...

### Deprecated
- ...

### Removed
- ...

### Security
- ...

[Unreleased]: https://github.com/owner/repo/compare/vX.Y.Z...HEAD
[X.Y.Z]: https://github.com/owner/repo/compare/vX.Y.Z-1...vX.Y.Z
```

**Ne pas inclure** les sections vides. Si aucun commit dans une catégorie, omettre la section.

---

## 6. Comportement selon le contexte

### Cas 1 : Premier changelog (pas de CHANGELOG.md, pas de tags)
Analyser tous les commits du repo. Créer `CHANGELOG.md` depuis zéro.
Suggérer une version initiale `v0.1.0` ou `v1.0.0` selon la maturité du projet.

### Cas 2 : Mise à jour d'un changelog existant
Lire le CHANGELOG.md existant pour identifier la dernière version.
Ajouter la nouvelle section **en tête du fichier** (après le titre et le paragraphe d'intro),
sans toucher aux sections précédentes.

### Cas 3 : Version spécifiée explicitement
L'utilisateur a fourni `v2.1.0` ou `--version 2.1.0` → utiliser cette version directement,
sans inférer via SemVer.

### Cas 4 : Plage de commits personnalisée
Si l'utilisateur précise `depuis v1.0.0` ou `entre v1.0.0 et v1.2.0` :
```bash
git log v1.0.0..v1.2.0 --oneline
```

---

## 7. Écrire le fichier

Écrire ou mettre à jour `CHANGELOG.md` à la racine du projet (ou dans le répertoire
spécifié par l'utilisateur).

Afficher un résumé :
```
CHANGELOG mis à jour — version v1.3.0
  • 3 nouvelles fonctionnalités (Added)
  • 5 corrections (Fixed)
  • 1 changement Breaking
```

---

## Edge cases

- **Commits sans préfixe conventionnel** : les inclure dans "Changed" avec leur message
  brut, en signalant à l'utilisateur qu'ils n'ont pas pu être catégorisés automatiquement.
- **Merges commits** : ignorer les `Merge branch '...'` et `Merge pull request #...`,
  sauf si le corps contient des informations utiles.
- **Repo sans remote** : omettre les liens de comparaison en bas du fichier.
- **Tags non-SemVer** : si le dernier tag n'est pas au format `vX.Y.Z`, le noter et
  demander confirmation avant de continuer.
