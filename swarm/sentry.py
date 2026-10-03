"""Agent 1 - Sentry: watches structured logs, extracts incidents, retrieves similar historical fixes."""
import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from .config import LATENCY_THRESHOLD_MS

FRAME_RE = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)')


def read_records(log_file) -> list:
    path = Path(log_file)
    if not path.exists():
        return []
    records = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            continue  # ignore non-JSON noise
    return records


def parse_traceback(tb: str):
    """Return (frames, exception_type, exception_message) from a Python traceback string."""
    frames = [
        {"file": m["file"], "line": int(m["line"]), "func": m["func"]}
        for m in FRAME_RE.finditer(tb)
    ]
    lines = [ln for ln in tb.strip().splitlines() if ln.strip()]
    last = lines[-1] if lines else ""
    etype, _, emsg = last.partition(":")
    return frames, etype.strip(), emsg.strip()


def make_signature(etype: str, emsg: str, frames: list) -> str:
    """Normalised, line-number-free fingerprint used for semantic matching."""
    norm = re.sub(r"\d+", "N", emsg)
    funcs = " > ".join(f["func"] for f in frames[-3:] if f["func"] != "<module>")
    return f"{etype}: {norm} @ {funcs}".strip()


def _incident_id(rec: dict) -> str:
    return hashlib.md5(json.dumps(rec, sort_keys=True).encode()).hexdigest()[:10]


def find_incident(log_file, seen: Optional[set] = None) -> Optional[dict]:
    """Newest unseen crash (ERROR + traceback) or latency anomaly."""
    seen = seen or set()
    for rec in reversed(read_records(log_file)):
        iid = _incident_id(rec)
        if iid in seen:
            continue
        level = str(rec.get("level", "")).upper()
        if level in ("ERROR", "CRITICAL") and rec.get("traceback"):
            frames, etype, emsg = parse_traceback(rec["traceback"])
            return {
                "id": iid,
                "kind": "crash",
                "service": rec.get("service", "unknown"),
                "timestamp": rec.get("ts", ""),
                "exception_type": etype,
                "exception_message": emsg,
                "traceback": rec["traceback"],
                "frames": frames,
                "signature": make_signature(etype, emsg, frames),
            }
        lat = rec.get("latency_ms")
        if lat is not None and float(lat) > LATENCY_THRESHOLD_MS and rec.get("file") and rec.get("func"):
            frames = [{"file": rec["file"], "line": rec.get("line"), "func": rec["func"]}]
            emsg = f"latency {lat}ms exceeds {LATENCY_THRESHOLD_MS}ms"
            return {
                "id": iid,
                "kind": "performance",
                "service": rec.get("service", "unknown"),
                "timestamp": rec.get("ts", ""),
                "exception_type": "PerformanceBottleneck",
                "exception_message": emsg,
                "traceback": json.dumps(rec),
                "frames": frames,
                "signature": make_signature("PerformanceBottleneck", emsg, frames),
            }
    return None
