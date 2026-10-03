"""CLI for the Self-Healing Autonomous Multi-Agent DevSecOps Engineer."""
import argparse
import time

from swarm.config import DRY_RUN_PR, ROOT


def _memory(disabled=False):
    if disabled:
        return None
    from swarm.vector_store import FixMemory
    return FixMemory()


def cmd_run(a):
    from swarm.graph import run_pipeline
    final = run_pipeline(a.repo, a.log, memory=_memory(a.no_memory), dry_run=False if a.real_pr else DRY_RUN_PR,
                         ignore_seen=a.force, sandbox_mode=a.sandbox)
    for e in final.get("events", []):
        print(f"[{e['t']}] {e['agent']:<12} {e['msg']}")
    print("\nFINAL STATUS:", final.get("status"))
    if final.get("patch"):
        print(final["patch"]["diff"])


def cmd_watch(a):
    from swarm.graph import run_pipeline
    mem = _memory(a.no_memory)
    print(f"Watching {a.log} every {a.interval}s (Ctrl+C to stop)")
    while True:
        final = run_pipeline(a.repo, a.log, memory=mem, dry_run=False if a.real_pr else DRY_RUN_PR, sandbox_mode=a.sandbox)
        if final.get("incident"):
            print(f"Handled incident {final['incident']['id']} -> {final.get('status')}")
        time.sleep(a.interval)


SEED = [
    ("ZeroDivisionError: division by zero @ average", "Empty input made the divisor zero.",
     "-    return total / len(items)\n+    if not items:\n+        return 0.0\n+    return total / len(items)"),
    ("KeyError: 'N' @ get_value", "Missing dictionary key; use .get() with a default.",
     "-    return data[key]\n+    return data.get(key)"),
    ("IndexError: list index out of range @ last_item", "Index beyond list bounds; use -1 and guard empty list.",
     "-    return items[len(items)]\n+    return items[-1] if items else None"),
    ("TypeError: unsupported operand type(s) for +: 'NoneType' and 'str' @ join_names",
     "None value concatenated with str; coerce None to empty string.",
     "-    return a + b\n+    return (a or '') + (b or '')"),
]


def cmd_seed(_):
    mem = _memory()
    for sig, expl, diff in SEED:
        mem.add_fix(sig, diff, expl, source="seed")
    print(f"Seeded {len(SEED)} historical fixes into Qdrant (embedder: {mem.embedder.kind}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", cmd_run), ("watch", cmd_watch)):
        p = sub.add_parser(name)
        p.add_argument("--repo", default=str(ROOT / "demo_service"))
        p.add_argument("--log", default=str(ROOT / "demo_service/logs/app.log"))
        p.add_argument("--sandbox", choices=["docker", "local"], default=None)
        p.add_argument("--no-memory", action="store_true")
        p.add_argument("--real-pr", action="store_true", help="push branch + open GitHub PR (needs GITHUB_TOKEN)")
        if name == "run":
            p.add_argument("--force", action="store_true", help="re-process already handled incidents")
        else:
            p.add_argument("--interval", type=int, default=10)
        p.set_defaults(func=fn)
    sub.add_parser("seed").set_defaults(func=cmd_seed)
    args = ap.parse_args()
    args.func(args)
