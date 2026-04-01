"""Tests pour scripts/package_skill.py"""

import json
import zipfile
import pytest
from pathlib import Path

from scripts.package_skill import package_skill, validate_skill


class TestValidateSkill:
    def test_valid_skill(self, skill_dir: Path) -> None:
        meta = validate_skill(skill_dir)
        assert meta["name"] == "my-skill"
        assert meta["description"] == "Test skill description."

    def test_missing_skill_md(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="SKILL.md introuvable"):
            validate_skill(tmp_path)

    def test_missing_name(self, tmp_path: Path) -> None:
        (tmp_path / "SKILL.md").write_text(
            "---\ndescription: only desc\n---\n", encoding="utf-8"
        )
        with pytest.raises(ValueError, match="name"):
            validate_skill(tmp_path)

    def test_missing_description(self, tmp_path: Path) -> None:
        (tmp_path / "SKILL.md").write_text(
            "---\nname: foo\n---\n", encoding="utf-8"
        )
        with pytest.raises(ValueError, match="description"):
            validate_skill(tmp_path)

    def test_large_file_rejected(self, skill_dir: Path) -> None:
        big = skill_dir / "scripts" / "huge.py"
        big.parent.mkdir(exist_ok=True)
        big.write_bytes(b"x" * (11 * 1024 * 1024))  # 11 MB
        with pytest.raises(ValueError, match="volumineux"):
            validate_skill(skill_dir)


class TestPackageSkill:
    def test_creates_skill_file(self, skill_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "my-skill.skill"
        path, files_added, size_kb = package_skill(skill_dir, output_path=out)
        assert path.exists()
        assert path.suffix == ".skill"

    def test_zip_contains_required_files(self, skill_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "out.skill"
        path, _, _ = package_skill(skill_dir, output_path=out)
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        assert "SKILL.md" in names
        assert "skill.json" in names

    def test_skill_json_metadata(self, skill_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "out.skill"
        path, _, _ = package_skill(skill_dir, output_path=out, version="2.1.0")
        with zipfile.ZipFile(path) as zf:
            meta = json.loads(zf.read("skill.json"))
        assert meta["name"] == "my-skill"
        assert meta["version"] == "2.1.0"
        assert meta["description"] == "Test skill description."

    def test_bundles_subdirs(self, skill_dir: Path, tmp_path: Path) -> None:
        # Créer des fichiers dans les sous-répertoires
        (skill_dir / "agents").mkdir()
        (skill_dir / "agents" / "grader.md").write_text("# Grader", encoding="utf-8")
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "helper.py").write_text("# helper", encoding="utf-8")
        out = tmp_path / "out.skill"
        path, files_added, _ = package_skill(skill_dir, output_path=out)
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        assert "agents/grader.md" in names
        assert "scripts/helper.py" in names
        assert files_added >= 3

    def test_excludes_pycache(self, skill_dir: Path, tmp_path: Path) -> None:
        cache = skill_dir / "scripts" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "utils.cpython-312.pyc").write_bytes(b"bytecode")
        out = tmp_path / "out.skill"
        path, _, _ = package_skill(skill_dir, output_path=out)
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        assert not any("__pycache__" in n for n in names)

    def test_default_output_path(self, skill_dir: Path) -> None:
        path, _, _ = package_skill(skill_dir)
        assert path == skill_dir.parent / "my-skill.skill"
        path.unlink(missing_ok=True)
