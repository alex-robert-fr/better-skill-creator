# Description améliorée — skill `code-reviewer`

## Description actuelle

```
Review code changes for quality and bugs.
```

## Description proposée

```
Review, audit, or proofread code changes, files, or pull requests for quality, bugs, security issues, and best practices. Use when the user asks to review, audit, check, analyze, inspect, or proofread code, or when they request feedback on implementation quality.
```

---

## Raisonnement

### Problème identifié

La description originale est trop restrictive pour deux raisons :

1. **Vocabulaire limité** : "Review code changes" ne couvre que le mot "review" associé à "changes". Les moteurs de déclenchement des skills Claude se basent sur la similarité sémantique entre la description et la requête utilisateur. Les variantes comme "relire", "auditer", "analyser", "inspecter", "vérifier" ne sont pas représentées.

2. **Périmètre trop étroit** : "code changes" implique des diffs/modifications, alors que l'utilisateur peut vouloir faire auditer un fichier existant, une PR, ou une implémentation complète — pas forcément des "changements".

### Stratégie d'amélioration

- **Enrichissement du vocabulaire d'action** : ajout de `audit`, `proofread`, `check`, `analyze`, `inspect`, `feedback` — tous des synonymes courants dans les demandes de revue de code.
- **Élargissement du périmètre objet** : `files`, `pull requests` en plus de `changes` pour couvrir les cas d'usage réels.
- **Ajout de l'axe qualité** : `security issues`, `best practices` précisent le type de feedback attendu, ce qui renforce l'alignement avec les requêtes utilisateur qui mentionnent ces aspects.
- **Clause d'activation explicite** : la deuxième phrase ("Use when...") liste les verbes déclencheurs clés, ce qui améliore la précision du matching sans rendre la description trop générique.

### Ce qui a été évité

- Ne pas utiliser une description trop vague comme "Help with code" qui déclencherait le skill de façon intempestive.
- Ne pas lister tous les langages de programmation, ce qui allongerait inutilement la description sans apport sémantique.
