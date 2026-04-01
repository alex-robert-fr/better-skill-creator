# Schemas JSON — skill-creator

Schemas de référence utilisés par tous les scripts et le viewer.

---

## evals.json

Définit les cas de test d'un skill. Situé dans `evals/evals.json` du répertoire du skill.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "Prompt de tâche réaliste",
      "expected_output": "Description de ce qu'on attend",
      "files": ["evals/files/sample.pdf"],
      "expectations": [
        "L'output contient X",
        "Le skill a utilisé le script Y"
      ]
    }
  ]
}
```

**Champs :**
- `skill_name` : nom correspondant au frontmatter du skill
- `evals[].id` : identifiant entier unique
- `evals[].prompt` : tâche à exécuter
- `evals[].expected_output` : description lisible du succès
- `evals[].files` : fichiers d'input (chemins relatifs à la racine du skill)
- `evals[].expectations` : assertions vérifiables

---

## grading.json

Sortie du grader agent. Situé dans `<run-dir>/grading.json`.

```json
{
  "expectations": [
    {
      "text": "L'output contient le nom 'Jean Dupont'",
      "passed": true,
      "evidence": "Trouvé en étape 3 : 'Noms extraits : Jean Dupont'"
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "total": 3,
    "pass_rate": 0.67
  },
  "execution_metrics": {
    "tool_calls": { "Read": 5, "Write": 2, "Bash": 8 },
    "total_tool_calls": 15,
    "total_steps": 6,
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  },
  "claims": [],
  "user_notes_summary": {
    "uncertainties": [],
    "needs_review": [],
    "workarounds": []
  },
  "eval_feedback": {
    "suggestions": [],
    "overall": "Aucune suggestion."
  }
}
```

**Important** : `expectations[].text`, `.passed`, `.evidence` sont obligatoires (noms exacts).

---

## metrics.json

Sortie de l'exécuteur. Situé dans `<run-dir>/outputs/metrics.json`.

```json
{
  "tool_calls": { "Read": 5, "Write": 2, "Bash": 8 },
  "total_tool_calls": 15,
  "total_steps": 6,
  "files_created": ["output.pdf"],
  "errors_encountered": 0,
  "output_chars": 12450,
  "transcript_chars": 3200
}
```

---

## timing.json

Timing d'un run. Situé dans `<run-dir>/timing.json`.

**Capture immédiate** : les champs `total_tokens` et `duration_ms` arrivent dans la notification
de complétion du subagent — ils ne sont pas persistés ailleurs.

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3,
  "executor_start": "2026-01-15T10:30:00Z",
  "executor_end": "2026-01-15T10:32:45Z",
  "executor_duration_seconds": 165.0,
  "grader_start": "2026-01-15T10:32:46Z",
  "grader_end": "2026-01-15T10:33:12Z",
  "grader_duration_seconds": 26.0
}
```

---

## benchmark.json

Sortie d'`aggregate_benchmark.py`. Supporte N configurations (with_skill, without_skill,
skill_v1, skill_v2...).

```json
{
  "metadata": {
    "skill_name": "pdf",
    "skill_path": "/path/to/pdf",
    "executor_model": "claude-sonnet-4-6",
    "timestamp": "2026-01-15T10:30:00Z",
    "evals_run": [1, 2, 3],
    "runs_per_configuration": 3,
    "configurations": {
      "with_skill": "/path/to/skill",
      "without_skill": null,
      "skill_v1": "/path/to/skill-v1"
    }
  },
  "runs": [
    {
      "eval_id": 1,
      "eval_name": "extract-table",
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 0.85,
        "passed": 6,
        "failed": 1,
        "total": 7,
        "time_seconds": 42.5,
        "tokens": 3800,
        "tool_calls": 18,
        "errors": 0
      },
      "expectations": [
        { "text": "...", "passed": true, "evidence": "..." }
      ],
      "notes": []
    }
  ],
  "run_summary": {
    "with_skill": {
      "pass_rate": { "mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90 },
      "time_seconds": { "mean": 45.0, "stddev": 12.0, "min": 32.0, "max": 58.0 },
      "tokens": { "mean": 3800, "stddev": 400, "min": 3200, "max": 4100 }
    },
    "without_skill": {
      "pass_rate": { "mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45 },
      "time_seconds": { "mean": 32.0, "stddev": 8.0, "min": 24.0, "max": 42.0 },
      "tokens": { "mean": 2100, "stddev": 300, "min": 1800, "max": 2500 }
    },
    "delta": {
      "pass_rate": "+0.50",
      "time_seconds": "+13.0",
      "tokens": "+1700"
    }
  },
  "token_efficiency": {
    "with_skill_vs_vanilla": {
      "tokens_delta": "+1700",
      "pass_rate_delta": "+0.50",
      "tokens_per_pass_rate_point": 3400
    }
  },
  "analyst_notes": [
    "L'assertion 'Output est un PDF' passe à 100% dans toutes les configs — non-discriminante",
    "Eval 3 : variance élevée (50% ± 40%) — potentiellement flaky",
    "Le skill consomme +1700 tokens mais améliore le pass_rate de +50%"
  ]
}
```

**Différences vs l'original :**
- `metadata.configurations` : map config → chemin du skill (null = vanilla)
- `token_efficiency` : section dédiée, KPI principal
- `analyst_notes` : intégré directement (pas de subagent séparé)
- N configs supportées (pas limité à with_skill/without_skill)

**Important** : le viewer lit `configuration`, `result.pass_rate`, `result.tokens` exactement.

---

## history.json

Trace la progression des itérations. Situé à la racine du workspace.

```json
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "pdf",
  "current_best": "iteration-2",
  "iterations": [
    {
      "version": "iteration-1",
      "parent": null,
      "pass_rate": 0.65,
      "tokens_mean": 2100,
      "result": "baseline"
    },
    {
      "version": "iteration-2",
      "parent": "iteration-1",
      "pass_rate": 0.85,
      "tokens_mean": 1800,
      "result": "won"
    }
  ]
}
```
