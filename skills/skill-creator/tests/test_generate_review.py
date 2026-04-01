"""Tests pour scripts/generate_review.py"""

import pytest
from pathlib import Path

from scripts.generate_review import _collect_runs, build_review_html
from scripts.utils import write_json


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Workspace avec 2 runs (with_skill + without_skill)."""
    for config, transcript in [("with_skill", "Output A"), ("without_skill", "Output B")]:
        run_dir = tmp_path / "eval-test" / config / "run-1"
        run_dir.mkdir(parents=True)
        (run_dir / "transcript.md").write_text(transcript, encoding="utf-8")
        write_json(run_dir / "grading.json", {
            "expectations": [{"text": "Check", "passed": config == "with_skill", "evidence": "ok"}],
            "summary": {"passed": 1 if config == "with_skill" else 0,
                        "failed": 0 if config == "with_skill" else 1,
                        "total": 1, "pass_rate": 1.0 if config == "with_skill" else 0.0},
            "timing": {"total_duration_seconds": 30.0},
            "user_notes_summary": {"uncertainties": [], "needs_review": [], "workarounds": []},
        })
        write_json(run_dir / "timing.json", {
            "total_tokens": 3000 if config == "with_skill" else 1000,
            "duration_ms": 30000,
            "total_duration_seconds": 30.0,
        })
    write_json(tmp_path / "eval-test" / "eval_metadata.json", {
        "eval_id": 1,
        "eval_name": "test-eval",
        "prompt": "Prompt de test",
        "assertions": [],
    })
    return tmp_path


class TestCollectRuns:
    def test_finds_both_configs(self, workspace: Path) -> None:
        runs = _collect_runs(workspace)
        configs = {r["configuration"] for r in runs}
        assert "with_skill" in configs
        assert "without_skill" in configs

    def test_run_fields(self, workspace: Path) -> None:
        runs = _collect_runs(workspace)
        run = next(r for r in runs if r["configuration"] == "with_skill")
        assert run["eval_name"] == "test-eval"
        assert run["prompt"] == "Prompt de test"
        assert run["transcript"] == "Output A"
        assert run["timing"]["total_tokens"] == 3000

    def test_grading_loaded(self, workspace: Path) -> None:
        runs = _collect_runs(workspace)
        run = next(r for r in runs if r["configuration"] == "with_skill")
        assert run["grading"]["summary"]["pass_rate"] == 1.0

    def test_empty_workspace(self, tmp_path: Path) -> None:
        runs = _collect_runs(tmp_path)
        assert runs == []

    def test_run_id_format(self, workspace: Path) -> None:
        runs = _collect_runs(workspace)
        for run in runs:
            assert run["configuration"] in run["run_id"]
            assert "run-1" in run["run_id"]


class TestBuildReviewHtml:
    def test_replaces_all_placeholders(self, workspace: Path) -> None:
        html = build_review_html(workspace, "mon-skill")
        assert "__EVAL_DATA_PLACEHOLDER__" not in html
        assert "__BENCHMARK_DATA_PLACEHOLDER__" not in html
        assert "__SKILL_NAME_PLACEHOLDER__" not in html
        assert "__PREVIOUS_DATA_PLACEHOLDER__" not in html

    def test_contains_skill_name(self, workspace: Path) -> None:
        html = build_review_html(workspace, "mon-skill")
        assert "mon-skill" in html

    def test_contains_transcript(self, workspace: Path) -> None:
        html = build_review_html(workspace, "mon-skill")
        assert "Output A" in html

    def test_with_benchmark(self, workspace: Path, benchmark_dir: Path) -> None:
        from scripts.aggregate_benchmark import (
            aggregate_results, compute_token_efficiency,
            generate_analyst_notes, load_run_results,
        )
        import json
        results = load_run_results(benchmark_dir)
        summary = aggregate_results(results)
        efficiency = compute_token_efficiency(summary)
        notes = generate_analyst_notes(results, summary)
        bk = {
            "metadata": {"skill_name": "test-skill", "executor_model": "—",
                         "timestamp": "2026-04-01", "evals_run": [], "runs_per_configuration": 1},
            "runs": [], "run_summary": summary,
            "token_efficiency": efficiency, "analyst_notes": notes,
        }
        benchmark_path = benchmark_dir / "benchmark.json"
        benchmark_path.write_text(json.dumps(bk), encoding="utf-8")
        html = build_review_html(workspace, "mon-skill", benchmark_path=benchmark_path)
        assert "mon-skill" in html

    def test_missing_template_raises(self, workspace: Path, tmp_path: Path, monkeypatch) -> None:
        # Pointer generate_review vers un faux __file__ sans assets/
        import scripts.generate_review as gr
        monkeypatch.setattr(gr, "__file__", str(tmp_path / "scripts" / "generate_review.py"))
        with pytest.raises(FileNotFoundError):
            build_review_html(workspace, "mon-skill")
