#!/usr/bin/env python3
"""
Agrège les résultats de runs individuels en statistiques de benchmark.

Supporte N configurations (with_skill, without_skill, skill_v1, skill_v2...).
La config de référence pour le delta est "without_skill" si elle existe, sinon la dernière.

Produit :
    - benchmark.json : données complètes avec token_efficiency et analyst_notes
    - benchmark.md   : résumé lisible, tokens en première colonne

Usage :
    python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <nom>

Structure de répertoires attendue :
    <benchmark_dir>/
    └── eval-<name>/
        ├── with_skill/
        │   └── run-1/
        │       ├── grading.json
        │       ├── timing.json
        │       └── outputs/metrics.json
        ├── without_skill/
        │   └── run-1/...
        └── skill_v1/
            └── run-1/...
"""

import argparse
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.utils import read_json, write_json


def calculate_stats(values: list[float]) -> dict:
    """Calcule mean, stddev, min, max pour une liste de valeurs."""
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}

    n = len(values)
    mean = sum(values) / n
    stddev = math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1)) if n > 1 else 0.0

    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def load_run_results(benchmark_dir: Path) -> dict[str, list]:
    """
    Charge tous les résultats de runs depuis un répertoire de benchmark.

    Parcourt eval-*/<config>/run-*/grading.json.
    Découverte automatique des configs — aucune liste hardcodée.

    Retourne un dict { config_name: [run_result, ...] }.
    Chaque run_result contient : eval_id, eval_name, run_number, pass_rate,
    passed, failed, total, time_seconds, tokens, tool_calls, errors,
    expectations, notes.
    """
    results: dict[str, list] = {}

    eval_dirs = sorted(benchmark_dir.glob("eval-*"))
    if not eval_dirs:
        print(f"Aucun répertoire eval-* trouvé dans {benchmark_dir}", file=sys.stderr)
        return results

    for eval_dir in eval_dirs:
        # Lire les métadonnées de l'eval
        metadata_path = eval_dir / "eval_metadata.json"
        if metadata_path.exists():
            try:
                meta = read_json(metadata_path)
                eval_id = meta.get("eval_id", 0)
                eval_name = meta.get("eval_name", eval_dir.name)
            except (FileNotFoundError, ValueError):
                eval_id = 0
                eval_name = eval_dir.name
        else:
            eval_id = 0
            eval_name = eval_dir.name

        # Découvrir les configs (sous-répertoires contenant des run-*)
        for config_dir in sorted(eval_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            run_dirs = sorted(config_dir.glob("run-*"))
            if not run_dirs:
                continue

            config = config_dir.name
            if config not in results:
                results[config] = []

            for run_dir in run_dirs:
                run_result = _load_single_run(run_dir, eval_id, eval_name)
                if run_result is not None:
                    results[config].append(run_result)

    return results


def _load_single_run(run_dir: Path, eval_id: int, eval_name: str) -> dict | None:
    """Charge un run depuis son répertoire. Retourne None si grading.json manque."""
    grading_path = run_dir / "grading.json"
    if not grading_path.exists():
        print(f"Avertissement : grading.json manquant dans {run_dir}", file=sys.stderr)
        return None

    try:
        grading = read_json(grading_path)
    except ValueError as e:
        print(f"Avertissement : {e}", file=sys.stderr)
        return None

    run_number_str = run_dir.name.split("-")[-1]
    run_number = int(run_number_str) if run_number_str.isdigit() else 1

    summary = grading.get("summary", {})
    result: dict = {
        "eval_id": eval_id,
        "eval_name": eval_name,
        "run_number": run_number,
        "pass_rate": summary.get("pass_rate", 0.0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "total": summary.get("total", 0),
        "time_seconds": 0.0,
        "tokens": 0,
        "tool_calls": 0,
        "errors": 0,
        "expectations": [],
        "notes": [],
    }

    # Timing : grading.json en priorité, puis timing.json sibling
    timing = grading.get("timing", {})
    result["time_seconds"] = timing.get("total_duration_seconds") or 0.0

    timing_path = run_dir / "timing.json"
    if result["time_seconds"] == 0.0 and timing_path.exists():
        try:
            timing_data = read_json(timing_path)
            result["time_seconds"] = timing_data.get("total_duration_seconds", 0.0)
            result["tokens"] = timing_data.get("total_tokens", 0)
        except (FileNotFoundError, ValueError):
            pass

    # Métriques d'exécution
    metrics = grading.get("execution_metrics", {})
    result["tool_calls"] = metrics.get("total_tool_calls", 0)
    result["errors"] = metrics.get("errors_encountered", 0)
    if result["tokens"] == 0:
        result["tokens"] = metrics.get("output_chars", 0)

    # Assertions — vérifier les champs requis par le viewer
    raw_expectations = grading.get("expectations", [])
    for exp in raw_expectations:
        if "text" not in exp or "passed" not in exp:
            print(
                f"Avertissement : assertion sans champs requis (text, passed) dans {grading_path}",
                file=sys.stderr,
            )
    result["expectations"] = raw_expectations

    # Notes depuis user_notes_summary
    notes_summary = grading.get("user_notes_summary") or {}
    notes = (
        notes_summary.get("uncertainties", [])
        + notes_summary.get("needs_review", [])
        + notes_summary.get("workarounds", [])
    )
    result["notes"] = notes

    return result


def aggregate_results(results: dict[str, list]) -> dict:
    """
    Agrège les run results en statistiques par configuration.

    Calcule mean/stddev/min/max pour pass_rate, time_seconds, tokens.
    Calcule le delta entre chaque config skill et la config de référence.

    La référence est "without_skill" si présente, sinon la dernière config.
    """
    configs = list(results.keys())
    run_summary: dict = {}

    for config in configs:
        runs = results[config]
        if not runs:
            run_summary[config] = {
                "pass_rate": calculate_stats([]),
                "time_seconds": calculate_stats([]),
                "tokens": calculate_stats([]),
            }
            continue

        run_summary[config] = {
            "pass_rate": calculate_stats([r["pass_rate"] for r in runs]),
            "time_seconds": calculate_stats([r["time_seconds"] for r in runs]),
            "tokens": calculate_stats([float(r["tokens"]) for r in runs]),
        }

    # Choisir la config de référence pour le delta
    ref_config = "without_skill" if "without_skill" in configs else (configs[-1] if configs else None)

    if ref_config and len(configs) >= 2:
        ref = run_summary.get(ref_config, {})
        ref_pr = ref.get("pass_rate", {}).get("mean", 0.0)
        ref_time = ref.get("time_seconds", {}).get("mean", 0.0)
        ref_tokens = ref.get("tokens", {}).get("mean", 0.0)

        # Delta pour chaque config non-référence
        for config in configs:
            if config == ref_config:
                continue
            cfg = run_summary[config]
            delta_pr = cfg["pass_rate"]["mean"] - ref_pr
            delta_time = cfg["time_seconds"]["mean"] - ref_time
            delta_tokens = cfg["tokens"]["mean"] - ref_tokens

            run_summary.setdefault("delta", {})[config] = {
                "vs": ref_config,
                "pass_rate": f"{delta_pr:+.2f}",
                "time_seconds": f"{delta_time:+.1f}",
                "tokens": f"{delta_tokens:+.0f}",
            }

    return run_summary


def compute_token_efficiency(run_summary: dict) -> dict:
    """
    Calcule la section token_efficiency pour chaque config vs référence.

    tokens_per_pass_rate_point = delta_tokens / delta_pass_rate
    Plus c'est bas, meilleur est le skill (peu de tokens pour beaucoup de gain qualité).
    Négatif = le skill consomme moins de tokens ET fait mieux → excellent.
    """
    efficiency: dict = {}
    delta = run_summary.get("delta", {})

    for config, d in delta.items():
        try:
            delta_tokens = float(d["tokens"].replace("+", ""))
            delta_pr = float(d["pass_rate"].replace("+", ""))
        except (KeyError, ValueError):
            continue

        if delta_pr == 0:
            tokens_per_point = None
            rating = "neutre"
        else:
            tokens_per_point = round(delta_tokens / delta_pr)
            if delta_tokens < 0 and delta_pr > 0:
                rating = "excellent"  # moins de tokens, meilleure qualité
            elif tokens_per_point < 1000:
                rating = "efficace"
            elif tokens_per_point < 3000:
                rating = "acceptable"
            else:
                rating = "coûteux"

        efficiency[config] = {
            "vs": d.get("vs", "reference"),
            "tokens_delta": d["tokens"],
            "pass_rate_delta": d["pass_rate"],
            "tokens_per_pass_rate_point": tokens_per_point,
            "rating": rating,
        }

    return efficiency


def generate_analyst_notes(results: dict[str, list], run_summary: dict) -> list[str]:
    """
    Génère les observations analytiques intégrées au benchmark.

    Détecte :
    - Assertions non-discriminantes (passent à 100% dans toutes les configs)
    - Evals à haute variance (stddev/mean > 0.3 → potentiellement flaky)
    - Trade-offs tokens/qualité remarquables
    - Configs qui surperforment sur certains evals mais pas d'autres
    """
    notes: list[str] = []
    configs = [c for c in results if c != "without_skill"]

    # Assertions non-discriminantes : passent à ≥95% dans toutes les configs
    assertion_pass_rates: dict[str, list[float]] = {}
    for config, runs in results.items():
        for run in runs:
            for exp in run.get("expectations", []):
                text = exp.get("text", "")
                if text not in assertion_pass_rates:
                    assertion_pass_rates[text] = []
                assertion_pass_rates[text].append(1.0 if exp.get("passed") else 0.0)

    for text, rates in assertion_pass_rates.items():
        if rates and sum(rates) / len(rates) >= 0.95:
            short = text[:60] + "..." if len(text) > 60 else text
            notes.append(
                f"Assertion non-discriminante ({sum(rates)/len(rates)*100:.0f}% dans toutes "
                f"les configs) : \"{short}\""
            )

    # Evals à haute variance
    for config, summary in run_summary.items():
        if config in ("delta",):
            continue
        pr = summary.get("pass_rate", {})
        mean = pr.get("mean", 0.0)
        stddev = pr.get("stddev", 0.0)
        if mean > 0 and stddev / mean > 0.3:
            notes.append(
                f"[{config}] variance élevée sur pass_rate "
                f"({mean*100:.0f}% ± {stddev*100:.0f}%) — eval potentiellement flaky"
            )

    # Trade-offs tokens/qualité
    delta = run_summary.get("delta", {})
    for config, d in delta.items():
        try:
            delta_tokens = float(d["tokens"].replace("+", ""))
            delta_pr = float(d["pass_rate"].replace("+", ""))
        except (KeyError, ValueError):
            continue

        if delta_tokens < 0 and delta_pr > 0:
            notes.append(
                f"[{config}] consomme {d['tokens']} tokens et améliore le pass_rate "
                f"de {d['pass_rate']} — gain net"
            )
        elif delta_tokens > 2000 and delta_pr < 0.1:
            notes.append(
                f"[{config}] coûte {d['tokens']} tokens supplémentaires pour seulement "
                f"{d['pass_rate']} de gain — à revoir"
            )

    return notes


def generate_markdown(benchmark: dict) -> str:
    """
    Génère benchmark.md lisible.

    Tokens en première colonne (KPI principal). Supporte N configs.
    """
    metadata = benchmark["metadata"]
    run_summary = benchmark["run_summary"]
    configs = [k for k in run_summary if k not in ("delta",)]

    lines = [
        f"# Benchmark : {metadata['skill_name']}",
        "",
        f"**Modèle** : {metadata.get('executor_model', '—')}",
        f"**Date** : {metadata['timestamp']}",
        f"**Evals** : {len(metadata.get('evals_run', []))} "
        f"({metadata.get('runs_per_configuration', 1)} run(s) par config)",
        "",
        "## Résumé",
        "",
    ]

    # En-tête dynamique selon le nombre de configs
    header = "| Métrique | " + " | ".join(c.replace("_", " ").title() for c in configs) + " |"
    separator = "|---------|" + "---------|" * len(configs)
    lines += [header, separator]

    def fmt_stat(stat: dict, pct: bool = False) -> str:
        mean = stat.get("mean", 0)
        stddev = stat.get("stddev", 0)
        if pct:
            return f"{mean*100:.0f}% ± {stddev*100:.0f}%"
        if mean > 100:
            return f"{mean:.0f} ± {stddev:.0f}"
        return f"{mean:.1f} ± {stddev:.1f}"

    # Tokens en premier (KPI principal)
    token_row = "| Tokens |"
    for config in configs:
        token_row += f" {fmt_stat(run_summary[config]['tokens'])} |"
    lines.append(token_row)

    # Pass rate
    pr_row = "| Pass Rate |"
    for config in configs:
        pr_row += f" {fmt_stat(run_summary[config]['pass_rate'], pct=True)} |"
    lines.append(pr_row)

    # Temps
    time_row = "| Temps (s) |"
    for config in configs:
        time_row += f" {fmt_stat(run_summary[config]['time_seconds'])} |"
    lines.append(time_row)

    # Token efficiency
    efficiency = benchmark.get("token_efficiency", {})
    if efficiency:
        lines += ["", "## Token Efficiency", ""]
        for config, eff in efficiency.items():
            lines.append(
                f"- **{config}** vs {eff['vs']} : "
                f"{eff['tokens_delta']} tokens, "
                f"{eff['pass_rate_delta']} pass_rate → "
                f"**{eff['rating']}**"
                + (f" ({eff['tokens_per_pass_rate_point']} tokens/point)"
                   if eff['tokens_per_pass_rate_point'] is not None else "")
            )

    # Notes analytiques
    analyst_notes = benchmark.get("analyst_notes", [])
    if analyst_notes:
        lines += ["", "## Observations", ""]
        for note in analyst_notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agrège les résultats de benchmark")
    parser.add_argument("benchmark_dir", type=Path, help="Répertoire iteration-N/")
    parser.add_argument("--skill-name", default="", help="Nom du skill benchmarké")
    parser.add_argument("--skill-path", default="", help="Chemin vers le skill")
    parser.add_argument("--output", "-o", type=Path, help="Chemin de sortie benchmark.json")
    args = parser.parse_args()

    if not args.benchmark_dir.exists():
        print(f"Répertoire introuvable : {args.benchmark_dir}", file=sys.stderr)
        sys.exit(1)

    results = load_run_results(args.benchmark_dir)
    if not results:
        print("Aucun résultat trouvé.", file=sys.stderr)
        sys.exit(1)

    run_summary = aggregate_results(results)
    token_efficiency = compute_token_efficiency(run_summary)
    analyst_notes = generate_analyst_notes(results, run_summary)

    # Construire la liste des runs pour benchmark.json
    runs = []
    for config, run_list in results.items():
        for r in run_list:
            runs.append({
                "eval_id": r["eval_id"],
                "eval_name": r["eval_name"],
                "configuration": config,
                "run_number": r["run_number"],
                "result": {
                    "pass_rate": r["pass_rate"],
                    "passed": r["passed"],
                    "failed": r["failed"],
                    "total": r["total"],
                    "time_seconds": r["time_seconds"],
                    "tokens": r["tokens"],
                    "tool_calls": r["tool_calls"],
                    "errors": r["errors"],
                },
                "expectations": r["expectations"],
                "notes": r["notes"],
            })

    eval_ids = sorted({r["eval_id"] for run_list in results.values() for r in run_list})
    runs_per_config = max(
        (len(run_list) // max(len(eval_ids), 1) for run_list in results.values()),
        default=1,
    )

    benchmark = {
        "metadata": {
            "skill_name": args.skill_name or "—",
            "skill_path": args.skill_path or "—",
            "executor_model": "—",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evals_run": eval_ids,
            "runs_per_configuration": runs_per_config,
        },
        "runs": runs,
        "run_summary": run_summary,
        "token_efficiency": token_efficiency,
        "analyst_notes": analyst_notes,
    }

    output_json = args.output or (args.benchmark_dir / "benchmark.json")
    output_md = output_json.with_suffix(".md")

    write_json(output_json, benchmark)
    output_md.write_text(generate_markdown(benchmark), encoding="utf-8")

    print(f"Généré : {output_json}")
    print(f"Généré : {output_md}")

    # Résumé terminal
    configs = [k for k in run_summary if k != "delta"]
    print("\nRésumé :")
    for config in configs:
        pr = run_summary[config]["pass_rate"]["mean"]
        tokens = run_summary[config]["tokens"]["mean"]
        print(f"  {config:<20} pass_rate={pr*100:.1f}%  tokens={tokens:.0f}")

    for config, eff in token_efficiency.items():
        print(f"  → {config} : {eff['rating']} ({eff['tokens_delta']} tokens, "
              f"{eff['pass_rate_delta']} pass_rate)")


if __name__ == "__main__":
    main()
