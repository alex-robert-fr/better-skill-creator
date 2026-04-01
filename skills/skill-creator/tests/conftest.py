"""Fixtures partagées entre les tests."""

import json
import pytest
from pathlib import Path


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    """Répertoire de skill minimal valide."""
    d = tmp_path / "my-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Test skill description.\n---\n\n# Body\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def eval_set() -> list[dict]:
    """Eval set de 10 queries pour les tests de split et trigger."""
    return [
        {"query": "créer un skill pour formater du code", "should_trigger": True},
        {"query": "améliorer le skill pdf", "should_trigger": True},
        {"query": "écrire une fonction python", "should_trigger": False},
        {"query": "tester mon skill de traduction", "should_trigger": True},
        {"query": "analyser ce CSV", "should_trigger": False},
        {"query": "faire un skill pour les commits git", "should_trigger": True},
        {"query": "déboguer mon code", "should_trigger": False},
        {"query": "benchmark skill v1 vs v2", "should_trigger": True},
        {"query": "installer node.js", "should_trigger": False},
        {"query": "optimiser la description de mon skill", "should_trigger": True},
    ]


@pytest.fixture
def benchmark_dir(tmp_path: Path) -> Path:
    """
    Structure de benchmark avec 2 configs et 2 evals.

    with_skill :    pass_rate=1.0, tokens=4000
    without_skill : pass_rate=0.0, tokens=1000
    """
    from scripts.utils import write_json

    def make_run(base: Path, pass_rate: float, tokens: int, time_s: float = 40.0) -> None:
        base.mkdir(parents=True)
        grading = {
            "expectations": [
                {"text": "Output correct", "passed": pass_rate == 1.0, "evidence": "ok"},
            ],
            "summary": {
                "passed": int(pass_rate),
                "failed": 1 - int(pass_rate),
                "total": 1,
                "pass_rate": pass_rate,
            },
            "execution_metrics": {
                "total_tool_calls": 8,
                "errors_encountered": 0,
                "output_chars": tokens,
            },
            "timing": {"total_duration_seconds": time_s},
            "user_notes_summary": {"uncertainties": [], "needs_review": [], "workarounds": []},
        }
        write_json(base / "grading.json", grading)
        write_json(base / "timing.json", {
            "total_tokens": tokens,
            "duration_ms": int(time_s * 1000),
            "total_duration_seconds": time_s,
        })

    for eval_name, eval_id in [("eval-pdf-extract", 1), ("eval-csv-parse", 2)]:
        make_run(tmp_path / eval_name / "with_skill" / "run-1", 1.0, 4000)
        make_run(tmp_path / eval_name / "without_skill" / "run-1", 0.0, 1000)
        write_json(tmp_path / eval_name / "eval_metadata.json", {
            "eval_id": eval_id,
            "eval_name": eval_name.replace("eval-", ""),
            "prompt": f"Test prompt {eval_id}",
            "assertions": [],
        })

    return tmp_path
