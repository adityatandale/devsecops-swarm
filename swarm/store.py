"""Run history persisted as JSON (read by the Streamlit dashboard)."""
import json
import time
from pathlib import Path

from .config import RUNS_DIR


def _seen_path() -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR / "seen.json"


def load_seen() -> set:
    p = _seen_path()
    return set(json.loads(p.read_text())) if p.exists() else set()


def mark_seen(incident_id: str) -> None:
    seen = load_seen()
    seen.add(incident_id)
    _seen_path().write_text(json.dumps(sorted(seen)))


def save_run(state: dict) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    inc = state.get("incident", {}).get("id", "none")
    path = RUNS_DIR / f"run_{time.strftime('%Y%m%d_%H%M%S')}_{inc}.json"
    path.write_text(json.dumps(state, indent=2, default=str))
    return path


def list_runs() -> list:
    if not RUNS_DIR.exists():
        return []
    runs = []
    for p in sorted(RUNS_DIR.glob("run_*.json"), reverse=True):
        try:
            runs.append({"file": p.name, **json.loads(p.read_text())})
        except json.JSONDecodeError:
            continue
    return runs
