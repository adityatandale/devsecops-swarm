"""Fault injector: calls a function in a target repo and logs the crash as structured JSON (like a microservice would)."""
import argparse
import importlib
import json
import sys
import time
import traceback
from pathlib import Path


def simulate(repo, module, call, log_file):
    repo = str(Path(repo).resolve())
    sys.path.insert(0, repo)
    mod = importlib.import_module(module)
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    service = Path(repo).name
    records = [{"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "level": "INFO", "service": service, "msg": "request received"}]
    try:
        eval(call, vars(mod))  # noqa: S307 - deliberate fault injection on demo code
        records.append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "level": "INFO", "service": service, "msg": "ok"})
    except Exception as exc:
        records.append({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "level": "ERROR", "service": service,
            "msg": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(),
        })
    with log_file.open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return records[-1]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="demo_service")
    ap.add_argument("--module", default="app")
    ap.add_argument("--call", default="average_order_value([])")
    ap.add_argument("--log", default="demo_service/logs/app.log")
    a = ap.parse_args()
    print(json.dumps(simulate(a.repo, a.module, a.call, a.log))[:300])
