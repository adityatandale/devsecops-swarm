"""Agent 3a - Patch Engine: asks the local LLM for a fixed function and applies it safely."""
import ast
import difflib
import re
import shutil
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

from .llm import chat

SYSTEM = (
    "You are a senior Python engineer fixing a production bug. "
    "You receive a stack trace and the single function that crashed. "
    "Return the corrected version of THAT FUNCTION ONLY.\n"
    "Rules: keep the exact function name and signature; do not include decorators, imports or other "
    "functions; keep behaviour for valid inputs; handle the failing case explicitly; no explanations "
    "inside the code block.\n"
    "Format: one line starting with 'EXPLANATION:' (root cause + fix, max 2 sentences), "
    "then one ```python code block."
)


class PatchError(Exception):
    pass


def build_prompt(incident: dict, target: dict, similar: list, prev: Optional[dict]) -> str:
    parts = [
        f"Incident type: {incident['kind']}",
        f"Error: {incident['exception_type']}: {incident['exception_message']}",
        f"Stack trace:\n{incident['traceback'][-1800:]}",
        f"File: {target['file']}  (crashed near line {target.get('line')})",
        f"Module outline:\n" + "\n".join(target.get("outline", [])),
        f"Function to fix:\n```python\n{target['source']}\n```",
    ]
    if similar:
        parts.append("Similar fixes applied to past incidents (use as hints, adapt to this code):")
        for s in similar[:2]:
            parts.append(f"- {s.get('explanation', '')}\n{s.get('diff', '')[:600]}")
    if prev:
        parts.append(
            "YOUR PREVIOUS ATTEMPT FAILED VALIDATION.\n"
            f"Previous function:\n```python\n{prev['function']}\n```\n"
            f"Test / security output:\n{prev['output'][-1500:]}\n"
            "Fix the problem and return an improved version."
        )
    return "\n\n".join(parts)


def parse_response(text: str):
    m = re.search(r"EXPLANATION:\s*(.+)", text)
    explanation = m.group(1).strip() if m else "No explanation provided."
    blocks = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.S)
    if not blocks:
        raise PatchError("LLM response contained no code block")
    return explanation, textwrap.dedent(blocks[0]).strip("\n")


def generate_patch(incident, target, similar, prev, attempt):
    try:
        raw = chat(SYSTEM, build_prompt(incident, target, similar, prev), temperature=0.1 + 0.2 * (attempt - 1))
    except Exception as exc:  # connection errors etc.
        raise PatchError(f"LLM call failed: {exc}") from exc
    return parse_response(raw)


def make_workdir(repo) -> str:
    """Ephemeral copy of the repo; the live repo is never modified by the sandbox loop."""
    dst = Path(tempfile.mkdtemp(prefix="swarm_")) / "src"
    shutil.copytree(
        repo,
        dst,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "logs", "*.pyc", "venv", ".venv"),
    )
    return str(dst)


def build_patched_text(repo, target: dict, new_func: str) -> str:
    orig = (Path(repo) / target["file"]).read_bytes()
    new_func = textwrap.dedent(new_func).strip("\n")
    try:
        node = ast.parse(new_func).body[0]
    except (SyntaxError, IndexError) as exc:
        raise PatchError(f"Generated code is not valid Python: {exc}") from exc
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != target["function"]:
        raise PatchError(f"Patch must define exactly function '{target['function']}'")
    lines = new_func.splitlines()
    indent = " " * target["col"]
    body = "\n".join([lines[0]] + [(indent + ln if ln.strip() else ln) for ln in lines[1:]])
    patched = orig[: target["start_byte"]] + body.encode() + orig[target["end_byte"]:]
    text = patched.decode("utf-8")
    try:
        ast.parse(text)
    except SyntaxError as exc:
        raise PatchError(f"Patched file has a syntax error: {exc}") from exc
    return text


def apply_patch(repo, workdir, target: dict, new_func: str):
    """Write patched file into the sandbox workdir; return (patched_text, unified_diff)."""
    patched = build_patched_text(repo, target, new_func)
    orig_text = (Path(repo) / target["file"]).read_text(encoding="utf-8")
    (Path(workdir) / target["file"]).write_text(patched, encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            orig_text.splitlines(True),
            patched.splitlines(True),
            fromfile=f"a/{target['file']}",
            tofile=f"b/{target['file']}",
        )
    )
    return patched, diff
