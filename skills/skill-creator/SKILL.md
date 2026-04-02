---
name: skill-creator
description: Create new skills, improve existing skills, and measure skill performance with token-efficiency benchmarking. Use when creating a skill from scratch, updating or optimizing an existing skill, running evals, benchmarking multiple skill versions against each other or against vanilla Claude, or optimizing a skill's trigger description. Trigger on any request involving skill authoring, skill testing, skill evals, skill iteration, skill packaging, or comparing skill versions.
---

# Skill Creator

Crée des skills, les améliore par itération mesurée, et optimise leur déclenchement.
Le KPI principal est l'efficacité token : gain de qualité rapporté aux tokens consommés.

Détermine où en est l'utilisateur dans le processus et démarre directement à la bonne étape.

---

## 1. Capture d'intention

Commence par répondre à ces 4 questions. Si la conversation contient déjà des éléments de
réponse, extrais-les — l'utilisateur confirme, il ne ressaisit pas.

1. **But** : que doit permettre de faire ce skill ?
2. **Déclenchement** : quelles phrases ou contextes doivent l'activer ?
3. **Format de sortie** : quel est le livrable attendu ?
4. **Tests** : des outputs objectivement vérifiables ? (fichiers générés, transformations de
   données, workflows en étapes fixes → oui ; style d'écriture, design → non)

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
  Voir `references/skill-writing-guide.md` pour les patterns et exemples.

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

### Étape 4 : Grader, agréger, lancer le viewer

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

**3. Lancer le viewer** — tuer l'ancienne instance si elle tourne, puis relancer :

```bash
# Trouver le chemin du skill-creator (ce script)
SKILL_CREATOR_PATH=$(dirname $(dirname $(realpath $0)))

# Couper l'ancienne instance sur le port 8765
kill $(lsof -ti :8765) 2>/dev/null; sleep 1

# Lancer avec PYTHONPATH pour les imports internes
PYTHONPATH="$SKILL_CREATOR_PATH" nohup python3 "$SKILL_CREATOR_PATH/scripts/generate_review.py" \
  <workspace>/iteration-N \
  --skill-name "mon-skill" \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --previous-workspace <workspace>/iteration-N-1 \
  > /tmp/viewer-<nom>.log 2>&1 &
VIEWER_PID=$!
```

**Important :** passer `--previous-workspace` même à l'itération 2 pour afficher la comparaison multi-itérations dans le dashboard. Le dashboard affiche toujours les 2 dernières itérations côte à côte.

Dire à l'utilisateur : "J'ai ouvert les résultats dans ton navigateur. Onglet 'Outputs' pour
naviguer entre les test cases et laisser du feedback, onglet 'Benchmark' pour les stats.
Reviens quand tu as terminé."

### Étape 5 : Lire le feedback

Quand l'utilisateur revient, lire `feedback.json` dans le workspace :

```json
{
  "reviews": [
    {"run_id": "eval-0-with_skill", "feedback": "...", "timestamp": "..."}
  ],
  "status": "complete"
}
```

Feedback vide = satisfaisant. Se concentrer sur les test cases avec des retours spécifiques.

Stopper le serveur viewer :
```bash
kill $VIEWER_PID 2>/dev/null
```

---

## Améliorer le skill

C'est le cœur de la boucle. Principes à respecter :

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

**Token efficiency** : comparer `token_efficiency` entre itérations. Une amélioration de
qualité qui coûte beaucoup plus de tokens peut ne pas valoir le coup.

### Boucle d'itération

1. Appliquer les améliorations au skill
2. Relancer tous les runs dans `iteration-<N+1>/` (with_skill + without_skill)
   - Si amélioration d'un skill existant : comparer aussi avec l'itération précédente
     (ajouter une config `previous_skill` pointant sur le snapshot)
3. Lancer le viewer avec `--previous-workspace`
4. Attendre le feedback utilisateur
5. Répéter jusqu'à :
   - L'utilisateur est satisfait
   - Tout le feedback est vide
   - Plus de progrès mesurable (pass_rate et token_efficiency stagnent)

---

## Description Optimization

La description est le mécanisme de déclenchement. Une mauvaise description = skill ignoré.

### Étape 1 : Générer le eval set

Créer 20 queries réalistes :
- 10 **should-trigger** : diverses formulations, certaines sans mentionner le skill explicitement,
  quelques cas peu communs, cas où ce skill concurrence un autre mais doit gagner
- 10 **should-not-trigger** : near-misses — même vocabulaire mais contexte différent,
  cas ambigus où un match naïf déclencherait mais ne devrait pas

Qualité des queries : concrètes, avec contexte (chemins de fichiers, noms de colonnes,
backstory courte). Éviter les queries trop évidentes dans les deux sens.

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

Lancer en arrière-plan. Suivre la progression périodiquement avec `tail`.

Le script : split 60/40 train/test stratifié, évalue la description courante (3 runs/query),
appelle Claude extended thinking pour améliorer, sélectionne par score test (pas train).

### Étape 4 : Appliquer le résultat

Prendre `best_description` du JSON retourné, mettre à jour le frontmatter du SKILL.md.
Montrer le before/after et les scores à l'utilisateur.

---

## Packaging

Vérifier d'abord que `present_files` est disponible. Si non, indiquer le chemin du .skill.

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

Retourner le chemin du fichier `.skill` généré.

---

## Fichiers de référence

- `references/schemas.md` — schemas JSON complets (evals, grading, benchmark, timing...)
- `references/skill-writing-guide.md` — patterns d'écriture, Progressive Disclosure, exemples
- `agents/grader.md` — instructions pour le subagent grader
