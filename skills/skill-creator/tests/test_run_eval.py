"""Tests pour scripts/run_eval.py"""

import pytest
from pathlib import Path

from scripts.run_eval import _write_timing, build_task_prompt
from scripts.utils import read_json


class TestBuildTaskPrompt:
    def test_includes_prompt(self) -> None:
        p = build_task_prompt("Fais X", [], Path("/tmp/out"), None)
        assert "Fais X" in p

    def test_includes_output_dir(self) -> None:
        p = build_task_prompt("task", [], Path("/workspace/outputs"), None)
        assert "/workspace/outputs" in p

    def test_includes_metrics_instruction(self) -> None:
        p = build_task_prompt("task", [], Path("/out"), None)
        assert "metrics.json" in p
        assert "tool_calls" in p

    def test_lists_input_files(self) -> None:
        p = build_task_prompt("task", ["/data/file.csv", "/data/img.png"], Path("/out"), None)
        assert "file.csv" in p
        assert "img.png" in p

    def test_no_files(self) -> None:
        p = build_task_prompt("task", [], Path("/out"), None)
        assert "Fichiers d'input" not in p


class TestWriteTiming:
    def test_writes_correct_fields(self, tmp_path: Path) -> None:
        _write_timing(tmp_path, 12500)
        data = read_json(tmp_path / "timing.json")
        assert data["duration_ms"] == 12500
        assert data["total_duration_seconds"] == 12.5
        assert "total_tokens" in data
        assert data["total_tokens"] == 0  # à compléter par le parent

    def test_zero_duration(self, tmp_path: Path) -> None:
        _write_timing(tmp_path, 0)
        data = read_json(tmp_path / "timing.json")
        assert data["total_duration_seconds"] == 0.0

    def test_rounding(self, tmp_path: Path) -> None:
        _write_timing(tmp_path, 33333)
        data = read_json(tmp_path / "timing.json")
        assert data["total_duration_seconds"] == 33.3
