"""Tests pour scripts/aggregate_benchmark.py"""

import pytest
from pathlib import Path

from scripts.aggregate_benchmark import (
    aggregate_results,
    calculate_stats,
    compute_token_efficiency,
    generate_analyst_notes,
    generate_markdown,
    load_run_results,
)


class TestCalculateStats:
    def test_single_value(self) -> None:
        s = calculate_stats([0.8])
        assert s["mean"] == 0.8
        assert s["stddev"] == 0.0
        assert s["min"] == s["max"] == 0.8

    def test_multiple_values(self) -> None:
        s = calculate_stats([0.0, 1.0])
        assert s["mean"] == 0.5
        assert s["stddev"] > 0
        assert s["min"] == 0.0
        assert s["max"] == 1.0

    def test_empty(self) -> None:
        s = calculate_stats([])
        assert s == {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}


class TestLoadRunResults:
    def test_loads_two_configs(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        assert "with_skill" in results
        assert "without_skill" in results

    def test_correct_pass_rates(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        # 2 evals × 1 run chacun
        assert len(results["with_skill"]) == 2
        assert all(r["pass_rate"] == 1.0 for r in results["with_skill"])
        assert all(r["pass_rate"] == 0.0 for r in results["without_skill"])

    def test_tokens_loaded(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        assert all(r["tokens"] == 4000 for r in results["with_skill"])
        assert all(r["tokens"] == 1000 for r in results["without_skill"])

    def test_empty_dir(self, tmp_path: Path) -> None:
        results = load_run_results(tmp_path)
        assert results == {}

    def test_missing_grading_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "eval-test" / "with_skill" / "run-1").mkdir(parents=True)
        # Pas de grading.json
        results = load_run_results(tmp_path)
        assert results.get("with_skill", []) == []


class TestAggregateResults:
    def test_stats_computed(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        summary = aggregate_results(results)
        assert summary["with_skill"]["pass_rate"]["mean"] == 1.0
        assert summary["without_skill"]["pass_rate"]["mean"] == 0.0

    def test_delta_vs_without_skill(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        summary = aggregate_results(results)
        delta = summary.get("delta", {}).get("with_skill", {})
        assert delta["vs"] == "without_skill"
        assert delta["pass_rate"] == "+1.00"
        assert delta["tokens"] == "+3000"

    def test_single_config_no_delta(self, tmp_path: Path) -> None:
        from scripts.utils import write_json
        run_dir = tmp_path / "eval-x" / "only_skill" / "run-1"
        run_dir.mkdir(parents=True)
        write_json(run_dir / "grading.json", {
            "expectations": [], "summary": {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0},
            "execution_metrics": {}, "timing": {}, "user_notes_summary": {"uncertainties": [], "needs_review": [], "workarounds": []},
        })
        results = load_run_results(tmp_path)
        summary = aggregate_results(results)
        assert "only_skill" in summary
        # Pas de delta avec une seule config
        assert "delta" not in summary or not summary.get("delta")


class TestTokenEfficiency:
    def test_basic(self) -> None:
        summary = {
            "with_skill":    {"pass_rate": {"mean": 0.9}, "tokens": {"mean": 4000.0}, "time_seconds": {"mean": 40.0}},
            "without_skill": {"pass_rate": {"mean": 0.4}, "tokens": {"mean": 1500.0}, "time_seconds": {"mean": 20.0}},
            "delta": {"with_skill": {"vs": "without_skill", "pass_rate": "+0.50", "tokens": "+2500"}},
        }
        eff = compute_token_efficiency(summary)
        assert "with_skill" in eff
        assert eff["with_skill"]["tokens_per_pass_rate_point"] == 5000

    def test_negative_tokens_positive_pass_rate_is_excellent(self) -> None:
        summary = {
            "delta": {"fast_skill": {"vs": "without_skill", "pass_rate": "+0.30", "tokens": "-500"}},
        }
        eff = compute_token_efficiency(summary)
        assert eff["fast_skill"]["rating"] == "excellent"

    def test_zero_pass_rate_delta(self) -> None:
        summary = {
            "delta": {"same_skill": {"vs": "without_skill", "pass_rate": "+0.00", "tokens": "+1000"}},
        }
        eff = compute_token_efficiency(summary)
        assert eff["same_skill"]["tokens_per_pass_rate_point"] is None
        assert eff["same_skill"]["rating"] == "neutre"


class TestGenerateAnalystNotes:
    def test_non_discriminant_assertion(self, benchmark_dir: Path) -> None:
        # L'assertion "Output correct" passe à 100% dans with_skill
        results = load_run_results(benchmark_dir)
        summary = aggregate_results(results)
        notes = generate_analyst_notes(results, summary)
        # with_skill = 100% mais without_skill = 0% → assertion discriminante, pas de note
        # (note seulement si ≥95% dans TOUTES les configs)
        assert isinstance(notes, list)

    def test_returns_list(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        summary = aggregate_results(results)
        notes = generate_analyst_notes(results, summary)
        assert isinstance(notes, list)


class TestGenerateMarkdown:
    def test_tokens_first(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        summary = aggregate_results(results)
        efficiency = compute_token_efficiency(summary)
        notes = generate_analyst_notes(results, summary)
        benchmark = {
            "metadata": {"skill_name": "test", "executor_model": "claude-sonnet-4-6",
                         "timestamp": "2026-04-01T00:00:00Z", "evals_run": [1,2], "runs_per_configuration": 1},
            "runs": [], "run_summary": summary,
            "token_efficiency": efficiency, "analyst_notes": notes,
        }
        md = generate_markdown(benchmark)
        # Tokens doit apparaître avant Pass Rate dans le markdown
        assert md.index("Tokens") < md.index("Pass Rate")

    def test_contains_all_configs(self, benchmark_dir: Path) -> None:
        results = load_run_results(benchmark_dir)
        summary = aggregate_results(results)
        benchmark = {
            "metadata": {"skill_name": "test", "executor_model": "—",
                         "timestamp": "2026-04-01", "evals_run": [], "runs_per_configuration": 1},
            "runs": [], "run_summary": summary, "token_efficiency": {}, "analyst_notes": [],
        }
        md = generate_markdown(benchmark)
        assert "With Skill" in md
        assert "Without Skill" in md
