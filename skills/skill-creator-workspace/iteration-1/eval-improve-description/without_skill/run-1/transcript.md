# Transcript — run-1 (without_skill)

**Date** : 2026-04-01  
**Approche** : Sans skill (subagent évaluation en mode direct)  
**Modèle** : claude-sonnet-4-6

---

## Tâche reçue

Améliorer la description du skill `code-reviewer` pour qu'il se déclenche aussi lors de demandes de "relecture" ou d'"audit de code".

- Description actuelle : `"Review code changes for quality and bugs."`
- Problème : déclenchement insuffisant

---

## Raisonnement interne

### Étape 1 — Comprendre le mécanisme de déclenchement des skills

Les skills Claude se déclenchent par correspondance sémantique entre la description du skill et la requête utilisateur. Plus la description contient de vocabulaire aligné avec les formulations naturelles des utilisateurs, plus le skill se déclenche.

La description actuelle contient uniquement :
- Action : "review"
- Objet : "code changes"
- But : "quality and bugs"

### Étape 2 — Identifier les cas manquants

Cas d'usage non couverts identifiés :
1. "Fais une relecture de mon code" → "review" en français non mappé, mais "proofread" serait l'équivalent en anglais
2. "Peux-tu auditer ce fichier ?" → "audit" absent de la description
3. "Analyse cette PR" → "analyze" / "pull request" absents
4. "Vérifie la qualité de cette implémentation" → "check", "inspect" absents
5. "Donne-moi du feedback sur ce code" → "feedback" absent

### Étape 3 — Construire la nouvelle description

Stratégie retenue : enrichir la description sur deux axes
1. **Verbes d'action** : review, audit, proofread, check, analyze, inspect, feedback
2. **Objets cibles** : code changes, files, pull requests

Ajouter une clause "Use when..." pour lister explicitement les déclencheurs, pratique courante dans les descriptions de skills Claude efficaces.

### Étape 4 — Vérifier la précision

S'assurer que la description ne devient pas trop générique :
- "Help with code" serait trop vague → évité
- "Work on code" serait trop vague → évité
- Les verbes retenus (audit, inspect, proofread) restent sémantiquement liés à la revue de code, pas à l'écriture ou la correction

---

## Résultat produit

**Nouvelle description :**

> Review, audit, or proofread code changes, files, or pull requests for quality, bugs, security issues, and best practices. Use when the user asks to review, audit, check, analyze, inspect, or proofread code, or when they request feedback on implementation quality.

---

## Observations sur l'approche "without_skill"

**Avantages** :
- Résultat rapide, single-pass
- Raisonnement direct sans overhead de chargement de skill

**Limites observées** :
- Pas de grille d'évaluation structurée pour mesurer la qualité de la description
- Pas de jeu de cas de test pour valider empiriquement le gain de couverture
- Pas de comparaison systématique avec d'autres formulations candidates
- La décision est basée sur le jugement du modèle sans critères formels — difficile à reproduire ou à calibrer

Ces limites sont précisément ce qu'un skill dédié (`skill-creator`) devrait adresser : processus structuré, critères explicites, évaluation multi-passes.
