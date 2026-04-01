#!/usr/bin/env python3
"""
Lance un run d'évaluation pour un skill donné.

Exécute `claude -p "<prompt>"` avec ou sans skill chargé, capture le transcript
et les métriques dans le répertoire de sortie.

Utilisé par deux contextes :
  1. run_loop.py — teste si un skill se déclenche pour une query donnée (trigger eval)
  2. Directement par les subagents du SKILL.md pour lancer les runs d'évaluation complets

Usage :
    python -m scripts.run_eval \\
        --skill-path skills/skill-creator \\
        --eval-id 1 \\
        --evals-file evals/evals.json \\
        --output-dir workspace/iteration-1/eval-pdf-extract/with_skill/run-1/

    # Vanilla (sans skill)
    python -m scripts.run_eval \\
        --eval-id 1 \\
        --evals-file evals/evals.json \\
        --output-dir workspace/iteration-1/eval-pdf-extract/without_skill/run-1/

Structure produite dans output-dir/ :
    transcript.md          ← réponse brute de claude
    timing.json            ← durée (total_tokens à remplir par le parent si subagent)
    outputs/               ← fichiers produits par la tâche
        metrics.json       ← outil calls, output_chars (écrit par claude si prompt correct)
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from scripts.utils import read_json, write_json


def build_task_prompt(
    eval_prompt: str,
    eval_files: list[str],
    outputs_dir: Path,
    skill_path: Path | None,
) -> str:
    """
    Construit le prompt complet envoyé à claude.

    Inclut le prompt de tâche, les chemins des fichiers d'input, où sauvegarder
    les outputs, et l'instruction d'écrire metrics.json.
    """
    lines = [eval_prompt, ""]

    if eval_files:
        lines.append("Fichiers d'input disponibles :")
        for f in eval_files:
            lines.append(f"  - {f}")
        lines.append("")

    lines += [
        f"Sauvegarde tous tes outputs dans : {outputs_dir}/",
        f"Écris également {outputs_dir}/metrics.json avec ce format exactement :",
        '{"tool_calls": {"Read": N, "Write": N, "Bash": N, "Edit": N, "Glob": N, "Grep": N},',
        ' "total_tool_calls": N,',
        ' "total_steps": N,',
        ' "files_created": ["fichier1", "fichier2"],',
        ' "errors_encountered": N,',
        ' "output_chars": N,',
        ' "transcript_chars": N}',
    ]

    return "\n".join(lines)


def run_eval(
    skill_path: Path | None,
    eval_prompt: str,
    eval_files: list[str],
    output_dir: Path,
    model: str = "claude-sonnet-4-6",
    timeout: int = 300,
) -> dict:
    """
    Exécute un run d'évaluation via `claude -p`.

    Args:
        skill_path : chemin vers le répertoire du skill (None = vanilla)
        eval_prompt : prompt de la tâche à exécuter
        eval_files  : chemins des fichiers d'input (copiés dans outputs/)
        output_dir  : répertoire de sortie du run
        model       : identifiant du modèle Claude
        timeout     : timeout en secondes (défaut 5 min)

    Returns:
        dict avec : success (bool), output_dir (str), duration_ms (int),
                    returncode (int), stderr (str)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = output_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Copier les fichiers d'input dans le workspace du run
    copied_files: list[str] = []
    for file_str in eval_files:
        src = Path(file_str)
        if src.exists():
            dest = outputs_dir / src.name
            shutil.copy2(src, dest)
            copied_files.append(str(dest))
        else:
            print(f"Avertissement : fichier d'input introuvable : {src}", file=sys.stderr)

    full_prompt = build_task_prompt(
        eval_prompt,
        copied_files or eval_files,
        outputs_dir,
        skill_path,
    )

    # Construire la commande claude
    cmd = ["claude", "--print", full_prompt, "--model", model]
    if skill_path is not None:
        cmd += ["--skill", str(skill_path)]

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        _write_timing(output_dir, duration_ms)
        return {
            "success": False,
            "output_dir": str(output_dir),
            "duration_ms": duration_ms,
            "returncode": -1,
            "stderr": f"Timeout après {timeout}s",
        }
    except FileNotFoundError:
        raise RuntimeError(
            "Commande 'claude' introuvable — vérifier que Claude Code CLI est installé"
        )

    duration_ms = int((time.monotonic() - start) * 1000)

    # Sauvegarder le transcript
    transcript = result.stdout.strip()
    (output_dir / "transcript.md").write_text(transcript, encoding="utf-8")

    if result.stderr:
        (output_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")

    # Écrire timing.json
    # Note : total_tokens n'est pas disponible depuis subprocess — le parent (subagent
    # dans le SKILL.md) doit le compléter depuis la notification de complétion de tâche.
    _write_timing(output_dir, duration_ms)

    # Si metrics.json n'a pas été écrit par claude, en créer un minimal
    metrics_path = outputs_dir / "metrics.json"
    if not metrics_path.exists():
        output_chars = sum(
            p.stat().st_size
            for p in outputs_dir.rglob("*")
            if p.is_file() and p.name != "metrics.json"
        )
        write_json(metrics_path, {
            "tool_calls": {},
            "total_tool_calls": 0,
            "total_steps": 0,
            "files_created": [p.name for p in outputs_dir.iterdir() if p.is_file()],
            "errors_encountered": 0 if result.returncode == 0 else 1,
            "output_chars": output_chars,
            "transcript_chars": len(transcript),
        })

    return {
        "success": result.returncode == 0,
        "output_dir": str(output_dir),
        "duration_ms": duration_ms,
        "returncode": result.returncode,
        "stderr": result.stderr[:500] if result.stderr else "",
    }


def _write_timing(output_dir: Path, duration_ms: int) -> None:
    """Écrit timing.json avec les données disponibles depuis subprocess."""
    write_json(output_dir / "timing.json", {
        "total_tokens": 0,  # à compléter par le parent depuis la notification de tâche
        "duration_ms": duration_ms,
        "total_duration_seconds": round(duration_ms / 1000, 1),
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Lance un run d'évaluation")
    parser.add_argument(
        "--skill-path", type=Path,
        help="Chemin vers le répertoire du skill. Absent = run vanilla.",
    )
    parser.add_argument("--eval-id", type=int, required=True, help="ID de l'eval dans evals.json")
    parser.add_argument("--evals-file", type=Path, required=True, help="Chemin vers evals.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="Répertoire de sortie du run")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    if not args.evals_file.exists():
        print(f"evals.json introuvable : {args.evals_file}", file=sys.stderr)
        sys.exit(1)

    evals_data = read_json(args.evals_file)
    evals = evals_data.get("evals", [])
    eval_entry = next((e for e in evals if e.get("id") == args.eval_id), None)

    if eval_entry is None:
        print(f"Eval id={args.eval_id} introuvable dans {args.evals_file}", file=sys.stderr)
        sys.exit(1)

    result = run_eval(
        skill_path=args.skill_path,
        eval_prompt=eval_entry["prompt"],
        eval_files=eval_entry.get("files", []),
        output_dir=args.output_dir,
        model=args.model,
        timeout=args.timeout,
    )

    status = "OK" if result["success"] else f"ERREUR (code {result['returncode']})"
    config = args.skill_path.name if args.skill_path else "vanilla"
    print(f"[{config}] eval-{args.eval_id} : {status} ({result['duration_ms']}ms)")
    print(f"  outputs → {result['output_dir']}/outputs/")

    if not result["success"]:
        if result["stderr"]:
            print(f"  stderr : {result['stderr']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
