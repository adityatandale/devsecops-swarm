"""Agent 3b - Sandbox Executor: runs tests + security scan in an ephemeral, network-less Docker container."""
import re
import subprocess
import sys

from .config import SANDBOX_IMAGE, SANDBOX_MODE, SANDBOX_TIMEOUT

# Runs pytest, then bandit (HIGH severity only); prints exit codes as markers.
CHECK_CMD = (
    'pytest -q -x -p no:cacheprovider 2>&1; echo "__PYTEST_EXIT=$?"; '
    'bandit -q -r . -x ./tests -lll 2>&1; echo "__BANDIT_EXIT=$?"'
)


def _parse(logs: str, mode: str) -> dict:
    py = re.search(r"__PYTEST_EXIT=(\d+)", logs)
    bd = re.search(r"__BANDIT_EXIT=(\d+)", logs)
    py_code = int(py.group(1)) if py else 99
    bd_code = int(bd.group(1)) if bd else 99
    test_out = logs.split("__PYTEST_EXIT=")[0].strip()
    after = logs.split("__PYTEST_EXIT=", 1)[1] if "__PYTEST_EXIT=" in logs else ""
    sec_out = after.split("\n", 1)[1] if "\n" in after else ""
    sec_out = sec_out.split("__BANDIT_EXIT")[0].strip()
    return {
        "passed": py_code == 0 and bd_code == 0,
        "tests_passed": py_code == 0,
        "security_passed": bd_code == 0,
        "output": test_out + ("\n\n[bandit]\n" + sec_out if bd_code != 0 else ""),
        "security": sec_out or "no high-severity findings",
        "mode": mode,
    }


def _run_docker(workdir: str) -> dict:
    import docker

    client = docker.from_env()
    container = None
    try:
        container = client.containers.run(
            SANDBOX_IMAGE,
            ["sh", "-c", CHECK_CMD],
            detach=True,
            volumes={str(workdir): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            network_mode="none",  # no network inside the sandbox
            mem_limit="512m",
            nano_cpus=1_000_000_000,
            pids_limit=128,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
        )
        try:
            container.wait(timeout=SANDBOX_TIMEOUT)
        except Exception:
            container.kill()
            return {"passed": False, "tests_passed": False, "security_passed": False,
                    "output": f"Sandbox timed out after {SANDBOX_TIMEOUT}s", "security": "", "mode": "docker"}
        logs = container.logs().decode("utf-8", errors="replace")
    finally:
        if container is not None:
            container.remove(force=True)
    return _parse(logs, "docker")


def _run_local(workdir: str) -> dict:
    """Development fallback - NO isolation. Use only on trusted demo code."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
            cwd=workdir, capture_output=True, text=True, timeout=SANDBOX_TIMEOUT,
        )
        out = (r.stdout + r.stderr).strip()
        code = r.returncode
    except subprocess.TimeoutExpired:
        return {"passed": False, "tests_passed": False, "security_passed": False,
                "output": "Local run timed out", "security": "", "mode": "local"}
    return {"passed": code == 0, "tests_passed": code == 0, "security_passed": True,
            "output": out, "security": "skipped in local mode", "mode": "local"}


def run_checks(workdir: str, mode: str = None) -> dict:
    mode = mode or SANDBOX_MODE
    try:
        return _run_docker(workdir) if mode == "docker" else _run_local(workdir)
    except Exception as exc:  # docker daemon down, image missing...
        return {"passed": False, "tests_passed": False, "security_passed": False,
                "output": f"Sandbox error: {exc}", "security": "", "mode": mode}
