# Description améliorée — skill `code-reviewer`

## Description originale

```
Review code changes for quality and bugs.
```

## Description proposée

```
Review code changes for quality, correctness, and bugs. Use whenever the user asks to review, audit, proofread, or inspect code — including requests like "can you look at this code", "relecture de mon code", "audit du code", "check this for issues", "is this code good", or "give me feedback on this implementation". Trigger also when the user shares a diff, a PR, or a file and asks for an opinion on it.
```

---

## Raisonnement

### Problème de la description originale

La description originale "Review code changes for quality and bugs." est trop restrictive sur deux axes :

1. **Verbe unique** : elle se déclenche principalement sur "review" mais pas sur les synonymes courants — "relecture", "audit", "check", "inspect", "feedback", "look at".
2. **Aucun pattern de déclenchement contextuel** : elle n'indique pas à Claude dans quels contextes activer le skill (partage de diff, de PR, de fichier avec demande d'avis).

### Triggers ajoutés

| Pattern ajouté | Justification |
|---|---|
| `audit` (en/fr) | Terme courant pour une revue formelle de code |
| `relecture` | Terme français naturel pour demander une revue |
| `proofread` | Utilisé quand l'utilisateur veut vérifier son code avant merge |
| `inspect` | Variante sémantique de review |
| `"can you look at this code"` | Formulation conversationnelle très courante |
| `"is this code good"` | Question d'évaluation générale |
| `"give me feedback on this implementation"` | Demande de feedback implicite sur la qualité |
| Partage de diff/PR/fichier + demande d'avis | Contexte structurel déclencheur sans mot-clé explicite |

### Patterns couverts

- Requêtes directes : "review my code", "audit this function"
- Requêtes indirectes : "can you look at this and tell me if it's ok"
- Requêtes en français : "relecture de code", "audit du code"
- Requêtes implicites : partage d'un fichier avec "thoughts?", "what do you think?", "any issues?"
- Requêtes formelles : "code audit", "security review", "code inspection"

### Principe appliqué

Suivant le guide `skill-writing-guide.md` — pattern "Fort" : inclure les contextes de déclenchement concrets, pas seulement ce que fait le skill. La description joue le rôle de signal d'activation — elle doit être "pushy" pour éviter que Claude sous-utilise le skill sur des formulations naturelles mais non littérales.
