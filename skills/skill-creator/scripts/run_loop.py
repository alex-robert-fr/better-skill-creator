#!/usr/bin/env python3
"""
Optimise la description d'un skill en boucle via l'API Anthropic.

Processus :
    1. Charger le eval set (queries should-trigger / should-not-trigger)
    2. Splitter en train (60%) et test (40%), stratifié par should_trigger
    3. Évaluer la description courante : pour chaque query, demander à Claude
       (API) si le skill se déclencherait → calcule un score de précision
    4. Appeler Claude (extended thinking) avec les échecs pour proposer une
       meilleure description
    5. Évaluer la nouvelle description sur train + test
    6. Répéter jusqu'à max_iterations
    7. Retourner la meilleure description selon le score test (pas train)

Pourquoi l'API plutôt que `claude -p` ?
    Tester le déclenchement via subprocess est non déterministe et lent.
    L'API permet de simuler exactement le mécanisme de triggering de Claude Code :
    on passe la description dans un contexte "available_skills" et on mesure
    si Claude décide d'utiliser le skill pour la query donnée.

Usage :
    python -m scripts.run_loop \\
        --eval-set trigger_evals.json \\
        --skill-path skills/my-skill \\
        --model claude-sonnet-4-6 \\
        --max-iterations 5 \\
        --verbose

Format du eval set :
    [
      {"query": "prompt réaliste", "should_trigger": true},
      {"query": "autre prompt", "should_trigger": false}
    ]

Sortie JSON (stdout) :
    {
      "best_description": "...",
      "best_score": 0.92,
      "history": [
        {"iteration": 0, "train_score": 0.70, "test_score": 0.65, "tokens": 1200},
        {"iteration": 1, "train_score": 0.85, "test_score": 0.80, "tokens": 2400}
      ]
    }
"""

import argparse
import random
import sys
import tempfile
from pathlib import Path

import anthropic

from scripts.utils import parse_skill_md, read_json, write_json

# Marqueur que Claude doit émettre s'il décide d'utiliser le skill
_TRIGGER_MARKER = "<<SKILL_ACTIVATED>>"

_TRIGGER_SYSTEM = """\
You have access to the following skill:

  Name: {skill_name}
  Description: {description}

Rules:
- If the user's message is a task where this skill would be genuinely useful, \
start your response with exactly: {marker}
- Otherwise, respond normally without any prefix.
- Do not explain your choice."""


def split_eval_set(
    eval_set: list[dict], holdout: float = 0.4, seed: int = 42
) -> tuple[list[dict], list[dict]]:
    """
    Stratified split en train/test selon should_trigger.

    Chaque groupe (trigger / no-trigger) est splitté séparément pour garantir
    une représentation équilibrée dans les deux sets.

    Returns:
        (train_set, test_set)
    """
    rng = random.Random(seed)

    triggers = [e for e in eval_set if e.get("should_trigger")]
    no_triggers = [e for e in eval_set if not e.get("should_trigger")]

    rng.shuffle(triggers)
    rng.shuffle(no_triggers)

    def split(items: list) -> tuple[list, list]:
        n_test = max(1, round(len(items) * holdout))
        return items[n_test:], items[:n_test]

    train_t, test_t = split(triggers)
    train_n, test_n = split(no_triggers)

    return train_t + train_n, test_t + test_n


def _check_trigger(
    client: anthropic.Anthropic,
    query: str,
    skill_name: str,
    description: str,
    model: str,
) -> tuple[bool, int]:
    """
    Vérifie si Claude déclencherait le skill pour cette query.

    Retourne (triggered: bool, tokens_used: int).
    """
    system = _TRIGGER_SYSTEM.format(
        skill_name=skill_name,
        description=description,
        marker=_TRIGGER_MARKER,
    )

    response = client.messages.create(
        model=model,
        max_tokens=64,
        system=system,
        messages=[{"role": "user", "content": query}],
    )

    text = response.content[0].text if response.content else ""
    triggered = text.strip().startswith(_TRIGGER_MARKER)
    tokens = response.usage.input_tokens + response.usage.output_tokens

    return triggered, tokens


