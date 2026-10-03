"""Shared state passed between LangGraph nodes."""
import time
from typing import Any, Dict, List, TypedDict


class SwarmState(TypedDict, total=False):
    # inputs
    repo: str
    log_file: str
    dry_run: bool
    ignore_seen: bool
    sandbox_mode: str
    # produced by agents
    incident: Dict[str, Any]
    similar_fixes: List[Dict[str, Any]]
    target: Dict[str, Any]
    workdir: str
    patch: Dict[str, Any]
    attempt: int
    attempts: List[Dict[str, Any]]
    test_result: Dict[str, Any]
    pr: Dict[str, Any]
    status: str
    events: List[Dict[str, str]]


def add_event(state: SwarmState, agent: str, msg: str) -> List[Dict[str, str]]:
    """Return a new events list with one more entry (LangGraph merges by replacement)."""
    return list(state.get("events", [])) + [
        {"t": time.strftime("%H:%M:%S"), "agent": agent, "msg": msg}
    ]
