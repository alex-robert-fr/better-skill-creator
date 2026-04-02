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
                outputs_content = {}
                outputs_dir = run_dir / "outputs"
                if outputs_dir.exists():
                    for p in sorted(outputs_dir.iterdir()):
                        if p.is_file() and p.name != "metrics.json":
                            outputs_list.append(p.name)
                            try:
                                outputs_content[p.name] = p.read_text(encoding="utf-8")
                            except Exception:
                                outputs_content[p.name] = ""

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
                    "outputs_content": outputs_content,
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

def _build_iteration_entry(benchmark_data: dict, iteration_number: int) -> tuple[dict, dict]:
    """
    Construit un entry d'itération et retourne (iteration_entry, eval_runs_by_id).
    """
    b_runs = benchmark_data.get("runs", [])
    run_summary = benchmark_data.get("run_summary", {})
    cost_per_token = 0.00001

    configs: dict[str, dict] = {}
    for cfg_name, cfg_stats in run_summary.items():
        if cfg_name == "delta":
            continue
        config_runs = [r for r in b_runs if r.get("configuration") == cfg_name]
        configs[cfg_name] = {
            "pass_rate": {
                "mean": cfg_stats["pass_rate"]["mean"],
                "stddev": cfg_stats["pass_rate"]["stddev"],
                "values": [r["result"]["pass_rate"] for r in config_runs],
            },
            "time_seconds": {
                "mean": cfg_stats["time_seconds"]["mean"],
                "stddev": cfg_stats["time_seconds"]["stddev"],
                "values": [r["result"]["time_seconds"] for r in config_runs],
            },
            "tokens": {
                "mean": cfg_stats["tokens"]["mean"],
                "stddev": cfg_stats["tokens"]["stddev"],
                "values": [float(r["result"]["tokens"]) for r in config_runs],
            },
            "cost_usd": {
                "mean": cfg_stats["tokens"]["mean"] * cost_per_token,
                "stddev": cfg_stats["tokens"]["stddev"] * cost_per_token,
                "values": [r["result"]["tokens"] * cost_per_token for r in config_runs],
            },
        }

    delta_raw = run_summary.get("delta", {}).get("with_skill", {})
    delta = {
        "pass_rate": f"{float(delta_raw.get('pass_rate', 0)):+.0f}%",
        "time_seconds": f"{float(delta_raw.get('time_seconds', 0)):+.1f}s",
        "tokens": delta_raw.get("tokens", "+0"),
        "cost_usd": f"${float(delta_raw.get('tokens', '0').lstrip('+')) * cost_per_token:+.4f}",
    }

    eval_runs: dict[int, list] = {}
    for r in b_runs:
        eid = r["eval_id"]
        if eid not in eval_runs:
            eval_runs[eid] = []
        eval_runs[eid].append({
            "iteration": iteration_number,
            "configuration": r["configuration"],
            "run_number": r["run_number"],
            "pass_rate": r["result"]["pass_rate"],
            "passed": r["result"]["passed"],
            "total": r["result"]["total"],
            "time_seconds": r["result"]["time_seconds"],
            "tokens": r["result"]["tokens"],
            "cost_usd": round(r["result"]["tokens"] * cost_per_token, 6),
            "errors": r["result"]["errors"],
            "expectations": r.get("expectations", []),
        })

    iteration_entry = {
        "iteration": iteration_number,
        "description": "",
        "description_hash": f"iter{iteration_number}",
        "configs": configs,
        "delta": delta,
    }
    return iteration_entry, eval_runs


def _build_dashboard_data(
    benchmark_data: dict,
    skill_name: str,
    previous_benchmarks: list[dict] | None = None,
) -> dict:
    """
    Transforme benchmark.json en format BENCHMARK_DATA pour le dashboard.
    Intègre toutes les itérations précédentes dans l'ordre chronologique.
    previous_benchmarks : liste ordonnée de la plus ancienne à la plus récente.
    """
    meta = benchmark_data.get("metadata", {})
    all_benchmarks = list(previous_benchmarks or []) + [benchmark_data]

    iterations = []
    eval_map: dict[int, dict] = {}

    for i, bench in enumerate(all_benchmarks):
        iter_number = i + 1
        entry, eval_runs = _build_iteration_entry(bench, iter_number)
        iterations.append(entry)
        for r in bench.get("runs", []):
            eid = r["eval_id"]
            if eid not in eval_map:
                eval_map[eid] = {
                    "eval_id": eid,
                    "eval_name": r["eval_name"],
                    "category": "general",
                    "runs": [],
                }
            eval_map[eid]["runs"].extend(eval_runs.get(eid, []))

    return {
        "metadata": {
            "generated_at": meta.get("timestamp", ""),
            "skill_name": skill_name,
            "skill_description": "",
            "model": meta.get("executor_model", ""),
            "total_iterations": len(iterations),
            "runs_per_config": meta.get("runs_per_configuration", 1),
        },
        "iterations": iterations,
        "evals": list(eval_map.values()),
        "trigger_eval": None,
    }


def build_review_html(
    workspace_dir: Path,
    skill_name: str,
    benchmark_path: Path | None = None,
    previous_workspace: Path | None = None,
    trigger_mode: bool = False,
) -> str:
    """
    Génère le HTML complet du viewer.

    Charge assets/eval_review_dashboard.html (ou eval_review_trigger.html
    en trigger_mode) et remplace les placeholders par les données JSON.
    """
    # Trouver le répertoire assets/ relatif à ce script
    scripts_dir = Path(__file__).parent
    if trigger_mode:
        asset_name = "eval_review_trigger.html"
    else:
        asset_name = "eval_review_dashboard.html"
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

    # Dashboard template : transformer les données au format BENCHMARK_DATA
    if "/*__BENCHMARK_DATA__*/" in html and benchmark_data:
        # Auto-détecter toutes les itérations précédentes dans le workspace parent
        previous_benchmarks: list[dict] = []
        workspace_parent = workspace_dir.parent

        def _iter_number(path: Path) -> int:
            try:
                return int(path.name.split("-")[-1])
            except ValueError:
                return -1

        current_iter_num = _iter_number(workspace_dir)
        if current_iter_num > 0:
            prev_dirs = sorted(
                [d for d in workspace_parent.iterdir()
                 if d.is_dir() and _iter_number(d) > 0 and _iter_number(d) < current_iter_num],
                key=_iter_number,
            )
            for prev_dir in prev_dirs:
                bench_path = prev_dir / "benchmark.json"
                if bench_path.exists():
                    try:
                        previous_benchmarks.append(read_json(bench_path))
                    except (FileNotFoundError, ValueError):
                        pass

        dashboard_data = _build_dashboard_data(benchmark_data, skill_name, previous_benchmarks)
        html = html.replace("/*__BENCHMARK_DATA__*/ null", safe_json(dashboard_data))

    # Templates classiques : placeholders historiques
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
