# Guide d'écriture de skills

Référence condensée pour écrire un SKILL.md efficace.

---

## Anatomie d'un skill

```
skill-name/
├── SKILL.md                ← requis, <500 lignes
├── scripts/                ← code Python déterministe et réutilisable
├── agents/                 ← instructions pour les subagents spécialisés
├── references/             ← docs chargées en contexte selon les besoins
└── assets/                 ← templates, HTML, fichiers statiques
```

## Frontmatter obligatoire

```yaml
---
name: mon-skill
description: Ce que fait le skill ET quand l'utiliser. Mécanisme de déclenchement principal.
---
```

### Écrire une bonne description

La description est ce que Claude lit pour décider d'activer le skill. Règles :

1. **Une seule ligne** — ne jamais utiliser `>` ou `|` YAML, même pour les longues descriptions
2. **Phrase naturelle** — pas une liste de mots-clés séparés par virgules
3. **"Pushy"** — inclure des contextes de déclenchement concrets, pas seulement ce que fait le skill
4. **≤500 caractères** — au-delà, chaque mot compte moins

**Faible** : `"How to build a dashboard."`

**Moyen** (bloc YAML — à éviter) :
```yaml
description: >
  Build a dashboard to display data. Use when: dashboards,
  data visualization, internal metrics, display data.
```

**Fort** (phrase naturelle sur une ligne) :
```yaml
description: Build a dashboard to display internal data. Use whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of data — even without the word "dashboard".
```

---

## Progressive Disclosure — 3 niveaux

1. **Metadata** (name + description) — toujours en contexte, ~100 tokens
2. **SKILL.md body** — chargé quand le skill est déclenché, idéalement <500 lignes
3. **Bundled resources** — chargés à la demande, taille illimitée

Si le SKILL.md approche 500 lignes, ajouter une couche hiérarchique avec des renvois clairs
vers les fichiers de référence.

---

## Patterns d'écriture

### Définir le format de sortie

```markdown
## Format de sortie
TOUJOURS utiliser ce template exact :
# [Titre]
## Résumé
## Points clés
## Recommandations
```

### Exemples

```markdown
## Format de commit
**Exemple 1 :**
Input : Ajout de l'authentification JWT
Output : ✨ feat(auth): implémenter l'authentification JWT
```

### Organisation multi-domaines

Quand un skill supporte plusieurs frameworks/contextes :

```
cloud-deploy/
├── SKILL.md        ← workflow + sélection du référentiel
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

Claude ne lit que le fichier pertinent.

---

## Style

- **Forme impérative** dans les instructions : "Lire le fichier", "Sauvegarder dans..."
- **Expliquer le pourquoi** plutôt que d'imposer des MUST : les LLMs modernes comprennent le
  raisonnement et s'adaptent mieux qu'avec des règles rigides
- **ALWAYS/NEVER en majuscules** = signal d'alarme — essayer de reformuler en expliquant
  la raison
- Structures trop rigides = sur-ajustement à des exemples précis — privilégier la généralisation

---

## Bundler des scripts

Si plusieurs runs de test produisent indépendamment le même helper script, c'est un signal fort
pour le bundler dans `scripts/` et demander au skill de l'utiliser. Chaque future invocation
bénéficie du script sans le réinventer.
