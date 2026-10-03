"""Benchmark harness: injects each bug, runs the swarm, reports fix rate / attempts / latency.

Usage:  python benchmarks/evaluate.py [--sandbox docker|local] [--ablate]
--ablate also runs every case WITHOUT Qdrant memory so you can quantify its contribution.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from swarm.graph import run_pipeline  # noqa: E402


def run_case(case_dir: Path, memory, sandbox: str):
    tmp = Path(tempfile.mkdtemp(prefix="bench_"))
    repo = tmp / case_dir.name
    shutil.copytree(case_dir, repo)
    cfg = json.loads((repo / "case.json").read_text())
    log = tmp / "app.log"
    subprocess.run([sys.executable, "-m", "swarm.simulate", "--repo", str(repo), "--module", cfg["module"],
                    "--call", cfg["call"], "--log", str(log)], cwd=ROOT, check=True, capture_output=True)
    t0 = time.time()
    final = run_pipeline(repo, log, memory=memory, dry_run=True, ignore_seen=True, sandbox_mode=sandbox, save=False)
    return {"case": case_dir.name, "status": final.get("status"), "attempts": final.get("attempt", 0),
            "seconds": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", default="docker", choices=["docker", "local"])
    ap.add_argument("--ablate", action="store_true")
    a = ap.parse_args()
    from swarm.vector_store import FixMemory
    cases = sorted(p for p in (ROOT / "benchmarks/cases").iterdir() if p.is_dir())
    results = {}
    configs = [("with_memory", True)] + ([("without_memory", False)] if a.ablate else [])
    for label, use_mem in configs:
        mem = FixMemory(path=Path(tempfile.mkdtemp(prefix="qd_"))) if use_mem else None
        if mem:  # seed with generic historical fixes
            import main as cli
            for sig, expl, diff in cli.SEED:
                mem.add_fix(sig, diff, expl, source="seed")
        results[label] = [run_case(c, mem, a.sandbox) for c in cases]
    for label, rows in results.items():
        ok = sum(r["status"] == "pr_submitted" for r in rows)
        print(f"\n== {label}: fixed {ok}/{len(rows)} ==")
        print("| case | status | attempts | seconds |\n|---|---|---|---|")
        for r in rows:
            print(f"| {r['case']} | {r['status']} | {r['attempts']} | {r['seconds']} |")
    (ROOT / "benchmarks/results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
