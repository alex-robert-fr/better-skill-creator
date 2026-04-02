---
name: skill-creator
description: Create new skills, improve existing skills, and measure skill performance with decision-driven benchmarking. Use when creating a skill from scratch, updating or optimizing an existing skill, running evals, benchmarking multiple skill versions against each other or against vanilla Claude, optimizing a skill's trigger description, or when the user wants to compare iterations and decide which direction to take. Trigger on any request involving skill authoring, skill testing, skill evals, skill iteration, skill packaging, comparing skill versions, or reviewing benchmark results.
---

# Skill Creator

Crée des skills, les améliore par itération mesurée, et optimise leur déclenchement.

**Philosophie** : chaque benchmark existe pour prendre une décision.
On ne mesure pas pour mesurer — on mesure pour savoir quoi garder, quoi jeter, et quoi
prioriser ensuite. Le livrable final d'un cycle de benchmark n'est pas un rapport de stats,
c'est un **brief de décision structuré** que l'utilisateur colle dans la prochaine session.

Détermine où en est l'utilisateur dans le processus et démarre directement à la bonne étape.

---

## 1. Capture d'intention

Commence par répondre à ces 5 questions. Si la conversation contient déjà des éléments de
réponse, extrais-les — l'utilisateur confirme, il ne ressaisit pas.

