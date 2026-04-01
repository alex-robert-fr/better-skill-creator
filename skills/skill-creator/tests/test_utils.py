"""Tests pour scripts/utils.py"""

import json
import pytest
from pathlib import Path

from scripts.utils import find_project_root, parse_skill_md, read_json, write_json


class TestParseSkillMd:
    def test_basic(self, skill_dir: Path) -> None:
        result = parse_skill_md(skill_dir / "SKILL.md")
        assert result["name"] == "my-skill"
        assert result["description"] == "Test skill description."
        assert "Body" in result["body"]

    def test_multiline_description(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text(
            "---\nname: foo\ndescription: Ligne 1\n  Ligne 2\n---\n",
            encoding="utf-8",
        )
        result = parse_skill_md(f)
        assert "Ligne 1" in result["description"]

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_skill_md(tmp_path / "nope.md")

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("# Just markdown, no frontmatter", encoding="utf-8")
        with pytest.raises(ValueError, match="frontmatter"):
            parse_skill_md(f)

    def test_unclosed_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: foo\n", encoding="utf-8")
        with pytest.raises(ValueError, match="non fermé"):
            parse_skill_md(f)

    def test_missing_name(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("---\ndescription: desc\n---\n", encoding="utf-8")
        with pytest.raises(ValueError, match="name"):
            parse_skill_md(f)


class TestFindProjectRoot:
    def test_finds_git(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        root = find_project_root(sub)
        assert root == tmp_path

    def test_finds_claude_plugin(self, tmp_path: Path) -> None:
        (tmp_path / ".claude-plugin").mkdir()
        root = find_project_root(tmp_path / "skills" / "my-skill")
        assert root == tmp_path

    def test_not_found(self, tmp_path: Path) -> None:
        isolated = tmp_path / "isolated"
        isolated.mkdir()
        with pytest.raises(FileNotFoundError):
            find_project_root(isolated)

    def test_from_file_path(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        f = tmp_path / "some" / "file.py"
        f.parent.mkdir(parents=True)
        f.touch()
        root = find_project_root(f)
        assert root == tmp_path


class TestReadWriteJson:
    def test_roundtrip(self, tmp_path: Path) -> None:
        data = {"key": [1, 2, 3], "nested": {"a": True}}
        path = tmp_path / "data.json"
        write_json(path, data)
        assert read_json(path) == data

    def test_creates_parents(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "file.json"
        write_json(path, {"x": 1})
        assert path.exists()

    def test_list_data(self, tmp_path: Path) -> None:
        data = [{"a": 1}, {"b": 2}]
        path = tmp_path / "list.json"
        write_json(path, data)
        assert read_json(path) == data

    def test_read_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_json(tmp_path / "nope.json")

    def test_read_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("{ not valid json }", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON invalide"):
            read_json(f)

    def test_utf8_content(self, tmp_path: Path) -> None:
        data = {"message": "héllo wörld — 日本語"}
        path = tmp_path / "utf8.json"
        write_json(path, data)
        assert read_json(path)["message"] == data["message"]
