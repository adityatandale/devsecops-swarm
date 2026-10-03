"""LangGraph definition: stateful, event-driven swarm with a self-correcting patch -> test loop."""
import time

from langgraph.graph import END, StateGraph

from .architect import architect_locate
from .config import DRY_RUN_PR, MAX_ATTEMPTS
from .gitops import submit_pr
from .patcher import PatchError, apply_patch, generate_patch, make_workdir
from .sandbox import run_checks
from .sentry import find_incident
from .state import SwarmState, add_event
from .store import load_seen, mark_seen, save_run


def build_graph(memory=None):
    # ---------------- nodes ----------------
    def sentry(state: SwarmState):
        seen = set() if state.get("ignore_seen") else load_seen()
        incident = find_incident(state["log_file"], seen)
        if not incident:
            return {"status": "healthy", "events": add_event(state, "Sentry", "No new incidents in logs.")}
        similar = memory.search(incident["signature"]) if memory else []
        ev = add_event(state, "Sentry", f"Incident {incident['id']} [{incident['kind']}]: {incident['signature']}")
        ev = ev + [{"t": time.strftime("%H:%M:%S"), "agent": "Sentry",
                    "msg": f"Retrieved {len(similar)} similar historical fix(es) from Qdrant"
                           + (f" (best score {similar[0]['score']})" if similar else "")}]
        return {"incident": incident, "similar_fixes": similar, "events": ev,
                "status": "incident_detected", "attempt": 0, "attempts": []}

    def architect(state: SwarmState):
        target = architect_locate(state["repo"], state["incident"])
        if not target:
            return {"status": "unlocalised",
                    "events": add_event(state, "Architect", "Could not map the stack trace to repository code.")}
        msg = (f"Isolated `{target['function']}()` in {target['file']} "
               f"(parser: {target['parser']}); module outline has {len(target['outline'])} symbols.")
        return {"target": target, "events": add_event(state, "Architect", msg), "status": "localised"}

    def patch_engine(state: SwarmState):
        attempt = state.get("attempt", 0) + 1
        workdir = state.get("workdir") or make_workdir(state["repo"])
        attempts = list(state.get("attempts", []))
        prev = None
        if attempts and attempts[-1].get("new_function"):
            prev = {"function": attempts[-1]["new_function"], "output": attempts[-1].get("test_output", "")}
        elif attempts:
            prev = {"function": "(invalid output)", "output": attempts[-1].get("test_output", "")}
        try:
            explanation, new_func = generate_patch(state["incident"], state["target"],
                                                   state.get("similar_fixes", []), prev, attempt)
            patched_text, diff = apply_patch(state["repo"], workdir, state["target"], new_func)
        except PatchError as exc:
            attempts.append({"n": attempt, "new_function": "", "passed": False,
                             "test_output": f"Patch rejected: {exc}"})
            return {"attempt": attempt, "workdir": workdir, "attempts": attempts, "patch": None,
                    "events": add_event(state, "PatchEngine", f"Attempt {attempt}: patch rejected - {exc}")}
        attempts.append({"n": attempt, "new_function": new_func, "diff": diff, "explanation": explanation})
        patch = {"explanation": explanation, "new_function": new_func, "diff": diff, "patched_text": patched_text}
        return {"attempt": attempt, "workdir": workdir, "attempts": attempts, "patch": patch,
                "events": add_event(state, "PatchEngine", f"Attempt {attempt}: generated patch. {explanation}")}

    def sandbox(state: SwarmState):
        attempts = list(state.get("attempts", []))
        if not state.get("patch"):
            res = {"passed": False, "output": attempts[-1]["test_output"], "mode": "n/a"}
            return {"test_result": res, "events": add_event(state, "Sandbox", "Skipped - no valid patch.")}
        res = run_checks(state["workdir"], state.get("sandbox_mode"))
        attempts[-1].update({"passed": res["passed"], "test_output": res["output"][-3000:]})
        verdict = "PASSED" if res["passed"] else "FAILED"
        return {"test_result": res, "attempts": attempts,
                "events": add_event(state, "Sandbox", f"Attempt {state['attempt']} {verdict} ({res['mode']} sandbox).")}

    def open_pr(state: SwarmState):
        dry = state.get("dry_run", DRY_RUN_PR)
        try:
            pr = submit_pr(state, dry_run=dry)
            status = "pr_submitted"
            msg = f"PR {'prepared (dry-run)' if dry else 'opened'}: {pr.get('url') or pr['patch_file']}"
        except Exception as exc:
            pr, status, msg = {"error": str(exc)}, "pr_failed", f"PR submission failed: {exc}"
        if status == "pr_submitted" and memory:
            memory.add_fix(state["incident"]["signature"], state["patch"]["diff"], state["patch"]["explanation"])
            msg += " | fix stored in Qdrant for future incidents."
        return {"pr": pr, "status": status, "events": add_event(state, "GitOps", msg)}

    def escalate(state: SwarmState):
        return {"status": "escalated",
                "events": add_event(state, "Orchestrator",
                                    f"Gave up after {state.get('attempt', 0)} attempts - escalating to a human.")}

    # ---------------- routing ----------------
    def after_sentry(state):
        return "architect" if state.get("incident") else "end"

    def after_architect(state):
        return "patch" if state.get("target") else "end"

    def after_sandbox(state):
        if state["test_result"]["passed"]:
            return "pr"
        return "patch" if state.get("attempt", 0) < MAX_ATTEMPTS else "escalate"

    g = StateGraph(SwarmState)
    for name, fn in [("sentry", sentry), ("architect", architect), ("patch", patch_engine),
                     ("sandbox", sandbox), ("pr", open_pr), ("escalate", escalate)]:
        g.add_node(name, fn)
    g.set_entry_point("sentry")
    g.add_conditional_edges("sentry", after_sentry, {"architect": "architect", "end": END})
    g.add_conditional_edges("architect", after_architect, {"patch": "patch", "end": END})
    g.add_edge("patch", "sandbox")
    g.add_conditional_edges("sandbox", after_sandbox, {"pr": "pr", "patch": "patch", "escalate": "escalate"})
    g.add_edge("pr", END)
    g.add_edge("escalate", END)
    return g.compile()


def run_pipeline(repo, log_file, memory=None, dry_run=None, ignore_seen=False, sandbox_mode=None, save=True):
    app = build_graph(memory)
    init = {"repo": str(repo), "log_file": str(log_file), "ignore_seen": ignore_seen,
            "dry_run": DRY_RUN_PR if dry_run is None else dry_run, "events": [], "attempts": [], "attempt": 0}
    if sandbox_mode:
        init["sandbox_mode"] = sandbox_mode
    final = app.invoke(init)
    if save:
        if final.get("incident") and not ignore_seen:
            mark_seen(final["incident"]["id"])
        save_run(final)
    return final