1. **But** : que doit permettre de faire ce skill ?
2. **Déclenchement** : quelles phrases ou contextes doivent l'activer ?
3. **Format de sortie** : quel est le livrable attendu ?
4. **Tests** : des outputs objectivement vérifiables ? (fichiers générés, transformations de
   données, workflows en étapes fixes → oui ; style d'écriture, design → non)
5. **Priorités** : qu'est-ce qui compte le plus — la qualité du résultat, la vitesse
   d'exécution, le coût en tokens, la précision du déclenchement ? Demander un ordre.
   Ce classement pilotera toutes les décisions d'optimisation.

---

## 2. Interview & Research

Pose les questions bloquantes sur les edge cases, formats d'input, fichiers d'exemple et
critères de succès. Ne pas passer à l'écriture avant d'avoir ces éléments.

Si des MCPs sont disponibles et utiles pour la recherche (docs, skills existants, bonnes
pratiques), lancer les recherches en parallèle via subagents avant de rédiger.

---

## 3. Écriture du SKILL.md

Rédiger le SKILL.md avec :

- **`name`** : identifiant du skill
- **`description`** : mécanisme de déclenchement principal. **Chaîne sur une seule ligne**
  (ne jamais utiliser `>` ou `|` YAML). Écrire comme une phrase naturelle qui couvre ce que
  fait le skill ET les contextes d'activation — "pushy" mais lisible, ≤500 caractères.

  ✓ `description: Do X. Use when the user asks to Y, Z, or mentions W — even without the word "X".`
  ✗ `description: >\n  Do X.\n  Use when: Y, Z, W.`

- **`compatibility`** : outils ou dépendances requis (rarement nécessaire)
- **Corps** : instructions, format de sortie, exemples, renvois vers les fichiers bundlés

Garder le SKILL.md sous 500 lignes. Si on approche la limite, déléguer vers `references/`.

---

## 4. Test cases

Rédiger 2-3 prompts réalistes — ce qu'un vrai utilisateur écrirait. Les partager avec
l'utilisateur pour validation avant de lancer les runs.

**Important :** sauvegarder aussi les evals dans le répertoire `outputs/` de chaque run lors
de la création (voir boucle d'évaluation). Les prompts doivent être génériques — éviter les
chemins spécifiques à l'environnement local (`/tmp/test-...`, `/home/user/...`).

Sauvegarder dans `evals/evals.json` (dans le répertoire du skill) :

```json
{
  "skill_name": "mon-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "Prompt réaliste avec contexte concret",
      "expected_output": "Description du résultat attendu",
      "files": [],
      "expectations": []
    }
  ]
}
```

Ne pas écrire les assertions maintenant — elles seront rédigées pendant les runs.
Schéma complet dans `references/schemas.md`.

---

## Boucle d'évaluation

Séquence continue — ne pas s'arrêter à mi-chemin.

### Étape 1 : Lancer tous les runs en parallèle (même turn)

Pour chaque test case, lancer en parallèle :

- Un run **with_skill** (avec le skill actuel)
- Un run **without_skill** (vanilla, sans skill) — référence fixe sur toutes les itérations

Si on compare plusieurs versions de skill, ajouter un run par version supplémentaire
(ex : `skill_v1`, `skill_v2`). Toujours lancer tout en parallèle dans le même turn.

**Workspace** : `<skill-name>-workspace/` en sibling du répertoire du skill.
**Organisation** : `iteration-<N>/eval-<name>/<config>/run-<M>/`

Prompt pour chaque subagent :

```
Execute this task:
- Skill path: <path-to-SKILL.md> (omit for without_skill)
- Task: <eval prompt>
- Input files: <eval files or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<name>/<config>/run-1/outputs/
- Outputs to save: <ce que l'utilisateur veut — fichier généré, CSV, etc.>
- Save metrics to: <workspace>/iteration-<N>/eval-<name>/<config>/run-1/outputs/metrics.json
  Format: {"tool_calls": {...}, "total_tool_calls": N, "total_steps": N,
           "files_created": [...], "errors_encountered": N,
           "output_chars": N, "transcript_chars": N}
```

Écrire un `eval_metadata.json` pour chaque eval (assertions vides pour l'instant) :

```json
{
  "eval_id": 1,
  "eval_name": "nom-descriptif",
  "prompt": "Le prompt",
  "assertions": []
}
```

### Étape 2 : Pendant les runs — rédiger les assertions

Ne pas attendre que les runs terminent. Rédiger les assertions pour chaque test case
et les expliquer à l'utilisateur.

Bonnes assertions : objectivement vérifiables, discriminantes (échouent si le skill n'aide pas).
Mauvaises assertions : triviales (passent même sans le skill), non vérifiables depuis les outputs.

Mettre à jour `eval_metadata.json` et `evals/evals.json` avec les assertions rédigées.

### Étape 3 : Capturer le timing à la complétion de chaque run

**Immédiat** : quand un subagent termine, sa notification contient `total_tokens` et
`duration_ms`. Ces données ne sont pas persistées — les sauvegarder tout de suite dans
`<run-dir>/timing.json` :

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

### Étape 4 : Grader, agréger, lancer le dashboard de décision

Une fois tous les runs terminés :

**1. Grader** — spawner un subagent grader par run (ou grader inline si peu de runs).
Lire `agents/grader.md` avant de spawner. Résultat dans `<run-dir>/grading.json`.
Pour les assertions vérifiables programmatiquement, écrire et exécuter un script
plutôt que d'évaluer à l'œil.

**2. Agréger** — générer le benchmark :

```bash
python -m scripts.aggregate_benchmark <workspace>/iteration-N \
  --skill-name <nom>
```

Produit `benchmark.json` et `benchmark.md`. Le benchmark inclut automatiquement :

- `token_efficiency` : delta tokens / delta pass_rate (KPI principal)
- `analyst_notes` : patterns non-discriminants, variance élevée, trade-offs

**3. Injecter les priorités utilisateur** dans le benchmark :

Avant de lancer le viewer, écrire un `user_priorities.json` dans le workspace :

```json
{
  "priorities": ["quality", "speed", "cost", "trigger_accuracy"],
  "thresholds": {
    "quality": 0.85,
    "speed": null,
    "cost": null,
    "trigger_accuracy": 0.9
  },
  "source": "captured at step 1"
}
```

Ce fichier est lu par le dashboard pour pré-remplir le classement des priorités.

**4. Lancer le dashboard de décision** — tuer l'ancienne instance si elle tourne,
puis relancer :

```bash
SKILL_CREATOR_PATH=$(dirname $(dirname $(realpath $0)))

kill $(lsof -ti :8765) 2>/dev/null; sleep 1

PYTHONPATH="$SKILL_CREATOR_PATH" nohup python3 "$SKILL_CREATOR_PATH/scripts/generate_review.py" \
  <workspace>/iteration-N \
  --skill-name "mon-skill" \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --priorities <workspace>/user_priorities.json \
  --previous-workspace <workspace>/iteration-N-1 \
  > /tmp/viewer-<nom>.log 2>&1 &
VIEWER_PID=$!
```

**Important :** passer `--previous-workspace` même à l'itération 2 pour que le dashboard
affiche la comparaison multi-itérations.

Dire à l'utilisateur :

> J'ai ouvert le dashboard dans ton navigateur.
>
> **Ce qu'il faut faire :**
>
> 1. **Overview** — lis les verdicts automatiques en haut pour voir si le skill va bien
> 2. **Evals** — annote chaque test : 👍 si ça te plaît, 👎 si ça doit changer (+ commentaire optionnel)
> 3. **Trigger** — vérifie les requêtes mal classées et décide pour chaque : corriger / acceptable / retirer
> 4. **Sidebar** — choisis ton itération préférée, vérifie tes priorités, et regarde la complétude
> 5. **Exporter** — clique "Exporter mes décisions" quand t'as fini, et colle le résumé ici
>
> Prends ton temps, tes décisions sont sauvegardées automatiquement.

### Étape 5 : Lire les décisions (PAS juste du feedback)

Quand l'utilisateur revient, il colle soit le résumé markdown, soit on lit `decisions.json` :

```json
{
  "metadata": {
    "skill_name": "mon-skill",
    "exported_at": "2025-07-15T16:00:00Z",
    "completeness": 0.78
  },
  "chosen_iteration": {
    "iteration": 3,
    "reason": null
  },
  "optimization_priorities": [
    {
      "rank": 1,
      "priority": "quality",
      "label": "Qualité (pass rate)",
      "minimum_threshold": 0.85
    },
    {
      "rank": 2,
      "priority": "speed",
      "label": "Vitesse",
      "minimum_threshold": null
    },
    {
      "rank": 3,
      "priority": "cost",
      "label": "Coût (tokens)",
      "minimum_threshold": null
    },
    {
      "rank": 4,
      "priority": "trigger_accuracy",
      "label": "Précision trigger",
      "minimum_threshold": 0.9
    }
  ],
  "eval_annotations": [
    {
      "eval_id": 1,
      "eval_name": "Creates valid PDF",
      "verdict": "approve",
      "comment": null
    },
    {
      "eval_id": 2,
      "eval_name": "Handles edge cases",
      "verdict": "reject",
      "comment": "Trop lent"
    }
  ],
  "critical_assertions": [
    {
      "eval_id": 1,
      "assertion": "PDF has correct headers",
      "priority": "critical"
    }
  ],
  "trigger_decisions": [
    {
      "query": "Write a fibonacci function",
      "expected": false,
      "got": true,
      "decision": "fix"
    },
    {
      "query": "Help me with my resume",
      "expected": false,
      "got": true,
      "decision": "acceptable"
    }
  ],
  "general_notes": "Le skill est trop agressif sur les triggers..."
}
```

**Interpréter chaque section :**

| Section                        | Action                                                                                                                                                                                              |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `chosen_iteration`             | Partir de la description de cette itération comme base                                                                                                                                              |
| `optimization_priorities`      | Respecter cet ordre dans tous les trade-offs. Si `quality` est #1, ne JAMAIS dégrader le pass rate pour gagner des tokens. Si `speed` est #1, un gain de vitesse vaut une légère baisse de qualité. |
| `eval_annotations.approve`     | Ces comportements sont VERROUILLÉS — ne pas les casser en itérant                                                                                                                                   |
| `eval_annotations.reject`      | Ce sont les problèmes à résoudre. Lire le commentaire pour comprendre le "pourquoi"                                                                                                                 |
| `critical_assertions`          | Ces assertions sont non-négociables. Elles doivent passer à 100% dans TOUTES les itérations futures. Les intégrer comme contraintes dures.                                                          |
| `trigger_decisions.fix`        | La description doit être modifiée pour corriger ces cas                                                                                                                                             |
| `trigger_decisions.acceptable` | Ignorer ces erreurs — l'utilisateur les considère comme du bruit                                                                                                                                    |
| `trigger_decisions.remove`     | Retirer ces queries de l'eval set — elles ne sont pas pertinentes                                                                                                                                   |
| `general_notes`                | Direction générale à intégrer                                                                                                                                                                       |

**Fallback** : si l'utilisateur colle du feedback libre au lieu du format structuré
(ex: "j'aime bien l'itération 3 mais c'est trop lent"), extraire les décisions implicites
et les confirmer avant de continuer.

Stopper le serveur viewer :

```bash
kill $VIEWER_PID 2>/dev/null
```

---

## Améliorer le skill

C'est le cœur de la boucle. L'amélioration est maintenant **pilotée par les décisions**,
pas par l'intuition.

### Ordre de résolution (dicté par les priorités)

1. **Contraintes dures d'abord** : les assertions marquées `critical` doivent passer.
   Si une d'entre elles échoue, c'est le problème #1 — peu importe les priorités.

2. **Evals rejetés (👎)** : résoudre en respectant l'ordre des priorités.
   - Si priorité #1 = qualité → améliorer le résultat même si ça coûte plus de tokens
   - Si priorité #1 = vitesse → trouver un chemin plus rapide, quitte à simplifier
   - Si priorité #1 = coût → réduire les tokens, chercher les raccourcis

3. **Triggers à corriger** : modifier la description pour fixer les FP/FN marqués `fix`.
   Ignorer les `acceptable`. Retirer les `remove` de l'eval set.

4. **Evals validés (👍)** : ne PAS toucher au code qui fait passer ces tests.
   Écrire un commentaire dans le SKILL.md si un passage est critique à préserver.

### Principes d'amélioration

**Respecter la hiérarchie des priorités** : chaque modification est évaluée à travers le
prisme des priorités utilisateur. Si `quality > speed > cost`, une modification qui
améliore la vitesse mais dégrade la qualité de 2% est REJETÉE.

**Généraliser** : le skill sera utilisé sur des milliers de prompts différents. Une correction
qui ne fonctionne que pour les exemples testés est inutile. Chercher la règle générale
derrière le problème observé.

**Rester lean** : supprimer ce qui n'apporte pas de valeur. Lire les transcripts — si le skill
fait perdre du temps sur des étapes non productives, supprimer ces étapes. Chaque ligne de
SKILL.md qui ne change pas le comportement consomme des tokens pour rien.

**Expliquer le pourquoi** : préférer "voici pourquoi X est important" à "ALWAYS do X".
Les LLMs modernes s'adaptent mieux avec du raisonnement qu'avec des règles rigides.

**Bundler les helpers répétés** : si plusieurs runs ont indépendamment produit le même
script helper, le bundler dans `scripts/` et demander au skill de l'utiliser.

**Token efficiency** : comparer `token_efficiency` entre itérations. Sauf si la priorité #1
est la qualité pure, une amélioration de qualité qui double les tokens est suspecte.

### Boucle d'itération

1. Résumer les décisions reçues en un plan d'action concret (3-5 bullet points max)
2. Demander confirmation à l'utilisateur : "Voici ce que je vais faire, ça te va ?"
3. Appliquer les améliorations au skill
4. Relancer tous les runs dans `iteration-<N+1>/` (with_skill + without_skill)
5. **Vérifier les contraintes dures AVANT de lancer le viewer** :
   - Les assertions critiques passent-elles toutes ? Si non, corriger immédiatement.
   - Les evals 👍 tiennent-ils toujours ? Si régression, revert et trouver une autre approche.
6. Lancer le dashboard de décision avec `--previous-workspace`
7. Attendre les nouvelles décisions de l'utilisateur
8. Répéter jusqu'à :
   - L'utilisateur est satisfait (toutes les annotations sont 👍)
   - Feedback "Exporter et conclure" — passer au packaging
   - Plus de progrès mesurable (pass_rate et token_efficiency stagnent)

### Rapport d'itération

Avant de lancer le viewer, résumer à l'utilisateur ce qui a changé :

```
## Itération 3 → 4 : résumé des changements

**Tes décisions appliquées :**
- ✅ "Handles edge cases" (👎) → refactorisé le parsing de tableaux, +15% pass rate
- ✅ Assertion critique "PDF has correct headers" → maintenant 100% (était 80%)
- ✅ Trigger FP "Write a fibonacci function" → corrigé dans la description

**Tes validations préservées :**
- ✅ "Creates valid PDF" (👍) → toujours 100%, pas de régression

**Impact sur tes priorités :**
- 🎯 Qualité : 78% → 92% (+14%) ✓ au-dessus de ton seuil de 85%
- ⚡ Vitesse : 12.3s → 13.1s (+0.8s) — léger surcoût acceptable
- 🪙 Tokens : 4500 → 4800 (+300) — contenu

**Ouvre le dashboard pour reviewer et prendre tes prochaines décisions.**
```

---

## Description Optimization

La description est le mécanisme de déclenchement. Une mauvaise description = skill ignoré.

### Étape 1 : Générer le eval set

Créer 20 queries réalistes :

- 10 **should-trigger** : diverses formulations, certaines sans mentionner le skill
  explicitement, quelques cas peu communs, cas où ce skill concurrence un autre mais doit
  gagner
- 10 **should-not-trigger** : near-misses — même vocabulaire mais contexte différent,
  cas ambigus où un match naïf déclencherait mais ne devrait pas

Qualité des queries : concrètes, avec contexte. Éviter les queries trop évidentes.

### Étape 2 : Review avec l'utilisateur

Lire `assets/eval_review_trigger.html`, remplacer les placeholders :

- `__EVAL_DATA_PLACEHOLDER__` → JSON array du eval set
- `__SKILL_NAME_PLACEHOLDER__` → nom du skill
- `__SKILL_DESCRIPTION_PLACEHOLDER__` → description courante

Écrire dans `/tmp/eval_trigger_<skill-name>.html` et ouvrir.
L'utilisateur édite et clique "Export Eval Set" → `~/Downloads/eval_set.json`.

### Étape 3 : Lancer la boucle d'optimisation

```bash
python -m scripts.run_loop \
  --eval-set <path>/eval_set.json \
  --skill-path <path/to/skill> \
  --model <model-id-de-cette-session> \
  --max-iterations 5 \
  --verbose
```

Le script : split 60/40 train/test stratifié, évalue la description courante (3 runs/query),
appelle Claude extended thinking pour améliorer, sélectionne par score test (pas train).

### Étape 4 : Appliquer avec les décisions de trigger

Si des `trigger_decisions` existent depuis un cycle précédent :

- Les queries marquées `fix` sont des contraintes prioritaires — la nouvelle description
  DOIT les corriger
- Les queries marquées `acceptable` sont exclues du score (ne pas optimiser dessus)
- Les queries marquées `remove` sont retirées de l'eval set avant de lancer le loop

Prendre `best_description` du JSON retourné, mettre à jour le frontmatter du SKILL.md.
Montrer le before/after et les scores à l'utilisateur.

---

## Clôture & Brief de décision final

Quand l'utilisateur est satisfait ou décide de conclure :

### 1. Générer le brief de clôture

Compiler un document `BENCHMARK_BRIEF.md` dans le workspace :

```markdown
# Brief de benchmark — [skill-name]

Date : [timestamp]
Itérations : [N]
Modèle : [model-id]

## Décision finale

Itération retenue : **[N]**
Description retenue : "[...]"

## Priorités appliquées

1. [priorité #1] — seuil minimum : [X]
2. [priorité #2]
3. ...

## Résultats finaux

- Pass rate : [X]% (seuil : [Y]%)
- Temps moyen : [X]s
- Tokens moyens : [X]
- Trigger F1 : [X] (seuil : [Y])
- Token efficiency : [X] (delta qualité / delta tokens)

## Ce qui a été validé (👍)

- [eval name] — [pass rate]

## Ce qui a été corrigé (👎 → ✅)

- [eval name] — [avant] → [après] — [commentaire user]

## Assertions critiques (toutes vérifiées ✅)

- [assertion] — [eval]

## Problèmes de trigger corrigés

- [query] — [type d'erreur] → [résolu]

## Problèmes de trigger acceptés (pas d'action)

- [query] — [type d'erreur]

## Notes utilisateur

[general_notes]

## Historique des itérations

| Iter | Pass Rate | Time | Tokens | F1 Trigger | Décision |
| ---- | --------- | ---- | ------ | ---------- | -------- |
| 1    | 65%       | 10s  | 3200   | 0.80       | Base     |
| 2    | 78%       | 11s  | 3800   | 0.88       | Amélioré |
| 3    | 92%       | 13s  | 4800   | 0.95       | ★ Retenu |
```

### 2. Sauvegarder un snapshot

Copier le SKILL.md final + ses dépendances dans `<workspace>/final/`.
Si un prochain cycle de benchmark est lancé, ce snapshot sert de `previous_skill`.

### 3. Packager si demandé

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

Retourner le chemin du fichier `.skill` généré.

---

## Fichiers de référence

- `references/schemas.md` — schemas JSON complets (evals, grading, benchmark, timing, decisions)
- `references/skill-writing-guide.md` — patterns d'écriture, Progressive Disclosure, exemples
- `agents/grader.md` — instructions pour le subagent grader
- `agents/analyzer.md` — instructions pour l'analyseur de benchmark
- `agents/comparator.md` — instructions pour la comparaison aveugle

---

## Résumé du flux décisionnel

```
Capture d'intention (priorités incluses)
    ↓
Écriture du skill + test cases
    ↓
┌─→ Runs parallèles (with/without skill)
│       ↓
│   Grading + Benchmark + Dashboard de décision
│       ↓
│   L'UTILISATEUR DÉCIDE :
│   • Itération préférée (★)
│   • Priorités (drag & drop)
│   • 👍 garder / 👎 changer (par eval)
│   • 📌 assertions critiques
│   • 🔧 triggers à corriger
│       ↓
│   Export decisions.json + résumé markdown
│       ↓
│   CLAUDE APPLIQUE les décisions :
│   • Contraintes dures d'abord (📌)
│   • Evals rejetés (👎) par ordre de priorité
│   • Triggers (🔧) dans la description
│   • Sans casser les validés (👍)
│       ↓
│   Vérification automatique (contraintes + régressions)
│       ↓
└── Nouvelle itération si nécessaire
        ↓
    Brief de clôture + packaging
```
