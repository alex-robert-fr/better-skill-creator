"""Utilitaires partagés entre les scripts skill-creator."""

import json
from pathlib import Path


def parse_skill_md(skill_path: Path) -> dict:
    """
    Parse le frontmatter YAML et le corps d'un fichier SKILL.md.

    Retourne un dict avec les clés :
      - name (str)
      - description (str)
      - body (str) : contenu markdown hors frontmatter

    Raises:
        FileNotFoundError si le fichier n'existe pas
        ValueError si le frontmatter est absent ou malformé
    """
    if not skill_path.exists():
        raise FileNotFoundError(f"SKILL.md introuvable : {skill_path}")

    content = skill_path.read_text(encoding="utf-8")

    if not content.startswith("---"):
        raise ValueError(f"Pas de frontmatter YAML dans {skill_path}")

    # Extraire le bloc frontmatter entre les deux "---"
    end = content.find("\n---", 3)
    if end == -1:
        raise ValueError(f"Frontmatter non fermé dans {skill_path}")

    frontmatter_block = content[3:end].strip()
    body = content[end + 4:].strip()

    # Parser le YAML manuellement (évite la dépendance PyYAML pour des champs simples)
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in frontmatter_block.splitlines():
        if line and not line.startswith(" ") and ":" in line:
            # Sauvegarder le champ précédent si multi-ligne
            if current_key is not None:
                fields[current_key] = "\n".join(current_lines).strip()
            key, _, value = line.partition(":")
            current_key = key.strip()
            current_lines = [value.strip()]
        elif current_key is not None:
            # Continuation d'une valeur multi-ligne (ex : description longue)
            current_lines.append(line.strip())

    if current_key is not None:
        fields[current_key] = "\n".join(current_lines).strip()

    name = fields.get("name", "")
    description = fields.get("description", "")

    if not name:
        raise ValueError(f"Champ 'name' manquant dans le frontmatter de {skill_path}")

    return {"name": name, "description": description, "body": body}


def find_project_root(start: Path) -> Path:
    """
    Remonte l'arborescence depuis `start` jusqu'à trouver la racine du projet
    (présence de .claude-plugin/ ou .git/).

    Raises:
        FileNotFoundError si aucune racine n'est trouvée
    """
    current = start if start.is_dir() else start.parent

    for directory in [current, *current.parents]:
        if (directory / ".claude-plugin").exists() or (directory / ".git").exists():
            return directory

    raise FileNotFoundError(
        f"Racine de projet introuvable depuis {start} "
        "(cherche .claude-plugin/ ou .git/)"
    )


def write_json(path: Path, data: dict | list, indent: int = 2) -> None:
    """Écrit `data` en JSON dans `path`, crée les répertoires parents si besoin."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict | list:
    """
    Lit et parse un fichier JSON.

    Raises:
        FileNotFoundError si le fichier n'existe pas
        ValueError si le JSON est invalide (avec le chemin dans le message)
    """
    if not path.exists():
        raise FileNotFoundError(f"Fichier JSON introuvable : {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON invalide dans {path} : {e}") from e
