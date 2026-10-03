"""Agent 2 - Architect: deterministic fault localisation with Tree-sitter ASTs (stdlib `ast` fallback)."""
import ast
import textwrap
from pathlib import Path
from typing import Optional


def locate_in_repo(repo: Path, path_str: str) -> Optional[Path]:
    """Map a path from a log (maybe from another machine/container) to a file inside the repo."""
    repo = Path(repo).resolve()
    p = Path(path_str)
    if "site-packages" in path_str or path_str.startswith("<"):
        return None
    if p.is_absolute() and p.exists():
        try:
            p.resolve().relative_to(repo)
            return p.resolve()
        except ValueError:
            return None  # exists locally but outside the repo -> not our code
    parts = p.parts
    for k in range(min(len(parts), 4), 0, -1):
        cand = repo / Path(*parts[-k:])
        if cand.is_file():
            return cand.resolve()
    return None


def _line_starts(b: bytes) -> list:
    starts = [0]
    for line in b.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _ts_find(src: bytes, func: str, line: Optional[int]):
    import tree_sitter_python as tsp
    from tree_sitter import Language, Parser

    parser = Parser(Language(tsp.language()))
    root = parser.parse(src).root_node
    best, stack = None, [root]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            name = n.child_by_field_name("name").text.decode()
            s, e = n.start_point[0] + 1, n.end_point[0] + 1
            if name == func and (line is None or s <= line <= e):
                if best is None or (e - s) < (best.end_point[0] - best.start_point[0]):
                    best = n  # innermost match
        stack.extend(n.children)
    if best is None:
        return None
    return best.start_byte, best.end_byte, best.start_point[1]


def _ast_find(src: bytes, func: str, line: Optional[int]):
    tree = ast.parse(src.decode("utf-8"))
    starts = _line_starts(src)
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func:
            if line is None or n.lineno <= line <= n.end_lineno:
                if best is None or (n.end_lineno - n.lineno) < (best.end_lineno - best.lineno):
                    best = n
    if best is None:
        return None
    s = starts[best.lineno - 1] + best.col_offset
    e = starts[best.end_lineno - 1] + best.end_col_offset
    return s, e, best.col_offset


def file_outline(src: bytes) -> list:
    try:
        tree = ast.parse(src.decode("utf-8"))
    except SyntaxError:
        return []
    out = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(f"def {n.name}(...)  [line {n.lineno}]")
        elif isinstance(n, ast.ClassDef):
            methods = [m.name for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            out.append(f"class {n.name}  methods={methods}  [line {n.lineno}]")
    return out


def extract_function(path: Path, func: str, line: Optional[int]) -> Optional[dict]:
    src = Path(path).read_bytes()
    parser = "tree-sitter"
    try:
        found = _ts_find(src, func, line)
    except Exception:
        found, parser = _ast_find(src, func, line), "python-ast (fallback)"
    if not found:
        return None
    start, end, col = found
    text = src[start:end].decode("utf-8")
    source = textwrap.dedent(" " * col + text)
    return {
        "start_byte": start,
        "end_byte": end,
        "col": col,
        "function": func,
        "source": source,
        "outline": file_outline(src),
        "parser": parser,
    }


def architect_locate(repo, incident: dict) -> Optional[dict]:
    """Walk the stack innermost-first and return the first frame that maps to repo code."""
    repo = Path(repo).resolve()
    for frame in reversed(incident.get("frames", [])):
        if frame["func"] == "<module>":
            continue
        fp = locate_in_repo(repo, frame["file"])
        if not fp:
            continue
        info = extract_function(fp, frame["func"], frame.get("line"))
        if info:
            info.update({"file": str(fp.relative_to(repo)), "line": frame.get("line")})
            return info
    return None
