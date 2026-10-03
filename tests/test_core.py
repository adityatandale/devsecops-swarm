"""Unit + integration tests for the swarm (LLM and Docker are mocked)."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from swarm import patcher  # noqa: E402
from swarm.architect import architect_locate, extract_function  # noqa: E402
from swarm.sentry import find_incident, make_signature, parse_traceback  # noqa: E402

TB = '''Traceback (most recent call last):
  File "/srv/app/main.py", line 9, in <module>
    run()
  File "/srv/app/app.py", line 4, in average_order_value
    return total / len(orders)
ZeroDivisionError: division by zero
'''


def _make_log(tmp: Path, tb: str = TB) -> Path:
    log = tmp / "app.log"
    log.write_text(json.dumps({"level": "INFO", "msg": "hi"}) + "\n"
                   + json.dumps({"level": "ERROR", "service": "demo", "traceback": tb}) + "\nnot json\n")
    return log


def test_parse_traceback():
    frames, etype, emsg = parse_traceback(TB)
    assert etype == "ZeroDivisionError" and emsg == "division by zero"
    assert frames[-1]["func"] == "average_order_value" and frames[-1]["line"] == 4


def test_signature_is_line_number_free():
    frames, etype, emsg = parse_traceback(TB)
    sig = make_signature(etype, emsg, frames)
    assert "average_order_value" in sig and "4" not in sig


def test_find_incident_and_seen():
    tmp = Path(tempfile.mkdtemp())
    inc = find_incident(_make_log(tmp))
    assert inc and inc["kind"] == "crash" and inc["exception_type"] == "ZeroDivisionError"
    assert find_incident(_make_log(tmp), seen={inc["id"]}) is None


def test_architect_maps_foreign_path_and_isolates_function():
    repo = ROOT / "demo_service"
    inc = find_incident(_make_log(Path(tempfile.mkdtemp())))
    target = architect_locate(repo, inc)
    assert target["file"] == "app.py" and target["function"] == "average_order_value"
    assert "def average_order_value" in target["source"] and "apply_discount" not in target["source"]


def test_patch_application_is_exact_and_validated():
    repo = ROOT / "demo_service"
    info = extract_function(repo / "app.py", "average_order_value", None)
    info["file"] = "app.py"
    new = 'def average_order_value(orders):\n    if not orders:\n        return 0.0\n    return sum(o["amount"] for o in orders) / len(orders)\n'
    text = patcher.build_patched_text(repo, info, new)
    assert "if not orders" in text and "def slugify" in text  # neighbours untouched
    with pytest.raises(patcher.PatchError):
        patcher.build_patched_text(repo, info, "def wrong_name(x):\n    return x\n")
    with pytest.raises(patcher.PatchError):
        patcher.build_patched_text(repo, info, "def average_order_value(orders:\n    pass")


def test_parse_llm_response():
    expl, code = patcher.parse_response("EXPLANATION: Guard empty list.\n```python\ndef f():\n    return 1\n```")
    assert expl.startswith("Guard") and code.startswith("def f")


def test_full_pipeline_with_mock_llm(monkeypatch):
    pytest.importorskip("langgraph")
    from swarm import graph

    good = ('EXPLANATION: Empty list divides by zero; return 0.0.\n```python\n'
            'def average_order_value(orders):\n    if not orders:\n        return 0.0\n'
            '    return sum(o["amount"] for o in orders) / len(orders)\n```')
    monkeypatch.setattr(patcher, "chat", lambda *a, **k: good)
    tmp = Path(tempfile.mkdtemp())
    repo = tmp / "svc"
    shutil.copytree(ROOT / "demo_service", repo, ignore=shutil.ignore_patterns("logs", "__pycache__"))
    from swarm.simulate import simulate
    simulate(repo, "app", "average_order_value([])", tmp / "app.log")
    final = graph.run_pipeline(repo, tmp / "app.log", memory=None, dry_run=True, ignore_seen=True,
                               sandbox_mode="local", save=False)
    assert final["status"] == "pr_submitted" and final["attempt"] == 1