def evaluate_description(
    client: anthropic.Anthropic,
    description: str,
    skill_name: str,
    eval_set: list[dict],
    model: str,
    runs_per_query: int = 3,
) -> dict:
    """
    Évalue le taux de déclenchement correct pour une description donnée.

    Pour chaque query, lance `runs_per_query` checks et prend la majorité.
    Score = (vrais positifs + vrais négatifs) / total.

    Returns:
        dict avec :
          - score         : précision globale (0.0 → 1.0)
          - results       : liste de {query, should_trigger, triggered, correct}
          - tokens_total  : tokens API consommés pour cette évaluation
          - false_positives  : queries should_trigger=False mais déclenchées
          - false_negatives  : queries should_trigger=True mais non déclenchées
    """
    results = []
    tokens_total = 0

    for entry in eval_set:
        query = entry["query"]
        should = entry["should_trigger"]

        # Majorité sur runs_per_query appels
        triggered_count = 0
        for _ in range(runs_per_query):
            triggered, tokens = _check_trigger(client, query, skill_name, description, model)
            triggered_count += int(triggered)
            tokens_total += tokens

        triggered = triggered_count > runs_per_query / 2
        correct = triggered == should

        results.append({
            "query": query,
            "should_trigger": should,
            "triggered": triggered,
            "correct": correct,
            "trigger_rate": triggered_count / runs_per_query,
        })

    score = sum(r["correct"] for r in results) / len(results) if results else 0.0
    false_positives = [r for r in results if not r["should_trigger"] and r["triggered"]]
    false_negatives = [r for r in results if r["should_trigger"] and not r["triggered"]]

    return {
        "score": round(score, 4),
        "results": results,
        "tokens_total": tokens_total,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def improve_description(
    client: anthropic.Anthropic,
    skill_name: str,
    current_description: str,
    train_score: float,
    false_positives: list[dict],
    false_negatives: list[dict],
    model: str,
) -> tuple[str, int]:
    """
    Appelle Claude avec extended thinking pour proposer une meilleure description.

    Fournit le contexte des échecs (faux positifs et faux négatifs) pour que
    Claude comprenne précisément ce qui ne va pas dans la description courante.

    Returns:
        (new_description: str, tokens_used: int)
    """
    failures_block = ""

    if false_negatives:
        failures_block += "Queries qui AURAIENT DÛ déclencher le skill mais ne l'ont pas fait :\n"
        for r in false_negatives:
            failures_block += f'  - "{r["query"]}"\n'
        failures_block += "\n"

    if false_positives:
        failures_block += "Queries qui N'AURAIENT PAS DÛ déclencher le skill mais l'ont fait :\n"
        for r in false_positives:
            failures_block += f'  - "{r["query"]}"\n'

    prompt = f"""\
Skill : {skill_name}
Description actuelle : {current_description}
Score actuel : {train_score*100:.0f}%

{failures_block}

Propose une meilleure description pour ce skill qui corrige ces erreurs de déclenchement.

Règles pour une bonne description :
- Indiquer ce que fait le skill ET les contextes concrets où l'utiliser
- Être "pushy" : mentionner les contextes même sans mot-clé explicite
- Rester concise (1-3 phrases maximum)
- Ne pas sur-spécifier au point de rater des cas légitimes

Réponds UNIQUEMENT avec la nouvelle description, sans explication ni guillemets."""

    response = client.messages.create(
        model=model,
        max_tokens=512,
        thinking={"type": "enabled", "budget_tokens": 2000},
        messages=[{"role": "user", "content": prompt}],
    )

    tokens = response.usage.input_tokens + response.usage.output_tokens

    # Extraire le texte hors du bloc thinking
    new_description = ""
    for block in response.content:
        if block.type == "text":
            new_description = block.text.strip()
            break

    return new_description or current_description, tokens


def run_loop(
    eval_set: list[dict],
    skill_path: Path,
    model: str,
    max_iterations: int = 5,
    runs_per_query: int = 3,
    holdout: float = 0.4,
    verbose: bool = False,
) -> dict:
    """
    Boucle principale d'optimisation de la description.

    Returns:
        dict avec :
          - best_description : meilleure description trouvée (selon score test)
          - best_score       : score test de la meilleure description
          - history          : liste d'itérations avec scores et tokens
    """
    skill = parse_skill_md(skill_path / "SKILL.md")
    skill_name = skill["name"]
    current_description = skill["description"]

    client = anthropic.Anthropic()
    train_set, test_set = split_eval_set(eval_set, holdout=holdout)

    if verbose:
        print(f"Skill : {skill_name}")
        print(f"Train : {len(train_set)} queries | Test : {len(test_set)} queries")
        print(f"Description initiale : {current_description[:80]}...")
        print()

    best_description = current_description
    best_test_score = 0.0
    history = []
    total_tokens = 0

    for iteration in range(max_iterations + 1):  # +1 pour évaluer la description initiale
        if verbose:
            print(f"── Itération {iteration} {'(initiale)' if iteration == 0 else ''}")

        # Évaluer sur train
        train_eval = evaluate_description(
            client, current_description, skill_name, train_set, model, runs_per_query
        )
        total_tokens += train_eval["tokens_total"]

        # Évaluer sur test
        test_eval = evaluate_description(
            client, current_description, skill_name, test_set, model, runs_per_query
        )
        total_tokens += test_eval["tokens_total"]

        if verbose:
            print(f"   Train : {train_eval['score']*100:.1f}%  "
                  f"Test : {test_eval['score']*100:.1f}%  "
                  f"Tokens : {train_eval['tokens_total'] + test_eval['tokens_total']}")

        history.append({
            "iteration": iteration,
            "description": current_description,
            "train_score": train_eval["score"],
            "test_score": test_eval["score"],
            "tokens": train_eval["tokens_total"] + test_eval["tokens_total"],
            "false_positives": len(train_eval["false_positives"]),
            "false_negatives": len(train_eval["false_negatives"]),
        })

        # Garder la meilleure selon le score test
        if test_eval["score"] > best_test_score:
            best_test_score = test_eval["score"]
            best_description = current_description
            if verbose:
                print(f"   ★ Nouveau meilleur score test : {best_test_score*100:.1f}%")

        # Arrêter si score parfait ou dernière itération
        if train_eval["score"] == 1.0 or iteration == max_iterations:
            break

        # Améliorer la description pour la prochaine itération
        new_description, improve_tokens = improve_description(
            client,
            skill_name,
            current_description,
            train_eval["score"],
            train_eval["false_positives"],
            train_eval["false_negatives"],
            model,
        )
        total_tokens += improve_tokens
        current_description = new_description

        if verbose:
            print(f"   Nouvelle description : {new_description[:80]}...")
            print()

    if verbose:
        print(f"\nTerminé. Meilleur score test : {best_test_score*100:.1f}%")
        print(f"Tokens totaux consommés : {total_tokens}")

    return {
        "best_description": best_description,
        "best_score": best_test_score,
        "history": history,
        "total_tokens": total_tokens,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimise la description d'un skill")
    parser.add_argument("--eval-set", type=Path, required=True,
                        help="Chemin vers trigger_evals.json")
    parser.add_argument("--skill-path", type=Path, required=True,
                        help="Répertoire du skill (contenant SKILL.md)")
    parser.add_argument("--model", required=True,
                        help="ID du modèle Claude (ex: claude-sonnet-4-6)")
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--runs-per-query", type=int, default=3)
    parser.add_argument("--holdout", type=float, default=0.4)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not args.eval_set.exists():
        print(f"Eval set introuvable : {args.eval_set}", file=sys.stderr)
        sys.exit(1)

    if not (args.skill_path / "SKILL.md").exists():
        print(f"SKILL.md introuvable dans : {args.skill_path}", file=sys.stderr)
        sys.exit(1)

    eval_set = read_json(args.eval_set)
    if not isinstance(eval_set, list):
        print("Le eval set doit être une liste JSON.", file=sys.stderr)
        sys.exit(1)

    result = run_loop(
        eval_set=eval_set,
        skill_path=args.skill_path,
        model=args.model,
        max_iterations=args.max_iterations,
        runs_per_query=args.runs_per_query,
        holdout=args.holdout,
        verbose=args.verbose,
    )

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
