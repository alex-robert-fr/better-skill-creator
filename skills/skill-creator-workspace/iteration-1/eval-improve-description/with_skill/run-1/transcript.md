# Transcript — eval-improve-description / with_skill / run-1

**Date** : 2026-04-01  
**Skill activé** : skill-creator  
**Tâche** : Améliorer la description du skill `code-reviewer` pour augmenter son taux de déclenchement

---

## Étape 1 — Lecture du SKILL.md

Lecture de `/data/arobert/PROJECTS/APPS/better-skill-creator/skills/skill-creator/SKILL.md`.

Section pertinente identifiée : **Description Optimization** (lignes 242–283).

Le skill indique que la description est "le mécanisme de déclenchement" et qu'une mauvaise description = skill ignoré. Il préconise d'être "pushy" et de s'appuyer sur le guide `references/skill-writing-guide.md`.

---

## Étape 2 — Lecture du guide d'écriture

Lecture de `/data/arobert/PROJECTS/APPS/better-skill-creator/skills/skill-creator/references/skill-writing-guide.md`.

Pattern clé extrait :

> **Faible** : "How to build a dashboard."  
> **Fort** : "How to build a dashboard to display internal data. Use whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of data — even without the word 'dashboard'."

---

## Étape 3 — Analyse de la description existante

**Description originale** : `Review code changes for quality and bugs.`

**Problèmes identifiés** :
- Verbe unique "review" — ne couvre pas "audit", "relecture", "inspect", "check", "feedback"
- Absence de patterns contextuels (partage de diff/PR/fichier + demande d'avis)
- Formulation passive, non directive — ne guide pas Claude vers le déclenchement

---

## Étape 4 — Génération de la description améliorée

**Approche** : enrichir la description avec :
1. Les synonymes courants du verbe "review" (en anglais et en français)
2. Des formulations conversationnelles naturelles
3. Des contextes structurels implicites (diff, PR, fichier partagé)

**Description proposée** :

```
Review code changes for quality, correctness, and bugs. Use whenever the user asks to review, audit, proofread, or inspect code — including requests like "can you look at this code", "relecture de mon code", "audit du code", "check this for issues", "is this code good", or "give me feedback on this implementation". Trigger also when the user shares a diff, a PR, or a file and asks for an opinion on it.
```

---

## Résultat

Fichier `improved_description.md` créé avec la nouvelle description et le raisonnement complet.

**Estimation d'impact** : couverture des triggers passant de ~1 formulation explicite à ~8 patterns distincts (synonymes + formulations conversationnelles + français + contextes implicites).
