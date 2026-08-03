"""Find exception handlers that discard a failure without recording it.

The shape this looks for is the one behind the history bug: a `try` around a
write, a broad `except`, and a body that returns or passes without logging,
counting, or re-raising. The instinct is usually right — a convenience feature
should not be able to interrupt counseling — but *failing open* and *failing
silently* are different decisions, and the code currently makes only one of
them explicitly.

A silent handler is not automatically a defect. `except User.DoesNotExist:
return 404` is control flow, and `except IntegrityError: pass` on a documented
double-tap race is correct. What this module produces is an inventory; the
judgement lives in `docs/qa/silent-failures.md` and in the classification in
`test_no_new_silent_failures.py`.

Stdlib only. No imports of the code being scanned — this parses source, so it
runs with no database, no settings and no services.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = [
    REPO_ROOT / "backend-fastapi" / "app",
    REPO_ROOT / "backend-django" / "apps",
]

SKIP_DIRS = {"__pycache__", "migrations", "venv", ".pytest_cache", "node_modules"}

# Anything that leaves a trace a human or a dashboard could later find.
RECORDING_CALLS = (
    "logger", "log", "logging", "warn", "warning", "error", "exception",
    "critical", "info", "debug", "print", "capture_exception", "capture_message",
    "sentry_sdk", "incr", "increment", "counter", "metric", "statsd", "gauge",
    "observe", "emit",
)

# Attribute/name fragments suggesting the guarded block mutates state.
WRITE_HINTS = (
    "execute", "save", "create", "update", "insert", "commit", "bulk_create",
    "get_or_create", "update_or_create", "delete", "upsert", "publish", "send",
    "write", "setex", "hset", "sadd", "lpush", "expire", "cursor", "conn",
    "objects", "put", "post",
)

BROAD = {"Exception", "BaseException"}


@dataclass(frozen=True)
class Handler:
    file: str
    line: int
    func: str
    exc: str
    is_broad: bool
    guards_write: bool

    @property
    def key(self) -> tuple[str, str, str]:
        """Identity that survives line-number drift.

        Deliberately excludes the line number: a handler that moves because
        something above it grew is the same handler, and a baseline that
        churns on every unrelated edit stops being read.
        """
        return (self.file, self.func, self.exc)


def _names(node: ast.AST) -> list[str]:
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute):
            out.append(n.attr)
        elif isinstance(n, ast.Name):
            out.append(n.id)
    return out


def _records(handler: ast.ExceptHandler) -> bool:
    for n in ast.walk(handler):
        if isinstance(n, ast.Raise):
            return True
        if isinstance(n, ast.Call):
            for name in _names(n.func):
                if any(frag in name.lower() for frag in RECORDING_CALLS):
                    return True
    return False


def _guards_write(node: ast.Try) -> bool:
    names = [n.lower() for stmt in node.body for n in _names(stmt)]
    return any(hint in name for hint in WRITE_HINTS for name in names)


def _enclosing_function(tree: ast.Module, node: ast.AST) -> str:
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.lineno <= node.lineno <= (n.end_lineno or n.lineno):
                if best is None or n.lineno > best.lineno:
                    best = n
    return best.name if best else "<module>"


def _python_files() -> list[Path]:
    out = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                path = Path(dirpath) / name
                if "test" in path.name or f"{os.sep}tests{os.sep}" in str(path):
                    continue
                out.append(path)
    return sorted(out)


def scan() -> list[Handler]:
    """Every exception handler that discards without recording."""
    found: list[Handler] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            guards_write = _guards_write(node)
            for handler in node.handlers:
                if _records(handler):
                    continue
                exc = ast.unparse(handler.type) if handler.type else "BARE"
                found.append(
                    Handler(
                        file=rel,
                        line=handler.lineno,
                        func=_enclosing_function(tree, handler),
                        exc=exc,
                        is_broad=handler.type is None
                        or (isinstance(handler.type, ast.Name) and handler.type.id in BROAD),
                        guards_write=guards_write,
                    )
                )
    return found


def broad_silent_handlers() -> list[Handler]:
    """The subset worth arguing about: broad catches that swallow."""
    return [h for h in scan() if h.is_broad]
