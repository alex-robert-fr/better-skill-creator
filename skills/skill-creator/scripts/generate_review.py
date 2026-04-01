#!/usr/bin/env python3
"""
Génère le viewer HTML de review et le sert localement.

Usage :
    # Review standard avec serveur
    python -m scripts.generate_review <workspace>/iteration-N \\
        --skill-name "mon-skill" \\
        --benchmark <workspace>/iteration-N/benchmark.json \\
        [--previous-workspace <workspace>/iteration-N-1]

    # Mode statique (fichier HTML standalone)
    python -m scripts.generate_review <workspace>/iteration-N \\
        --skill-name "mon-skill" \\
        --static /tmp/review.html

    # Mode trigger (résultats description optimization)
    python -m scripts.generate_review <workspace>/iteration-N \\
        --skill-name "mon-skill" \\
        --trigger-mode
"""

import argparse
import http.server
import json
import socketserver
import threading
import webbrowser
from pathlib import Path

from scripts.utils import read_json


# ---------------------------------------------------------------------------
# Collecte des données depuis le workspace
# ---------------------------------------------------------------------------

def _collect_runs(workspace_dir: Path) -> list[dict]:
    """
    Parcourt eval-*/<config>/run-*/ et construit la liste des runs pour le viewer.

    Chaque run contient : run_id, eval_name, configuration, prompt,
    transcript, grading, outputs_list.
    """
    runs = []

    for eval_dir in sorted(workspace_dir.glob("eval-*")):
        eval_name = eval_dir.name

        # Lire le prompt depuis eval_metadata.json
        prompt = ""
        meta_path = eval_dir / "eval_metadata.json"
        if meta_path.exists():
            try:
                meta = read_json(meta_path)
                prompt = meta.get("prompt", "")
                eval_name = meta.get("eval_name", eval_dir.name)
            except (FileNotFoundError, ValueError):
                pass

        for config_dir in sorted(eval_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            run_dirs = sorted(config_dir.glob("run-*"))
            if not run_dirs:
                continue

            for run_dir in run_dirs:
                run_id = f"{eval_dir.name}-{config_dir.name}-{run_dir.name}"

                transcript = ""
                transcript_path = run_dir / "transcript.md"
                if transcript_path.exists():
                    transcript = transcript_path.read_text(encoding="utf-8")

                grading = {}
                grading_path = run_dir / "grading.json"
                if grading_path.exists():
                    try:
                        grading = read_json(grading_path)
                    except (FileNotFoundError, ValueError):
                        pass

                outputs_list = []
                outputs_dir = run_dir / "outputs"
                if outputs_dir.exists():
                    outputs_list = [
                        p.name for p in sorted(outputs_dir.iterdir())
                        if p.is_file() and p.name != "metrics.json"
                    ]

                timing = {}
                timing_path = run_dir / "timing.json"
                if timing_path.exists():
                    try:
                        timing = read_json(timing_path)
                    except (FileNotFoundError, ValueError):
                        pass

                runs.append({
                    "run_id": run_id,
                    "eval_name": eval_name,
                    "configuration": config_dir.name,
                    "prompt": prompt,
                    "transcript": transcript,
                    "grading": grading,
                    "outputs_list": outputs_list,
                    "timing": timing,
                })

    return runs


def _collect_previous_runs(previous_workspace: Path) -> list[dict]:
    """Collecte les runs de l'itération précédente (pour comparaison)."""
    if not previous_workspace or not previous_workspace.exists():
        return []
    return _collect_runs(previous_workspace)


# ---------------------------------------------------------------------------
# Génération HTML
# ---------------------------------------------------------------------------

def build_review_html(
    workspace_dir: Path,
    skill_name: str,
    benchmark_path: Path | None = None,
    previous_workspace: Path | None = None,
    trigger_mode: bool = False,
) -> str:
    """
    Génère le HTML complet du viewer.

    Charge assets/eval_review.html (ou eval_review_trigger.html en trigger_mode),
    remplace les placeholders par les données JSON sérialisées.
    """
    # Trouver le répertoire assets/ relatif à ce script
    scripts_dir = Path(__file__).parent
    asset_name = "eval_review_trigger.html" if trigger_mode else "eval_review.html"
    asset_path = scripts_dir.parent / "assets" / asset_name

    if not asset_path.exists():
        raise FileNotFoundError(f"Template HTML introuvable : {asset_path}")

    template = asset_path.read_text(encoding="utf-8")

    # Collecter les données
    runs = _collect_runs(workspace_dir)
    previous_runs = _collect_previous_runs(previous_workspace) if previous_workspace else []

    benchmark_data = {}
    if benchmark_path and benchmark_path.exists():
        try:
            benchmark_data = read_json(benchmark_path)
        except (FileNotFoundError, ValueError):
            pass

    def safe_json(data) -> str:
        return json.dumps(data, ensure_ascii=False, indent=None)

    html = template
    html = html.replace("__EVAL_DATA_PLACEHOLDER__", safe_json(runs))
    html = html.replace("__BENCHMARK_DATA_PLACEHOLDER__", safe_json(benchmark_data))
    html = html.replace("__SKILL_NAME_PLACEHOLDER__", skill_name)
    html = html.replace("__PREVIOUS_DATA_PLACEHOLDER__", safe_json(previous_runs))

    return html


# ---------------------------------------------------------------------------
# Serveur HTTP local
# ---------------------------------------------------------------------------

def serve_review(html_content: str, port: int = 8765) -> tuple[socketserver.TCPServer, int]:
    """
    Sert le HTML dans un thread background sur le port donné.
    Essaie des ports suivants si le port est déjà occupé.

    Returns:
        (server, port_used)
    """
    html_bytes = html_content.encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)

        def log_message(self, fmt, *args):
            pass  # Silence les logs HTTP

    for attempt in range(10):
        try:
            server = socketserver.TCPServer(("", port + attempt), Handler)
            actual_port = port + attempt
            break
        except OSError:
            continue
    else:
        raise RuntimeError(f"Impossible de trouver un port disponible depuis {port}")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return server, actual_port


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Génère et sert le viewer de review")
    parser.add_argument("workspace_dir", type=Path, help="Répertoire iteration-N/")
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--benchmark", type=Path, help="Chemin vers benchmark.json")
    parser.add_argument("--previous-workspace", type=Path, help="Workspace itération précédente")
    parser.add_argument("--static", type=Path, help="Écrire le HTML dans ce fichier (pas de serveur)")
    parser.add_argument("--trigger-mode", action="store_true", help="Mode description optimization")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if not args.workspace_dir.exists():
        import sys
        print(f"Workspace introuvable : {args.workspace_dir}", file=sys.stderr)
        sys.exit(1)

    html = build_review_html(
        workspace_dir=args.workspace_dir,
        skill_name=args.skill_name,
        benchmark_path=args.benchmark,
        previous_workspace=args.previous_workspace,
        trigger_mode=args.trigger_mode,
    )

    # Mode statique : écrire le fichier et indiquer le chemin
    if args.static:
        args.static.parent.mkdir(parents=True, exist_ok=True)
        args.static.write_text(html, encoding="utf-8")
        print(f"Viewer écrit dans : {args.static}")
        return

    # Mode serveur : démarrer et ouvrir le navigateur
    server, port = serve_review(html, port=args.port)
    url = f"http://localhost:{port}"
    print(f"Viewer disponible sur : {url}")
    print("Appuyer sur Ctrl+C pour arrêter.")

    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServeur arrêté.")


if __name__ == "__main__":
    main()
