#!/usr/bin/env python3
"""
Package un skill en fichier .skill installable.

Le fichier .skill est une archive ZIP renommée contenant :
    skill.json     : métadonnées (name, description, version)
    SKILL.md       : instructions principales
    scripts/       : scripts Python (si présents)
    agents/        : instructions agents (si présents)
    references/    : fichiers de référence (si présents)
    assets/        : fichiers statiques (si présents)

Usage :
    python -m scripts.package_skill <path/to/skill-folder> \\
        [--output <path/to/output.skill>] \\
        [--version 1.0.0]
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path

from scripts.utils import parse_skill_md

# Répertoires inclus dans le package (dans cet ordre)
_BUNDLED_DIRS = ["scripts", "agents", "references", "assets"]

# Fichiers/dossiers exclus du package
_EXCLUDE_PATTERNS = {
    "__pycache__", ".pytest_cache", ".ruff_cache",
    ".DS_Store", "*.pyc", "evals", "*-workspace",
}

_MAX_FILE_SIZE_MB = 10


def _is_excluded(path: Path) -> bool:
    for pattern in _EXCLUDE_PATTERNS:
        if "*" in pattern:
            if path.match(pattern):
                return True
        elif path.name == pattern:
            return True
    return False


def validate_skill(skill_dir: Path) -> dict:
    """
    Valide qu'un répertoire est un skill valide avant packaging.

    Vérifie :
    - Présence de SKILL.md
    - Frontmatter avec name et description non vides
    - Aucun fichier > 10 MB

    Returns:
        dict avec name et description du skill

    Raises:
        ValueError si la validation échoue
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise ValueError(f"SKILL.md introuvable dans {skill_dir}")

    parsed = parse_skill_md(skill_md)

    if not parsed["name"]:
        raise ValueError("Le frontmatter SKILL.md doit contenir un champ 'name' non vide")
    if not parsed["description"]:
        raise ValueError("Le frontmatter SKILL.md doit contenir un champ 'description' non vide")

    # Vérifier les tailles de fichiers
    for file_path in skill_dir.rglob("*"):
        if file_path.is_file() and not _is_excluded(file_path):
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > _MAX_FILE_SIZE_MB:
                raise ValueError(
                    f"Fichier trop volumineux ({size_mb:.1f} MB > {_MAX_FILE_SIZE_MB} MB) : "
                    f"{file_path.relative_to(skill_dir)}"
                )

    return {"name": parsed["name"], "description": parsed["description"]}


def package_skill(
    skill_dir: Path,
    output_path: Path | None = None,
    version: str = "1.0.0",
) -> Path:
    """
    Package le skill en fichier .skill (archive ZIP).

    Structure dans le ZIP :
        skill.json
        SKILL.md
        scripts/...
        agents/...
        references/...
        assets/...

    Returns:
        Chemin du fichier .skill généré
    """
    meta = validate_skill(skill_dir)

    if output_path is None:
        output_path = skill_dir.parent / f"{meta['name']}.skill"

    skill_json = {
        "name": meta["name"],
        "description": meta["description"],
        "version": version,
    }

    files_added = 0

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # skill.json en premier
        zf.writestr("skill.json", json.dumps(skill_json, indent=2, ensure_ascii=False))

        # SKILL.md
        zf.write(skill_dir / "SKILL.md", "SKILL.md")
        files_added += 1

        # Répertoires bundlés
        for dir_name in _BUNDLED_DIRS:
            dir_path = skill_dir / dir_name
            if not dir_path.exists():
                continue
            for file_path in sorted(dir_path.rglob("*")):
                if not file_path.is_file():
                    continue
                if _is_excluded(file_path):
                    continue
                arcname = file_path.relative_to(skill_dir)
                zf.write(file_path, arcname)
                files_added += 1

    size_kb = output_path.stat().st_size / 1024
    return output_path, files_added, size_kb


def main() -> None:
    parser = argparse.ArgumentParser(description="Package un skill en fichier .skill")
    parser.add_argument("skill_dir", type=Path, help="Répertoire du skill (contient SKILL.md)")
    parser.add_argument("--output", type=Path, help="Chemin de sortie (défaut: sibling du skill)")
    parser.add_argument("--version", default="1.0.0", help="Version du skill")
    args = parser.parse_args()

    if not args.skill_dir.exists():
        print(f"Répertoire introuvable : {args.skill_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        output_path, files_added, size_kb = package_skill(
            args.skill_dir,
            output_path=args.output,
            version=args.version,
        )
    except ValueError as e:
        print(f"Erreur de validation : {e}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ {output_path}")
    print(f"  {files_added} fichiers — {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
